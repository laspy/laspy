import logging
import pathlib
import typing
from copy import deepcopy
from typing import BinaryIO, Iterable, Sequence, overload

import numpy as np
from numpy.typing import NDArray

from . import errors
from .compression import LazBackend
from .header import LasHeader
from .laswriter import LasWriter
from .point import ExtraBytesParams, PointFormat, record
from .point.dims import ScaledArrayView, SubFieldView
from .point.record import DimensionNameValidity
from .vlrs.vlrlist import VLRList
from .waveform import WaveformRecord
from .waveform.utils import deduplicate_waveform_indices, iter_runs

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
        points: record.PackedPointRecord | record.ScaleAwarePointRecord | None = None,
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
                waveform_state=points._waveform_state,
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
    def evlrs(self) -> VLRList | None:
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

    def add_extra_dims(self, params: list[ExtraBytesParams]) -> None:
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
        do_compress: bool | None = ...,
        laz_backend: LazBackend | Sequence[LazBackend] | None = ...,
        *,
        waveform_chunksize: int = ...,
        waveforms: bool = ...,
    ) -> None: ...

    @overload
    def write(
        self,
        destination: BinaryIO,
        do_compress: bool | None = ...,
        laz_backend: LazBackend | Sequence[LazBackend] | None = ...,
        *,
        waveform_chunksize: int = ...,
        waveforms: bool = ...,
    ) -> None: ...

    def write(
        self,
        destination,
        do_compress=None,
        laz_backend=None,
        *,
        waveform_chunksize: int = 64 * 1024 * 1024,
        waveforms: bool = True,
    ):
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
        should_write_waveforms = waveforms and self.points._waveform_state is not None
        if isinstance(destination, (str, pathlib.Path)):
            destination_path = pathlib.Path(destination)
            if should_write_waveforms:
                self._write_waveforms(
                    destination_path,
                    waveform_chunksize=waveform_chunksize,
                )
            do_compress = destination_path.suffix.lower() == ".laz"

            with destination_path.open(mode="wb+") as out:
                self._write_to(out, do_compress=do_compress, laz_backend=laz_backend)
        else:
            if should_write_waveforms:
                raise NotImplementedError(
                    "Writing to file-like objects is not supported for waveform LAS/LAZ files"
                )
            self._write_to(
                destination, do_compress=do_compress, laz_backend=laz_backend
            )

    def _write_waveforms(
        self,
        destination_path: pathlib.Path,
        *,
        waveform_chunksize: int,
    ) -> None:
        if "wavepacket_index" not in self.points.array.dtype.names:
            raise ValueError(
                "Point data has no 'wavepacket_index' dimension, cannot write waveforms"
            )

        point_count = len(self.points)
        has_waveform_mask = np.asarray(
            self.points.array["wavepacket_index"] != 0, dtype=bool
        )
        offsets = np.zeros(point_count, dtype=np.uint64)
        sizes = np.zeros(point_count, dtype=self.points.array["wavepacket_size"].dtype)
        if not has_waveform_mask.any():
            self.points.array["wavepacket_offset"] = offsets
            self.points.array["wavepacket_size"] = sizes
            self._set_waveform_storage_flags(False)
            return

        match self.points._waveform_state:
            case record.LazyWaveformState() as lazy_state:
                self._write_wdp_lazy(
                    destination=destination_path,
                    lazy_state=lazy_state,
                    has_waveform_mask=has_waveform_mask,
                    waveform_size=lazy_state.reader.wave_size_bytes,
                    chunksize=waveform_chunksize,
                )
            case record.EagerWaveformState() as eager_state:
                self._write_wdp_eager(
                    destination_path,
                    has_waveform_mask,
                    eager_state=eager_state,
                )
            case None:
                raise RuntimeError(
                    "Internal error: _write_waveforms called without waveform state"
                )

    def _write_wdp_eager(
        self,
        destination_path: pathlib.Path,
        has_waveform_mask: NDArray[np.bool],
        *,
        eager_state: record.EagerWaveformState,
    ) -> None:
        waveforms = eager_state.waveforms
        points_waveform_index = eager_state.points_waveform_index

        point_count = len(self.points)
        wave_size_bytes = waveforms.wave_size
        offsets = np.zeros(point_count, dtype=np.uint64)
        offsets[has_waveform_mask] = (
            np.asarray(points_waveform_index[has_waveform_mask], dtype=np.uint64)
            * wave_size_bytes
        )
        self.points.array["wavepacket_offset"] = offsets
        self._finalize_waveform_write(has_waveform_mask, wave_size_bytes)
        self._write_wdp(destination_path.with_suffix(".wdp"), waveforms)

    @staticmethod
    def _write_wdp(path: pathlib.Path, waveforms: WaveformRecord | None) -> None:
        if waveforms is None:
            return
        samples = np.ascontiguousarray(waveforms.samples)
        with path.open("wb") as out_wdp:
            out_wdp.write(memoryview(samples))

    def _write_wdp_lazy(
        self,
        *,
        destination: pathlib.Path,
        lazy_state: record.LazyWaveformState,
        has_waveform_mask: NDArray[np.bool],
        waveform_size: int,
        chunksize: int,
    ) -> None:
        self._validate_waveform_sizes(has_waveform_mask, waveform_size)

        point_count = len(self.points)
        if point_count == 0:
            destination.with_suffix(".wdp").open("wb").close()
            return

        points_per_chunk = self._points_per_chunk(waveform_size, chunksize)

        wdp_path = destination.with_suffix(".wdp")
        self._write_wdp_lazy_dedup(
            wdp_path,
            lazy_state.reader,
            has_waveform_mask,
            waveform_size,
            points_per_chunk,
        )
        self._finalize_waveform_write(has_waveform_mask, waveform_size)

    def _validate_waveform_sizes(
        self,
        has_waveform_mask: NDArray[np.bool],
        waveform_size: int,
    ) -> None:
        sizes = np.asarray(self.points.array["wavepacket_size"], dtype=np.uint64)
        sizes_to_check = sizes[has_waveform_mask]

        actual = set(sizes_to_check)
        if actual - {waveform_size}:
            raise ValueError(
                f"Inconsistent waveform sizes in point data: {actual} but descriptor size is {waveform_size}"
            )

    @staticmethod
    def _points_per_chunk(waveform_size: int, chunksize: int) -> int:
        if chunksize <= 0:
            raise ValueError("waveform_chunksize must be > 0")
        return max(1, int(chunksize // waveform_size))

    def _write_wdp_lazy_dedup(
        self,
        wdp_path: pathlib.Path,
        waveform_reader: record.IWaveformReader,
        has_waveform_mask: NDArray[np.bool],
        waveform_size: int,
        points_per_chunk: int,
    ) -> None:
        point_count = len(self.points)
        offsets = np.asarray(self.points.array["wavepacket_offset"], dtype=np.uint64)
        unique_indices, inverse_indices = deduplicate_waveform_indices(
            offsets, has_waveform_mask, waveform_size
        )

        with wdp_path.open("wb") as dst:
            for run_start, run_end in iter_runs(unique_indices):
                count = int(run_end - run_start + 1)
                waveform_reader.seek(run_start)
                while count > 0:
                    chunk_count = min(points_per_chunk, count)
                    dst.write(waveform_reader.read_n_waveforms(int(chunk_count)))
                    count -= chunk_count

        offset_dtype = self.points.array["wavepacket_offset"].dtype
        new_offsets = np.zeros(point_count, dtype=offset_dtype)
        if has_waveform_mask.any():
            new_offsets[has_waveform_mask] = (
                inverse_indices.astype(np.uint64) * waveform_size
            ).astype(offset_dtype, copy=False)
        self.points.array["wavepacket_offset"] = new_offsets

    def _finalize_waveform_write(
        self,
        has_waveform_mask: NDArray[np.bool],
        waveform_size: int,
    ) -> None:
        size_dtype = self.points.array["wavepacket_size"].dtype
        sizes = np.zeros(len(self.points), dtype=size_dtype)
        sizes[has_waveform_mask] = waveform_size
        self.points.array["wavepacket_size"] = sizes

        self._set_waveform_storage_flags(bool(has_waveform_mask.any()))

    def _set_waveform_storage_flags(self, has_waveforms: bool) -> None:
        self.header.global_encoding.waveform_data_packets_external = has_waveforms
        if self.header.global_encoding.waveform_data_packets_internal:
            self.header.global_encoding.waveform_data_packets_internal = False
        if self.header.version.minor >= 3:
            self.header.start_of_waveform_data_packet_record = 0

    def _write_to(
        self,
        out_stream: BinaryIO,
        do_compress: bool | None = None,
        laz_backend: LazBackend | Sequence[LazBackend] | None = None,
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
        self, item: str | list[str]
    ) -> np.ndarray | ScaledArrayView | SubFieldView: ...

    @typing.overload
    def __getitem__(self, item: int | typing.Iterable[int] | slice) -> "LasData": ...

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
