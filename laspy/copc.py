import io
import multiprocessing
import os
import struct
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from math import ceil, log2
from operator import attrgetter
from queue import Queue, SimpleQueue
from threading import Thread
from typing import Dict, Iterator, List, Optional, Tuple, Union

try:
    import requests
except ModuleNotFoundError:
    requests = None
else:
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry


try:
    import lazrs
except ModuleNotFoundError:
    lazrs = None

import numpy as np

from .compression import DecompressionSelection
from .errors import LaspyException, LazError
from .header import LasHeader
from .point.record import PackedPointRecord, ScaleAwarePointRecord
from .vlrs.known import BaseKnownVLR

DEFAULT_HTTP_WORKERS_NUM = multiprocessing.cpu_count() * 5


def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# Multi-Range bytes are a thing, and could be used to query
# all needed chunks in one request, however it does not seems well supported by servers
# (eg AWS S3) so we don't try to use it
#
# We could try to test if the server support multi range bytes
# https://docs.python-requests.org/en/latest/user/advanced/#body-content-workflow


class HttpRangeStream:
    """
    class used to mimic file-object interface for HTTP endpoints.

    This works by using Range-Requests.
    """

    def __init__(self, url: str) -> None:
        if requests is None:
            raise LaspyException(
                "HTTP support requires the 'requests' package to be installed"
            )
        self.url = url
        self.range_start = 0
        self.session = requests_retry_session()

    def seek(self, pos, whence=io.SEEK_SET):
        if whence != io.SEEK_SET:
            raise RuntimeError("Only SEEK_SET is supported")

        if pos < 0:
            raise RuntimeError("pos must be >= 0")

        self.range_start = pos

    def read(self, n) -> bytes:
        if n == 0:
            return b""

        range_end = self.range_start + n - 1
        headers = {"Range": f"bytes={self.range_start}-{range_end}"}

        r = self.session.get(self.url, headers=headers)

        r.raise_for_status()

        self.range_start += n

        return r.content

    def tell(self) -> int:
        return self.range_start

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()


class CopcInfoVlr(BaseKnownVLR):
    def __init__(self):
        super().__init__()

        # Actual (unscaled) coordinate of the center of the octree
        self.center = np.zeros(3, dtype=np.float64)

        # Perpendicular distance from the center to any side of the root node.
        self.halfsize = 0.0

        # Space between points at the root node.
        # This value is halved at each octree level
        self.spacing = 0.0

        # Where to find the first hierarchy page in the file
        self.hierarchy_root_offset = 0

        # The `page_size` of the root page
        self.hierarchy_root_size = 0

        self.gps_min = 0.0
        self.gps_max = 0.0

    @staticmethod
    def official_user_id():
        return "copc"

    @staticmethod
    def official_record_ids():
        return (1,)

    def record_data_bytes(self):
        raise NotImplementedError("Writing COPC is not supported")

    def parse_record_data(self, record_data_bytes: bytes):
        stream = io.BytesIO(record_data_bytes)
        for i in range(3):
            self.center[i] = struct.unpack("<d", stream.read(8))[0]

        self.halfsize = struct.unpack("<d", stream.read(8))[0]
        self.spacing = struct.unpack("<d", stream.read(8))[0]

        self.hierarchy_root_offset = struct.unpack("<Q", stream.read(8))[0]
        self.hierarchy_root_size = struct.unpack("<Q", stream.read(8))[0]

        self.gps_min = struct.unpack("<d", stream.read(8))[0]
        self.gps_max = struct.unpack("<d", stream.read(8))[0]


@dataclass
class Bounds:
    mins: np.ndarray
    maxs: np.ndarray

    def overlaps(self, other: "Bounds") -> bool:
        return bool(np.all((self.mins <= other.maxs) & (self.maxs >= other.mins)))

    def ensure_3d(self, mins: np.ndarray, maxs: np.ndarray) -> "Bounds":
        new_mins = np.zeros(3, dtype=np.float64)
        new_maxs = np.zeros(3, dtype=np.float64)

        new_mins[: len(self.mins)] = self.mins[:]
        new_mins[len(self.mins) :] = mins[len(self.mins) :]
        new_maxs[: len(self.maxs)] = self.maxs[:]
        new_maxs[len(self.maxs) :] = maxs[len(self.maxs) :]

        return Bounds(new_mins, new_maxs)


