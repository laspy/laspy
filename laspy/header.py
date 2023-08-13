import enum
import io
import logging
import struct
import typing
from datetime import date, timedelta
from typing import BinaryIO, Iterable, List, NamedTuple, Optional, Union
from uuid import UUID

import numpy as np

from . import __version__, extradims
from ._compression.format import (
    compressed_id_to_uncompressed,
    is_point_format_compressed,
    uncompressed_id_to_compressed,
)
from .errors import LaspyException
from .point import dims
from .point.format import ExtraBytesParams, PointFormat
from .point.record import PackedPointRecord
from .utils import read_string, write_string
from .vlrs import VLR
from .vlrs.geotiff import create_geotiff_projection_vlrs
from .vlrs.known import (
    ExtraBytesStruct,
    ExtraBytesVlr,
    GeoAsciiParamsVlr,
    GeoKeyDirectoryVlr,
    WktCoordinateSystemVlr,
)
from .vlrs.vlrlist import VLRList

logger = logging.getLogger(__name__)

GENERATING_SOFTWARE_LEN = 32
SYSTEM_IDENTIFIER_LEN = 32

LAS_FILE_SIGNATURE = b"LASF"
DEFAULT_GENERATING_SOFTWARE = f"laspy {__version__}"
assert len(DEFAULT_GENERATING_SOFTWARE) < GENERATING_SOFTWARE_LEN


class Version(NamedTuple):
    major: int
    minor: int

    @classmethod
    def from_str(cls, string: str) -> "Version":
        major, minor = tuple(map(int, string.split(".")))
        return cls(major, minor)

    def __eq__(self, other):
        if isinstance(other, str):
            return str(self) == other
        else:
            return other.major == self.major and other.minor == self.minor

    def __str__(self):
        return f"{self.major}.{self.minor}"


class GpsTimeType(enum.IntEnum):
    WEEK_TIME = 0
    STANDARD = 1


class GlobalEncoding:
    GPS_TIME_TYPE_MASK = 0b0000_0000_0000_0001
    WAVEFORM_INTERNAL_MASK = 0b0000_0000_0000_0010  # 1.3
    WAVEFORM_EXTERNAL_MASK = 0b0000_0000_0000_0100  # 1.3
    SYNTHETIC_RETURN_NUMBERS_MASK = 0b0000_0000_0000_1000  # 1.3
    WKT_MASK = 0b0000_0000_0001_0000  # 1.4

    def __init__(self, value=0):
        self.value = value

    def _set_bit(self, mask):
        self.value |= mask

    def _unset_bit(self, mask):
        self.value ^= mask

    def _set_if_true(self, mask, value):
        if bool(value) is True:
            self._set_bit(mask)
        else:
            self._unset_bit(mask)

    @property
    def gps_time_type(self) -> GpsTimeType:
        return GpsTimeType(self.value & self.GPS_TIME_TYPE_MASK)

    @gps_time_type.setter
    def gps_time_type(self, value: GpsTimeType):
        self.value ^= self.GPS_TIME_TYPE_MASK
        self.value |= int(value) & self.GPS_TIME_TYPE_MASK

    @property
    def waveform_data_packets_internal(self) -> bool:
        return bool(self.value & self.WAVEFORM_INTERNAL_MASK)

    @waveform_data_packets_internal.setter
    def waveform_data_packets_internal(self, value):
        self._set_if_true(self.WAVEFORM_INTERNAL_MASK, value)

    @property
    def waveform_data_packets_external(self) -> bool:
        return bool(self.value & self.WAVEFORM_EXTERNAL_MASK)

    @waveform_data_packets_external.setter
    def waveform_data_packets_external(self, value):
        self._set_if_true(self.WAVEFORM_EXTERNAL_MASK, value)

    @property
    def synthetic_return_numbers(self) -> bool:
        return bool(self.value & self.SYNTHETIC_RETURN_NUMBERS_MASK)

    @synthetic_return_numbers.setter
    def synthetic_return_numbers(self, value):
        self._set_if_true(self.SYNTHETIC_RETURN_NUMBERS_MASK, value)

    @property
    def wkt(self) -> bool:
        return bool(self.value & self.WKT_MASK)

    @wkt.setter
    def wkt(self, value):
        self._set_if_true(self.WKT_MASK, value)

    @classmethod
    def read_from(cls, stream: BinaryIO) -> "GlobalEncoding":
        return cls(int.from_bytes(stream.read(2), byteorder="little", signed=False))

    def write_to(self, stream: BinaryIO) -> None:
        stream.write(self.value.to_bytes(2, byteorder="little", signed=False))


