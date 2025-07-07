"""The definition of the VLR Header, VLR, the KnownVLRs
are in this module.

A KnownVLR is a VLR for which we know how to parse its record_data
"""

import abc
import ctypes
import logging
import struct
from copy import copy
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar, Union

import numpy as np

from ..extradims import get_dtype_for_extra_dim
from ..point.dims import ScaledArrayView
from ..point.format import ExtraBytesParams
from ..point.record import PackedPointRecord
from ..utils import encode_to_null_terminated
from .vlr import VLR, BaseVLR

abstractmethod = abc.abstractmethod

logger = logging.getLogger(__name__)

NULL_BYTE = b"\0"

GeoKeyDirectoryType = TypeVar("GeoKeyDirectoryType", bound="GeoKeyDirectoryVlr")
GeoAsciiParamsType = TypeVar("GeoAsciiParamsType", bound="GeoAsciiParamsVlr")


class IKnownVLR(abc.ABC):
    """Interface that any KnownVLR must implement.
    A KnownVLR is a VLR for which we know how to parse its record_data

    Implementing this interfaces allows to automatically call the
    right parser for the right VLR when reading them.
    """

    @staticmethod
    @abstractmethod
    def official_user_id() -> str:
        """Shall return the official user_id as described in the documentation"""
        pass

    @staticmethod
    @abstractmethod
    def official_record_ids() -> Tuple[int, ...]:
        """Shall return the official record_id for the VLR

        .. note::

            Even if the VLR has one record_id, the return type must be a tuple

        Returns
        -------
        tuple of int
            The record_ids this VLR type can have
        """
        pass

    @abstractmethod
    def record_data_bytes(self) -> bytes:
        """Shall return the bytes corresponding to the record_data part of the VLR
        as they should be written in the file.

        Returns
        -------
        bytes
            The bytes of the vlr's record_data

        """
        pass

    @abstractmethod
    def parse_record_data(self, record_data: bytes) -> None:
        """Shall parse the given record_data into a user-friendlier structure

        Parameters
        ----------
        record_data: bytes
            The record_data bytes read from the file

        """
        pass


class BaseKnownVLR(BaseVLR, IKnownVLR, abc.ABC):
    """Base Class to factorize common code between the different type of Known VLRs"""

    def __init__(self, record_id=None, description=""):
        super().__init__(
            self.official_user_id(),
            self.official_record_ids()[0] if record_id is None else record_id,
            description,
        )

    @classmethod
    def from_raw(cls, raw: VLR):
        know_vlr = cls()
        know_vlr._description = raw.description
        know_vlr.parse_record_data(raw.record_data)
        return know_vlr


class ClassificationLookupVlr(BaseKnownVLR):
    """This vlr maps class numbers to short descriptions / names

    >>> lookup = ClassificationLookupVlr()
    >>> lookup[0] = "never_classified"
    >>> lookup[2] = "ground"
    >>> lookup[0]
    'never_classified'
    """

    _lookup_struct = struct.Struct("<B15s")

    def __init__(self):
        super().__init__(description="Classification Lookup")
        self.lookups: Dict[int, str] = {}

    def parse_record_data(self, record_data: bytes) -> None:
        for class_id, desc in struct.iter_unpack("<B15s", record_data):
            # index using desc[i:i+1], because desc[i] gives an int, and we want a byte
            description = b"".join(
                desc[i : i + 1]
                for i in range(len(desc))
                if desc[i : i + 1].isalnum() or desc[i : i + 1] == b" "
            ).decode()
            self.lookups[class_id] = description

    def record_data_bytes(self) -> bytes:
        def lookup_converter(lookup_dict):
            for class_id, description in lookup_dict.items():
                description_bytes = description.encode("ascii")
                if len(description_bytes) > 15:
                    raise ValueError(
                        "decription ({}) is to long ({} bytes), it must not exceed 15 bytes when encoded".format(
                            description, len(description_bytes)
                        )
                    )
                yield class_id, description_bytes

        return b"".join(
            self._lookup_struct.pack(class_id, desc)
            for class_id, desc in lookup_converter(self.lookups)
        )

    def __getitem__(self, class_id: int) -> str:
        return self.lookups[class_id]

    def __setitem__(self, class_id: int, description: str):
        if class_id not in range(256):
            raise ValueError("Class id {} is not in range [0, 255]".format(class_id))

        self.lookups[class_id] = description

    @staticmethod
    def official_user_id() -> str:
        return "LASF_Spec"

    @staticmethod
    def official_record_ids() -> Tuple[int, ...]:
        return (0,)


