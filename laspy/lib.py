""" 'Entry point' of the library, Contains the various functions meant to be
used directly by a user
"""

import copy
import io
import logging
import os
from pathlib import Path
from typing import Optional, Union

from .compression import DecompressionSelection, LazBackend
from .errors import LaspyException
from .header import LasHeader, Version
from .lasappender import LasAppender
from .lasdata import LasData
from .lasmmap import LasMMAP
from .lasreader import LasReader
from .laswriter import LasWriter
from .point import PointFormat, dims, record
from .vlrs.vlrlist import VLRList

logger = logging.getLogger(__name__)


def open_las(
    source,
    mode="r",
    closefd=True,
    laz_backend=None,
    header=None,
    do_compress=None,
    encoding_errors: str = "strict",
    read_evlrs: bool = True,
    decompression_selection: DecompressionSelection = DecompressionSelection.all(),
) -> Union[LasReader, LasWriter, LasAppender]:
    """The laspy.open opens a LAS/LAZ file in one of the 3 supported
    mode:

     - "r" => Reading => a :class:`laspy.LasReader` will be returned
     - "w" => Writing => a :class:`laspy.LasWriter` will be returned
     - "a" => Appending => a :class:`laspy.LasAppender` will be returned


    When opening a file in 'w' mode, a header (:class:`laspy.LasHeader`)
    is required

        >>> with open_las('tests/data/simple.las') as f:
        ...     print(f.header.point_format.id)
        3


        >>> f = open('tests/data/simple.las', mode='rb')
        >>> with open_las(f,closefd=False) as flas:
        ...     print(flas.header)
        <LasHeader(1.2, <PointFormat(3, 0 bytes of extra dims)>)>
        >>> f.closed
        False
        >>> f.close()
        >>> f.closed
        True


        >>> f = open('tests/data/simple.las', mode='rb')
        >>> with open_las(f) as flas:
        ...    las = flas.read()
        >>> f.closed
        True

    Parameters
    ----------
    source: str or bytes or io.BytesIO
        if source is a str it must be a filename

    mode: Optional, the mode to open the file:
        - "r" for reading (default)
        - "w" for writing
        - "a" for appending

    laz_backend: Optional, laspy.LazBackend, the LAZ backend to use to handle decompression/compression

        By default available backends are detected, see LazBackend to see the
        preference order when multiple backends are available

    header: The header to use when opening in write mode.

    do_compress: optional, bool, only meaningful in writing mode:
        - None (default) guess if compression is needed using the file extension
          or if a laz_backend was explicitely provided
        - True compresses the file
        - False do not compress the file

    closefd: optional, bool, True by default
        Whether the stream/file object shall be closed, this only work
        when using open_las in a with statement. An exception is raised if
        closefd is specified and the source is a filename

    encoding_errors: str, default 'strict'
        Only used in writing and appending mode.
        How encoding errors should be treated.
        Possible values and their explanation can be seen here:
        https://docs.python.org/3/library/codecs.html#error-handlers.

    read_evlrs: bool, default True
            Only applies to 'r' mode.

            If True the evlrs will be read during the __init__ / file opening
            along with the LasHeader.

            It is fine for most of the cases,
            but can be problematic when opening file from a data stream like
            AWS S3 as EVLRs are located at the end of the files, thus
            will require to pull the whole file.

            Does nothing if the input file does not support
            EVLRs

    decompression_selection: DecompressionSelection, default All
        Only applies to 'r' mode and for files which suport selective decompression
        (version >= 1.4 and point format id >= 6), ignored otherwise.

        Allows to select which fields should be decompressed or not, allowing to save time
        by not decompressing unused fields.

        By default all fields are decompressed

    .. versionadded:: 2.4
        The ``read_evlrs`` and ``decompression_selection`` parameters.
    """
    if mode == "r":
        if header is not None:
            raise LaspyException(
                "header argument is not used when opening in read mode, "
                "did you meant to open in write mode ?"
            )
        if do_compress is not None:
            raise LaspyException(
                "do_compress argument is not used when opening in read mode, "
                "did you meant to open in write mode ?"
            )
        if isinstance(source, (str, Path)):
            stream = open(source, mode="rb", closefd=closefd)
        elif isinstance(source, bytes):
            stream = io.BytesIO(source)
        else:
            stream = source
        try:
            return LasReader(
                stream,
                closefd=closefd,
                laz_backend=laz_backend,
                read_evlrs=read_evlrs,
                decompression_selection=decompression_selection,
            )
        except:
            if closefd:
                stream.close()
            raise
    elif mode == "w":
        if header is None:
            raise ValueError("A header is needed when opening a file for writing")

        if isinstance(source, (str, Path)):
            if do_compress is None:
                do_compress = os.path.splitext(source)[1].lower() == ".laz"
            stream = open(source, mode="wb+", closefd=closefd)
        elif isinstance(source, bytes):
            stream = io.BytesIO(source)
        else:
            assert source.seekable()
            stream = source

        try:
            return LasWriter(
                stream,
                header=header,
                do_compress=do_compress,
                laz_backend=laz_backend,
                closefd=closefd,
                encoding_errors=encoding_errors,
            )
        except:
            if closefd:
                stream.close()
            raise
    elif mode == "a":
        if isinstance(source, (str, Path)):
            stream = open(source, mode="rb+", closefd=closefd)
        elif isinstance(source, bytes):
            stream = io.BytesIO(source)
        else:
            stream = source

        try:
            return LasAppender(
                stream,
                closefd=closefd,
                laz_backend=laz_backend,
                encoding_errors=encoding_errors,
            )
        except:
            if closefd:
                stream.close()
            raise
    else:
        raise ValueError(f"Unknown mode '{mode}'")


