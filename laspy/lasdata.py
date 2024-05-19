import logging
import pathlib
import typing
from copy import deepcopy
from typing import BinaryIO, Iterable, List, Optional, Sequence, Union, overload

import numpy as np

from . import errors
from .compression import LazBackend
from .header import LasHeader
from .laswriter import LasWriter
from .point import ExtraBytesParams, PointFormat, dims, record
from .point.dims import OLD_LASPY_NAMES, ScaledArrayView, SubFieldView
from .point.record import DimensionNameValidity
from .vlrs.vlrlist import VLRList

logger = logging.getLogger(__name__)


class LasData:
    """Class synchronizing all the moving parts of LAS files.

    It connects the point record, header, vlrs together.

    To access points dimensions using this class you have two possibilities

    .. code:: python

        las = laspy.read('some_file.las')
        las.classification
        # or
        las['classification']
    """

    def __init__(
        self,
        header: LasHeader,
        points: Optional[
            Union[record.PackedPointRecord, record.ScaleAwarePointRecord]
        ] = None,
    ) -> None:
        if points is None:
            points = record.ScaleAwarePointRecord.zeros(
                header.point_count, header=header
            )
        if points.point_format != header.point_format:
            raise errors.LaspyException("Incompatible Point Formats")
        if isinstance(points, record.PackedPointRecord):
            points = record.ScaleAwarePointRecord(
                points.array,
                header.point_format,
                scales=header.scales,
                offsets=header.offsets,
            )
        else:
            assert np.all(header.scales, points.scales)
            assert np.all(header.offsets, points.offsets)
        self.__dict__["_points"] = points
        self.points: record.ScaleAwarePointRecord
        self.header: LasHeader = header

    @property
    def point_format(self) -> PointFormat:
        """Shortcut to get the point format"""
        return self.points.point_format

    @property
    def xyz(self) -> np.ndarray:
        """Returns a **new** 2D numpy array with the x,y,z coordinates

        >>> import laspy
        >>> las = laspy.read("tests/data/simple.las")
        >>> xyz = las.xyz
        >>> xyz.ndim
        2
        >>> xyz.shape
        (1065, 3)
        >>> bool(np.all(xyz[..., 0] == las.x))
        True
        """
        return np.vstack((self.x, self.y, self.z)).transpose()

    @xyz.setter
    def xyz(self, value) -> None:
        self.points[("x", "y", "z")] = value

    @property
    def points(self) -> record.PackedPointRecord:
        """Returns the point record"""
        return self._points

    @points.setter
    def points(self, new_points: record.PackedPointRecord) -> None:
        if new_points.point_format != self.point_format:
            raise errors.IncompatibleDataFormat(
                "Cannot set points with a different point format, convert first"
            )
        self._points = new_points
        self.update_header()
        # make sure both point format point to the same object
        self._points.point_format = self.header.point_format

    @property
    def vlrs(self) -> VLRList:
        return self.header.vlrs

    @vlrs.setter
    def vlrs(self, vlrs) -> None:
        self.header.vlrs = vlrs

    @property
    def evlrs(self) -> Optional[VLRList]:
        return self.header.evlrs

    @evlrs.setter
    def evlrs(self, evlrs: VLRList) -> None:
        self.header.evlrs = evlrs

    def add_extra_dim(self, params: ExtraBytesParams) -> None:
        """Adds a new extra dimension to the point record

        .. note::

            If you plan on adding multiple extra dimensions,
            prefer :meth:`.add_extra_dims` as it will
            save re-allocations and data copy

        Parameters
        ----------
        params : ExtraBytesParams
            parameters of the new extra dimension to add

        """
        self.add_extra_dims([params])

    def add_extra_dims(self, params: List[ExtraBytesParams]) -> None:
        """Add multiple extra dimensions at once

        Parameters
        ----------

        params: list of parameters of the new extra dimensions to add
        """
        self.header.add_extra_dims(params)
        new_point_record = record.ScaleAwarePointRecord.zeros(
            len(self.points), header=self.header
        )
        new_point_record.copy_fields_from(self.points)
        self.points = new_point_record

    def remove_extra_dims(self, names: Iterable[str]) -> None:
        """Remove multiple extra dimensions from this object

        Parameters
        ----------

        names: iterable,
            names of the extra dimensions to be removed


        Raises
        ------

        LaspyException: if you try to remove an extra dimension that do not exist.

        """
        extra_dimension_names = list(self.point_format.extra_dimension_names)
        not_extra_dimension = [
            name for name in names if name not in extra_dimension_names
        ]
        if not_extra_dimension:
            raise errors.LaspyException(
                f"'{not_extra_dimension}' are not extra dimensions and cannot be removed"
            )

        self.header.remove_extra_dims(names)
        new_point_record = record.ScaleAwarePointRecord.zeros(
            len(self.points), header=self.header
        )
        new_point_record.copy_fields_from(self.points)
        self.points = new_point_record

    def remove_extra_dim(self, name: str) -> None:
        """Remove an extra dimensions from this object

        .. note::

             If you plan on removing multiple extra dimensions,
             prefer :meth:`.remove_extra_dims` as it will
             save re-allocations and data copy

        Parameters
        ----------

        name: str,
            name of the extra dimension to be removed


        Raises
        ------

        LaspyException: if you try to remove an extra dimension that do not exist.

        """
        self.remove_extra_dims([name])

    def update_header(self) -> None:
        """Update the information stored in the header
        to be in sync with the actual data.

        This method is called automatically when you save a file using
        :meth:`laspy.lasdatas.base.LasBase.write`
        """
        self.header.update(self.points)
        self.header.point_format_id = self.points.point_format.id
        self.header.point_data_record_length = self.points.point_size

        if self.header.version.minor >= 4:
            if self.evlrs is not None:
                self.header.number_of_evlrs = len(self.evlrs)
            self.header.start_of_waveform_data_packet_record = 0
            # TODO
            # if len(self.vlrs.get("WktCoordinateSystemVlr")) == 1:
            #     self.header.global_encoding.wkt = 1
        else:
            self.header.number_of_evlrs = 0

    @overload
    def write(
        self,
        destination: str,
        laz_backend: Optional[Union[LazBackend, Sequence[LazBackend]]] = ...,
    ) -> None:
        ...

    @overload
    def write(
        self,
        destination: BinaryIO,
        do_compress: Optional[bool] = ...,
        laz_backend: Optional[Union[LazBackend, Sequence[LazBackend]]] = ...,
    ) -> None:
        ...

    def write(self, destination, do_compress=None, laz_backend=None):
        """Writes to a stream or file

        .. note::

            When destination is a string, it will be interpreted as the path were the file should be written to,
            and whether the file will be compressed depends on the extension used (case insensitive):

                - .laz -> compressed
                - .las -> uncompressed

            And the do_compress option will be ignored


        Parameters
        ----------
        destination: str or file object
            filename or stream to write to
        do_compress: bool, optional
            Flags to indicate if you want to compress the data
        laz_backend: optional, the laz backend to use
            By default, laspy detect available backends
        """
        if isinstance(destination, (str, pathlib.Path)):
            do_compress = pathlib.Path(destination).suffix.lower() == ".laz"

            with open(destination, mode="wb+") as out:
                self._write_to(out, do_compress=do_compress, laz_backend=laz_backend)
        else:
            self._write_to(
                destination, do_compress=do_compress, laz_backend=laz_backend
            )

    def _write_to(
        self,
        out_stream: BinaryIO,
        do_compress: Optional[bool] = None,
        laz_backend: Optional[Union[LazBackend, Sequence[LazBackend]]] = None,
    ) -> None:
        with LasWriter(
            out_stream,
            self.header,
            do_compress=do_compress,
            closefd=False,
            laz_backend=laz_backend,
        ) as writer:
            writer.write_points(self.points)
            if self.header.version.minor >= 4 and self.evlrs is not None:
                writer.write_evlrs(self.evlrs)

    def change_scaling(self, scales=None, offsets=None) -> None:
        """This changes the scales and/or offset used for the x,y,z
        dimensions.

        It recomputes the internal, non-scaled X,Y,Z dimensions
        to match the new scales and offsets.

        It also updates the header with the new values of scales and offsets.

        Parameters
        ----------
        scales: optional
                New scales to be used. If not provided, the scales won't change.
        offsets: optional
                 New offsets to be used. If not provided, the offsets won't change.

        Example
        -------

        >>> import laspy
        >>> header = laspy.LasHeader()
        >>> header.scales = np.array([0.1, 0.1, 0.1])
        >>> header.offsets = np.array([0, 0 ,0])

        >>> las = laspy.LasData(header=header)
        >>> las.x = [10.0]
        >>> las.y = [20.0]
        >>> las.z = [30.0]

        >>> # X = (x - x_offset) / x_scale
        >>> assert np.all(las.xyz == [[10.0, 20., 30]])
        >>> assert np.all(las.X == [100])
        >>> assert np.all(las.Y == [200])
        >>> assert np.all(las.Z == [300])

        We change the scales (only changing x_scale here)
        but not the offsets.

        The xyz coordinates (double) are the same (minus possible rounding with actual coordinates)
        However the integer coordinates changed

        >>> las.change_scaling(scales=[0.01, 0.1, 0.1])
        >>> assert np.all(las.xyz == [[10.0, 20., 30]])
        >>> assert np.all(las.X == [1000])
        >>> assert np.all(las.Y == [200])
        >>> assert np.all(las.Z == [300])

        Same idea if we change the offsets, the xyz do not change
        but XYZ does

        >>> las.change_scaling(offsets=[0, 10, 15])
        >>> assert np.all(las.xyz == [[10.0, 20., 30]])
        >>> assert np.all(las.X == [1000])
        >>> assert np.all(las.Y == [100])
        >>> assert np.all(las.Z == [150])
        """
        self.points.change_scaling(scales, offsets)

        if scales is not None:
            self.header.scales = scales
        if offsets is not None:
            self.header.offsets = offsets

    def __getattr__(self, item):
        """Automatically called by Python when the attribute
        named 'item' is no found. We use this function to forward the call the
        point record. This is the mechanism used to allow the users to access
        the points dimensions directly through a LasData.

        Parameters
        ----------
        item: str
            name of the attribute, should be a dimension name

        Returns
        -------
        The requested dimension if it exists

        """
        try:
            return self.points[item]
        except ValueError:
            raise AttributeError(
                f"{self.__class__.__name__} object has no attribute '{item}'"
            ) from None

    def __setattr__(self, key, value):
        """This is called on every access to an attribute of the instance.
        Again we use this to forward the call the the points record

        But this time checking if the key is actually a dimension name
        so that an error is raised if the user tries to set a valid
        LAS dimension even if it is not present in the field.
        eg: user tries to set the red field of a file with point format 0:
        an error is raised
        """
        if key in ("x", "y", "z"):
            # It is possible that user created a `LasData` object
            # via `laspy.create`, and changed the headers offsets and scales
            # values afterwards. So we need to sync the points's record.
            self.points.offsets = self.header.offsets
            self.points.scales = self.header.scales
            self.points[key] = value
            return

        name_validity = self.points.validate_dimension_name(key)
        if name_validity == DimensionNameValidity.Valid:
            self[key] = value
        elif name_validity == DimensionNameValidity.Unsupported:
            raise ValueError(
                f"Point format {self.point_format} does not support {key} dimension"
            )
        else:
            super().__setattr__(key, value)

    @typing.overload
    def __getitem__(
        self, item: Union[str, List[str]]
    ) -> Union[np.ndarray, ScaledArrayView, SubFieldView]:
        ...

    @typing.overload
    def __getitem__(self, item: Union[int, typing.Iterable[int], slice]) -> "LasData":
        ...

    def __getitem__(self, item):
        try:
            item_is_list_of_str = all(isinstance(el, str) for el in iter(item))
        except TypeError:
            item_is_list_of_str = False

        if isinstance(item, str) or item_is_list_of_str:
            return self.points[item]
        else:
            las = LasData(deepcopy(self.header), points=self.points[item])
            las.update_header()
            return las

    def __setitem__(self, key, value):
        self.points[key] = value

    def __len__(self):
        return len(self.points)

    def __repr__(self) -> str:
        return "<LasData({}.{}, point fmt: {}, {} points, {} vlrs)>".format(
            self.header.version.major,
            self.header.version.minor,
            self.points.point_format,
            len(self.points),
            len(self.vlrs),
        )
