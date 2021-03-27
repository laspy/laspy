import io
import mmap

from . import lasdata
from .header import LasHeader
from .point import record
from .typehints import PathLike

WHOLE_FILE = 0


class LasMMAP(lasdata.LasData):
    """Memory map a LAS file.
    It works like a regular LasData however the data is not actually read in memory,

    Access to dimensions are made directly from the file itself, changes made to the points
    are directly reflected in the mmap file.

    Vlrs cannot be modified.

    This can be useful if you want to be able to process a big LAS file

    .. note::
        A LAZ (compressed LAS) cannot be mmapped
    """

    def __init__(self, filename: PathLike) -> None:
        fileref = open(filename, mode="r+b")

        m = mmap.mmap(fileref.fileno(), length=WHOLE_FILE, access=mmap.ACCESS_WRITE)
        header = LasHeader.read_from(m)
        if header.are_points_compressed:
            raise ValueError("Cannot mmap a compressed LAZ file")

        points_data = record.PackedPointRecord.from_buffer(
            m,
            header.point_format,
            count=header.point_count,
            offset=header.offset_to_point_data,
        )
        super().__init__(header=header, points=points_data)

        self.fileref, self.mmap = fileref, m
        self.mmap.seek(0, io.SEEK_SET)

    def close(self) -> None:
        # These need to be set to None, so that
        # mmap.close() does not give an error because
        # there are still exported pointers
        self._points = None
        self.mmap.close()
        self.fileref.close()

    def __enter__(self) -> "LasMMAP":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