class LasZipVlr(BaseKnownVLR):
    """Contains the information needed by laszip (or any other laz backend)
    to compress the point records.
    """

    def __init__(self, data: bytes) -> None:
        super().__init__(description="http://laszip.org")
        self.record_data = data

    def parse_record_data(self, record_data: bytes) -> None:
        # Only laz backends know how to parse this
        pass

    def record_data_bytes(self) -> bytes:
        return self.record_data

    @staticmethod
    def official_user_id() -> str:
        return "laszip encoded"

    @staticmethod
    def official_record_ids() -> Tuple[int, ...]:
        return (22204,)

    @classmethod
    def from_raw(cls, raw_vlr):
        return cls(raw_vlr.record_data)


class ExtraBytesStruct(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("reserved", ctypes.c_uint8 * 2),
        ("data_type", ctypes.c_uint8),
        ("options", ctypes.c_uint8),
        ("name", ctypes.c_char * 32),
        ("unused", ctypes.c_uint8 * 4),
        ("_no_data", (ctypes.c_byte * 8) * 3),
        ("_min", (ctypes.c_byte * 8) * 3),
        ("_max", (ctypes.c_byte * 8) * 3),
        ("_scale", ctypes.c_double * 3),
        ("_offset", ctypes.c_double * 3),
        ("description", ctypes.c_char * 32),
    ]

    _uint64t_struct = struct.Struct("<Q")
    _int64t_struct = struct.Struct("<q")
    _double_struct = struct.Struct("<d")

    NO_DATA_BIT_MASK = 0b000_0001
    MIN_BIT_MASK = 0b0000_0010
    MAX_BIT_MASK = 0b0000_0100
    SCALE_BIT_MASK = 0b000_1000
    OFFSET_BIT_MASK = 0b0001_0000

    def __init__(
        self,
        name: bytes,
        data_type: Union[int, Tuple[int, int]],
        description: bytes = b"",
        scale: Optional[np.ndarray] = None,
        offset: Optional[np.ndarray] = None,
        no_data: Optional[np.ndarray] = None,
    ) -> None:

        if isinstance(data_type, Tuple):
            options = data_type[1]
            data_type = data_type[0]
        else:
            options = 0

        super().__init__(
            name=name, description=description, data_type=data_type, options=options
        )

        if self.data_type != 0:
            self.scale = scale
            self.offset = offset
            self.no_data = no_data

            self.options |= self.MIN_BIT_MASK
            self.options |= self.MAX_BIT_MASK

            self.partial_reset()

    def _long_type(self):
        data_type = ((self.data_type - 1) % 10) + 1
        if data_type in [2, 4, 6, 8]:
            long_type = np.int64
        elif data_type in [9, 10]:
            long_type = np.float64
        elif data_type in [1, 3, 5, 7]:
            long_type = np.uint64
        else:
            raise NotImplementedError

        return long_type

    def _parse_special_property(self, name) -> np.ndarray:
        dtype = self.dtype().base
        long_type = self._long_type()
        return np.frombuffer(getattr(self, name), dtype=long_type)[
            : self.num_elements()
        ].astype(dtype)

    @property
    def no_data(self):
        if self.options & self.NO_DATA_BIT_MASK != 0:
            return self._parse_special_property("_no_data")
        return None

    @no_data.setter
    def no_data(self, value):
        if value is None:
            self.options &= ~self.NO_DATA_BIT_MASK
        else:
            dtype = self._long_type()
            num_elements = self.num_elements()
            ptrs = [
                np.array([v])
                .astype(dtype)
                .ctypes.data_as(ctypes.POINTER((ctypes.c_byte * 8)))[0]
                for v in value[:num_elements]
            ]
            self._no_data[:num_elements] = ptrs
            self.options |= self.NO_DATA_BIT_MASK

    @property
    def min(self):
        if not self.min_is_relevant():
            return None

        min = self._parse_special_property("_min")

        scale = self.scale
        if scale is not None:
            min = min * scale

        offset = self.offset
        if offset is not None:
            min = min + offset

        return min

    @property
    def max(self):
        if not self.max_is_relevant():
            return None

        max = self._parse_special_property("_max")

        scale = self.scale
        if scale is not None:
            max = max * scale

        offset = self.offset
        if offset is not None:
            max = max + offset

        return max

    @property
    def offset(self) -> Optional[Any]:
        if self.options & self.OFFSET_BIT_MASK != 0:
            return self._offset[: self.num_elements()]
        return None

    @offset.setter
    def offset(self, value):
        if value is None:
            self.options &= ~self.OFFSET_BIT_MASK
        else:
            num_elements = self.num_elements()
            self._offset[:num_elements] = value[:num_elements]
            self.options |= self.OFFSET_BIT_MASK

    @property
    def scale(self):
        if self.options & self.SCALE_BIT_MASK != 0:
            return self._scale[: self.num_elements()]
        return None

    @scale.setter
    def scale(self, value):
        if value is None:
            self.options &= ~self.SCALE_BIT_MASK
        else:
            num_elements = self.num_elements()
            self._scale[:num_elements] = value[:num_elements]
            self.options |= self.SCALE_BIT_MASK

    def format_name(self):
        return self.name.rstrip(NULL_BYTE).decode()

    def dtype(self) -> np.dtype:
        if self.data_type == 0:
            if self.options == 1:
                # numpy says doing '1u1' is deprecated
                return np.dtype("u1")
            return np.dtype(f"{self.options}u1")
        return get_dtype_for_extra_dim(self.data_type)

    def num_elements(self) -> int:
        if self.data_type == 0:
            return self.options
        elif self.data_type <= 10:
            return 1
        elif self.data_type <= 20:
            return 2
        else:
            return 3

    def min_is_relevant(self):
        return self.options & self.MIN_BIT_MASK != 0

    def max_is_relevant(self):
        return self.options & self.MAX_BIT_MASK != 0

    def _raw_min(self):
        if self.min_is_relevant():
            return np.frombuffer(self._min, dtype=self._long_type())[
                : self.num_elements()
            ]
        return None

    def _raw_max(self):
        if self.max_is_relevant():
            return np.frombuffer(self._max, dtype=self._long_type())[
                : self.num_elements()
            ]
        return None

    def grow(self, points: PackedPointRecord):
        if self.data_type == 0:
            # The data type is not specified (treated as raw bytes)
            # So we don't try to track min / max
            return

        if not self.min_is_relevant() and not self.max_is_relevant():
            return

        try:
            pts = points[self.format_name()]
        except ValueError:
            # The points did not contain the field
            return

        num_elements = self.num_elements()
        long_type = self._long_type()
        no_data = self.no_data

        local_min = np.zeros(num_elements, dtype=long_type)
        local_max = np.zeros(num_elements, dtype=long_type)

        for i in range(num_elements):
            if no_data is not None:
                valid_indices = pts[..., i] != no_data[i]
                if valid_indices.ndim == 0:
                    return
                sub_pts = pts[valid_indices, i]
            else:
                sub_pts = pts[..., i]

            if self.min_is_relevant():
                if isinstance(sub_pts, ScaledArrayView):
                    local_min[i] = sub_pts.array.min()
                else:
                    local_min[i] = sub_pts.min()

            if self.max_is_relevant():
                if isinstance(sub_pts, ScaledArrayView):
                    local_max[i] = sub_pts.array.max()
                else:
                    local_max[i] = sub_pts.max()

        if self.min_is_relevant():
            raw_min = self._raw_min()
            v = np.min([raw_min, local_min], axis=0)
            raw_min[:] = v.astype(long_type)[:]

        if self.max_is_relevant():
            raw_max = self._raw_max()
            v = np.max([raw_max, local_max], axis=0)
            raw_max[:] = v.astype(long_type)[:]

    def partial_reset(self):
        long_type = self._long_type()

        if long_type == np.float64 or long_type == np.float32:
            info = np.finfo(long_type)
        else:
            info = np.iinfo(long_type)

        num_elements = self.num_elements()
        np.frombuffer(self._min, dtype=long_type)[:num_elements] = info.max
        np.frombuffer(self._max, dtype=long_type)[:num_elements] = info.min

    @staticmethod
    def size():
        return ctypes.sizeof(ExtraBytesStruct)

    def __repr__(self):
        return "<ExtraBytesStruct({}, {}, {})>".format(
            self.format_name(), self.data_type, self.description
        )


