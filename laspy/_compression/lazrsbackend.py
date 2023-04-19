import io
import math
from typing import Any, BinaryIO, List, Optional, Tuple, Union, cast

import numpy as np

from .._pointappender import IPointAppender
from .._pointreader import IPointReader
from .._pointwriter import IPointWriter
from ..errors import LaspyException
from ..header import LasHeader
from ..point.format import PointFormat
from ..point.record import PackedPointRecord
from ..vlrs.known import LasZipVlr
from .lazbackend import ILazBackend
from .selection import DecompressionSelection

try:
    import lazrs
except ModuleNotFoundError:
    lazrs = None


class LazrsBackend(ILazBackend):
    def __init__(
        self,
        parallel: bool = True,
    ):
        self._parallel = parallel

    def is_available(self) -> bool:
        return lazrs is not None

    @property
    def supports_append(self) -> bool:
        return True

    def create_appender(self, dest: BinaryIO, header: LasHeader) -> IPointAppender:
        return LazrsAppender(dest, header, parallel=self._parallel)

    def create_reader(
        self,
        source: Any,
        header: LasHeader,
        decompression_selection: Optional[DecompressionSelection] = None,
    ) -> IPointReader:
        if decompression_selection is None:
            decompression_selection = DecompressionSelection.all()
        laszip_vlr: LasZipVlr = header.vlrs[header.vlrs.index("LasZipVlr")]
        return LazrsPointReader(
            source,
            laszip_vlr,
            parallel=self._parallel,
            decompression_selection=decompression_selection,
        )

    def create_writer(
        self,
        dest: Any,
        header: "LasHeader",
    ) -> IPointWriter:
        return LazrsPointWriter(dest, header.point_format, parallel=self._parallel)


class LazrsPointReader(IPointReader):
    """Implementation for the laz-rs backend, supports single-threaded decompression
    as well as multi-threaded decompression
    """

    def __init__(
        self,
        source,
        laszip_vlr: LasZipVlr,
        parallel: bool,
        decompression_selection: DecompressionSelection,
    ) -> None:
        self._source = source
        self.vlr = lazrs.LazVlr(laszip_vlr.record_data)
        selection = decompression_selection.to_lazrs()
        if parallel:
            self.decompressor = lazrs.ParLasZipDecompressor(
                source, laszip_vlr.record_data, selection
            )
        else:
            self.decompressor = lazrs.LasZipDecompressor(
                source, laszip_vlr.record_data, selection
            )

    @property
    def source(self):
        return self._source

    def read_n_points(self, n: int) -> bytearray:
        point_bytes = bytearray(n * self.vlr.item_size())
        self.decompressor.decompress_many(point_bytes)
        return point_bytes

    def seek(self, point_index: int) -> None:
        self.decompressor.seek(point_index)

    def close(self) -> None:
        self.source.close()

    def read_chunk_table_only(self) -> List[Tuple[int, int]]:
        """
        This function requires the source to be at the start of the chunk table
        """
        assert isinstance(self.decompressor, lazrs.LasZipDecompressor)
        return self.decompressor.read_chunk_table_only()

    def read_raw_bytes(self, n: int) -> bytes:
        """
        reads and returns exactly `n` bytes from the source used by
        this point reader.
        """
        b = bytearray(n)
        self.decompressor.read_raw_bytes_into(b)
        return bytes(b)


class LazrsPointWriter(IPointWriter):
    """
    Compressed point writer using lazrs backend
    """

    def __init__(
        self, dest: BinaryIO, point_format: PointFormat, parallel: bool
    ) -> None:
        self.dest = dest
        self.vlr = lazrs.LazVlr.new_for_compression(
            point_format.id, point_format.num_extra_bytes
        )
        self.parallel = parallel
        self.compressor: Optional[
            Union[lazrs.ParLasZipCompressor, lazrs.LasZipCompressor]
        ] = None

    def write_initial_header_and_vlrs(
        self, header: LasHeader, encoding_errors: str
    ) -> None:
        laszip_vlr = LasZipVlr(self.vlr.record_data())
        header.vlrs.append(laszip_vlr)
        super().write_initial_header_and_vlrs(header, encoding_errors)
        # We have to initialize our compressor here
        # because on init, it writes the offset to chunk table
        # so the header and vlrs have to be written
        if self.parallel:
            self.compressor = lazrs.ParLasZipCompressor(self.dest, self.vlr)
        else:
            self.compressor = lazrs.LasZipCompressor(self.dest, self.vlr)

    @property
    def destination(self) -> BinaryIO:
        return self.dest

    def write_points(self, points: PackedPointRecord) -> None:
        assert (
            self.compressor is not None
        ), "Trying to write points without having written header"
        points_bytes = np.frombuffer(points.array, np.uint8)
        self.compressor.compress_many(points_bytes)

    def done(self) -> None:
        if self.compressor is not None:
            self.compressor.done()