class VoxelKey:
    """
    Represents the `VoxelKey` struct of the COPC Specification
    """

    __slots__ = ["level", "x", "y", "z"]
    unpacker = struct.Struct("<iiii")

    def __init__(self) -> None:
        # <0 means invalid
        self.level = -1
        self.x = 0
        self.y = 0
        self.z = 0

    @classmethod
    def from_bytes(cls, data: bytes):
        key = cls()
        key.level, key.x, key.y, key.z = cls.unpacker.unpack(data)
        return key

    def child(self, dir: int) -> "VoxelKey":
        key = VoxelKey()
        key.level = self.level + 1
        key.x = (self.x << 1) | (dir & 0x1)
        key.y = (self.y << 1) | ((dir >> 1) & 0x1)
        key.z = (self.z << 1) | ((dir >> 2) & 0x1)
        return key

    def childs(self) -> Iterator["VoxelKey"]:
        return (self.child(i) for i in range(8))

    def bounds(self, root_bounds: Bounds) -> Bounds:
        # In an octree every cell is a cube
        side_size = (root_bounds.maxs[0] - root_bounds.mins[0]) / 2**self.level
        mins = root_bounds.mins + (np.array([self.x, self.y, self.z]) * side_size)
        maxs = root_bounds.mins + (
            np.array([self.x + 1, self.y + 1, self.z + 1]) * side_size
        )

        return Bounds(mins, maxs)

    def __hash__(self):
        return hash((self.level, self.x, self.y, self.z))

    def __eq__(self, other: "VoxelKey") -> bool:
        return (
            self.level == other.level
            and self.x == other.x
            and self.y == other.y
            and self.z == other.z
        )

    def __repr__(self) -> str:
        return f"VoxelKey(level={self.level}, x={self.x}, y={self.y}, z={self.z})"


class Entry:
    """
    Represents the `Entry` struct of the COPC Specification
    """

    __slots__ = ("key", "offset", "byte_size", "point_count")

    unpacker = struct.Struct("<Qii")

    def __init__(self) -> None:
        self.key = VoxelKey()
        # if point count > 0, offset to LAZ chunk
        # elif point count == -1, offset to a child hierarchy page
        # elif point count == 0, 0
        self.offset = 0

        # if point count > 0, size of the LAZ chunk
        # elif point count == -1, size of the hierarchy page
        # elif point count == 0, 0
        self.byte_size = 0

        # if > 0, number of points in the chunk
        # if == -1, the info for this entry is in another page (see offset)
        # 0 no point data exists for this key
        self.point_count = 0

    @classmethod
    def from_bytes(cls, data: bytes) -> "Entry":
        entry = cls()

        key_bytes, rest = data[: VoxelKey.unpacker.size], data[VoxelKey.unpacker.size :]
        entry.key = VoxelKey.from_bytes(key_bytes)
        entry.offset, entry.byte_size, entry.point_count = cls.unpacker.unpack(rest)

        return entry

    def __repr__(self) -> str:
        return f"Entry(key={self.key}, offset={self.offset}, byte_size={self.byte_size}, point_count={self.point_count})"


class HierarchyPage:
    """
    Represents the `HierarchyPage` struct of the COPC Specification
    """

    def __init__(self) -> None:
        self.entries: Dict[VoxelKey, Entry] = {}

    @classmethod
    def from_bytes(cls, data: bytes) -> "HierarchyPage":
        page = cls()

        entry_size = Entry.unpacker.size + VoxelKey.unpacker.size
        num_entries = len(data) // entry_size

        for i in range(num_entries):
            entry_bytes = data[i * entry_size : (i + 1) * entry_size]
            entry = Entry.from_bytes(entry_bytes)
            page.entries[entry.key] = entry
        return page


class CopcHierarchyVlr(BaseKnownVLR):
    """ "
    Hierarchy VLR from COPC Specification
    """

    def __init__(self) -> None:
        super().__init__()
        self.data: bytes = b""
        self.root_page = HierarchyPage()

    @staticmethod
    def official_user_id():
        return "copc"

    @staticmethod
    def official_record_ids():
        return (1000,)

    def record_data_bytes(self):
        raise NotImplementedError("Writing COPC is not supported")

    def parse_record_data(self, record_data_bytes: bytes):
        # We just save the bytes as to parse them we need some
        # info from the CopcInfoVlr
        self.bytes = record_data_bytes


