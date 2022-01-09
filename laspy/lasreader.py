import abc
import io
import logging
from typing import Optional, BinaryIO, Iterable, Union

from . import errors
from .compression import LazBackend
from .header import LasHeader
from .lasdata import LasData
from .point import record
from .vlrs.known import LasZipVlr
from .vlrs.vlrlist import VLRList

try:
    import lazrs
except ModuleNotFoundError:
    pass

try:
    import laszip
except ModuleNotFoundError:
    pass

logger = logging.getLogger(__name__)


class LasReader:
    """The reader class handles LAS and LAZ via one of the supported backend"""

    def __init__(
        self,
        source: BinaryIO,
        closefd: bool = True,
        laz_backend: Optional[Union[LazBackend, Iterable[LazBackend]]] = None,
    ):
        """
        Initialize the LasReader

        Parameters
        ----------
        source: file_object
        closefd: bool, default True
        laz_backend: LazBackend or list of LazBackend, optional
        """
        self.closefd = closefd
        if laz_backend is None:
            laz_backend = LazBackend.detect_available()
        self.laz_backend = laz_backend
        self.header = LasHeader.read_from(source)

        if self.header.point_count > 0:
            if self.header.are_points_compressed:
                self.point_source = self._create_laz_backend(source)
                if self.point_source is None:
                    raise errors.LaspyException(
                        "Data is compressed, but no LazBacked could be initialized"
                    )
            else:
                self.point_source = UncompressedPointReader(source, self.header)
        else:
            self.point_source = EmptyPointReader()

        self.points_read = 0

    def read_points(self, n: int) -> record.ScaleAwarePointRecord:
        """Read n points from the file


        Will only read as many points as the header advertise.
        That is, if you ask to read 50 points and there are only 45 points left
        this function will only read 45 points.

        If there are no points left to read, returns an empty point record.

        Parameters
        ----------
        n: The number of points to read
           if n is less than 0, this function will read the remaining points
        """
        points_left = self.header.point_count - self.points_read
        if points_left <= 0:
            return record.ScaleAwarePointRecord.empty(
                self.header.point_format,
                self.header.scales,
                self.header.offsets,
            )

        if n < 0:
            n = points_left
        else:
            n = min(n, points_left)

        r = record.PackedPointRecord.from_buffer(
            self.point_source.read_n_points(n), self.header.point_format
        )
        if len(r) < n:
            logger.error(f"Could only read {len(r)} of the requested {n} points")

        points = record.ScaleAwarePointRecord(
            r.array, r.point_format, self.header.scales, self.header.offsets
        )

        self.points_read += n
        return points

    def read(self) -> LasData:
        """Reads all the points not read and returns a LasData object"""
        points = self.read_points(-1)
        las_data = LasData(header=self.header, points=points)

        if self.header.version.minor >= 4:
            if (
                self.header.are_points_compressed
                and not self.point_source.source.seekable()
            ):
                # We explicitly require seekable stream because we have to seek
                # past the chunk table of LAZ file
                raise errors.LaspyException(
                    "source must be seekable, to read evlrs form LAZ file"
                )
            self.point_source.source.seek(self.header.start_of_first_evlr, io.SEEK_SET)
            las_data.evlrs = self._read_evlrs(self.point_source.source, seekable=True)

        return las_data

    def seek(self, pos: int, whence: int = io.SEEK_SET) -> int:
        """Seeks to the start of the point at the given pos

        Parameters
        ----------
        pos: index of the point to seek to
        whence: optional, controls how the pos parameter is interpreted:
                io.SEEK_SET: (default) pos is the index of the point from the beginning
                io.SEEK_CUR: pos is the point_index relative to the point_index of the last point read
                io.SEEK_END: pos is the point_index relative to last point
        Returns
        -------
        The index of the point the reader seeked to, relative to the first point
        """
        if whence == io.SEEK_SET:
            allowed_range = range(0, self.header.point_count)
            point_index = pos
        elif whence == io.SEEK_CUR:
            allowed_range = range(
                -self.points_read, self.header.point_count - self.points_read
            )
            point_index = self.points_read + pos
        elif whence == io.SEEK_END:
            allowed_range = range(-self.header.point_count, 0)
            point_index = self.header.point_count + pos
        else:
            raise ValueError(f"Invalid value for whence: {whence}")

        if pos not in allowed_range:
            whence_str = ["start", "current point", "end"]
            raise IndexError(
                f"When seeking from the {whence_str[whence]}, pos must be in {allowed_range}"
            )

        self.point_source.seek(point_index)
        self.points_read = point_index
        return point_index

    def chunk_iterator(self, points_per_iteration: int) -> "PointChunkIterator":
        """Returns an iterator, that will read points by chunks
        of the requested size

        :param points_per_iteration: number of points to be read with each iteration
        :return:
        """
        return PointChunkIterator(self, points_per_iteration)

    def close(self) -> None:
        """closes the file object used by the reader"""
        if self.closefd:
            self.point_source.close()

    def _create_laz_backend(self, source) -> Optional["IPointReader"]:
        """Creates the laz backend to use according to `self.laz_backend`.

        If `self.laz_backend` contains mutilple backends, this functions will
        try to create them in order until one of them is successfully constructed.

        If none could be constructed, the error of the last backend tried wil be raised
        """
        if not self.laz_backend:
            raise errors.LaspyException(
                "No LazBackend selected, cannot decompress data"
            )

        try:
            backends = iter(self.laz_backend)
        except TypeError:
            backends = (self.laz_backend,)

        laszip_vlr = self.header.vlrs.pop(self.header.vlrs.index("LasZipVlr"))
        last_error = None
        for backend in backends:
            try:
                if not backend.is_available():
                    raise errors.LaspyException(f"The '{backend}' is not available")

                if backend == LazBackend.LazrsParallel:
                    return LazrsPointReader(source, laszip_vlr, parallel=True)
                elif backend == LazBackend.Lazrs:
                    return LazrsPointReader(source, laszip_vlr, parallel=False)
                elif backend == LazBackend.Laszip:
                    return LaszipPointReader(source, self.header)
                else:
                    raise errors.LaspyException(
                        "Unknown LazBackend: {}".format(backend)
                    )

            except Exception as e:
                last_error = e
                logger.error(e)

        raise last_error

    def _read_evlrs(self, source, seekable=False) -> Optional[VLRList]:
        """Reads the EVLRs of the file, will fail if the file version
        does not support evlrs
        """
        if (
            self.header.version.minor >= 4
            and self.points_read == self.header.point_count
        ):
            if seekable:
                source.seek(self.header.start_of_first_evlr)
            return VLRList.read_from(source, self.header.number_of_evlrs, extended=True)
        else:
            return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class PointChunkIterator:
    def __init__(self, reader: LasReader, points_per_iteration: int) -> None:
        self.reader = reader
        self.points_per_iteration = points_per_iteration

    def __next__(self) -> record.ScaleAwarePointRecord:
        points = self.reader.read_points(self.points_per_iteration)
        if not points:
            raise StopIteration
        return points

    def __iter__(self) -> "PointChunkIterator":
        return self