class ExtraBytesVlr(BaseKnownVLR):
    def __init__(self):
        super().__init__(description="Extra Bytes Record")
        self.extra_bytes_structs: List[ExtraBytesStruct] = []

    def parse_record_data(self, data):
        if (len(data) % ExtraBytesStruct.size()) != 0:
            raise ValueError(
                "Data length of ExtraBytes vlr must be a multiple of {}".format(
                    ExtraBytesStruct.size()
                )
            )
        num_extra_bytes_structs = len(data) // ExtraBytesStruct.size()
        self.extra_bytes_structs = [None] * num_extra_bytes_structs
        for i in range(num_extra_bytes_structs):
            self.extra_bytes_structs[i] = ExtraBytesStruct.from_buffer_copy(
                data[ExtraBytesStruct.size() * i : ExtraBytesStruct.size() * (i + 1)]
            )

    def record_data_bytes(self):
        return b"".join(
            bytes(extra_struct) for extra_struct in self.extra_bytes_structs
        )

    def type_of_extra_dims(self) -> List[ExtraBytesParams]:
        dim_info_list: List[ExtraBytesParams] = []
        for eb_struct in self.extra_bytes_structs:
            num_elements = eb_struct.num_elements()

            scales = eb_struct.scale
            offsets = eb_struct.offset

            if scales is not None or offsets is not None:
                # If one of scales or offsets is defined,
                # we expect the other to be as well
                # so set default scales or offsets
                if offsets is None:
                    offsets = np.zeros(num_elements, np.float64)
                else:
                    offsets = np.array(offsets[:num_elements])

                if scales is None:
                    scales = np.ones(num_elements, np.float64)
                else:
                    scales = np.array(scales[:num_elements])

            dim_info_list.append(
                ExtraBytesParams(
                    eb_struct.format_name(),
                    eb_struct.dtype(),
                    description=eb_struct.description.rstrip(NULL_BYTE).decode(),
                    scales=scales,
                    offsets=offsets,
                )
            )
        return dim_info_list

    def grow(self, points: PackedPointRecord):
        for eb_struct in self.extra_bytes_structs:
            eb_struct.grow(points)

    def partial_reset(self):
        for eb_struct in self.extra_bytes_structs:
            eb_struct.partial_reset()

    def __repr__(self):
        return "<ExtraBytesVlr(extra bytes structs: {})>".format(
            len(self.extra_bytes_structs)
        )

    @staticmethod
    def official_user_id():
        return "LASF_Spec"

    @staticmethod
    def official_record_ids():
        return (4,)