class LazrsAppender(IPointAppender):
    """Appending in LAZ file
    works by seeking to start of the last chunk
    of compressed points, decompress it while keeping the points in
    memory.

    Then seek back to the start of the last chunk, and recompress
    the points we just read, so that we have a compressor in the proper state
    ready to compress new points.
    """

    def __init__(self, dest: BinaryIO, header: LasHeader, parallel: bool) -> None:
        self.dest = dest
        self.offset_to_point_data = header.offset_to_point_data
        laszip_vlr = cast(LasZipVlr, header.vlrs.get("LasZipVlr")[0])

        self.dest.seek(header.offset_to_point_data, io.SEEK_SET)
        decompressor = lazrs.LasZipDecompressor(self.dest, laszip_vlr.record_data)
        vlr = decompressor.vlr()
        number_of_complete_chunk = int(
            math.floor(header.point_count / vlr.chunk_size())
        )

        if vlr.uses_variable_size_chunks():
            # TODO: this is probably implementable but until its really needed,
            #       or i'm bored, there is no point.
            raise LaspyException(
                "LazrsAppender does not support LAZ files with variable size chunks"
            )

        self.dest.seek(header.offset_to_point_data, io.SEEK_SET)
        chunk_table = [
            byte_count
            for (point_count, byte_count) in lazrs.read_chunk_table(self.dest, vlr)
        ]
        if chunk_table is None:
            # The file does not have a chunk table
            # we cannot seek to the last chunk, so instead, we will
            # decompress points (which is slower) and build the chunk table
            # to write it later

            self.chunk_table = []
            start_of_chunk = self.dest.tell()
            point_buf = bytearray(vlr.chunk_size() * vlr.item_size())

            for _ in range(number_of_complete_chunk):
                decompressor.decompress_many(point_buf)
                pos = self.dest.tell()
                self.chunk_table.append(pos - start_of_chunk)
                start_of_chunk = pos
        else:
            self.chunk_table = chunk_table[:number_of_complete_chunk]
            idx_first_point_of_last_chunk = number_of_complete_chunk * vlr.chunk_size()
            decompressor.seek(idx_first_point_of_last_chunk)
        assert (
            len(self.chunk_table) == len(chunk_table)
            or len(self.chunk_table) == len(chunk_table) - 1
        )
        num_points_in_last_chunk = header.point_count - (
            number_of_complete_chunk * vlr.chunk_size()
        )

        points_of_last_chunk = bytearray(num_points_in_last_chunk * vlr.item_size())
        decompressor.decompress_many(points_of_last_chunk)

        self.dest.seek(header.offset_to_point_data, io.SEEK_SET)
        if parallel:
            self.compressor = lazrs.ParLasZipCompressor(self.dest, vlr)
        else:
            self.compressor = lazrs.LasZipCompressor(self.dest, vlr)
        # This effectively overwrites the old offset value.
        # But, more importantly, it makes the compressor aware of where to
        # write the offset value when its done.
        self.compressor.reserve_offset_to_chunk_table()
        assert self.dest.tell() == header.offset_to_point_data + 8
        self.dest.seek(sum(self.chunk_table), io.SEEK_CUR)
        self.compressor.compress_many(points_of_last_chunk)
        self.vlr = vlr

    def append_points(self, points: PackedPointRecord) -> None:
        points_bytes = np.frombuffer(points.array, np.uint8)
        self.compressor.compress_many(points_bytes)

    def done(self) -> None:
        # The chunk table written is at the good position
        # but it is incomplete (it's missing the chunk_table of
        # chunks before the one we appended)
        self.compressor.done()

        # Read the chunk table corresponding to our appended chunks
        self.dest.seek(self.offset_to_point_data, io.SEEK_SET)
        appended_chunk_table = [
            byte_count
            for (point_count, byte_count) in lazrs.read_chunk_table(self.dest, self.vlr)
        ]
        chunk_table = self.chunk_table + appended_chunk_table

        # Rewrite the fully complete chunk table.
        self.dest.seek(self.offset_to_point_data, io.SEEK_SET)
        offset_to_chunk_table = int.from_bytes(self.dest.read(8), "little", signed=True)
        self.dest.seek(offset_to_chunk_table, io.SEEK_SET)
        lazrs.write_chunk_table(
            self.dest,
            [(self.vlr.chunk_size(), byte_count) for byte_count in chunk_table],
            self.vlr,
        )
