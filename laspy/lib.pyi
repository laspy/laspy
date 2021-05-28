from typing import Union, BinaryIO, Iterable, Optional, overload, Literal

from . import LasWriter, PointFormat
from .compression import LazBackend
from .header import LasHeader
from .lasappender import LasAppender
from .lasdata import LasData
from .lasmmap import LasMMAP
from .lasreader import LasReader
from .typehints import PathLike

LazBackend = LazBackend
@overload
def open_las(
    source: PathLike,
    mode: Literal["r"] = ...,
    laz_backend: Union[LazBackend, Iterable[LazBackend]] = ...,
) -> LasReader: ...
@overload
def open_las(
    source: BinaryIO,
    mode: Literal["r"] = ...,
    closefd: bool = ...,
    laz_backend: Union[LazBackend, Iterable[LazBackend]] = ...,
) -> LasReader: ...
@overload
def open_las(
    source: PathLike,
    mode: Literal["w"],
    header: LasHeader,
    do_compress: Optional[bool] = ...,
    laz_backend: Union[LazBackend, Iterable[LazBackend]] = ...,
) -> LasWriter: ...
@overload
def open_las(
    source: BinaryIO,
    mode: Literal["w"],
    header: LasHeader,
    do_compress: Optional[bool] = ...,
    closefd: bool = ...,
    laz_backend: Union[LazBackend, Iterable[LazBackend]] = ...,
) -> LasWriter: ...
@overload
def open_las(
    source: PathLike,
    mode: Literal["a"],
    laz_backend: Union[LazBackend, Iterable[LazBackend]] = ...,
) -> LasAppender: ...
@overload
def open_las(
    source: BinaryIO,
    mode: Literal["a"],
    closefd: bool = ...,
    laz_backend: Union[LazBackend, Iterable[LazBackend]] = ...,
) -> LasAppender: ...
def read_las(
    source: Union[BinaryIO, PathLike],
    closefd: bool = True,
    laz_backend: Union[
        LazBackend, Iterable[LazBackend]
    ] = LazBackend.detect_available(),
) -> LasData: ...
def mmap_las(filename: PathLike) -> LasMMAP: ...
def merge_las(las_files: Union[Iterable[LasData], LasData]) -> LasData: ...
def create_las(
    *, point_format: Union[int, PointFormat] = 0, file_version: Optional[str] = 0
) -> LasData: ...
def convert(
    source_las: LasData,
    *,
    point_format_id: Optional[int] = ...,
    file_version: Optional[str] = ...
) -> LasData: ...
def create_from_header(header: LasHeader) -> LasData: ...
def write_then_read_again(
    las: LasData, do_compress: bool = ..., laz_backend: LazBackend = ...
) -> LasData: ...
