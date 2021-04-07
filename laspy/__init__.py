__version__ = "2.0.0a0"

import logging

from . import errors, vlrs
from .errors import LaspyError
from .laswriter import LasWriter
from .lasreader import LasReader
from .lib import LazBackend, convert
from .lib import create_las as create
from .lib import mmap_las as mmap
from .lib import open_las as open
from .lib import read_las as read
from .point import PointFormat, ExtraBytesParams, DimensionKind, DimensionInfo
from .point.dims import supported_point_formats, supported_versions
from .point.format import lost_dimensions
from .header import LasHeader
from .lasdata import LasData
from .vlrs import VLR

logging.getLogger(__name__).addHandler(logging.NullHandler())


class File:
    def __init__(self, *args, **kwargs) -> None:
        raise errors.LaspyError(
            "laspy changed:"
            "To read a file do: las = laspy.read('somefile.laz')"
            "To create a new LAS data do: las = laspy.create(point_format=2, file_version='1.2')"
            "To write a file previously read or created: las.write('somepath.las')"
            "See the documentation for more information about the changes"
        )
