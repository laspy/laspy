""" Contains the classes that manages Las PointRecords
Las PointRecords are represented using Numpy's structured arrays,
The PointRecord classes provide a few extra things to manage these arrays
in the context of Las point data
"""

import logging
from copy import deepcopy
from enum import Enum, auto
from typing import Optional

import numpy as np

from ..point import PointFormat
from . import dims
from .dims import OLD_LASPY_NAMES, ScaledArrayView

logger = logging.getLogger(__name__)


def scale_dimension(array_dim, scale, offset):
    return (array_dim * scale) + offset


def unscale_dimension(array_dim, scale, offset):
    return np.round((np.array(array_dim) - offset) / scale)


class DimensionNameValidity(Enum):
    """Helper class to make the return value of
    PackedPointRecord.validate_dimentsion_name more expressive.
    """

    # Means the name is valid and supported by the point format
    Valid = auto()
    # Means the name is valid but _not_ supported by the point format
    Unsupported = auto()
    # The name does not exist in LAS spec
    Invalid = auto()


class PackedPointRecord:
    """
    In the PackedPointRecord, fields that are a combinations of many sub-fields (fields stored on less than a byte)
    are still packed together and are only de-packed and re-packed when accessed.

    This uses of less memory than if the sub-fields were unpacked

    >>> #return number is a sub-field
    >>> from laspy import PointFormat, PackedPointRecord
    >>> packed_point_record = PackedPointRecord.zeros(10,PointFormat(0))
    >>> return_number = packed_point_record['return_number']
    >>> return_number
    <SubFieldView([0 0 0 0 0 0 0 0 0 0])>
    >>> return_number[:] = 1
    >>> bool(np.all(packed_point_record['return_number'] == 1))
    True
    """

    def __init__(self, data: np.ndarray, point_format: PointFormat):
        self.__dict__["array"] = data
        self.__dict__["point_format"] = point_format
        self.__dict__["sub_fields_dict"] = dims.get_sub_fields_dict(point_format.id)

    @property
    def point_size(self):
        """Returns the point size in bytes taken by each points of the record

        Returns
        -------
        int
            The point size in byte

        """
        return self.array.dtype.itemsize

    @staticmethod
    def zeros(point_count, point_format):
        """Creates a new point record with all dimensions initialized to zero

        Parameters
        ----------
        point_format: PointFormat
            The point format id the point record should have
        point_count : int
            The number of point the point record should have

        Returns
        -------
        PackedPointRecord

        """
        data = np.zeros(point_count, point_format.dtype())
        return PackedPointRecord(data, point_format)

    @staticmethod
    def empty(point_format):
        """Creates an empty point record.

        Parameters
        ----------
        point_format: laspy.PointFormat
            The point format id the point record should have

        Returns
        -------
        PackedPointRecord

        """
        return PackedPointRecord.zeros(point_count=0, point_format=point_format)

    @classmethod
    def from_point_record(
        cls, other_point_record: "PackedPointRecord", new_point_format: PointFormat
    ) -> "PackedPointRecord":
        """Construct a new PackedPointRecord from an existing one with the ability to change
        to point format while doing so
        """
        array = np.zeros_like(other_point_record.array, dtype=new_point_format.dtype())
        new_record = cls(array, new_point_format)
        new_record.copy_fields_from(other_point_record)
        return new_record

    @classmethod
    def from_buffer(cls, buffer, point_format, count=-1, offset=0):
        points_dtype = point_format.dtype()
        data = np.frombuffer(buffer, dtype=points_dtype, offset=offset, count=count)

        return cls(data, point_format)

    def copy_fields_from(self, other_record: "PackedPointRecord") -> None:
        """Tries to copy the values of the current dimensions from other_record"""
        for dim_name in self.point_format.dimension_names:
            try:
                self[dim_name] = np.array(other_record[dim_name])
            except ValueError:
                pass

    def copy(self) -> "PackedPointRecord":
        return PackedPointRecord(self.array.copy(), deepcopy(self.point_format))

    def memoryview(self) -> memoryview:
        return memoryview(self.array)

    def resize(self, new_size: int) -> None:
        size_diff = new_size - len(self.array)
        if size_diff > 0:
            self.array = np.append(
                self.array, np.zeros(size_diff, dtype=self.array.dtype)
            )
        elif size_diff < 0:
            self.array = self.array[:new_size].copy()

    def _append_zeros_if_too_small(self, value):
        """Appends zeros to the points stored if the value we are trying to
        fit is bigger
        """
        if len(value) > len(self.array):
            self.resize(len(value))

    def __eq__(self, other):
        return self.point_format == other.point_format and np.all(
            self.array == other.array
        )

    def __len__(self):
        if self.array.ndim == 0:
            return 1
        return self.array.shape[0]

    def __getitem__(self, item):
        """Gives access to the underlying numpy array
        Unpack the dimension if item is the name a sub-field
        """
        if isinstance(item, (int, slice, np.ndarray, list, tuple)):
            return PackedPointRecord(self.array[item], self.point_format)

        try:
            item = OLD_LASPY_NAMES[item]
        except KeyError:
            pass

        # 1) Is it a sub field ?
        try:
            composed_dim, sub_field = self.sub_fields_dict[item]
            return dims.SubFieldView(self.array[composed_dim], sub_field.mask)
        except KeyError:
            pass

        # 2) Is it a Scaled Extra Byte Dimension ?
        try:
            dim_info = self.point_format.dimension_by_name(item)
            if dim_info.is_standard is False and dim_info.is_scaled:
                assert dim_info.scales is not None and dim_info.offsets is not None
                return ScaledArrayView(
                    self.array[item], dim_info.scales, dim_info.offsets
                )
        except ValueError:
            pass

        return self.array[item]

    def __setitem__(self, key, value):
        """Sets elements in the array"""
        if isinstance(key, (tuple, list)):
            if not isinstance(value, np.ndarray):
                value = np.asarray(value)

            if value.dtype.isbuiltin == 0:
                # value is most likely a structured array (dtype = [('name1', 'type1'), ...])
                # https://numpy.org/devdocs/reference/generated/numpy.dtype.isbuiltin.html
                for name, v_name in zip(key, value.dtype.names):
                    self[name] = value[v_name]
            else:
                if len(key) == 1 and value.ndim == 1:
                    value = value[..., np.newaxis]
                for i, name in enumerate(key):
                    self[name] = value[..., i]
            return

        self._append_zeros_if_too_small(value)
        if isinstance(key, str):
            self[key][:] = value
        else:
            self.array[key] = value

    def __getattr__(self, item):
        try:
            return self[item]
        except ValueError:
            raise AttributeError("{} is not a valid dimension".format(item)) from None

    def validate_dimension_name(self, key: str) -> DimensionNameValidity:
        """Given a name of a dimension this validates it."""
        try:
            key = OLD_LASPY_NAMES[key]
        except KeyError:
            pass

        if key in self.point_format.dimension_names or key in self.array.dtype.names:
            return DimensionNameValidity.Valid
        elif key in dims.DIMENSIONS_TO_TYPE:
            return DimensionNameValidity.Unsupported
        else:
            return DimensionNameValidity.Invalid

    def __setattr__(self, key, value):
        name_validity = self.validate_dimension_name(key)
        if name_validity == DimensionNameValidity.Valid:
            self[key] = value
        elif name_validity == DimensionNameValidity.Unsupported:
            raise ValueError(
                f"Point format {self.point_format} does not support {key} dimension"
            )
        else:
            super().__setattr__(key, value)

    def __repr__(self):
        return "<{}(fmt: {}, len: {}, point size: {})>".format(
            self.__class__.__name__,
            self.point_format,
            len(self),
            self.point_format.size,
        )