class OctreeNode:
    """Our 'custom' type to build an octree from COPC hierarchy page"""

    def __init__(self) -> None:
        self.key = VoxelKey()
        # The bounds this node represents, in file's coordinate
        self.bounds = Bounds(np.zeros(3), np.zeros(3))
        # Offset to start of corresponding LAZ chunk for this node
        self.offset = 0
        # Number of bytes the corresponding LAZ chunk has
        self.byte_size = 0
        # Number of LAS points contained in this node
        self.point_count = 0
        # Childs of this node, since its an octree, there
        # are at most 8 childs
        self.childs: List[OctreeNode] = []

    def remove_child(self, child: "OctreeNode") -> None:
        idx = self.childs.index(child)
        del self.childs[idx]

    def __repr__(self) -> str:
        return f"OctreeNode(key={self.key})"


def load_octree_for_query(
    source,
    info: CopcInfoVlr,
    hierarchy_page: HierarchyPage,
    query_bounds: Optional[Bounds] = None,
    level_range: Optional[range] = None,
) -> List[OctreeNode]:
    """
    Loads the nodes of the COPC octree from the `source` that
    satisfies the parameters `query_bounds` and `level_range`.

    It returns the root node of the loaded 'sub-octree'
    """
    root_bounds = Bounds(
        mins=info.center - info.halfsize,
        maxs=info.center + info.halfsize,
    )

    root_node = OctreeNode()
    root_node.key.level = 0

    satisfying_nodes = []
    nodes_to_load: List[OctreeNode] = [root_node]
    while nodes_to_load:
        current_node = nodes_to_load.pop()
        current_node.bounds = current_node.key.bounds(root_bounds)

        is_in_bounds = query_bounds is None or current_node.bounds.overlaps(
            query_bounds
        )

        if not is_in_bounds:
            continue

        if level_range is not None and current_node.key.level >= level_range.stop:
            continue

        try:
            entry = hierarchy_page.entries[current_node.key]
        except KeyError:
            continue

        # get the info of the node
        if entry.point_count == -1:
            source.seek(entry.offset)
            page_bytes = source.read(entry.byte_size)
            page = HierarchyPage.from_bytes(page_bytes)
            hierarchy_page.entries.update(page.entries)
            nodes_to_load.insert(0, current_node)
            continue
        elif entry.point_count != 0:
            current_node.offset = entry.offset
            current_node.byte_size = entry.byte_size
            current_node.point_count = entry.point_count

            for child_key in current_node.key.childs():
                child_node = OctreeNode()
                child_node.key = child_key
                current_node.childs.append(child_node)
                nodes_to_load.append(child_node)

        is_in_level = level_range is None or current_node.key.level in level_range
        if is_in_level:
            satisfying_nodes.append(current_node)

    return satisfying_nodes


class ChunkIter:
    """
    Simple iterator that returns slices to chunks of byte.
    """

    def __init__(self, buffer: bytearray):
        self.buffer = memoryview(buffer)

    def next(self, size: int):
        slc = self.buffer[:size]
        self.buffer = self.buffer[size:]
        return slc


class HttpFetcherThread(Thread):
    def __init__(self, url: str, query_queue: Queue, result_queue: SimpleQueue) -> None:
        super().__init__()
        self.url = url
        self.query_queue = query_queue
        self.result_queue = result_queue

    def run(self) -> None:
        with HttpRangeStream(self.url) as http_reader:
            while not self.query_queue.empty():
                offset, size = self.query_queue.get()
                try:
                    http_reader.seek(offset)
                    data = http_reader.read(size)
                    self.result_queue.put((data, offset))
                except Exception as e:
                    self.result_queue.put(e)
                finally:
                    self.query_queue.task_done()


def http_queue_strategy(
    source: HttpRangeStream,
    byte_queries: List[Tuple[int, int]],
    out_compressed_bytes: bytearray,
    num_threads: int,
) -> None:
    query_queue = Queue()
    result_queue = SimpleQueue()

    for query in byte_queries:
        query_queue.put(query)

    for _ in range(min(len(byte_queries), num_threads)):
        HttpFetcherThread(source.url, query_queue, result_queue).start()

    query_queue.join()

    results = []
    while not result_queue.empty():
        result = result_queue.get()
        if isinstance(result, Exception):
            raise result
        results.append(result)
    results.sort(key=lambda x: x[1])

    citer = ChunkIter(out_compressed_bytes)
    for group_bytes, _ in results:
        cc = citer.next(len(group_bytes))
        cc[:] = group_bytes