class WaveformPacketStruct(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("bits_per_sample", ctypes.c_ubyte),
        ("waveform_compression_type", ctypes.c_ubyte),
        ("number_of_samples", ctypes.c_uint32),
        ("temporal_sample_spacing", ctypes.c_uint32),
        ("digitizer_gain", ctypes.c_double),
        ("digitizer_offset", ctypes.c_double),
    ]

    @staticmethod
    def size():
        return ctypes.sizeof(WaveformPacketStruct)


class WaveformPacketVlr(BaseKnownVLR):
    def __init__(self, record_id, description=""):
        super().__init__(record_id=record_id, description=description)
        self.parsed_record = None

    def parse_record_data(self, record_data):
        self.parsed_record = WaveformPacketStruct.from_buffer_copy(record_data)

    def record_data_bytes(self):
        return bytes(self.parsed_record)

    @staticmethod
    def official_record_ids():
        return range(100, 356)

    @staticmethod
    def official_user_id():
        return "LASF_Spec"

    @classmethod
    def from_raw(cls, raw_vlr):
        vlr = cls(raw_vlr.record_id, description=raw_vlr.description)
        vlr._description = raw_vlr.description
        vlr.parse_record_data(raw_vlr.record_data)
        return vlr


class GeoKeyEntryStruct(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        # Id of the key
        #
        # Ids are broken down in sub domains:
        # [    0,  1023]       Reserved
        # [ 1024,  2047]       GeoTIFF Configuration Keys
        # [ 2048,  3071]       Geographic/Geocentric CS Parameter Keys
        # [ 3072,  4095]       Projected CS Parameter Keys
        # [ 4096,  5119]       Vertical CS Parameter Keys
        # [ 5120, 32767]       Reserved
        # [32768, 65535]       Private use
        ("id", ctypes.c_uint16),
        # Where to find the data for the key:
        # 0 => The _actual_ value is stored directly in the "value_offset" member
        # Otherwise, the tiff tag location is the record_id of the VLR in which the value is stored.
        # In the case of LAS files the 2 possible values are `34736`, `34737`.
        ("tiff_tag_location", ctypes.c_uint16),
        # Number of values in the key.
        # Implied to be `1` if `tiff_tag_location` is 0
        ("count", ctypes.c_uint16),
        # Depending on `tiff_tag_location`, this contains either
        # the value itself _or_ the offset in the record_data of the containing VLR
        ("value_offset", ctypes.c_uint16),
    ]

    @staticmethod
    def size():
        return ctypes.sizeof(GeoKeysHeaderStructs)

    def __repr__(self):
        return "<GeoKey(Id: {}, Location: {}, count: {}, offset: {})>".format(
            self.id, self.tiff_tag_location, self.count, self.value_offset
        )


