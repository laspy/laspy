import logging
import os
from .waveform import WaveformPacketDescriptorRegistry, WaveformRecord
from pathlib import Path
from ._compression.selection import DecompressionSelection
from collections.abc import Iterable
from ._compression.backend import LazBackend
from typing import BinaryIO, Optional, Union, Any
from .lasreader import LasReader
from .lasdata import LasData
from .point import record
import numpy as np


logger = logging.getLogger(__name__)


class WaveformPointRecord(record.ScaleAwarePointRecord):
    def __init__(
        self,
        array: np.ndarray,
        point_format,
        scales: np.ndarray,
        offsets: np.ndarray,
        waveforms: WaveformRecord,
        points_waveform_index: np.ndarray[Any, np.dtype[np.int64]],
    ):
        super().__init__(array, point_format, scales, offsets)
        self._waveforms = waveforms
        self._points_waveform_index = points_waveform_index
        old = array.dtype.descr
        new = old + waveforms.samples.dtype.descr
        self._array = np.empty(array.shape, dtype=new)
        for name in array.dtype.names:  # ty:ignore[not-iterable]
            self._array[name] = array[name]
        self._array["wave"] = waveforms.samples["wave"][self._points_waveform_index]
    
    @classmethod
    def merge_points_waveforms(
        cls,
        points: record.ScaleAwarePointRecord,
        waveforms: WaveformRecord,
        points_waveform_index: np.ndarray[Any, np.dtype[np.int64]],
    ) -> "WaveformPointRecord":
        return cls(
            points.array,
            points.point_format,
            points.scales,
            points.offsets,
            waveforms,
            points_waveform_index,
        )

    def __getitem__(self, item):
        if isinstance(item, (int, slice, np.ndarray, list, tuple)):
            if isinstance(item, (list, tuple)):
                item = [
                    item if item not in ("x", "y", "z") else item.upper()
                    for item in item
                ]
            return WaveformPointRecord(
                self.array[item],
                self.point_format,
                self.scales,
                self.offsets,
                self._waveforms,
                self._points_waveform_index[item],
            )
        if item == "wave":
            return self._array["wave"]
        return super().__getitem__(item)


class WaveformLasData(LasData):
    def __init__(
        self,
        header,
        points: record.ScaleAwarePointRecord,
        waveform_points: WaveformPointRecord,
    ) -> None:
        super().__init__(header=header, points=points)
        self._waveform_points = waveform_points

    @property
    def waveform_points(self) -> WaveformPointRecord:
        return self._waveform_points
    
    def __repr__(self) -> str:
        return "<WaveformLasData({}.{}, point fmt: {}, {} points, {} vlrs, {} waveforms)>".format(
            self.header.version.major,
            self.header.version.minor,
            self.points.point_format,
            len(self.points),
            len(self.vlrs),
            len(self.waveform_points._waveforms),
        )


