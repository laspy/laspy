import io
import logging
import os
from pathlib import Path
from typing import BinaryIO, Iterable, Optional, Union

import numpy as np

from . import errors
from ._compression.backend import LazBackend
from ._compression.lazrsbackend import LazrsPointReader
from ._pointreader import IPointReader
from .compression import DecompressionSelection
from .header import LasHeader
from .lasdata import LasData
from .point import record
from .vlrs.vlrlist import VLRList
from .waveform import WaveformRecord
from .waveform.descriptor import (
    WaveformPacketDescriptorRegistry,
    WavePacketDescriptorRecordId,
)
from .waveform.mode import WaveformMode
from .waveform.record import IWaveformReader

logger = logging.getLogger(__name__)


class LasReader:
    """The reader class handles LAS and LAZ via one of the supported backend"""

    def __init__(
        self,
        source: BinaryIO,
        closefd: bool = True,
        laz_backend: Optional[Union[LazBackend, Iterable[LazBackend]]] = None,
        read_evlrs: bool = True,
        decompression_selection: DecompressionSelection = DecompressionSelection.all(),
        waveform_mode: WaveformMode = WaveformMode.NEVER,
    ):
        """
        Initialize the LasReader

        Parameters
        ----------
        source: file_object
        closefd: bool, default True
        laz_backend: LazBackend or list of LazBackend, optional
        read_evlrs: bool, default True
            only applies to __init__ phase, and for files
            that support evlrs
        decompression_selection: optional, DecompressionSelection
            Selection of fields to decompress, only works form point format >= 6 <= 10
            Ignored on other point formats

        .. versionadded:: 2.4
            The ``read_evlrs`` and ``decompression_selection`` parameters.
        """
        self.closefd = closefd
        if laz_backend is None:
            laz_backend = LazBackend.detect_available()
        self.laz_backend = laz_backend
        self.header = LasHeader.read_from(source, read_evlrs=read_evlrs)
        self.decompression_selection = decompression_selection

        # The point source is lazily instanciated.
        # Because some reader implementation may
        # read informations that require to seek towards the end of
        # the file (eg: chunk table), and we prefer to limit opening
        # to reading the header
        self._point_source: Optional["IPointReader"] = None
        self._source = source

        self.points_read = 0
        self._waveform_mode = WaveformMode(waveform_mode)
        self._waveform_source: Optional[WaveReader] = None
        self._waveform_descriptors_registry = WaveformPacketDescriptorRegistry()

    @property
    def evlrs(self) -> Optional[VLRList]:
        return self.header.evlrs

    @evlrs.setter
    def evlrs(self, evlrs: VLRList) -> None:
        self.header.evlrs = evlrs

    @property
    def point_source(self) -> "IPointReader":
        if self._point_source is None:
            self._point_source = self._create_point_source(self._source)
        return self._point_source

    def _read_points(self, n: int) -> record.ScaleAwarePointRecord:
        """Read n points from the file


        Will only read as many points as the header advertise.
        That is, if you ask to read 50 points and there are only 45 points left
        this function will only read 45 points.

        If there are no points left to read, returns an empty point record.

        Parameters
        ----------
        n: The number of points to read
           if n is less than 0, this function will read the remaining points
        """
        points_left = self.header.point_count - self.points_read
        if points_left <= 0:
            return record.ScaleAwarePointRecord.empty(
                self.header.point_format,
                self.header.scales,
                self.header.offsets,
            )

        if n < 0:
            n = points_left
        else:
            n = min(n, points_left)

        r = record.PackedPointRecord.from_buffer(
            self.point_source.read_n_points(n), self.header.point_format
        )
        if len(r) < n:
            logger.error(f"Could only read {len(r)} of the requested {n} points")

        points = record.ScaleAwarePointRecord(
            r.array, r.point_format, self.header.scales, self.header.offsets
        )

        self.points_read += n
        return points

    def _ensure_waveform_source(self) -> bool:
        if self._waveform_source is not None:
            return True

        if not self.header.point_format.has_waveform_packet:
            return False

        if not self.header.global_encoding.waveform_data_packets_external:
            raise ValueError(
                "This reader expects waveform data to live in an external .wdp file"
            )

        source_name = getattr(self._source, "name", None)
        if source_name is None:
            raise ValueError(
                "Cannot locate the external waveform .wdp file from this source."
            )

        self._waveform_descriptors_registry = (
            WaveformPacketDescriptorRegistry.from_vlrs(self.header.vlrs)
        )
        wave_dtype = self._waveform_descriptors_registry.dtype()

        las_path = Path(source_name)
        wdp_path = las_path.with_suffix(".wdp")
        waveform_file = wdp_path.open("rb")
        if wave_dtype is None:
            waveform_file.close()
            raise ValueError("No waveform packet descriptors found in VLRs")

        self._waveform_source = WaveReader(
            waveform_file,
            bits_per_sample=self._waveform_descriptors_registry.bits_per_sample,
            number_of_samples=self._waveform_descriptors_registry.number_of_samples,
            temporal_sample_spacing=self._waveform_descriptors_registry.temporal_sample_spacing,
            wave_dtype=wave_dtype,
            closefd=True,
            source_path=wdp_path,
        )
        waveform_file.seek(0, os.SEEK_SET)
        return True

    def _ensure_points_have_valid_waveform_descriptors(
        self, points: record.ScaleAwarePointRecord
    ) -> None:
        descriptor_indices = points.array["wavepacket_index"]
        no_waveform_mask = descriptor_indices == 0

        valid_descriptor_indices = np.array(
            [
                record_id - WavePacketDescriptorRecordId.RECORD_ID_OFFSET
                for record_id in self._waveform_descriptors_registry.data.keys()
            ],
            dtype=descriptor_indices.dtype,
        )
        known_descriptor_mask = np.isin(descriptor_indices, valid_descriptor_indices)
        unknown_descriptor_mask = ~known_descriptor_mask & ~no_waveform_mask
        missing_descriptors = bool(np.any(unknown_descriptor_mask))

        if missing_descriptors:
            if valid_descriptor_indices.size == 0:
                raise ValueError("No waveform packet descriptors found in VLRs")
            first_missing_point = int(np.flatnonzero(unknown_descriptor_mask)[0])
            missing_descriptor_index = int(descriptor_indices[first_missing_point])
            raise ValueError(
                f"No matching descriptor found for point {first_missing_point}.\n"
                f" Available waveform descriptors record IDs: {list(self._waveform_descriptors_registry.data.keys())}\n"
                f" Waveform descriptor record ID found: {WavePacketDescriptorRecordId.from_index(missing_descriptor_index)}"
            )

    def read_points(
        self,
        n: int,
        *,
        waveform_mode: WaveformMode | None = None,
    ) -> record.ScaleAwarePointRecord:
        """Read n points from the file, and their associated waveforms.


        Will only read as many points as the header advertise.
        That is, if you ask to read 50 points and there are only 45 points left
        this function will only read 45 points.

        If there are no points left to read, returns an empty point record.

        Parameters
        ----------
        n: The number of points to read
           if n is less than 0, this function will read the remaining points
        """
        if waveform_mode is None:
            waveform_mode = self._waveform_mode
        else:
            waveform_mode = WaveformMode(waveform_mode)

        waveform_available = False
        if waveform_mode is not WaveformMode.NEVER:
            waveform_available = self._ensure_waveform_source()

        points = self._read_points(n)
        if (
            len(points) == 0
            or waveform_mode is WaveformMode.NEVER
            or not waveform_available
            or self._waveform_source is None
        ):
            points._set_waveform_state(None)
            return points

        self._ensure_points_have_valid_waveform_descriptors(points)

        if waveform_mode is WaveformMode.LAZY:
            points._set_waveform_state(record.LazyWaveformState(self._waveform_source))
            return points

        waveforms_record, points_waveform_index = WaveformRecord.from_points(
            points.array,
            self._waveform_source,
        )

        points._set_waveform_state(
            record.EagerWaveformState(
                waveforms_record,
                points_waveform_index,
            )
        )
        return points

    def read(
        self,
        *,
        waveform_mode: WaveformMode | None = None,
    ) -> LasData:
        """
        Reads all the points that are not read and returns a LasData object

        This will also read EVLRS

        """
        if self._waveform_source is not None:
            self._waveform_source.source.seek(0, os.SEEK_SET)
        points = self.read_points(
            -1,
            waveform_mode=waveform_mode,
        )
        las_data = LasData(header=self.header, points=points)

        shall_read_evlr = (
            self.header.version.minor >= 4
            and self.header.number_of_evlrs > 0
            and self.evlrs is None
        )
        if shall_read_evlr:
            # If we have to read evlrs by now, it either means:
            #   - the user asked for them not to be read during the opening phase.
            #   - and/or the stream is not seekable, thus they could not be read during opening phase
            #
            if self.point_source.source.seekable():
                self.read_evlrs()
            else:
                # In that case we are still going to
                # try to read the evlrs by relying on the fact that they should generally be
                # right after the last point, which is where we are now.
                if self.header.are_points_compressed:
                    if not isinstance(self.point_source, LazrsPointReader):
                        raise errors.LaspyException(
                            "Reading EVLRs from a LAZ in a non-seekable stream "
                            "can only be done with lazrs backend"
                        )
                    # Few things: If the stream is non seekable, only a LazrsPointReader
                    # could have been created (parallel requires ability to seek)
                    #
                    # Also, to work, the next lines of code assumes that:
                    # 1) We actually are just after the last point
                    # 2) The chunk table _starts_ just after the last point
                    # 3) The first EVLR starts just after the chunk table
                    # These assumptions should be fine for most of the cases
                    # and non seekable sources are probably not that common
                    _ = self.point_source.read_chunk_table_only()

                    # Since the LazrsDecompressor uses a buffered reader
                    # the python file object's position is not at the position we
                    # think it is.
                    # So we have to read data from the decompressor's
                    # buffered stream.
                    class LocalReader:
                        def __init__(self, source: LazrsPointReader) -> None:
                            self.source = source

                        def read(self, n: int) -> bytes:
                            return self.source.read_raw_bytes(n)

                    self.evlrs = VLRList.read_from(
                        LocalReader(self.point_source),
                        self.header.number_of_evlrs,
                        extended=True,
                    )
                else:
                    # For this to work, we assume that the first evlr
                    # start just after the last point
                    self.header.evlrs = VLRList.read_from(
                        self.point_source.source,
                        self.header.number_of_evlrs,
                        extended=True,
                    )
        return las_data

    def seek(self, pos: int, whence: int = io.SEEK_SET) -> int:
        """Seeks to the start of the point at the given pos

        Parameters
        ----------
        pos: index of the point to seek to
        whence: optional, controls how the pos parameter is interpreted:
                io.SEEK_SET: (default) pos is the index of the point from the beginning
                io.SEEK_CUR: pos is the point_index relative to the point_index of the last point read
                io.SEEK_END: pos is the point_index relative to last point
        Returns
        -------
        The index of the point the reader seeked to, relative to the first point
        """
        if whence == io.SEEK_SET:
            allowed_range = range(0, self.header.point_count)
            point_index = pos
        elif whence == io.SEEK_CUR:
            allowed_range = range(
                -self.points_read, self.header.point_count - self.points_read
            )
            point_index = self.points_read + pos
        elif whence == io.SEEK_END:
            allowed_range = range(-self.header.point_count, 0)
            point_index = self.header.point_count + pos
        else:
            raise ValueError(f"Invalid value for whence: {whence}")

        if pos not in allowed_range:
            whence_str = ["start", "current point", "end"]
            raise IndexError(
                f"When seeking from the {whence_str[whence]}, pos must be in {allowed_range}"
            )

        self.point_source.seek(point_index)
        self.points_read = point_index
        return point_index

    def chunk_iterator(self, points_per_iteration: int) -> "PointChunkIterator":
        """Returns an iterator, that will read points by chunks
        of the requested size

        :param points_per_iteration: number of points to be read with each iteration
        :return:
        """
        return PointChunkIterator(self, points_per_iteration)

    def read_evlrs(self):
        self.header.read_evlrs(self._source)

    def close(self) -> None:
        """closes the file object used by the reader"""
        if self._waveform_source is not None:
            self._waveform_source.close()
            self._waveform_source = None

        if self.closefd:
            # We check the actual source,
            # to avoid creating it, just to close it
            if self._point_source is not None:
                self._point_source.close()
            else:
                self._source.close()

    def _create_laz_backend(self, source) -> IPointReader:
        """Creates the laz backend to use according to `self.laz_backend`.

        If `self.laz_backend` contains mutilple backends, this functions will
        try to create them in order until one of them is successfully constructed.

        If none could be constructed, the error of the last backend tried wil be raised
        """
        if not self.laz_backend:
            raise errors.LaspyException(
                "No LazBackend selected, cannot decompress data"
            )

        try:
            backends = iter(self.laz_backend)
        except TypeError:
            backends = (self.laz_backend,)

        last_error: Optional[Exception] = None
        for backend in backends:
            try:
                if not backend.is_available():
                    raise errors.LaspyException(f"The '{backend}' is not available")

                reader: IPointReader = backend.create_reader(
                    source,
                    self.header,
                    decompression_selection=self.decompression_selection,
                )
            except Exception as e:
                last_error = e
                logger.error(e)
            else:
                self.header.vlrs.pop(self.header.vlrs.index("LasZipVlr"))
                return reader

        raise last_error

    def _create_point_source(self, source) -> IPointReader:
        if self.header.point_count > 0:
            if self.header.are_points_compressed:
                point_source = self._create_laz_backend(source)
                if point_source is None:
                    raise errors.LaspyException(
                        "Data is compressed, but no LazBacked could be initialized"
                    )
                return point_source
            else:
                return UncompressedPointReader(source, self.header)
        else:
            return EmptyPointReader()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class PointChunkIterator:
    def __init__(self, reader: LasReader, points_per_iteration: int) -> None:
        self.reader = reader
        self.points_per_iteration = points_per_iteration

    def __next__(self) -> record.ScaleAwarePointRecord:
        points = self.reader._read_points(self.points_per_iteration)
        if not points:
            raise StopIteration
        return points

    def __iter__(self) -> "PointChunkIterator":
        return self