class GeoKeysHeaderStructs(ctypes.LittleEndianStructure):
    _pack_ = 1
    _fields_ = [
        ("key_directory_version", ctypes.c_uint16),
        ("key_revision", ctypes.c_uint16),
        ("minor_revision", ctypes.c_uint16),
        ("number_of_keys", ctypes.c_uint16),
    ]

    def __init__(self):
        super().__init__(
            key_directory_version=1, key_revision=1, minor_revision=0, number_of_keys=0
        )

    @staticmethod
    def size():
        return ctypes.sizeof(GeoKeysHeaderStructs)

    def __repr__(self):
        return "<GeoKeysHeader(vers: {}, rev:{}, minor: {}, num_keys: {})>".format(
            self.key_directory_version,
            self.key_revision,
            self.minor_revision,
            self.number_of_keys,
        )


class GeoKeyDirectoryVlr(BaseKnownVLR):
    def __init__(self):
        super().__init__(description="GeoTIFF GeoKeyDirectoryTag")
        self.geo_keys_header = GeoKeysHeaderStructs()
        self.geo_keys = [GeoKeyEntryStruct()]

    def parse_record_data(self, record_data):
        record_data = bytearray(record_data)
        header_data = record_data[: ctypes.sizeof(GeoKeysHeaderStructs)]
        self.geo_keys_header = GeoKeysHeaderStructs.from_buffer(header_data)
        self.geo_keys = []
        keys_data = record_data[GeoKeysHeaderStructs.size() :]
        num_keys = (
            len(record_data[GeoKeysHeaderStructs.size() :]) // GeoKeyEntryStruct.size()
        )
        if num_keys != self.geo_keys_header.number_of_keys:
            self.geo_keys_header.number_of_keys = num_keys

        for i in range(self.geo_keys_header.number_of_keys):
            data = keys_data[
                (i * GeoKeyEntryStruct.size()) : (i + 1) * GeoKeyEntryStruct.size()
            ]
            self.geo_keys.append(GeoKeyEntryStruct.from_buffer(data))

    def record_data_bytes(self):
        b = bytes(self.geo_keys_header)
        b += b"".join(map(bytes, self.geo_keys))
        return b

    def parse_crs(self):
        import pyproj

        # TODO import is done here to avoid cyclic import,
        # this should probably be fixed
        from .geotiff import GeographicTypeGeoKey, ProjectedCSTypeGeoKey

        geographic_cs = None
        projected_cs = None
        for key in self.geo_keys:
            if key.id == ProjectedCSTypeGeoKey.id:
                if 1024 <= key.value_offset <= 32766:
                    # http://docs.opengeospatial.org/is/19-008r4/19-008r4.html#_requirements_class_projectedcrsgeokey
                    # "ProjectedCRSGeoKey values in the range 1024-32766 SHALL be EPSG Projected CRS Codes"
                    projected_cs = pyproj.CRS.from_epsg(key.value_offset)
            elif key.id == GeographicTypeGeoKey.id:
                # http://docs.opengeospatial.org/is/19-008r4/19-008r4.html#_requirements_class_geodeticcrsgeokey
                # GeodeticCRSGeoKey values in the range 1024-32766 SHALL be EPSG geographic 2D or geocentric CRS codes
                if 1024 <= key.value_offset <= 32766:
                    geographic_cs = pyproj.CRS.from_epsg(key.value_offset)

        # Projected Coordinate Systems take precedence since,
        # if they are present, the Geographic CS is probably
        # redundant and the positioning information in the LAS
        # file is projected.
        return projected_cs or geographic_cs

    def __repr__(self):
        return "<{}({} geo_keys)>".format(self.__class__.__name__, len(self.geo_keys))

    @staticmethod
    def official_user_id():
        return "LASF_Projection"

    @staticmethod
    def official_record_ids():
        return (34735,)


