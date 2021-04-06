""" Contains the classes that manages Las PointRecords
Las PointRecords are represented using Numpy's structured arrays,
The PointRecord classes provide a few extra things to manage these arrays
in the context of Las point data
"""
import logging
from typing import NoReturn

import numpy as np

from . import dims
from .dims import ScaledArrayView
from .dims import ScaledArrayView, OLD_LASPY_NAMES
from .. import errors
from ..point import PointFormat

logger = logging.getLogger(__name__)


def scale_dimension(array_dim, scale, offset):
    return (array_dim * scale) + offset


def unscale_dimension(array_dim, scale, offset):
    return np.round((np.array(array_dim) - offset) / scale)


def raise_not_enough_bytes_error(
        expected_bytes_len, missing_bytes_len, point_data_buffer_len, points_dtype
) -> NoReturn:
    raise errors.LaspyError(
        "The file does not contain enough bytes to store the expected number of points\n"
        "expected {} bytes, read {} bytes ({} bytes missing == {} points) and it cannot be corrected\n"
        "{} (bytes) / {} (point_size) = {} (points)".format(
            expected_bytes_len,
            point_data_buffer_len,
            missing_bytes_len,
            missing_bytes_len / points_dtype.itemsize,
            point_data_buffer_len,
            points_dtype.itemsize,
            point_data_buffer_len / points_dtype.itemsize,
        )
    )


class PackedPointRecord:
    """
    In the PackedPointRecord, fields that are a combinations of many sub-fields (fields stored on less than a byte)
    are still packed together and are only de-packed and re-packed when accessed.

    This uses of less memory than if the sub-fields were unpacked

    >>> #return number is a sub-field
    >>> from laspy import PointFormat
    >>> packed_point_record = PackedPointRecord.zeros(PointFormat(0), 10)
    >>> return_number = packed_point_record['return_number']
    >>> return_number
    <SubFieldView([0 0 0 0 0 0 0 0 0 0])>
    >>> return_number[:] = 1
    >>> np.alltrue(packed_point_record['return_number'] == 1)
    True
    """

    def __init__(self, data: np.ndarray, point_format: PointFormat):
        self.array = data
        self.point_format = point_format
        self.sub_fields_dict = dims.get_sub_fields_dict(point_format.id)

    @property
    def point_size(self):
        """Returns the point size in bytes taken by each points of the record

        Returns
        -------
        int
            The point size in byte

        """
        return self.array.dtype.itemsize

    @classmethod
    def zeros(cls, point_format, point_count):
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
        return cls(data, point_format)

    @classmethod
    def empty(cls, point_format):
        """Creates an empty point record.

        Parameters
        ----------
        point_format: laspy.PointFormat
            The point format id the point record should have

        Returns
        -------
        PackedPointRecord

        """
        return cls.zeros(point_format, point_count=0)

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
    def from_buffer(cls, buffer, point_format, count, offset=0):
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

    def memoryview(self) -> memoryview:
        return memoryview(self.array)

    def resize(self, new_size: int) -> None:
        size_diff = new_size - len(self.array)
        if size_diff > 0:
            self.array = np.append(
                self.array, np.zeros(size_diff, dtype=self.array.dtype)
            )
        elif size_diff < 0:
            self.array = self._array[:new_size].copy()

    def _append_zeros_if_too_small(self, value):
        """Appends zeros to the points stored if the value we are trying to
        fit is bigger
        """
        size_diff = len(value) - len(self.array)
        if size_diff > 0:
            self.resize(size_diff)

    def __eq__(self, other):
        return self.point_format == other.point_format and np.all(
            self.array == other.array
        )

    def __len__(self):
        return self.array.shape[0]

    def __getitem__(self, item):
        """Gives access to the underlying numpy array
        Unpack the dimension if item is the name a sub-field
        """
        if isinstance(item, (int, slice, np.ndarray)):
            return PackedPointRecord(self.array[item], self.point_format)

        old_laspy_names = {
            "flag_byte": "bit_fields",
            "return_num": "return_number",
            "num_returns": "number_of_returns",
            "scan_dir_flag": "scan_direction_flag",
            "edge_flight_line": "edge_of_flight_line",
            "pt_src_id": "point_source_id",
            "wave_packet_desc_index": "wavepacket_index",
            "byte_offset_to_waveform_data": "wavepacket_offset",
            "waveform_packet_size": "wavepacket_size",
            "return_point_waveform_loc": "return_point_wave_location"
        }

        try:
            item = old_laspy_names[item]
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
            if dim_info.is_standard is False:
                if dim_info.scales is not None or dim_info.offsets is not None:
                    scale = (
                        np.ones(dim_info.num_elements, np.float64)
                        if dim_info.scales is None
                        else dim_info.scales[: dim_info.num_elements]
                    )
                    offset = (
                        np.zeros(dim_info.num_elements, np.float64)
                        if dim_info.offsets is None
                        else dim_info.offsets[: dim_info.num_elements]
                    )
                    return ScaledArrayView(self.array[item], scale, offset)
        except ValueError:
            pass

        return self.array[item]

    def __setitem__(self, key, value):
        """Sets elements in the array"""
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
    record["Z"] = unscale_dimension(np.asarray(record.x), scales[2], offsets[2])


class ScaleAwarePointRecord(PackedPointRecord):
    def __init__(self, array, point_format, scales, offsets):
        super().__init__(array, point_format)
        self.scales = scales
        self.offsets = offsets

    def change_scaling(self, scales=None, offsets=None) -> None:
        if scales is not None:
            self.scales = scales
        if offsets is not None:
            self.offsets = offsets

        apply_new_scaling(self, scales, offsets)

        self.scales = scales
        self.offsets = offsets

    def __getitem__(self, item):
        if isinstance(item, (slice, np.ndarray)):
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
