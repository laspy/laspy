"""  This module contains things like the definitions of the point formats dimensions,
the mapping between dimension names and their type, mapping between point format and
compatible file version
"""

import abc
import collections
import operator
from collections import UserDict
from enum import Enum
from typing import (
    Any,
    Dict,
    Generic,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import numpy as np

from .. import errors
from . import packing

ValueType = TypeVar("ValueType")


class PointFormatDict(UserDict, Generic[ValueType]):
    """Simple wrapper around a dict that changes
    the exception raised when accessing a key that is not-present

    """

    def __init__(self, wrapped_dict: Dict[int, ValueType]):
        super().__init__(wrapped_dict)

    def __getitem__(self, key: int) -> ValueType:
        try:
            return self.data[key]
        except KeyError:
            raise errors.PointFormatNotSupported(key) from None


class SubField(NamedTuple):
    name: str
    mask: int


def _point_format_to_dtype(
    point_format: Iterable[str], dimensions_to_type: Mapping[str, np.dtype]
) -> np.dtype:
    """build the numpy.dtype for a point format

    Parameters:
    ----------
    point_format : iterable of str
        The dimensions names of the point format
    dimensions : dict
        The dictionary of dimensions
    Returns
    -------
    numpy.dtype
        The dtype for the input point format
    """
    return np.dtype(
        [(dim_name, dimensions_to_type[dim_name]) for dim_name in point_format]
    )


def _build_point_formats_dtypes(
    point_format_dimensions: Mapping[int, Tuple[str]],
    dimensions_dict: Mapping[str, np.dtype],
) -> Dict[int, np.dtype]:
    """Builds the dict mapping point format id to numpy.dtype
    In the dtypes, bit fields are still packed, and need to be unpacked each time
    you want to access them
    """
    return {
        fmt_id: _point_format_to_dtype(point_fmt, dimensions_dict)
        for fmt_id, point_fmt in point_format_dimensions.items()
    }


OLD_LASPY_NAMES = {
    "flag_byte": "bit_fields",
    "return_num": "return_number",
    "num_returns": "number_of_returns",
    "scan_dir_flag": "scan_direction_flag",
    "edge_flight_line": "edge_of_flight_line",
    "pt_src_id": "point_source_id",
    "wave_packet_desc_index": "wavepacket_index",
    "byte_offset_to_waveform_data": "wavepacket_offset",
    "waveform_packet_size": "wavepacket_size",
    "return_point_waveform_loc": "return_point_wave_location",
}

# Definition of the points dimensions and formats
# LAS version [1.0, 1.1, 1.2, 1.3, 1.4]
DIMENSIONS_TO_TYPE: Dict[str, np.dtype] = {
    "X": np.dtype("i4"),
    "Y": np.dtype("i4"),
    "Z": np.dtype("i4"),
    "intensity": np.dtype("u2"),
    "bit_fields": np.dtype("u1"),
    "raw_classification": np.dtype("u1"),
    "scan_angle_rank": np.dtype("i1"),
    "user_data": np.dtype("u1"),
    "point_source_id": np.dtype("u2"),
    "gps_time": np.dtype("f8"),
    "red": np.dtype("u2"),
    "green": np.dtype("u2"),
    "blue": np.dtype("u2"),
    # Waveform related dimensions
    "wavepacket_index": np.dtype("u1"),
    "wavepacket_offset": np.dtype("u8"),
    "wavepacket_size": np.dtype("u4"),
    "return_point_wave_location": np.dtype("f4"),
    "x_t": np.dtype("f4"),
    "y_t": np.dtype("f4"),
    "z_t": np.dtype("f4"),
    # Las 1.4
    "classification_flags": np.dtype("u1"),
    "scan_angle": np.dtype("i2"),
    "classification": np.dtype("u1"),
    "nir": np.dtype("u2"),
}

POINT_FORMAT_0: Tuple[str, ...] = (
    "X",
    "Y",
    "Z",
    "intensity",
    "bit_fields",
    "raw_classification",
    "scan_angle_rank",
    "user_data",
    "point_source_id",
)

POINT_FORMAT_6: Tuple[str, ...] = (
    "X",
    "Y",
    "Z",
    "intensity",
    "bit_fields",
    "classification_flags",
    "classification",
    "user_data",
    "scan_angle",
    "point_source_id",
    "gps_time",
)

WAVEFORM_FIELDS_NAMES: Tuple[str, ...] = (
    "wavepacket_index",
    "wavepacket_offset",
    "wavepacket_size",
    "return_point_wave_location",
    "x_t",
    "y_t",
    "z_t",
)

COLOR_FIELDS_NAMES: Tuple[str, ...] = ("red", "green", "blue")

POINT_FORMAT_DIMENSIONS = PointFormatDict(
    {
        0: POINT_FORMAT_0,
        1: POINT_FORMAT_0 + ("gps_time",),
        2: POINT_FORMAT_0 + COLOR_FIELDS_NAMES,
        3: POINT_FORMAT_0 + ("gps_time",) + COLOR_FIELDS_NAMES,
        4: POINT_FORMAT_0 + ("gps_time",) + WAVEFORM_FIELDS_NAMES,
        5: POINT_FORMAT_0 + ("gps_time",) + COLOR_FIELDS_NAMES + WAVEFORM_FIELDS_NAMES,
        6: POINT_FORMAT_6,
        7: POINT_FORMAT_6 + COLOR_FIELDS_NAMES,
        8: POINT_FORMAT_6 + COLOR_FIELDS_NAMES + ("nir",),
        9: POINT_FORMAT_6 + WAVEFORM_FIELDS_NAMES,
        10: POINT_FORMAT_6 + COLOR_FIELDS_NAMES + ("nir",) + WAVEFORM_FIELDS_NAMES,
    }
)

# sub fields of the 'bit_fields' dimension
RETURN_NUMBER_MASK_0 = 0b00000111
NUMBER_OF_RETURNS_MASK_0 = 0b00111000
SCAN_DIRECTION_FLAG_MASK_0 = 0b01000000
EDGE_OF_FLIGHT_LINE_MASK_0 = 0b10000000

# sub fields of the 'raw_classification' dimension
CLASSIFICATION_MASK_0 = 0b00011111
SYNTHETIC_MASK_0 = 0b00100000
KEY_POINT_MASK_0 = 0b01000000
WITHHELD_MASK_0 = 0b10000000

# sub fields of the bit_fields
RETURN_NUMBER_MASK_6 = 0b00001111
NUMBER_OF_RETURNS_MASK_6 = 0b11110000

# sub fields of classification flags
CLASSIFICATION_FLAGS_MASK_6 = 0b00001111

SYNTHETIC_MASK_6 = 0b00000001
KEY_POINT_MASK_6 = 0b00000010
WITHHELD_MASK_6 = 0b00000100
OVERLAP_MASK_6 = 0b00001000
SCANNER_CHANNEL_MASK_6 = 0b00110000
SCAN_DIRECTION_FLAG_MASK_6 = 0b01000000
EDGE_OF_FLIGHT_LINE_MASK_6 = 0b10000000

COMPOSED_FIELDS_0: Dict[str, List[SubField]] = {
    "bit_fields": [
        SubField("return_number", RETURN_NUMBER_MASK_0),
        SubField("number_of_returns", NUMBER_OF_RETURNS_MASK_0),
        SubField("scan_direction_flag", SCAN_DIRECTION_FLAG_MASK_0),
        SubField("edge_of_flight_line", EDGE_OF_FLIGHT_LINE_MASK_0),
    ],
    "raw_classification": [
        SubField("classification", CLASSIFICATION_MASK_0),
        SubField("synthetic", SYNTHETIC_MASK_0),
        SubField("key_point", KEY_POINT_MASK_0),
        SubField("withheld", WITHHELD_MASK_0),
    ],
}

COMPOSED_FIELDS_6: Dict[str, List[SubField]] = {
    "bit_fields": [
        SubField("return_number", RETURN_NUMBER_MASK_6),
        SubField("number_of_returns", NUMBER_OF_RETURNS_MASK_6),
    ],
    "classification_flags": [
        SubField("synthetic", SYNTHETIC_MASK_6),
        SubField("key_point", KEY_POINT_MASK_6),
        SubField("withheld", WITHHELD_MASK_6),
        SubField("overlap", OVERLAP_MASK_6),
        SubField("scanner_channel", SCANNER_CHANNEL_MASK_6),
        SubField("scan_direction_flag", SCAN_DIRECTION_FLAG_MASK_6),
        SubField("edge_of_flight_line", EDGE_OF_FLIGHT_LINE_MASK_6),
    ],
}

# Dict giving the composed fields for each point_format_id
COMPOSED_FIELDS = PointFormatDict(
    {
        0: COMPOSED_FIELDS_0,
        1: COMPOSED_FIELDS_0,
        2: COMPOSED_FIELDS_0,
        3: COMPOSED_FIELDS_0,
        4: COMPOSED_FIELDS_0,
        5: COMPOSED_FIELDS_0,
        6: COMPOSED_FIELDS_6,
        7: COMPOSED_FIELDS_6,
        8: COMPOSED_FIELDS_6,
        9: COMPOSED_FIELDS_6,
        10: COMPOSED_FIELDS_6,
    }
)

VERSION_TO_POINT_FMT: Dict[str, Tuple[int, ...]] = {
    "1.1": (0, 1),
    "1.2": (0, 1, 2, 3),
    "1.3": (0, 1, 2, 3, 4, 5),
    "1.4": (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
}

POINT_FORMATS_DTYPE = PointFormatDict(
    _build_point_formats_dtypes(POINT_FORMAT_DIMENSIONS, DIMENSIONS_TO_TYPE)
)
# This Dict maps point_format_ids to their dimensions names
ALL_POINT_FORMATS_DIMENSIONS = PointFormatDict({**POINT_FORMAT_DIMENSIONS})
# This Dict maps point_format_ids to their numpy.dtype
# the dtype corresponds to the de packed data
ALL_POINT_FORMATS_DTYPE = PointFormatDict({**POINT_FORMATS_DTYPE})


def get_sub_fields_dict(point_format_id: int) -> Dict[str, Tuple[str, SubField]]:
    sub_fields_dict = {}
    for composed_dim_name, sub_fields in COMPOSED_FIELDS[point_format_id].items():
        for sub_field in sub_fields:
            sub_fields_dict[sub_field.name] = (composed_dim_name, sub_field)
    return sub_fields_dict


class DimensionKind(Enum):
    SignedInteger = 0
    UnsignedInteger = 1
    FloatingPoint = 2
    BitField = 3

    @classmethod
    def from_letter(cls, letter: str) -> "DimensionKind":
        if letter == "u":
            return cls.UnsignedInteger
        elif letter == "i":
            return cls.SignedInteger
        elif letter == "f":
            return cls.FloatingPoint
        else:
            raise ValueError(f"Unknown type letter '{letter}'")

    def letter(self) -> Optional[str]:
        if self == DimensionKind.UnsignedInteger:
            return "u"
        elif self == DimensionKind.SignedInteger:
            return "i"
        elif self == DimensionKind.FloatingPoint:
            return "f"
        else:
            return None


def num_bit_set(n: int) -> int:
    """Count the number of bits that are set (1) in the number n

    Brian Kernighan's algorithm
    """
    count = 0
    while n != 0:
        count += 1
        n = n & (n - 1)
    return count


class DimensionInfo(NamedTuple):
    """Tuple that contains information of a dimension"""

    name: str
    kind: DimensionKind
    num_bits: int
    num_elements: int = 1
    is_standard: bool = True
    description: str = ""
    offsets: Optional[np.ndarray] = None
    scales: Optional[np.ndarray] = None

    @classmethod
    def from_extra_bytes_param(cls, params):
        me = cls(
            params.name,
            DimensionKind.from_letter(params.type.base.kind),
            params.type.itemsize * 8,
            params.type.shape[0] if params.type.ndim == 1 else 1,
            False,
            params.description,
            params.offsets,
            params.scales,
        )
        me._validate()
        return me

    @classmethod
    def from_dtype(
        cls,
        name: str,
        dtype: np.dtype,
        is_standard: bool = True,
        description: str = "",
        offsets: Optional[np.ndarray] = None,
        scales: Optional[np.ndarray] = None,
    ) -> "DimensionInfo":
        if dtype.ndim != 0:
            num_elements = dtype.shape[0]
        else:
            num_elements = 1

        kind = DimensionKind.from_letter(dtype.base.kind)
        num_bits = dtype.itemsize * 8

        self = cls(
            name,
            kind,
            num_bits,
            num_elements,
            is_standard,
            description=description,
            offsets=offsets,
            scales=scales,
        )
        self._validate()
        return self

    @classmethod
    def from_bitmask(
        cls, name: str, bit_mask: int, is_standard: bool = False
    ) -> "DimensionInfo":
        kind = DimensionKind.BitField
        bit_size = num_bit_set(bit_mask)
        return cls(name, kind, bit_size, is_standard=is_standard)

    @property
    def num_bytes(self) -> int:
        return int(self.num_bits // 8)

    @property
    def num_bytes_singular_element(self) -> int:
        return int(self.num_bits // (8 * self.num_elements))

    @property
    def is_scaled(self) -> bool:
        return self.scales is not None or self.offsets is not None

    @property
    def max(self):
        if self.kind == DimensionKind.BitField:
            return (2**self.num_bits) - 1
        elif self.kind == DimensionKind.FloatingPoint:
            return np.finfo(self.type_str()).max
        else:
            return np.iinfo(self.type_str()).max

    @property
    def min(self):
        if (
            self.kind == DimensionKind.BitField
            or self.kind == DimensionKind.UnsignedInteger
        ):
            return 0
        elif self.kind == DimensionKind.FloatingPoint:
            return np.finfo(self.type_str()).min
        else:
            return np.iinfo(self.type_str()).min

    def type_str(self) -> Optional[str]:
        if self.kind == DimensionKind.BitField:
            return None

        if self.num_elements == 1:
            return f"{self.kind.letter()}{self.num_bytes_singular_element}"
        return (
            f"{self.num_elements}{self.kind.letter()}{self.num_bytes_singular_element}"
        )

    @property
    def dtype(self) -> Optional[np.dtype]:
        type_str = self.type_str()
        if type_str is not None:
            return np.dtype(type_str)
        return None

    def __eq__(self, other: "DimensionInfo") -> bool:
        # Named Tuple implements that for us, but
        # when scales and offset are not None (thus are array)
        # The default '==' won't work
        # (ValueError, value of an array with more than one element is ambiguous)
        return (
            self.name == other.name
            and self.kind == other.kind
            and self.num_bits == other.num_bits
            and self.is_standard == other.is_standard
            and self.description == other.description
            and np.all(self.offsets == other.offsets)
            and np.all(self.scales == other.scales)
        )

    def __ne__(self, other: "DimensionInfo") -> bool:
        return not self == other

    def _validate(self):
        if (self.offsets is not None and self.scales is None) or (
            self.offsets is None and self.scales is not None
        ):
            raise ValueError("Cannot provide scales without offsets and vice-versa")

        if self.offsets is not None and len(self.offsets) != self.num_elements:
            raise ValueError(
                f"len(offsets) ({len(self.offsets)}) is not the same as the number of elements ({self.num_elements})"
            )

        if self.scales is not None and len(self.scales) != self.num_elements:
            raise ValueError(
                f"len(scales) ({len(self.scales)}) is not the same as the number of elements ({self.num_elements})"
            )


def size_of_point_format_id(point_format_id: int) -> int:
    return ALL_POINT_FORMATS_DTYPE[point_format_id].itemsize


def preferred_file_version_for_point_format(point_format_id: int) -> str:
    def inclusive_range(start: int, stop: int):
        return range(start, stop + 1)

    if point_format_id in inclusive_range(0, 3):
        return "1.2"
    elif point_format_id in inclusive_range(4, 5):
        return "1.3"
    elif point_format_id in inclusive_range(6, 10):
        return "1.4"
    else:
        raise errors.PointFormatNotSupported(point_format_id)


def min_point_format_for_version(version: str) -> int:
    return VERSION_TO_POINT_FMT[version][0]


def supported_versions() -> Set[str]:
    """Returns the set of supported file versions"""
    return set(VERSION_TO_POINT_FMT.keys())


def supported_point_formats() -> Set[int]:
    """Returns a set of all the point formats supported in laspy"""
    return set(POINT_FORMAT_DIMENSIONS.keys())


def is_point_fmt_compatible_with_version(
    point_format_id: int, file_version: str
) -> bool:
    """Returns true if the file version support the point_format_id"""
    try:
        return point_format_id in VERSION_TO_POINT_FMT[str(file_version)]
    except KeyError:
        raise errors.FileVersionNotSupported(file_version)


def raise_if_version_not_compatible_with_fmt(point_format_id: int, file_version: str):
    if not is_point_fmt_compatible_with_version(point_format_id, file_version):
        raise errors.LaspyException(
            "Point format {} is not compatible with file version {}".format(
                point_format_id, file_version
            )
        )


def _convert_array_views_to_array(
    view_class: Type, some_args: Union[List[Any], Tuple[Any, ...]]
) -> List[Any]:
    converted_args = []
    for arg in some_args:
        if isinstance(arg, (list, tuple)):
            converted_args.append(_convert_array_views_to_array(view_class, arg))
        elif isinstance(arg, view_class):
            converted_args.append(np.array(arg))
        else:
            converted_args.append(arg)

    return converted_args


class ArrayView(abc.ABC):
    def __init__(self, array) -> None:
        self.array = array

    @abc.abstractmethod
    def __array__(self, *args, **kwargs) -> np.ndarray:
        ...

    @abc.abstractmethod
    def __getitem__(self, item):
        ...

    @abc.abstractmethod
    def __setitem__(self, key, value):
        ...

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        inpts = _convert_array_views_to_array(self.__class__, inputs)
        return getattr(ufunc, method)(*inpts, **kwargs)

    def __array_function__(self, func, types, args, kwargs):
        argslist = _convert_array_views_to_array(self.__class__, args)
        return func(*argslist, **kwargs)

    def copy(self) -> np.ndarray:
        return np.array(self)

    @property
    def dtype(self):
        return self.array.dtype

    @property
    def shape(self):
        return self.array.shape

    @property
    def ndim(self):
        return self.array.ndim

    def max(self, *args, **kwargs):
        return np.array(self).max(*args, **kwargs)

    def min(self, *args, **kwargs):
        return np.array(self).min(*args, **kwargs)

    def __len__(self):
        return len(self.array)

    def __lt__(self, other):
        return np.array(self) < other

    def __le__(self, other):
        return np.array(self) <= other

    def __ge__(self, other):
        return np.array(self) >= other

    def __gt__(self, other):
        return np.array(self) > other

    def __eq__(self, other):
        return np.array(self) == other

    def __ne__(self, other):
        return np.array(self) != other

    def __add__(self, other):
        return np.array(self) + other

    def __sub__(self, other):
        return np.array(self) - other

    def __mul__(self, other):
        return np.array(self) * other

    def __truediv__(self, other):
        return np.array(self) / other

    def __floordiv__(self, other):
        return np.array(self) // other

    def __repr__(self):
        return f"<{self.__class__.__name__}({np.array(self)})>"


class SubFieldView(ArrayView):
    """Offers a view onto a LAS field that is a bit field.

    This class allows to read and modify, the array that stores the
    bit field directly.
    """

    def __init__(self, array: np.ndarray, bit_mask):
        super().__init__(array)
        self.bit_mask = self.array.dtype.type(bit_mask)
        self.lsb = packing.least_significant_bit_set(bit_mask)
        self.max_value_allowed = int(self.bit_mask >> self.lsb)

    def masked_array(self):
        return (self.array & self.bit_mask) >> self.lsb

    def _do_comparison(self, value, comp):
        if isinstance(value, (int, type(self.array.dtype))):
            if value > self.max_value_allowed:
                return np.zeros_like(self.array, bool)
        return comp(self.array & self.bit_mask, value << self.lsb)

    def __array__(self, *args, **kwargs):
        ret = self.masked_array()
        if not isinstance(ret, np.ndarray):
            ret = np.array(ret)
        return ret

    def __lt__(self, other):
        return self._do_comparison(other, operator.lt)

    def __le__(self, other):
        return self._do_comparison(other, operator.le)

    def __ge__(self, other):
        return self._do_comparison(other, operator.ge)

    def __gt__(self, other):
        return self._do_comparison(other, operator.gt)

    def __setitem__(self, key, value):
        # bail out on empty sequences
        if isinstance(value, collections.abc.Sized) and len(value) == 0:
            return

        if np.max(value) > self.max_value_allowed:
            raise OverflowError(
                f"value {np.max(value)} is greater than allowed (max: {self.max_value_allowed})"
            )
        value = np.asarray(value)
        self.array[key] &= ~self.bit_mask

        # This is not allowed without a casting="unsafe" argument
        # in Numpy 2.0
        # self.array[key] |= shifted
        shifted = value << self.lsb
        self.array[key] = np.bitwise_or(self.array[key], shifted, casting="unsafe")

    def __getitem__(self, item):
        sliced = SubFieldView(self.array[item], int(self.bit_mask))
        if isinstance(item, int):
            return sliced.masked_array()
        return sliced


class ScaledArrayView(ArrayView):
    def __init__(
        self,
        array: np.ndarray,
        scale: Union[float, np.ndarray],
        offset: Union[float, np.ndarray],
    ) -> None:
        super().__init__(array)
        self.scale = scale
        self.offset = offset

    def scaled_array(self):
        return self._apply_scale(self.array)

    def __array__(self, *args, **kwargs) -> np.ndarray:
        return self.scaled_array()

    def _apply_scale(self, value):
        return (value * self.scale) + self.offset

    def _remove_scale(self, value):
        return np.round((value - self.offset) / self.scale)

    def max(self, *args, **kwargs):
        return self._apply_scale(self.array.max(*args, **kwargs))

    def min(self, *args, **kwargs):
        return self._apply_scale(self.array.min(*args, **kwargs))

    @property
    def dtype(self):
        return np.dtype(np.float64)

    def _do_comparison(self, other, op):
        # The implementation of comparison by the base class
        # does a conversion to np.array of self, which is not free
        # we try to avoid that here
        if isinstance(other, (int, float, np.number)):
            other = self._remove_scale(other)
            return getattr(self.array, op)(other)
        return getattr(super(), op)(other)

    def __ge__(self, other):
        return self._do_comparison(other, "__ge__")

    def __gt__(self, other):
        return self._do_comparison(other, "__gt__")

    def __le__(self, other):
        return self._do_comparison(other, "__le__")

    def __lt__(self, other):
        return self._do_comparison(other, "__lt__")

    def __eq__(self, other):
        return self._do_comparison(other, "__eq__")

    def __ne__(self, other):
        return self._do_comparison(other, "__ne__")

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._apply_scale(self.array[item])
        elif isinstance(item, slice):
            return self.__class__(self.array[item], self.scale, self.offset)
        else:
            sliced_array = self.array[item]
            if len(item) == 2:
                if item[1] is Ellipsis:
                    # item is (index, ...), it queries for all the dimensions
                    # of a point or set of point, so we don't slice the scales/offsets
                    return self.__class__(sliced_array, self.scale, self.offset)
                elif item[0] is Ellipsis:
                    # item is something like (..., index)
                    # it queries for one dimension or set of dimension
                    # for all the points, so we need to slice the scales/offsets
                    return self.__class__(
                        sliced_array, self.scale[item[1]], self.offset[item[1]]
                    )
            return self.__class__(sliced_array, self.scale, self.offset)

    def __setitem__(self, key, value):
        # bail out on empty sequences
        if isinstance(value, collections.abc.Sized) and len(value) == 0:
            return

        try:
            info = np.iinfo(self.array.dtype)
        except ValueError:
            info = np.finfo(self.array.dtype)

        new_max = np.max(value)
        new_min = np.min(value)

        max_allowed = self._apply_scale(info.max)
        min_allowed = self._apply_scale(info.min)

        if np.any(new_max > max_allowed) or np.any(new_min < min_allowed):
            raise OverflowError(
                "Values given do not fit after applying offset and scale"
            )
        if isinstance(value, ScaledArrayView):
            value = np.array(value)
        self.array[key] = self._remove_scale(value)

    def __repr__(self):
        return f"<ScaledArrayView({self.scaled_array()})>"