class WaveReader:
    def __init__(
        self,
        source: BinaryIO,
        bits_per_sample: int,
        number_of_samples: int,
        closefd: bool = True,
    ):
        self._source = source
        self.bits_per_sample = bits_per_sample
        self.number_of_samples = number_of_samples
        self._closefd = closefd
        self.wave_size_bytes = (self.bits_per_sample // 8) * self.number_of_samples

    @property
    def source(self) -> BinaryIO:
        return self._source

    def read_n_waveforms(self, n: int) -> bytearray:
        total_size = n * self.wave_size_bytes
        data = self._source.read(total_size)
        return bytearray(data)

    def seek(self, waveform_index: int) -> None:
        offset = waveform_index * self.wave_size_bytes
        self._source.seek(offset)

    def close(self) -> None:
        if self._closefd:
            self._source.close()


class LasFWReader(LasReader):
    def __init__(
        self,
        source: BinaryIO,
        closefd: bool = True,
        laz_backend: Optional[Union[LazBackend, Iterable[LazBackend]]] = None,
        read_evlrs: bool = True,
        decompression_selection: DecompressionSelection = DecompressionSelection.all(),
    ):
        super().__init__(
            source,
            closefd=closefd,
            laz_backend=laz_backend,
            read_evlrs=read_evlrs,
            decompression_selection=decompression_selection,
        )
        if not self.header.point_format.has_waveform_packet:
            raise ValueError("Point format does not carry waveform attributes")

        if not self.header.global_encoding.waveform_data_packets_external:
            raise ValueError(
                "This reader expects waveform data to live in an external .wdp file"
            )

        las_path = Path(source.name)
        waveform_file = las_path.with_suffix(".wdp").open("rb")
        self._waveform_descriptors_registry = (
            WaveformPacketDescriptorRegistry.from_vlrs(self.header.vlrs)
        )
        self._waveform_source = WaveReader(
            waveform_file,
            bits_per_sample=self._waveform_descriptors_registry.bits_per_sample,
            number_of_samples=self._waveform_descriptors_registry.number_of_samples,
            closefd=True,
        )
        self.waves_read = 0
        waveform_file.seek(0, os.SEEK_SET)

    def read_points_waveforms(
        self, n: int
    ) -> tuple[record.ScaleAwarePointRecord, WaveformPointRecord]:
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
        points_left = self.header.point_count - self.points_read
        if points_left <= 0:
            raise NotImplementedError

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

        # Extract waveform offsets and sizes
        waveform_offsets = points.array["wavepacket_offset"]
        waveform_sizes = points.array["wavepacket_size"]
        if set(waveform_sizes) - {self._waveform_source.wave_size_bytes}:
            raise ValueError(
                f"Inconsistent waveform sizes in point data: {set(waveform_sizes)} but descriptor size is {self._waveform_source.wave_size_bytes}"
            )
        waveform_size = self._waveform_source.wave_size_bytes

        # So here we have a lot of offsets, duplicated, potentially not sorted
        # and with potential gaps.
        # We want to minimize the number reads from disk.
        # So we will sort the offsets, read the waveforms in order
        # and then reassemble the waveforms in the original order.
        # When N offsets are adjacent, we can read them in a single read with self.point_source.read_n_points(N)
        unique_offsets, inverse_indices = np.unique(
            waveform_offsets, return_inverse=True
        )
        # sort the unique offsets
        sorted_indices = np.argsort(unique_offsets)
        sorted_unique_offsets = unique_offsets[sorted_indices]
        # Find runs of adjacent offsets
        runs = []
        start = sorted_unique_offsets[0]
        last = start
        for offset in sorted_unique_offsets[1:]:
            if offset == last + waveform_size:
                last = offset
            else:
                runs.append((start, last))
                start = offset
                last = offset
        runs.append((start, last))

        # Read the waveforms in runs
        waveform_data = bytearray()
        for start, end in runs:
            count = (end - start) // waveform_size + 1
            self._waveform_source.seek(start // waveform_size)
            data = self._waveform_source.read_n_waveforms(count)
            waveform_data.extend(data)
        waveforms = WaveformRecord.from_buffer(
            waveform_data,
            self._waveform_descriptors_registry.dtype(),
            self._waveform_descriptors_registry.number_of_samples,
            self._waveform_descriptors_registry.temporal_sample_spacing,
            count=len(unique_offsets),
        )

        # Map each point to its waveform index in sorted_unique_offsets without per-wave scans.
        # np.unique gives indices into unique_offsets; remap those to sorted indices.
        unique_to_sorted = np.empty_like(sorted_indices)
        unique_to_sorted[sorted_indices] = np.arange(len(sorted_indices))
        points_waveform_index = unique_to_sorted[inverse_indices]

        waveforms = WaveformPointRecord(
            points.array,
            points.point_format,
            points.scales,
            points.offsets,
            waveforms,
            np.asarray(points_waveform_index, dtype=np.int64),
        )
        return points, waveforms

    def read(self) -> WaveformLasData:
        self._waveform_source.source.seek(0, os.SEEK_SET)
        self.waves_read = 0
        points, waveform_points = self.read_points_waveforms(-1)

        return WaveformLasData(
            header=self.header,
            points=points,
            waveform_points=waveform_points,
        )
