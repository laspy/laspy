import io
import math
from typing import Union, Iterable, BinaryIO, Optional, cast

import numpy as np

from .compression import LazBackend
from .errors import LaspyException
from .header import LasHeader
from .laswriter import UncompressedPointWriter
from .point.record import PackedPointRecord
from .vlrs.known import LasZipVlr
from .vlrs.vlrlist import VLRList

try:
    import lazrs
except ModuleNotFoundError:
    pass


class LasAppender:
    """Allows to append points to and existing LAS/LAZ file.

    Appending to LAZ is only supported by the lazrs backend
    """

    def __init__(
        self,
        dest: BinaryIO,
        laz_backend: Optional[Union[LazBackend, Iterable[LazBackend]]] = None,
        closefd: bool = True,
        encoding_errors: str = "strict",
    ) -> None:
        if not dest.seekable():
            raise TypeError("Expected the 'dest' to be a seekable file object")
        header = LasHeader.read_from(dest)
        if laz_backend is None:
            laz_backend = [
                bck
                for bck in LazBackend.detect_available()
                if bck is not LazBackend.Laszip
            ]

        self.dest = dest
        self.header = header

        if not header.are_points_compressed:
            self.points_writer = UncompressedPointWriter(self.dest)
            self.dest.seek(
                (self.header.point_count * self.header.point_format.size)
                + self.header.offset_to_point_data,
                io.SEEK_SET,
            )
        else:
            self.points_writer = self._create_laz_backend(laz_backend)

        if header.version.minor >= 4 and header.number_of_evlrs > 0:
            assert (
                self.dest.tell() <= self.header.start_of_first_evlr
            ), "The position is past the start of evlrs"
            pos = self.dest.tell()
            self.dest.seek(self.header.start_of_first_evlr, io.SEEK_SET)
            self.evlrs: Optional[VLRList] = VLRList.read_from(
                self.dest, self.header.number_of_evlrs, extended=True
            )
            dest.seek(self.header.start_of_first_evlr, io.SEEK_SET)
            self.dest.seek(pos, io.SEEK_SET)
        else:
            self.evlrs: Optional[VLRList] = None

        self.closefd = closefd
        self.encoding_errors = encoding_errors

    def append_points(self, points: PackedPointRecord) -> None:
        """Append the points to the file, the points
        must have the same point format as the points
        already contained within the file.

        :param points: The points to append
        """
        if points.point_format != self.header.point_format:
            raise LaspyException("Point formats do not match")

        self.points_writer.write_points(points)
        self.header.grow(points)

    def close(self) -> None:
        self.points_writer.done()
        self._write_evlrs()
        self._write_updated_header()

        if self.closefd:
            self.dest.close()

    def _write_evlrs(self) -> None:
        if (
            self.header.version.minor >= 4
            and self.evlrs is not None
            and len(self.evlrs) > 0
        ):
            self.header.number_of_evlr = len(self.evlrs)
            self.header.start_of_first_evlr = self.dest.tell()
            self.evlrs.write_to(self.dest, as_extended=True)

    def _write_updated_header(self) -> None:
        pos = self.dest.tell()
        self.dest.seek(0, io.SEEK_SET)
        self.header.write_to(
            self.dest, ensure_same_size=True, encoding_errors=self.encoding_errors
        )
        self.dest.seek(pos, io.SEEK_SET)

    def _create_laz_backend(
        self,
        laz_backend: Union[LazBackend, Iterable[LazBackend]] = (
            LazBackend.LazrsParallel,
            LazBackend.Lazrs,
        ),
    ) -> "LazrsAppender":
        try:
            laz_backend = iter(laz_backend)
        except TypeError:
            laz_backend = (laz_backend,)

        last_error = None
        for backend in laz_backend:
            if backend == LazBackend.Laszip:
                raise LaspyException("Laszip backend does not support appending")
            elif backend == LazBackend.LazrsParallel:
                try:
                    return LazrsAppender(self.dest, self.header, parallel=True)
                except Exception as e:
                    last_error = e
            elif backend == LazBackend.Lazrs:
                try:
                    return LazrsAppender(self.dest, self.header, parallel=False)
                except Exception as e:
                    last_error = e

        if last_error is not None:
            raise LaspyException(f"Could not initialize a laz backend: {last_error}")
        else:
            raise LaspyException(f"No valid laz backend selected")

    def __enter__(self) -> "LasAppender":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class LazrsAppender:
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
            self.chunk_table = chunk_table[:-1]
            idx_first_point_of_last_chunk = number_of_complete_chunk * vlr.chunk_size()
            decompressor.seek(idx_first_point_of_last_chunk)

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

    def write_points(self, points: PackedPointRecord) -> None:
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