class IPointReader(abc.ABC):
    """The interface to be implemented by the class that actually reads
    points from as LAS/LAZ file so that the LasReader can use it.

    It is used to manipulate LAS/LAZ (with different LAZ backends) in the
    reader
    """

    @abc.abstractmethod
    def read_n_points(self, n: int) -> bytearray:
        ...

    @abc.abstractmethod
    def seek(self, point_index: int) -> None:
        ...

    @abc.abstractmethod
    def close(self) -> None:
        ...


class UncompressedPointReader(IPointReader):
    """Implementation of IPointReader for the simple uncompressed case"""

    def __init__(self, source, header: LasHeader) -> None:
        self.source = source
        self.header = header

    def read_n_points(self, n: int) -> bytearray:
        try:
            readinto = self.source.readinto
        except AttributeError:
            data = bytearray(self.source.read(n * self.header.point_format.size))
        else:
            data = bytearray(n * self.header.point_format.size)
            num_read = readinto(data)
            if num_read < len(data):
                data = data[:num_read]

        return data

    def seek(self, point_index: int) -> None:
        self.source.seek(
            self.header.offset_to_point_data
            + (point_index * self.header.point_format.size)
        )

    def close(self):
        self.source.close()


class LaszipPointReader(IPointReader):
    """Implementation for the laszip backend"""

    def __init__(self, source: BinaryIO, header: LasHeader) -> None:
        self.source = source
        self.source.seek(0)
        self.unzipper = laszip.LasUnZipper(source)
        unzipper_header = self.unzipper.header
        assert unzipper_header.point_data_format == header.point_format.id
        assert unzipper_header.point_data_record_length == header.point_format.size
        self.point_size = header.point_format.size

    def read_n_points(self, n: int) -> bytearray:
        points_data = bytearray(n * self.point_size)
        self.unzipper.decompress_into(points_data)
        return points_data

    def seek(self, point_index: int) -> None:
        self.unzipper.seek(point_index)

    def close(self) -> None:
        self.source.close()


class LazrsPointReader(IPointReader):
    """Implementation for the laz-rs backend, supports single-threaded decompression
    as well as multi-threaded decompression
    """

    def __init__(self, source, laszip_vlr: LasZipVlr, parallel: bool) -> None:
        self.source = source
        self.vlr = lazrs.LazVlr(laszip_vlr.record_data)
        if parallel:
            self.decompressor = lazrs.ParLasZipDecompressor(
                source, laszip_vlr.record_data
            )
        else:
            self.decompressor = lazrs.LasZipDecompressor(source, laszip_vlr.record_data)

    def read_n_points(self, n: int) -> bytearray:
        point_bytes = bytearray(n * self.vlr.item_size())
        self.decompressor.decompress_many(point_bytes)
        return point_bytes

    def seek(self, point_index: int) -> None:
        self.decompressor.seek(point_index)

    def close(self) -> None:
        self.source.close()


class EmptyPointReader(IPointReader):
    """Does nothing but returning empty bytes.
    Used to make sure we handle empty LAS files in a robust way.
    """

    def read_n_points(self, n: int) -> bytearray:
        return bytearray()

    def close(self) -> None:
        pass

    def seek(self, point_index: int) -> None:
        pass