class LasHeader:
    """Contains the information from the header of as LAS file
    with 'implementation' field left out and 'users' field
    stored in more ergonomic classes.

    This header also contains the VLRs

    Examples
    --------

    Creating a default header:

    >>> header = LasHeader()
    >>> header
    <LasHeader(1.2, <PointFormat(3, 0 bytes of extra dims)>)>

    Creating a header with the wanted version and point format:

    >>> header = LasHeader(version=Version(1, 4), point_format=PointFormat(6))
    >>> header
    <LasHeader(1.4, <PointFormat(6, 0 bytes of extra dims)>)>

    >>> header = LasHeader(version="1.4", point_format=6)
    >>> header
    <LasHeader(1.4, <PointFormat(6, 0 bytes of extra dims)>)>
    """

    #: The default version used when None is given to init
    DEFAULT_VERSION = Version(1, 2)
    #: The default point format Used when None is given to init
    DEFAULT_POINT_FORMAT = PointFormat(3)

    _OLD_LASPY_NAMES = {
        "max": "maxs",
        "min": "mins",
        "scale": "scales",
        "offset": "offsets",
        "filesource_id": "file_source_id",
        "system_id": "system_identifier",
        "date": "creation_date",
        "point_return_count": "number_of_points_by_return",
        "software_id": "generating_software",
        "point_records_count": "point_count",
    }

    def __init__(
        self,
        *,
        version: Optional[Union[Version, str]] = None,
        point_format: Optional[Union[PointFormat, int]] = None,
    ) -> None:
        if isinstance(point_format, int):
            point_format = PointFormat(point_format)
        if isinstance(version, str):
            version = Version.from_str(version)

        if version is None and point_format is None:
            version = LasHeader.DEFAULT_VERSION
            point_format = LasHeader.DEFAULT_POINT_FORMAT
        elif version is not None and point_format is None:
            point_format = PointFormat(dims.min_point_format_for_version(str(version)))
        elif version is None and point_format is not None:
            version = Version.from_str(
                dims.preferred_file_version_for_point_format(point_format.id)
            )
        dims.raise_if_version_not_compatible_with_fmt(point_format.id, str(version))

        #: File source id
        self.file_source_id: int = 0
        self.global_encoding: GlobalEncoding = GlobalEncoding()
        #: Project ID
        #: Initialized to null UUID
        self.uuid: UUID = UUID(bytes_le=b"\0" * 16)
        self._version: Version = version
        #: System identifier
        #: Initialized to 'OTHER'
        self.system_identifier: Union[str, bytes] = "OTHER"
        #: The software which generated the file
        #: Initialized to 'laspy'
        self.generating_software: Union[str, bytes] = DEFAULT_GENERATING_SOFTWARE
        self._point_format: PointFormat = point_format
        #: Day the file was created, initialized to date.today
        self.creation_date: Optional[date] = date.today()
        #: The number of points in the file
        self.point_count: int = 0
        #: The numbers used to scale the x,y,z coordinates
        self.scales: np.ndarray = np.array([0.01, 0.01, 0.01], dtype=np.float64)
        #: The numbers used to offset the x,y,z coordinates
        self.offsets: np.ndarray = np.zeros(3, dtype=np.float64)
        # The max values for x,y,z
        self.maxs: np.ndarray = np.zeros(3, dtype=np.float64)
        # The min values for x,y,z
        self.mins: np.ndarray = np.zeros(3, dtype=np.float64)

        #: Number of points by return
        #: for las <= 1.2 only the first 5 elements matters
        self.number_of_points_by_return: np.ndarray = np.zeros(15, dtype=np.uint32)

        #: The VLRS
        self._vlrs: VLRList = VLRList()

        #: Extra bytes between end of header and first vlrs
        self.extra_header_bytes: bytes = b""
        #: Extra bytes between end of vlr end first point
        self.extra_vlr_bytes: bytes = b""

        #: Las >= 1.3
        self.start_of_waveform_data_packet_record: int = 0

        #: Las >= 1.4
        #: Offset to the first evlr in the file
        self.start_of_first_evlr: int = 0
        #: The number of evlrs in the file
        self.number_of_evlrs: int = 0

        #: EVLRs, even though they are not stored in the 'header'
        #: part of the file we keep them in this class
        #: as they contain same information as vlr.
        #: None when the file does not support EVLR
        self.evlrs: Optional[VLRList] = None

        # Info we keep because it's useful for us but not the user
        self.offset_to_point_data: int = 0
        self.are_points_compressed: bool = False

        self._sync_extra_bytes_vlr()

    @property
    def point_format(self) -> PointFormat:
        """The point format"""
        return self._point_format

    @point_format.setter
    def point_format(self, new_point_format: PointFormat) -> None:
        dims.raise_if_version_not_compatible_with_fmt(
            new_point_format.id, str(self.version)
        )
        self._point_format = new_point_format
        self._sync_extra_bytes_vlr()

    @property
    def version(self) -> Version:
        """The version"""
        return self._version

    @version.setter
    def version(self, version: Version) -> None:
        dims.raise_if_version_not_compatible_with_fmt(
            self.point_format.id, str(version)
        )
        self._version = version

    # scale properties
    @property
    def x_scale(self) -> float:
        return self.scales[0]

    @x_scale.setter
    def x_scale(self, value: float) -> None:
        self.scales[0] = value

    @property
    def y_scale(self) -> float:
        return self.scales[1]

    @y_scale.setter
    def y_scale(self, value: float) -> None:
        self.scales[1] = value

    @property
    def z_scale(self) -> float:
        return self.scales[2]

    @z_scale.setter
    def z_scale(self, value: float) -> None:
        self.scales[2] = value

    # offset properties
    @property
    def x_offset(self) -> float:
        return self.offsets[0]

    @x_offset.setter
    def x_offset(self, value: float) -> None:
        self.offsets[0] = value

    @property
    def y_offset(self) -> float:
        return self.offsets[1]

    @y_offset.setter
    def y_offset(self, value: float) -> None:
        self.offsets[1] = value

    @property
    def z_offset(self) -> float:
        return self.offsets[2]

    @z_offset.setter
    def z_offset(self, value: float) -> None:
        self.offsets[2] = value

    # max properties
    @property
    def x_max(self) -> float:
        return self.maxs[0]

    @x_max.setter
    def x_max(self, value: float) -> None:
        self.maxs[0] = value

    @property
    def y_max(self) -> float:
        return self.maxs[1]

    @y_max.setter
    def y_max(self, value: float) -> None:
        self.maxs[1] = value

    @property
    def z_max(self) -> float:
        return self.maxs[2]

    @z_max.setter
    def z_max(self, value: float) -> None:
        self.maxs[2] = value

    # min properties
    @property
    def x_min(self) -> float:
        return self.mins[0]

    @x_min.setter
    def x_min(self, value: float) -> None:
        self.mins[0] = value

    @property
    def y_min(self) -> float:
        return self.mins[1]

    @y_min.setter
    def y_min(self, value: float) -> None:
        self.mins[1] = value

    @property
    def z_min(self) -> float:
        return self.mins[2]

    @z_min.setter
    def z_min(self, value: float) -> None:
        self.mins[2] = value

    @property
    def vlrs(self) -> VLRList:
        return self._vlrs

    @vlrs.setter
    def vlrs(self, vlrs: typing.Iterable[VLR]) -> None:
        self._vlrs = VLRList(vlrs)

        try:
            self.vlrs.extract("LaszipVlr")
        except ValueError:
            pass

        self._sync_extra_bytes_vlr()

    def add_extra_dims(self, params: List[ExtraBytesParams]) -> None:
        for param in params:
            self.point_format.add_extra_dimension(param)
        self._sync_extra_bytes_vlr()

    def add_extra_dim(self, params: ExtraBytesParams):
        self.add_extra_dims([params])

    def add_crs(self, crs: "pyproj.CRS", keep_compatibility: bool = True) -> None:
        """Add a Coordinate Reference System VLR from a pyproj CRS object.

        The type of VLR created depends on the las version and point format
        version. Las version >= 1.4 use WKT string, las version < 1.4 and point
        format < 6 use GeoTiff tags.

        .. warning::
            This requires `pyproj`.

        .. warning::
            Not all CRS are supported when adding GeoTiff tags.
            For example, custom CRS.

            Typically, if the CRS has an EPSG code it will be supported.
        """
        import pyproj

        # check and remove any existing crs vlrs
        for crs_vlr_name in (
            "WktCoordinateSystemVlr",
            "GeoKeyDirectoryVlr",
            "GeoAsciiParamsVlr",
            "GeoDoubleParamsVlr",
        ):
            try:
                self._vlrs.extract(crs_vlr_name)
            except IndexError:
                pass

        new_ver = self._version >= Version(1, 4)
        new_pt = self.point_format.id >= 6

        if new_pt or (new_ver and not keep_compatibility):
            self._vlrs.append(WktCoordinateSystemVlr(crs.to_wkt()))
            self.global_encoding.wkt = True
        else:
            self._vlrs.extend(create_geotiff_projection_vlrs(crs))

    def remove_extra_dim(self, name: str) -> None:
        self.remove_extra_dims([name])

    def remove_extra_dims(self, names: Iterable[str]) -> None:
        for name in names:
            self.point_format.remove_extra_dimension(name)
        self._sync_extra_bytes_vlr()

    def set_version_and_point_format(
        self, version: Version, point_format: PointFormat
    ) -> None:
        dims.raise_if_version_not_compatible_with_fmt(point_format.id, str(version))
        self._version = version
        self.point_format = point_format

    def partial_reset(self) -> None:
        f64info = np.finfo(np.float64)
        self.maxs = np.ones(3, dtype=np.float64) * f64info.min
        self.mins = np.ones(3, dtype=np.float64) * f64info.max

        self.start_of_first_evlr = 0
        self.number_of_evlrs = 0
        self.point_count = 0
        self.number_of_points_by_return = np.zeros(15, dtype=np.uint32)

    def update(self, points: PackedPointRecord) -> None:
        self.partial_reset()
        if not points:
            self.maxs = [0.0, 0.0, 0.0]
            self.mins = [0.0, 0.0, 0.0]
        else:
            self.grow(points)

    def grow(self, points: PackedPointRecord) -> None:
        self.x_max = max(
            self.x_max,
            (points["X"].max() * self.x_scale) + self.x_offset,
        )
        self.y_max = max(
            self.y_max,
            (points["Y"].max() * self.y_scale) + self.y_offset,
        )
        self.z_max = max(
            self.z_max,
            (points["Z"].max() * self.z_scale) + self.z_offset,
        )
        self.x_min = min(
            self.x_min,
            (points["X"].min() * self.x_scale) + self.x_offset,
        )
        self.y_min = min(
            self.y_min,
            (points["Y"].min() * self.y_scale) + self.y_offset,
        )
        self.z_min = min(
            self.z_min,
            (points["Z"].min() * self.z_scale) + self.z_offset,
        )

        for return_number, count in zip(
            *np.unique(points.return_number, return_counts=True)
        ):
            if return_number == 0:
                continue
            if return_number > len(self.number_of_points_by_return):
                break  # np.unique sorts unique values
            self.number_of_points_by_return[return_number - 1] += count
        self.point_count += len(points)

    def set_compressed(self, state: bool) -> None:
        self.are_points_compressed = state

    def max_point_count(self) -> int:
        if self.version <= Version(1, 3):
            return np.iinfo(np.uint32).max
        else:
            return np.iinfo(np.uint64).max

    @classmethod
    def read_from(
        cls, original_stream: BinaryIO, read_evlrs: bool = False
    ) -> "LasHeader":
        """
        Reads the header from the stream

        read_evlrs: If true, evlrs will be read

        Leaves the stream pos right before the point starts
        (regardless of is read_evlrs was true)

        """
        little_endian = "little"
        header = cls()

        stream = io.BytesIO(cls._prefetch_header_data(original_stream))

        file_sig = stream.read(4)
        # This should not be possible as _prefetch already checks this
        assert file_sig == LAS_FILE_SIGNATURE

        header.file_source_id = int.from_bytes(
            stream.read(2), little_endian, signed=False
        )
        header.global_encoding = GlobalEncoding.read_from(stream)

        header.uuid = UUID(bytes_le=stream.read(16))
        header._version = Version(
            int.from_bytes(stream.read(1), little_endian, signed=False),
            int.from_bytes(stream.read(1), little_endian, signed=False),
        )

        header.system_identifier = read_string(stream, SYSTEM_IDENTIFIER_LEN)
        header.generating_software = read_string(stream, GENERATING_SOFTWARE_LEN)

        creation_day_of_year = int.from_bytes(
            stream.read(2), little_endian, signed=False
        )
        creation_year = int.from_bytes(stream.read(2), little_endian, signed=False)
        try:
            header.creation_date = date(creation_year, 1, 1) + timedelta(
                creation_day_of_year - 1
            )
        except ValueError:
            header.creation_date = None

        header_size = int.from_bytes(stream.read(2), little_endian, signed=False)
        header.offset_to_point_data = int.from_bytes(
            stream.read(4), little_endian, signed=False
        )
        number_of_vlrs = int.from_bytes(stream.read(4), little_endian, signed=False)

        point_format_id = int.from_bytes(stream.read(1), little_endian, signed=False)
        point_size = int.from_bytes(stream.read(2), little_endian, signed=False)

        header.point_count = int.from_bytes(stream.read(4), little_endian, signed=False)
        for i in range(5):
            header.number_of_points_by_return[i] = int.from_bytes(
                stream.read(4), little_endian, signed=False
            )

        for i in range(3):
            header.scales[i] = struct.unpack("<d", stream.read(8))[0]
        for i in range(3):
            header.offsets[i] = struct.unpack("<d", stream.read(8))[0]
        for i in range(3):
            header.maxs[i] = struct.unpack("<d", stream.read(8))[0]
            header.mins[i] = struct.unpack("<d", stream.read(8))[0]

        if header.version.minor >= 3:
            header.start_of_waveform_data_packet_record = int.from_bytes(
                stream.read(8), little_endian, signed=False
            )
        if header.version.minor >= 4:
            header.start_of_first_evlr = int.from_bytes(
                stream.read(8), little_endian, signed=False
            )
            header.number_of_evlrs = int.from_bytes(
                stream.read(4), little_endian, signed=False
            )
            header.point_count = int.from_bytes(
                stream.read(8), little_endian, signed=False
            )
            for i in range(15):
                header.number_of_points_by_return[i] = int.from_bytes(
                    stream.read(8), little_endian, signed=False
                )

        current_pos = stream.tell()
        if current_pos < header_size:
            header.extra_header_bytes = stream.read(header_size - current_pos)
        elif current_pos > header_size:
            raise LaspyException("Incoherent header size")

        header._vlrs = VLRList.read_from(stream, num_to_read=number_of_vlrs)

        current_pos = stream.tell()
        if current_pos < header.offset_to_point_data:
            header.extra_vlr_bytes = stream.read(
                header.offset_to_point_data - current_pos
            )
        elif current_pos > header.offset_to_point_data:
            raise LaspyException("Incoherent offset to point data")

        header.are_points_compressed = is_point_format_compressed(point_format_id)
        point_format_id = compressed_id_to_uncompressed(point_format_id)
        point_format = PointFormat(point_format_id)
        try:
            extra_bytes_vlr = typing.cast(
                ExtraBytesVlr, header._vlrs.get("ExtraBytesVlr")[0]
            )
        except IndexError:
            pass
        else:
            if point_size == point_format.size:
                logger.warning(
                    "There is an ExtraByteVlr but the header.point_size matches the "
                    "point size without extra bytes. The extra bytes vlr info will be ignored"
                )
                header._vlrs.extract("ExtraBytesVlr")
            else:
                for extra_dim_info in extra_bytes_vlr.type_of_extra_dims():
                    point_format.add_extra_dimension(extra_dim_info)
        header._point_format = point_format

        if point_size > point_format.size:
            # We have unregistered extra bytes
            num_extra_bytes = point_size - point_format.size
            point_format.dimensions.append(
                dims.DimensionInfo(
                    name="ExtraBytes",
                    kind=dims.DimensionKind.UnsignedInteger,
                    num_bits=8 * num_extra_bytes,
                    num_elements=num_extra_bytes,
                    is_standard=False,
                    description="Un-registered ExtraBytes",
                )
            )
        elif point_size < point_format.size:
            raise LaspyException(
                f"Incoherent point size, "
                f"header says {point_size} point_format created says {point_format.size}"
            )

        if read_evlrs:
            header.read_evlrs(original_stream)
            stream.seek(header.offset_to_point_data)

        return header

    def write_to(
        self,
        stream: BinaryIO,
        ensure_same_size: bool = False,
        encoding_errors: str = "strict",
    ) -> None:
        """
        ensure_same_size: if true this function will raise an internal error
        if the written header would change the offset to point data
        it originally had (meaning the file could become broken),
        Used when rewriting a header to update the file (new point count, mins, maxs, etc)
        """
        if self.point_count > self.max_point_count():
            raise LaspyException(
                f"Version {self.version} cannot save clouds with more than"
                f" {self.max_point_count()} points (current: {self.point_count})"
            )

        little_endian = "little"
        with io.BytesIO() as tmp:
            self._vlrs.write_to(tmp, encoding_errors=encoding_errors)
            vlr_bytes = tmp.getvalue()

        header_size = LAS_HEADERS_SIZE[str(self.version)]
        header_size += len(self.extra_header_bytes)
        new_offset_to_data = header_size + len(vlr_bytes) + len(self.extra_vlr_bytes)

        if ensure_same_size and new_offset_to_data != self.offset_to_point_data:
            raise LaspyException(
                "Internal error, writing header would change original offset to data"
                "and break the file"
            )
        self.offset_to_point_data = new_offset_to_data

        stream.write(LAS_FILE_SIGNATURE)
        stream.write(self.file_source_id.to_bytes(2, little_endian, signed=False))
        self.global_encoding.write_to(stream)
        stream.write(self.uuid.bytes_le)
        stream.write(self.version.major.to_bytes(1, little_endian, signed=False))
        stream.write(self.version.minor.to_bytes(1, little_endian, signed=False))

        was_truncated = write_string(
            stream,
            self.system_identifier,
            SYSTEM_IDENTIFIER_LEN,
            encoding_errors=encoding_errors,
        )
        if was_truncated:
            logger.warning(
                f"system identifier does not fit into the {SYSTEM_IDENTIFIER_LEN} maximum bytes,"
                f" it will be truncated"
            )

        was_truncated = write_string(
            stream,
            self.generating_software,
            GENERATING_SOFTWARE_LEN,
            encoding_errors=encoding_errors,
        )
        if was_truncated:
            logger.warning(
                f"generating software does not fit into the {GENERATING_SOFTWARE_LEN} maximum bytes,"
                f" it will be truncated"
            )

        if self.creation_date is None:
            self.creation_date = date.today()

        stream.write(
            self.creation_date.timetuple().tm_yday.to_bytes(
                2, little_endian, signed=False
            )
        )
        stream.write(self.creation_date.year.to_bytes(2, little_endian, signed=False))

        stream.write(header_size.to_bytes(2, little_endian, signed=False))
        stream.write(self.offset_to_point_data.to_bytes(4, little_endian, signed=False))
        stream.write(len(self._vlrs).to_bytes(4, little_endian, signed=False))

        point_format_id = self.point_format.id
        if self.are_points_compressed:
            point_format_id = uncompressed_id_to_compressed(point_format_id)
        stream.write(point_format_id.to_bytes(1, little_endian, signed=False))
        stream.write(self.point_format.size.to_bytes(2, little_endian, signed=False))

        # Point Count
        if self.version.minor >= 4:
            stream.write(int(0).to_bytes(4, little_endian, signed=False))
            for i in range(5):
                stream.write(int(0).to_bytes(4, little_endian, signed=False))
        else:
            stream.write(self.point_count.to_bytes(4, little_endian, signed=False))
            for i in range(5):
                stream.write(
                    int(self.number_of_points_by_return[i]).to_bytes(
                        4, little_endian, signed=False
                    )
                )

        for i in range(3):
            stream.write(struct.pack("<d", self.scales[i]))
        for i in range(3):
            stream.write(struct.pack("<d", self.offsets[i]))
        for i in range(3):
            stream.write(struct.pack("<d", self.maxs[i]))
            stream.write(struct.pack("<d", self.mins[i]))

        if self.version.minor >= 3:
            stream.write(
                self.start_of_waveform_data_packet_record.to_bytes(
                    8, little_endian, signed=False
                )
            )

        if self.version.minor >= 4:
            stream.write(
                self.start_of_first_evlr.to_bytes(8, little_endian, signed=False)
            )
            stream.write(self.number_of_evlrs.to_bytes(4, little_endian, signed=False))
            stream.write(self.point_count.to_bytes(8, little_endian, signed=False))
            for i in range(15):
                stream.write(
                    int(self.number_of_points_by_return[i]).to_bytes(
                        8, little_endian, signed=False
                    )
                )
        stream.write(self.extra_header_bytes)
        stream.write(vlr_bytes)
        stream.write(self.extra_vlr_bytes)

    def parse_crs(self, prefer_wkt=True) -> Optional["pyproj.CRS"]:
        """
        Method to parse OGC WKT or GeoTiff VLR keys into a pyproj CRS object

        Returns None if no CRS VLR is present, or if the CRS specified
        in the VLRS is not understood.


        Parameters
        ----------
        prefer_wkt: Optional, default True,
            If True the WKT VLR will be preferred in case
            both the WKT and Geotiff VLR are present

        .. warning::
            This requires `pyproj`.

        .. versionadded:: 2.5
            The ``prefer_wkt`` parameters.
        """

        geo_vlr = self._vlrs.get_by_id("LASF_Projection")

        if self.evlrs is not None:
            geo_vlr.extend(self.evlrs.get_by_id("LASF_Projection"))

        parsed_crs = {}
        for rec in geo_vlr:
            if isinstance(rec, (WktCoordinateSystemVlr, GeoKeyDirectoryVlr)):
                crs = rec.parse_crs()
                if crs is not None:
                    parsed_crs[type(rec)] = crs

        # Could not parse anything / there was nothing to parse
        if not parsed_crs:
            return None

        if prefer_wkt:
            preferred, other = WktCoordinateSystemVlr, GeoKeyDirectoryVlr
        else:
            preferred, other = GeoKeyDirectoryVlr, WktCoordinateSystemVlr

        try:
            return parsed_crs[preferred]
        except KeyError:
            return parsed_crs[other]

    def read_evlrs(self, stream):
        """
        Reads EVLRs from the stream and sets them in the
        data property.

        The evlrs are accessed from the `evlrs` property

        Does nothing if either of these is true:
            - The file does not support EVLRS (version < 1.4)
            - The file has no EVLRS
            - The stream does not support seeking

        Leaves/restores the stream position to where it was before the call
        """
        if self.version.minor >= 4:
            if self.number_of_evlrs > 0 and stream.seekable():
                saved_pos = stream.tell()
                stream.seek(self.start_of_first_evlr, io.SEEK_SET)
                self.evlrs = VLRList.read_from(
                    stream, self.number_of_evlrs, extended=True
                )
                stream.seek(saved_pos)
            elif self.number_of_evlrs > 0 and not stream.seekable():
                self.evlrs = None
            else:
                self.evlrs = VLRList()
        else:
            self.evlrs = None

    @staticmethod
    def _prefetch_header_data(source) -> bytes:
        """
        reads (and returns) from the source all the bytes that
        are between the beginning of the file and the start of point data
        (which corresponds to Header + VLRS).

        It is done in two calls to the source's `read` method

        This is done because `LasHeader.read_from`
        does a bunch of read to the source, so we prefer to
        prefetch data in memory in case the original source
        is not buffered (like a http source could be)
        """
        header_bytes = source.read(LAS_HEADERS_SIZE["1.1"])

        file_sig = header_bytes[: len(LAS_FILE_SIGNATURE)]
        if not file_sig:
            raise LaspyException(f"Source is empty")
        if file_sig != LAS_FILE_SIGNATURE:
            raise LaspyException(f'Invalid file signature "{file_sig}"')
        if len(header_bytes) < LAS_HEADERS_SIZE["1.1"]:
            raise LaspyException("File is to small to be a valid LAS")

        offset_to_data = int.from_bytes(
            header_bytes[96 : 96 + 4], byteorder="little", signed=False
        )

        rest = source.read(offset_to_data - len(header_bytes))

        return header_bytes + rest

    def _sync_extra_bytes_vlr(self) -> None:
        try:
            self._vlrs.extract("ExtraBytesVlr")
        except IndexError:
            pass

        extra_dimensions = list(self.point_format.extra_dimensions)
        if not extra_dimensions:
            return

        eb_vlr = ExtraBytesVlr()
        for extra_dimension in extra_dimensions:
            dtype = extra_dimension.dtype
            assert dtype is not None

            eb_struct = ExtraBytesStruct(
                name=extra_dimension.name.encode(),
                description=extra_dimension.description.encode(),
            )

            if extra_dimension.num_elements > 3 and dtype.base == np.uint8:
                type_id = 0
                eb_struct.options = extra_dimension.num_elements
            else:
                type_id = extradims.get_id_for_extra_dim_type(dtype)

            eb_struct.data_type = type_id
            eb_struct.scale = extra_dimension.scales
            eb_struct.offset = extra_dimension.offsets

            eb_vlr.extra_bytes_structs.append(eb_struct)

        self._vlrs.append(eb_vlr)

    # To keep some kind of backward compatibility
    @property
    def major_version(self) -> int:
        return self.version.major

    @property
    def minor_version(self) -> int:
        return self.version.minor

    def __getattr__(self, item):
        try:
            return getattr(self, self._OLD_LASPY_NAMES[item])
        except KeyError:
            raise AttributeError(f"No attribute {item} in LasHeader") from None

    def __setattr__(self, key, value):
        try:
            return setattr(self, self._OLD_LASPY_NAMES[key], value)
        except KeyError:
            super().__setattr__(key, value)

    def __repr__(self) -> str:
        return f"<LasHeader({self.version.major}.{self.version.minor}, {self.point_format})>"


LAS_HEADERS_SIZE = {
    "1.1": 227,
    "1.2": 227,
    "1.3": 235,
    "1.4": 375,
}