def read_las(
    source,
    closefd=True,
    laz_backend=LazBackend.detect_available(),
    decompression_selection: DecompressionSelection = DecompressionSelection.all(),
):
    """Entry point for reading las data in laspy

    Reads the whole file into memory.

    >>> las = read_las("tests/data/simple.las")
    >>> las.classification
    <SubFieldView([1 1 1 ... 1 1 1])>

    Parameters
    ----------
    source : str or io.BytesIO
        The source to read data from

    laz_backend: Optional, the backend to use when the file is as LAZ file.
                 By default laspy will find the backend to use by itself.
                 Use if you want a specific backend to be used

    closefd: bool
            if True and the source is a stream, the function will close it
            after it is done reading

    decompression_selection: DecompressionSelection,
        see :func:`laspy.open`


    Returns
    -------
    laspy.LasData
        The object you can interact with to get access to the LAS points & VLRs


    .. versionadded:: 2.4
        The ``decompression_selection`` parameter.
    """
    with open_las(
        source,
        closefd=closefd,
        laz_backend=laz_backend,
        decompression_selection=decompression_selection,
    ) as reader:
        return reader.read()


def mmap_las(filename):
    """MMap a file, much like laspy did"""
    return LasMMAP(filename)


def create_las(
    *,
    point_format: Optional[Union[int, PointFormat]] = None,
    file_version: Optional[Union[str, Version]] = None,
):
    """Function to create a new empty las data object

    .. note::

        If you provide both point_format and file_version
        an exception will be raised if they are not compatible

    >>> las = create_las(point_format=6,file_version="1.2")
    Traceback (most recent call last):
     ...
    laspy.errors.LaspyException: Point format 6 is not compatible with file version 1.2


    If you provide only the point_format the file_version will automatically
    selected for you.

    >>> las = create_las(point_format=0)
    >>> las.header.version == '1.2'
    True

    >>> las = create_las(point_format=PointFormat(6))
    >>> las.header.version == '1.4'
    True


    Parameters
    ----------
    point_format:
        The point format you want the created file to have

    file_version:
        The las version you want the created las to have

    Returns
    -------
    laspy.lasdatas.base.LasBase
       A new las data object

    """
    header = LasHeader(point_format=point_format, version=file_version)
    return LasData(header=header)


def convert(source_las, *, point_format_id=None, file_version=None):
    """Converts a Las from one point format to another
    Automatically upgrades the file version if source file version is not compatible with
    the new point_format_id


    convert to point format 0

    >>> las = read_las('tests/data/simple.las')
    >>> las.header.version
    Version(major=1, minor=2)
    >>> las = convert(las, point_format_id=0)
    >>> las.header.point_format.id
    0
    >>> str(las.header.version)
    '1.2'

    convert to point format 6, which need version >= 1.4
    then convert back to point format 0, version is not downgraded

    >>> las = read_las('tests/data/simple.las')
    >>> str(las.header.version)
    '1.2'
    >>> las = convert(las, point_format_id=6)
    >>> las.header.point_format.id
    6
    >>> str(las.header.version)
    '1.4'
    >>> las = convert(las, point_format_id=0)
    >>> str(las.header.version)
    '1.4'

    an exception is raised if the requested point format is not compatible
    with the file version

    >>> las = read_las('tests/data/simple.las')
    >>> convert(las, point_format_id=6, file_version='1.2')
    Traceback (most recent call last):
     ...
    laspy.errors.LaspyException: Point format 6 is not compatible with file version 1.2

    Parameters
    ----------
    source_las : laspy.lasdatas.base.LasBase
        The source data to be converted

    point_format_id : int, optional
        The new point format id (the default is None, which won't change the source format id)

    file_version : str, optional,
        The new file version. None by default which means that the file_version
        may be upgraded for compatibility with the new point_format. The file version will not
        be downgraded.

    Returns
    -------
        laspy.lasdatas.base.LasBase
    """
    if point_format_id is None:
        point_format_id = source_las.point_format.id

    if file_version is None:
        file_version = max(
            str(source_las.header.version),
            dims.preferred_file_version_for_point_format(point_format_id),
        )
    else:
        file_version = str(file_version)
        dims.raise_if_version_not_compatible_with_fmt(point_format_id, file_version)

    version = Version.from_str(file_version)

    point_format = PointFormat(point_format_id)
    point_format.dimensions.extend(source_las.point_format.extra_dimensions)

    header = copy.deepcopy(source_las.header)
    header.set_version_and_point_format(version, point_format)

    if source_las.evlrs is not None:
        evlrs = VLRList(source_las.evlrs.copy())
    else:
        evlrs = None

    points = record.PackedPointRecord.from_point_record(
        source_las.points, header.point_format
    )
    las = LasData(header=header, points=points)

    if file_version < "1.4" and evlrs is not None and evlrs:
        logger.warning(
            "The source contained {} EVLRs,"
            " they will be lost as version {} doest not support them".format(
                len(evlrs), file_version
            )
        )
    else:
        las.evlrs = evlrs

    return las


def write_then_read_again(
    las, do_compress=False, laz_backend=LazBackend.detect_available()
):
    """writes the given las into memory using BytesIO and
    reads it again, returning the newly read file.

    Mostly used for testing purposes, without having to write to disk
    """
    out = io.BytesIO()
    las.write(out, do_compress=do_compress, laz_backend=laz_backend)
    out.seek(0)
    return read_las(out)