def apply_new_scaling(record, scales: np.ndarray, offsets: np.ndarray) -> None:
    record["X"] = unscale_dimension(np.asarray(record.x), scales[0], offsets[0])
    record["Y"] = unscale_dimension(np.asarray(record.y), scales[1], offsets[1])
    record["Z"] = unscale_dimension(np.asarray(record.z), scales[2], offsets[2])


class ScaleAwarePointRecord(PackedPointRecord):
    """A ScaleAwarePointRecord is a point record that knows the scales and offets
    to use, and is thus able to get and set the scaled x, y, z coordinates

    To create one, use :meth:`.ScaleAwarePointRecord.zeros` or :meth:`.ScaleAwarePointRecord.empty`

    """

    def __init__(self, array, point_format, scales, offsets):
        super().__init__(array, point_format)
        self.scales = np.array(scales)
        self.offsets = np.array(offsets)

        if self.scales.shape != (3,):
            raise ValueError("scales must be an array of 3 elements")

        if self.offsets.shape != (3,):
            raise ValueError("offsets must be an array of 3 elements")

    @staticmethod
    def zeros(
        point_count, *, point_format=None, scales=None, offsets=None, header=None
    ):
        """Creates a new point record with all dimensions initialized to zero

        Examples
        --------

        >>> record = ScaleAwarePointRecord.zeros(
        ... 5, point_format=PointFormat(3), scales=[1.0, 1.0, 1.0], offsets=[0.1, 0.5, 17.5])
        >>> len(record)
        5

        >>> import laspy
        >>> hdr = laspy.LasHeader()
        >>> record = ScaleAwarePointRecord.zeros(5, header=hdr)
        >>> len(record)
        5

        >>> hdr = laspy.LasHeader()
        >>> record = ScaleAwarePointRecord.zeros(5, header=hdr, scales=[1.0, 1.0, 1.0])
        Traceback (most recent call last):
        ValueError: header argument is mutually exclusive with point_format, scales and offets

        >>> record = ScaleAwarePointRecord.zeros(5, point_format=PointFormat(3))
        Traceback (most recent call last):
        ValueError: You have to provide all 3: point_format, scale and offsets
        """
        first_set = (point_format, scales, offsets)

        if header is not None:
            if any(arg is not None for arg in first_set):
                raise ValueError(
                    "header argument is mutually exclusive with point_format, scales and offets"
                )
            point_format = header.point_format
            scales = header.scales
            offsets = header.offsets
        else:
            if any(arg is None for arg in first_set):
                raise ValueError(
                    "You have to provide all 3: " "point_format, scale and offsets"
                )

        data = np.zeros(point_count, point_format.dtype())
        return ScaleAwarePointRecord(data, point_format, scales, offsets)

    @staticmethod
    def empty(point_format=None, scales=None, offsets=None, header=None):
        """Creates an empty point record."""
        return ScaleAwarePointRecord.zeros(
            point_count=0,
            point_format=point_format,
            scales=scales,
            offsets=offsets,
            header=header,
        )

    def change_scaling(self, scales=None, offsets=None) -> None:
        """See :meth:`.LasData.change_scaling`"""
        if scales is None:
            scales = self.scales
        if offsets is None:
            offsets = self.offsets

        apply_new_scaling(self, scales, offsets)

        self.scales = scales
        self.offsets = offsets

    def __getitem__(self, item):
        if isinstance(item, (int, slice, np.ndarray, list, tuple)):
            if isinstance(item, (list, tuple)):
                # x, y ,z do not really exists in the array, but they are computed from X, Y, Z
                item = [
                    item if item not in ("x", "y", "z") else item.upper()
                    for item in item
                ]
            return ScaleAwarePointRecord(
                self.array[item], self.point_format, self.scales, self.offsets
            )

        if item == "x":
            return ScaledArrayView(self.array["X"], self.scales[0], self.offsets[0])
        elif item == "y":
            return ScaledArrayView(self.array["Y"], self.scales[1], self.offsets[1])
        elif item == "z":
            return ScaledArrayView(self.array["Z"], self.scales[2], self.offsets[2])
        else:
            return super().__getitem__(item)

    def __setattr__(self, key, value):
        if key in ("x", "y", "z"):
            self[key][:] = value
        else:
            return super().__setattr__(key, value)