class GeoDoubleParamsVlr(BaseKnownVLR):
    """
    Stores all of the `double` valued GeoKeys.
    """

    def __init__(self):
        super().__init__(description="GeoTIFF GeoDoubleParamsTag")
        self.doubles = []

    def parse_record_data(self, record_data):
        sizeof_double = ctypes.sizeof(ctypes.c_double)
        if len(record_data) % sizeof_double != 0:
            raise ValueError(
                "GeoDoubleParams record data length () is not a multiple of sizeof(double) ()".format(
                    len(record_data), sizeof_double
                )
            )
        record_data = bytearray(record_data)
        num_doubles = len(record_data) // sizeof_double
        for i in range(num_doubles):
            b = record_data[i * sizeof_double : (i + 1) * sizeof_double]
            self.doubles.append(ctypes.c_double.from_buffer(b))

    def record_data_bytes(self):
        return b"".join(map(bytes, self.doubles))

    def __repr__(self):
        return "<GeoDoubleParamsVlr({})>".format(self.doubles)

    @staticmethod
    def official_user_id():
        return "LASF_Projection"

    @staticmethod
    def official_record_ids():
        return (34736,)


class GeoAsciiParamsVlr(BaseKnownVLR):
    """
    Stores all of the `ASCII` valued GeoKeys.

    From GeoTIFF's spec:
    To avoid problems with naive tiff dump programs the separator between geokeys is not
    the null-terminator `\0` but `|`.

    """

    def __init__(self):
        super().__init__(description="GeoTIFF GeoAsciiParamsTag")
        self.strings = []

    def parse_record_data(self, record_data):
        self.strings = [s.decode("ascii") for s in record_data.split(NULL_BYTE)]
        self.rd = record_data

    def record_data_bytes(self):
        return NULL_BYTE.join(s.encode("ascii") for s in self.strings)

    def __repr__(self):
        return "<GeoAsciiParamsVlr({})>".format(self.strings)

    @staticmethod
    def official_user_id():
        return "LASF_Projection"

    @staticmethod
    def official_record_ids():
        return (34737,)


class WktMathTransformVlr(BaseKnownVLR):
    """
    From the Spec:
        Note that the math transform WKT record is added for completeness, and a coordinate system WKT
        may or may not require a math transform WKT record

    """

    def __init__(self):
        super().__init__(description="")
        self.string = ""

    def _encode_string(self):
        return encode_to_null_terminated(self.string, codec="utf-8")

    def parse_record_data(self, record_data):
        self.string = record_data.decode("utf-8").rstrip("\0")

    def record_data_bytes(self):
        return self._encode_string()

    @staticmethod
    def official_user_id():
        return "LASF_Projection"

    @staticmethod
    def official_record_ids():
        return (2111,)


class WktCoordinateSystemVlr(BaseKnownVLR):
    """Replaces Coordinates Reference System for new las files (point fmt >= 5)
    "LAS is not using the “ESRI WKT”
    """

    def __init__(self, wkt_string=""):
        super().__init__(description="OGC Transformation Record")
        self.string = wkt_string

    def _encode_string(self):
        return encode_to_null_terminated(self.string, codec="utf-8")

    def parse_record_data(self, record_data):
        self.string = record_data.decode("utf-8").rstrip("\0")

    def record_data_bytes(self):
        return self._encode_string()

    def parse_crs(self):
        import pyproj

        if not self.string:
            return None

        return pyproj.CRS.from_wkt(self.string)

    @staticmethod
    def official_user_id():
        return "LASF_Projection"

    @staticmethod
    def official_record_ids():
        return (2112,)


def vlr_factory(vlr: VLR):
    """Given a vlr tries to find its corresponding KnownVLR class
    that can parse its data.
    If no KnownVLR implementation is found, returns the input vlr unchanged
    """
    user_id = vlr.user_id
    known_vlrs = BaseKnownVLR.__subclasses__()
    for known_vlr in known_vlrs:
        if (
            known_vlr.official_user_id() == user_id
            and vlr.record_id in known_vlr.official_record_ids()
        ):
            try:
                return known_vlr.from_raw(vlr)
            except Exception as err:
                logger.warning(f"Failed to parse {known_vlr}: {err}")
                return vlr

    return vlr
