"""  This module contains things like the definitions of the point formats dimensions,
the mapping between dimension names and their type, mapping between point format and
compatible file version
"""
import itertools
import operator
from collections import UserDict
from enum import Enum
from typing import (
    NamedTuple,
    Optional,
    Dict,
    Tuple,
    Set,
    Iterable,
    Mapping,
    TypeVar,
    Generic,
    List,
    Union,
    Any,
)

import numpy as np

from . import packing
from .. import errors

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
    point_format: Iterable[str], dimensions_to_type: Mapping[str, str]
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
    dimensions_dict: Mapping[str, str],
) -> Dict[int, np.dtype]:
    """Builds the dict mapping point format id to numpy.dtype
    In the dtypes, bit fields are still packed, and need to be unpacked each time
    you want to access them
    """
    return {
        fmt_id: _point_format_to_dtype(point_fmt, dimensions_dict)
        for fmt_id, point_fmt in point_format_dimensions.items()
    }


# Definition of the points dimensions and formats
# LAS version [1.0, 1.1, 1.2, 1.3, 1.4]
DIMENSIONS_TO_TYPE: Dict[str, str] = {
    "X": "i4",
    "Y": "i4",
    "Z": "i4",
    "intensity": "u2",
    "bit_fields": "u1",
    "raw_classification": "u1",
    "scan_angle_rank": "i1",
    "user_data": "u1",
    "point_source_id": "u2",
    "gps_time": "f8",
    "red": "u2",
    "green": "u2",
    "blue": "u2",
    # Waveform related dimensions
    "wavepacket_index": "u1",
    "wavepacket_offset": "u8",
    "wavepacket_size": "u4",
    "return_point_wave_location": "u4",
    "x_t": "f4",
    "y_t": "f4",
    "z_t": "f4",
    # Las 1.4
    "classification_flags": "u1",
    "scan_angle": "i2",
    "classification": "u1",
    "nir": "u2",
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
    def from_type_str(
        cls,
        name: str,
        type_str: str,
        is_standard: bool = True,
        description: str = "",
        offsets: Optional[np.ndarray] = None,
        scales: Optional[np.ndarray] = None,
    ) -> "DimensionInfo":
        if (
            offsets is not None
            and scales is None
            or offsets is None
            and scales is not None
        ):
            raise ValueError("Cannot provide scales without offsets and vice-versa")

        first_digits = "".join(itertools.takewhile(lambda l: l.isdigit(), type_str))
        if first_digits:
            num_elements = int(first_digits)
            type_str = type_str[len(first_digits) :]
        else:
            num_elements = 1

        dtype = np.dtype(type_str)
        kind = DimensionKind.from_letter(type_str[0])
        num_bits = num_elements * dtype.itemsize * 8

        if offsets is not None and len(offsets) != num_elements:
            raise ValueError(
                f"len(offsets) ({len(offsets)}) is not the same as the number of elements ({num_elements})"
            )

        if scales is not None and len(scales) != num_elements:
            raise ValueError(
                f"len(scales) ({len(scales)}) is not the same as the number of elements ({num_elements})"
            )

        return cls(
            name,
            kind,
            num_bits,
            num_elements,
            is_standard,
            description=description,
            offsets=offsets,
            scales=scales,
        )

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
    def max(self):
        if self.kind == DimensionKind.BitField:
            return (2 ** self.num_bits) - 1
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


def size_of_point_format_id(point_format_id: int) -> int:
    return ALL_POINT_FORMATS_DTYPE[point_format_id].itemsize


def min_file_version_for_point_format(point_format_id: int) -> str:
    """Returns the minimum file version that supports the given point_format_id"""
    for version, point_formats in sorted(VERSION_TO_POINT_FMT.items()):
        if point_format_id in point_formats:
            return version
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
        raise errors.LaspyError(
            "Point format {} is not compatible with file version {}".format(
                point_format_id, file_version
            )
        )


class SubFieldView:
    """Offers a view onto a LAS field that is a bit field.

    This class allows to read and modify, the array that stores the
    bit field directly.
    """

    def __init__(self, array: np.ndarray, bit_mask):
        self.array = array
        self.bit_mask = self.array.dtype.type(bit_mask)
        self.lsb = packing.least_significant_bit_set(bit_mask)
        self.max_value_allowed = int(self.bit_mask >> self.lsb)

    def masked_array(self):
        return (self.array & self.bit_mask) >> self.lsb

    def copy(self):
        return SubFieldView(self.array.copy(), int(self.bit_mask))

    def _do_comparison(self, value, comp):
        if isinstance(value, (int, type(self.array.dtype))):
            if value > self.max_value_allowed:
                return np.zeros_like(self.array, np.bool)
        return comp(self.array & self.bit_mask, value << self.lsb)

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        inpts = SubFieldView._convert_sub_views_to_arrays(inputs)
        ret = getattr(ufunc, method)(*inpts, **kwargs)
        if ret is not None and isinstance(ret, np.ndarray):
            if ret.dtype == np.bool:
                return ret
            return self.__class__(ret, int(self.bit_mask))
        return ret

    def __array_function__(self, func, types, args, kwargs):
        argslist = SubFieldView._convert_sub_views_to_arrays(args)
        return func(*argslist, **kwargs)

    @property
    def dtype(self):
        return self.array.dtype

    @property
    def shape(self):
        return self.array.shape

    @property
    def ndim(self):
        return self.array.ndim

    def __array__(self, **kwargs):
        return self.masked_array()

    def max(self, **unused_kwargs):
        return self.masked_array().max()

    def min(self, **unused_kwargs):
        return self.masked_array().min()

    def __len__(self):
        return len(self.array)

    def __lt__(self, other):
        return self._do_comparison(other, operator.lt)

    def __le__(self, other):
        return self._do_comparison(other, operator.le)

    def __ge__(self, other):
        return self._do_comparison(other, operator.ge)

    def __gt__(self, other):
        return self._do_comparison(other, operator.gt)

    def __eq__(self, other):
        if isinstance(other, SubFieldView):
            return self.bit_mask == other.bit_mask and self.masked_array() == other
        else:
            return self._do_comparison(other, operator.eq)

    def __ne__(self, other):
        if isinstance(other, SubFieldView):
            return self.bit_mask != other.bit_mask and self.masked_array() != other
        else:
            return self._do_comparison(other, operator.ne)

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

    def __setitem__(self, key, value):
        if np.max(value) > self.max_value_allowed:
            raise OverflowError(
                f"value {np.max(value)} is greater than allowed (max: {self.max_value_allowed})"
            )
        value = np.array(value, copy=False).astype(self.array.dtype)
        self.array[key] &= ~self.bit_mask
        self.array[key] |= value << self.lsb

    def __getitem__(self, item):
        sliced = SubFieldView(self.array[item], int(self.bit_mask))
        if isinstance(item, int):
            return sliced.masked_array()
        return sliced

    def __repr__(self):
        return f"<SubFieldView({self.masked_array()})>"

    @staticmethod
    def _convert_sub_views_to_arrays(
        some_args: Union[List[Any], Tuple[Any, ...]]
    ) -> List[Any]:
        converted_args = []
        for arg in some_args:
            if isinstance(arg, (list, tuple)):
                converted_args.append(SubFieldView._convert_sub_views_to_arrays(arg))
            elif isinstance(arg, SubFieldView):
                converted_args.append(arg.masked_array())
            else:
                converted_args.append(arg)

        return converted_args


class ScaledArrayView:
    def __init__(
        self,
        array: np.ndarray,
        scale: Union[float, np.ndarray],
        offset: Union[float, np.ndarray],
    ) -> None:
        self.array = array
        self.scale = scale
        self.offset = offset

    def scaled_array(self):
        return self._apply_scale(self.array)

    def copy(self):
        return ScaledArrayView(self.array.copy(), self.scale, self.offset)

    def _apply_scale(self, value):
        return (value * self.scale) + self.offset

    def _remove_scale(self, value):
        return np.round((value - self.offset) / self.scale)

    def max(self, **unused_kwargs):
        return self._apply_scale(self.array.max())

    def min(self, **unused_kwargs):
        return self._apply_scale(self.array.min())

    def __array__(self):
        return self.scaled_array()

    @property
    def dtype(self):
        return np.dtype(np.float64)

    @property
    def shape(self):
        return self.array.shape

    @property
    def ndim(self):
        return self.array.ndim

    def __array_function__(self, func, types, args, kwargs):
        args = ScaledArrayView._convert_scaled_views_to_arrays(args)
        ret = func(*args, **kwargs)
        if ret is not None:
            if isinstance(ret, np.ndarray) and ret.dtype != np.bool:
                return self.__class__(ret, self.scale, self.offset)
            else:
                return ret
        return ret

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        inpts = ScaledArrayView._convert_scaled_views_to_arrays(inputs)
        ret = getattr(ufunc, method)(*inpts, **kwargs)
        if ret is not None:
            if isinstance(ret, np.ndarray):
                return self.__class__(ret, self.scale, self.offset)
            elif ret.dtype != np.bool:
                return self._apply_scale(ret)
            else:
                return ret
        return ret

    @staticmethod
    def _convert_scaled_views_to_arrays(
        some_args: Union[List[Any], Tuple[Any, ...]]
    ) -> List[Any]:
        converted_args = []
        for arg in some_args:
            if isinstance(arg, (list, tuple)):
                converted_args.append(
                    ScaledArrayView._convert_scaled_views_to_arrays(arg)
                )
            elif isinstance(arg, ScaledArrayView):
                converted_args.append(arg.scaled_array())
            else:
                converted_args.append(arg)

        return converted_args

    def __len__(self):
        return len(self.array)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.scale == other.scale
                and self.offset == other.offset
                and np.all(self.array == other.array)
            )
        else:
            return self.scaled_array() == other

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.scale != other.scale
                and self.offset != other.offset
                and np.all(self.array != other.array)
            )
        else:
            return self.scaled_array() != other

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

    def __lt__(self, other):
        return self.array < self._remove_scale(other)

    def __gt__(self, other):
        return self.array > self._remove_scale(other)

    def __ge__(self, other):
        return self.array >= self._remove_scale(other)

    def __le__(self, other):
        return self.array <= self._remove_scale(other)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._apply_scale(self.array[item])
        elif isinstance(item, slice):
            return self.__class__(self.array[item], self.scale, self.offset)
        else:
            return self.__class__(self.array[item], self.scale[item], self.offset[item])

    def __setitem__(self, key, value):
        if isinstance(value, ScaledArrayView):
            iinfo = np.iinfo(self.array.dtype)
            if value.array.max() > iinfo.max or value.array.min() < iinfo.min:
                raise OverflowError(
                    "Values given do not fit after applying offset and scale"
                )
            self.array[key] = value.array[key]
        else:
            try:
                info = np.iinfo(self.array.dtype)
            except ValueError:
                info = np.finfo(self.array.dtype)

            new_max = self._remove_scale(np.max(value))
            new_min = self._remove_scale(np.min(value))
            if np.all(new_max > info.max) or np.all(new_min < info.min):
                raise OverflowError(
                    "Values given do not fit after applying offset and scale"
                )
            self.array[key] = self._remove_scale(value)

    def __repr__(self):
        return f"<ScaledArrayView({self.scaled_array()})>"