def http_thread_executor_strategy(
    source: HttpRangeStream,
    byte_queries: List[Tuple[int, int]],
    out_compressed_bytes: bytearray,
    num_threads: int,
) -> None:

    # HTTP queries are more of a bottle neck
    # so we want to fetch multiple chunks at the same time
    with ThreadPoolExecutor(max_workers=num_threads) as downloader_pool:

        def fetch_data_job(source, offset, size):
            source.seek(offset)
            return source.read(size)

        jobs = []
        for offset, size in byte_queries:
            jobs.append(
                downloader_pool.submit(
                    fetch_data_job,
                    HttpRangeStream(source.url),
                    offset,
                    size,
                )
            )

        # results = [future.result() for future in concurrent.futures.as_completed(jobs)]
        # results.sort(key=lambda x: x[1])
        # for group_bytes, _ in results:
        #     cc = citer.next(len(group_bytes))
        #     cc[:] = np.frombuffer(group_bytes, np.uint8)

        # We don't use concurrent.futures.as_completed
        # as we need to keep the order
        citer = ChunkIter(out_compressed_bytes)
        for future in jobs:
            group_bytes = future.result()
            cc = citer.next(len(group_bytes))
            cc[:] = group_bytes


class CopcReader:
    """
    Class allowing to do queries over a `COPC`_ LAZ

    In short, COPC files are LAZ 1.4 files organized in a particular way
    (Octree) making it possible to do spatial queries
    as well as queries with a level of details.

    CopcReader **requires** the ``lazrz`` backend to work.

    Optionaly, if ``requests`` is installed, CopcReader can handle
    Copc files that are on a remote HTTP server

    This class *only* reads COPC files, it does not support normal
    LAS/LAZ files.

    To create an instance of it you'll likely
    want to use the :meth:`.CopcReader.open` constructor


    .. versionadded:: 2.2

    .. _COPC: https://github.com/copcio/copcio.github.io
    """

    def __init__(
        self,
        stream,
        close_fd: bool = True,
        http_num_threads: int = DEFAULT_HTTP_WORKERS_NUM,
        _http_strategy: str = "queue",
        decompression_selection: DecompressionSelection = DecompressionSelection.all(),
    ):
        """
        Creates a CopcReader.

        Parameters
        ---------

        stream: the stream from where data can be read.
                It must have the following file object methods:
                read, seek, tell

        http_num_threads: int, optional, default num cpu * 5
            Number of worker threads to do concurent HTTP requests,
            ignored when reading non-HTTP file

        close_fd: optional, default bool
            Whether the stream/file object shall be closed, this only work
            when using the CopcReader in a with statement.

        decompression_selection: DecompressionSelection,
            see :func:`laspy.open`



        .. versionadded:: 2.4
            The ``decompression_selection`` parameter.
        """
        if lazrs is None:
            raise LazError("COPC support requires the 'lazrs' backend")
        self.source = stream
        self.close_fd = close_fd
        self.http_num_threads = http_num_threads
        self.http_strategy = _http_strategy
        self.decompression_selection: lazrs.DecompressionSelection = (
            decompression_selection.to_lazrs()
        )

        self.header = LasHeader.read_from(self.source)

        self.copc_info: CopcInfoVlr = self.header.vlrs[0]
        if not isinstance(self.copc_info, CopcInfoVlr):
            copc_info_exists = any(
                isinstance(vlr, CopcInfoVlr) for vlr in self.header.vlrs
            )
            if copc_info_exists:
                raise LaspyException(
                    "This file is not a valid COPC, "
                    "it does have a COPC VLR, however it is not the first VLR "
                    "as it should"
                )
            else:
                raise LaspyException(
                    "This file is not a valid COPC, " "it does not have a COPC VLR"
                )

        if self.copc_info.hierarchy_root_offset < self.header.offset_to_point_data:
            self.hierarchy = self.header.vlrs.extract("CopcHierarchyVlr")[0]
        else:
            # TODO maybe we could read the whole EVLR's byte
            # so we could load the octree without having any more requests to do
            # since everything would be in memory
            self.source.seek(self.copc_info.hierarchy_root_offset)
            # This only contains the record_data_bytes
            root_hierarchy_vlr_bytes = self.source.read(
                self.copc_info.hierarchy_root_size
            )
            hierarchy = CopcHierarchyVlr()
            hierarchy.parse_record_data(root_hierarchy_vlr_bytes)

        self.laszip_vlr = self.header.vlrs.pop(self.header.vlrs.index("LasZipVlr"))

        self.source.seek(self.copc_info.hierarchy_root_offset)
        root_page_bytes = self.source.read(self.copc_info.hierarchy_root_size)
        # At first the hierary only contains the root page entries
        # but it will get updated as the queries may need more pages
        self.root_page = HierarchyPage.from_bytes(root_page_bytes)

    @classmethod
    def open(
        cls,
        source: Union[str, os.PathLike, io.IOBase],
        http_num_threads: int = DEFAULT_HTTP_WORKERS_NUM,
        _http_strategy: str = "queue",
        decompression_selection: DecompressionSelection = DecompressionSelection.all(),
    ) -> "CopcReader":
        """
        Opens the COPC file.


        Parameters
        ----------
        source: str, io.IOBase, uri or file-like object of the COPC file.
            Supported sources are:

                - 'local' files accesible with a path.
                - HTTP / HTTPS endpoints. The pyhon package ``requests`` is
                  required in order to be able to work with HTTP endpoints.
                - file-like objects, e.g. fsspec io.IOBase objects.

        http_num_threads: int, optional, default num cpu * 5
            Number of worker threads to do concurent HTTP requests,
            ignored when reading non-HTTP file

        decompression_selection: DecompressionSelection,
            see :func:`laspy.open`


        Opening a local file

        .. code-block:: Python

            from laspy import CopcReader

            with CopcReader.open("some_file.laz") as reader:
                ...

        Opening a file on a remite HTTP server
        (``requests`` package required)

        .. code-block:: Python

            from laspy import CopcReader

            url = "https://s3.amazonaws.com/hobu-lidar/autzen-classified.copc.laz"
            with CopcReader.open(url) as reader:
                ...



        .. versionadded:: 2.4
            The ``decompression_selection`` parameter.
        """
        if isinstance(source, (str, os.PathLike)):
            source = str(source)
            if source.startswith("http"):
                source = HttpRangeStream(source)
            else:
                source = open(source, mode="rb")

        return cls(
            source,
            http_num_threads=http_num_threads,
            decompression_selection=decompression_selection,
        )

    def query(
        self,
        bounds: Optional[Bounds] = None,
        resolution: Optional[Union[float, int]] = None,
        level: Optional[Union[int, range]] = None,
    ) -> ScaleAwarePointRecord:
        """ "
        Query the COPC file to retrieve the points matching the
        requested bounds and level.

        Parameters
        ----------
        bounds: Bounds, optional, default None
                The bounds for which you wish to aquire points.
                If None, the whole file's bounds will be considered
                2D bounds are suported, (No point will be filtered on its Z coordinate)

        resolution: float or int, optional, default None
                Limits the octree levels to be queried in order to have
                a point cloud with the requested resolution.

                - The unit is the one of the data.

                - If None, the resulting cloud will be at the
                  full resolution offered by the COPC source

                - Mutually exclusive with level parameter

        level: int or range, optional, default None
               The level of detail (LOD).

               - If None, all LOD are going to be considered
               - If it is an int, only points that are of the requested LOD
                 will be returned.
               - If it is a range, points for which the LOD is within the range
                 will be returned
        """

        if resolution is not None and level is not None:
            raise ValueError("Cannot specify both level and resolution")
        elif resolution is not None and level is None:
            level_max = max(1, ceil(log2(self.copc_info.spacing / resolution)) + 1)
            level = range(0, level_max)

        if isinstance(level, int):
            level = range(level, level + 1)

        if bounds is not None:
            bounds = bounds.ensure_3d(self.header.mins, self.header.maxs)

        nodes = load_octree_for_query(
            self.source,
            self.copc_info,
            self.root_page,
            query_bounds=bounds,
            level_range=level,
        )
        # print("num nodes to query:", len(nodes));
        points = self._fetch_and_decrompress_points_of_nodes(nodes)

        if bounds is not None:
            MINS = np.round(
                (bounds.mins - self.header.offsets) / self.header.scales
            ).astype(np.int32)
            MAXS = np.round(
                (bounds.maxs - self.header.offsets) / self.header.scales
            ).astype(np.int32)
            x_keep = (MINS[0] <= points.X) & (points.X <= MAXS[0])
            y_keep = (MINS[1] <= points.Y) & (points.Y <= MAXS[1])
            z_keep = (MINS[2] <= points.Z) & (points.Z <= MAXS[2])

            # using scaled coordinates
            # x, y, z = np.array(points.x), np.array(points.y), np.array(points.z)
            # x_keep = (bounds.mins[0] <= x) & (x <= bounds.maxs[0])
            # y_keep = (bounds.mins[1] <= y) & (y <= bounds.maxs[1])
            # z_keep = (bounds.mins[2] <= z) & (z <= bounds.maxs[2])

            keep_mask = x_keep & y_keep & z_keep
            points.array = points.array[keep_mask].copy()
        return points

    def spatial_query(self, bounds: Bounds) -> ScaleAwarePointRecord:
        return self.query(bounds=bounds, level=None)

    def level_query(self, level: Union[int, range]) -> ScaleAwarePointRecord:
        return self.query(bounds=None, level=level)

    def _fetch_and_decrompress_points_of_nodes(
        self, nodes_to_read: List[OctreeNode]
    ) -> ScaleAwarePointRecord:
        if not nodes_to_read:
            return ScaleAwarePointRecord.empty(header=self.header)

        # Group together contiguous nodes
        # so that we minimize the number of
        # read requests (seek + read) / http requests
        nodes_to_read = sorted(nodes_to_read, key=attrgetter("offset"))
        grouped_nodes: List[List[OctreeNode]] = []
        current_group: List[OctreeNode] = []
        last_node_end = nodes_to_read[0].offset
        for node in nodes_to_read:
            if node.offset == last_node_end:
                current_group.append(node)
                last_node_end += node.byte_size
            else:
                grouped_nodes.append(current_group)
                current_group = [node]
                last_node_end = node.offset + node.byte_size
        if current_group:
            grouped_nodes.append(current_group)

        compressed_bytes, num_points, chunk_table = self._fetch_all_chunks(
            grouped_nodes
        )
        points_array = np.zeros(
            num_points * self.header.point_format.size, dtype=np.uint8
        )

        lazrs.decompress_points_with_chunk_table(
            compressed_bytes,
            self.laszip_vlr.record_data,
            points_array,
            chunk_table,
            self.decompression_selection,
        )
        r = PackedPointRecord.from_buffer(points_array, self.header.point_format)
        points = ScaleAwarePointRecord(
            r.array, r.point_format, self.header.scales, self.header.offsets
        )

        return points

    def _fetch_all_chunks(
        self, grouped_nodes: List[List[OctreeNode]]
    ) -> Tuple[bytearray, int, List[Tuple[int, int]]]:

        num_points = 0
        num_compressed_bytes = 0
        chunk_table: List[Tuple[int, int]] = []
        byte_queries: List[Tuple[int, int]] = []
        for group in grouped_nodes:
            num_compressed_group_bytes = 0
            for node in group:
                chunk_table.append((node.point_count, node.byte_size))
                num_compressed_group_bytes += node.byte_size
                num_points += node.point_count

            num_compressed_bytes += num_compressed_group_bytes
            byte_queries.append((group[0].offset, num_compressed_group_bytes))

        compressed_bytes = bytearray(num_compressed_bytes)

        if isinstance(self.source, HttpRangeStream):
            if self.http_strategy == "queue":
                http_queue_strategy(
                    self.source, byte_queries, compressed_bytes, self.http_num_threads
                )
            else:
                http_thread_executor_strategy(
                    self.source, byte_queries, compressed_bytes, self.http_num_threads
                )

        elif hasattr(self.source, "readinto"):
            citer = ChunkIter(compressed_bytes)
            for offset, size in byte_queries:
                self.source.seek(offset)
                cc = citer.next(size)
                self.source.readinto(cc)
        else:
            citer = ChunkIter(compressed_bytes)
            for offset, size in byte_queries:
                self.source.seek(offset)
                cc = citer.next(size)
                cc[:] = self.source.read(size)

        return compressed_bytes, num_points, chunk_table

    def __enter__(self) -> "CopcReader":
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        if self.close_fd:
            self.source.close()
