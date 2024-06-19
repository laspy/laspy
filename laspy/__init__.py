__version__ = "2.5.4"

import logging

from . import errors, file, vlrs
from .copc import Bounds, CopcReader
from .errors import LaspyException
from .header import LasHeader
from .lasdata import LasData
from .lasreader import LasReader
from .laswriter import LasWriter
from .lib import DecompressionSelection, LazBackend, convert
from .lib import create_las as create
from .lib import mmap_las as mmap
from .lib import open_las as open
from .lib import read_las as read
from .point import DimensionInfo, DimensionKind, ExtraBytesParams, PointFormat
from .point.dims import supported_point_formats, supported_versions
from .point.format import lost_dimensions
from .point.record import PackedPointRecord, ScaleAwarePointRecord
from .vlrs import VLR

logging.getLogger(__name__).addHandler(logging.NullHandler())
