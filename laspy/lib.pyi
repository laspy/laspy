from typing import BinaryIO, Iterable, Literal, overload

from . import LasWriter, PointFormat
from .compression import DecompressionSelection, LazBackend
from .header import LasHeader, Version
from .lasappender import LasAppender
from .lasdata import LasData
from .lasmmap import LasMMAP
from .lasreader import LasReader
from .typehints import PathLike

LazBackend = LazBackend
DecompressionSelection = DecompressionSelection

@overload
def open_las(
    source: BinaryIO | PathLike | bytes,
    mode: Literal["r"] = ...,
    closefd: bool = ...,
    laz_backend: LazBackend | Iterable[LazBackend] = ...,
    read_evlrs: bool = ...,
    decompression_selection: DecompressionSelection = ...,
    fullwave: Literal["never", "lazy", "eager"] = ...,
) -> LasReader: ...
@overload
def open_las(
    source: PathLike,
    mode: Literal["r"] = ...,
    laz_backend: LazBackend | Iterable[LazBackend] = ...,
    read_evlrs: bool = ...,
    decompression_selection: DecompressionSelection = ...,
    fullwave: Literal["never", "lazy", "eager"] = ...,
) -> LasReader: ...
@overload
def open_las(
    source: BinaryIO | bytes,
    mode: Literal["r"] = ...,
    closefd: bool = ...,
    laz_backend: LazBackend | Iterable[LazBackend] = ...,
    read_evlrs: bool = ...,
    decompression_selection: DecompressionSelection = ...,
    fullwave: Literal["never", "lazy", "eager"] = ...,
) -> LasReader: ...
@overload
def open_las(
    source: PathLike,
    mode: Literal["w"],
    header: LasHeader,
    do_compress: bool | None = ...,
    laz_backend: LazBackend | Iterable[LazBackend] = ...,
    encoding_errors: str = ...,
    fullwave: Literal["never", "lazy", "eager"] = ...,
) -> LasWriter: ...
@overload
def open_las(
    source: BinaryIO | bytes,
    mode: Literal["w"],
    header: LasHeader,
    do_compress: bool | None = ...,
    closefd: bool = ...,
    laz_backend: LazBackend | Iterable[LazBackend] = ...,
    encoding_errors: str = ...,
    fullwave: Literal["never", "lazy", "eager"] = ...,
) -> LasWriter: ...
@overload
def open_las(
    source: PathLike,
    mode: Literal["a"],
    laz_backend: LazBackend | Iterable[LazBackend] = ...,
    encoding_errors: str = ...,
    fullwave: Literal["never", "lazy", "eager"] = ...,
) -> LasAppender: ...
@overload
def open_las(
    source: BinaryIO | bytes,
    mode: Literal["a"],
    closefd: bool = ...,
    laz_backend: LazBackend | Iterable[LazBackend] = ...,
    encoding_errors: str = ...,
    fullwave: Literal["never", "lazy", "eager"] = ...,
) -> LasAppender: ...
def read_las(
    source: BinaryIO | PathLike | bytes,
    closefd: bool = True,
    laz_backend: LazBackend | Iterable[LazBackend] = LazBackend.detect_available(),
    decompression_selection: DecompressionSelection = DecompressionSelection.all(),
    fullwave: Literal["never", "lazy", "eager"] = ...,
) -> LasData: ...
def mmap_las(filename: PathLike) -> LasMMAP: ...
def create_las(
    *, point_format: int | PointFormat | None = None, file_version: str | Version | None = None
) -> LasData: ...
def convert(
    source_las: LasData,
    *,
    point_format_id: int | None = ...,
    file_version: str | None = ...,
) -> LasData: ...
def write_then_read_again(
    las: LasData,
    do_compress: bool = ...,
    laz_backend: LazBackend | Iterable[LazBackend] = ...,
) -> LasData: ...
