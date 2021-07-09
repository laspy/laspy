import logging
import pathlib
from typing import Union, Optional, List, Sequence, overload, BinaryIO

from . import errors
from .compression import LazBackend
from .header import LasHeader
from .laswriter import LasWriter
from .point import record, dims, ExtraBytesParams, PointFormat
from .point.dims import ScaledArrayView, OLD_LASPY_NAMES
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
        self, header: LasHeader, points: Optional[record.PackedPointRecord] = None
    ) -> None:
        if points is None:
            points = record.PackedPointRecord.zeros(
                header.point_count, header.point_format
            )
        elif points.point_format != header.point_format:
            raise errors.LaspyException("Incompatible Point Formats")
        self.__dict__["_points"] = points
        self.points: record.PackedPointRecord
        self.header: LasHeader = header
        if header.version.minor >= 4:
            self.evlrs: Optional[VLRList] = VLRList()
        else:
            self.evlrs: Optional[VLRList] = None

    @property
    def x(self) -> ScaledArrayView:
        """Returns the scaled x positions of the points as doubles"""
        return ScaledArrayView(self.X, self.header.x_scale, self.header.x_offset)

    @x.setter
    def x(self, value) -> None:
        if len(value) > len(self.points):
            self.points.resize(len(value))
        self.x[:] = value

    @property
    def y(self) -> ScaledArrayView:
        """Returns the scaled y positions of the points as doubles"""
        return ScaledArrayView(self.Y, self.header.y_scale, self.header.y_offset)

    @y.setter
    def y(self, value) -> None:
        if len(value) > len(self.points):
            self.points.resize(len(value))
        self.y[:] = value

    @property
    def z(self) -> ScaledArrayView:
        """Returns the scaled z positions of the points as doubles"""
        return ScaledArrayView(self.Z, self.header.z_scale, self.header.z_offset)

    @z.setter
    def z(self, value) -> None:
        if len(value) > len(self.points):
            self.points.resize(len(value))
        self.z[:] = value

    @property
    def point_format(self) -> PointFormat:
        """Shortcut to get the point format"""
        return self.points.point_format

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
        new_point_record = record.PackedPointRecord.from_point_record(
            self.points, self.header.point_format
        )
        self.points = new_point_record

    def update_header(self) -> None:
        """Update the information stored in the header
        to be in sync with the actual data.

        This method is called automatically when you save a file using
        :meth:`laspy.lasdatas.base.LasBase.write`
        """
        self.header.partial_reset()
        self.header.point_format_id = self.points.point_format.id
        self.header.point_data_record_length = self.points.point_size

        if len(self.points) > 0:
            self.header.update(self.points)

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
        """
        if scales is None:
            scales = self.header.scales
        if offsets is None:
            offsets = self.header.offsets

        record.apply_new_scaling(self, scales, offsets)

        self.header.scales = scales
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

        try:
            key = OLD_LASPY_NAMES[key]
        except KeyError:
            pass

        if (
            key in self.point_format.dimension_names
            or key in self.points.array.dtype.names
        ):
            self.points[key] = value
        elif key in dims.DIMENSIONS_TO_TYPE:
            raise ValueError(
                f"Point format {self.point_format} does not support {key} dimension"
            )
        else:
            super().__setattr__(key, value)

    def __getitem__(self, item):
        return self.points[item]

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