class UncompressedPointReader(IPointReader):
    """Implementation of IPointReader for the simple uncompressed case"""

    def __init__(self, source, header: LasHeader) -> None:
        self._source = source
        self.header = header

    @property
    def source(self):
        return self._source

    def read_n_points(self, n: int) -> bytearray:
        try:
            readinto = self.source.readinto
        except AttributeError:
            data = bytearray(self.source.read(n * self.header.point_format.size))
        else:
            data = bytearray(n * self.header.point_format.size)
            num_read = readinto(data)
            if num_read < len(data):
                data = data[:num_read]

        return data

    def seek(self, point_index: int) -> None:
        self.source.seek(
            self.header.offset_to_point_data
            + (point_index * self.header.point_format.size)
        )

    def close(self):
        self.source.close()


class EmptyPointReader(IPointReader):
    """Does nothing but returning empty bytes.
    Used to make sure we handle empty LAS files in a robust way.
    """

    @property
    def source(self):
        pass

    def read_n_points(self, n: int) -> bytearray:
        return bytearray()

    def close(self) -> None:
        pass

    def seek(self, point_index: int) -> None:
        pass


class WaveReader(IWaveformReader):
    def __init__(
        self,
        source: BinaryIO,
        bits_per_sample: int,
        number_of_samples: int,
        temporal_sample_spacing: int,
        wave_dtype: np.dtype,
        closefd: bool = True,
        source_path: Path | None = None,
    ):
        self._source = source
        self.bits_per_sample = bits_per_sample
        self.number_of_samples = number_of_samples
        self._temporal_sample_spacing = temporal_sample_spacing
        self._wave_dtype = wave_dtype
        self._closefd = closefd
        self._source_path = source_path
        self._wave_size_bytes = (self.bits_per_sample // 8) * self.number_of_samples

    @property
    def source(self) -> BinaryIO:
        return self._source

    @property
    def temporal_sample_spacing(self) -> int:
        return self._temporal_sample_spacing

    @property
    def wave_dtype(self) -> np.dtype:
        return self._wave_dtype

    @property
    def wave_size_bytes(self) -> int:
        return self._wave_size_bytes

    def _ensure_open(self) -> None:
        if self._source.closed:
            if self._source_path is None:
                raise ValueError(
                    "Waveform source is closed and cannot be reopened; "
                    "keep the reader open or use fullwave='eager'."
                )
            self._source = self._source_path.open("rb")
            self._closefd = True

    def read_n_waveforms(self, n: int) -> bytearray:
        self._ensure_open()
        total_size = n * self.wave_size_bytes
        data = self._source.read(total_size)
        if len(data) != total_size:
            raise ValueError(
                f"failed to fill whole waveform buffer: requested {total_size} bytes, got {len(data)}"
            )
        return bytearray(data)

    def seek(self, waveform_index: int) -> None:
        self._ensure_open()
        offset = waveform_index * self.wave_size_bytes
        self._source.seek(offset)

    def close(self) -> None:
        if self._closefd:
            self._source.close()
