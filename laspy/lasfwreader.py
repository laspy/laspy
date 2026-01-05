from copy import deepcopy
import logging
import os
from .waveform import WaveformPacketDescriptorRegistry, WaveformRecord, WavePacketDescriptorRecordId
from pathlib import Path
from ._compression.selection import DecompressionSelection
from collections.abc import Iterable, Sequence
from ._compression.backend import LazBackend
from typing import BinaryIO, Optional, Union, Any, overload
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
        self._points_waveform_index = points_waveform_index # maps each point to its waveform index in waveforms

    def __getitem__(self, item):
        if isinstance(item, (int, slice, np.ndarray, list, tuple)):
            if isinstance(item, (list, tuple)):
                item = [
                    item if item not in ("x", "y", "z") else item.upper()
                    for item in item
                ]
            elif isinstance(item, (int, slice, np.ndarray)):
                # we want to subset the waveforms as well
                points_waveform_index_subset = self._points_waveform_index[item]
                unique_waves_indices, inverse_indices = np.unique(
                    points_waveform_index_subset, return_inverse=True
                )
                waveforms_subset = WaveformRecord(
                    self._waveforms.samples[unique_waves_indices],
                    self._waveforms.sample_spacing_ps,
                )
                points_waveform_index = np.asarray(inverse_indices, dtype=np.int64)
                return WaveformPointRecord(
                    self.array[item],
                    self.point_format,
                    self.scales,
                    self.offsets,
                    waveforms_subset,
                    points_waveform_index,
                )
        if item == "wave":
            return self._waveforms.samples["wave"][self._points_waveform_index]
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
    
    def __getitem__(self, item):
        try:
            item_is_list_of_str = all(isinstance(el, str) for el in iter(item))
        except TypeError:
            item_is_list_of_str = False

        if isinstance(item, str) or item_is_list_of_str:
            return self.points[item]
        else:
            las = WaveformLasData(deepcopy(self.header), points=self.points[item], waveform_points=self.waveform_points[item])
            las.update_header()
            return las
    
    def __repr__(self) -> str:
        return "<WaveformLasData({}.{}, point fmt: {}, {} points, {} vlrs, {} waveforms)>".format(
            self.header.version.major,
            self.header.version.minor,
            self.points.point_format,
            len(self.points),
            len(self.vlrs),
            len(self.waveform_points._waveforms),
        )
    
    @overload
    def write(
        self,
        destination: str,
        laz_backend: Optional[Union[LazBackend, Sequence[LazBackend]]] = ...,
    ) -> None: ...
    @overload
    def write(
        self,
        destination: BinaryIO,
        do_compress: Optional[bool] = ...,
        laz_backend: Optional[Union[LazBackend, Sequence[LazBackend]]] = ...,
    ) -> None: ...

    def write(self, destination: Union[str, BinaryIO], do_compress: Optional[bool] = None, laz_backend: Optional[Union[LazBackend, Sequence[LazBackend]]] = None):
        if not self.header.point_format.has_waveform_packet:
            raise ValueError("Point format does not carry waveform attributes")

        registry = WaveformPacketDescriptorRegistry.from_vlrs(self.header.vlrs)
        waveforms = self.waveform_points._waveforms
        points_waveform_index = self.waveform_points._points_waveform_index

        if len(points_waveform_index) != len(self.points):
            raise ValueError(
                "Waveform index mapping size does not match number of points"
            )

        wave_size_bytes = waveforms.wave_size
        expected_wave_size = registry.dtype().itemsize
        if wave_size_bytes != expected_wave_size:
            raise ValueError(
                f"Inconsistent waveform sizes: wave record size is {wave_size_bytes} bytes but descriptor expects {expected_wave_size} bytes"
            )

        if len(self.points) and len(waveforms) == 0:
            raise ValueError("Waveform data is missing for points")

        if len(points_waveform_index) > 0:
            if points_waveform_index.min() < 0 or points_waveform_index.max() >= len(
                waveforms
            ):
                raise ValueError("Waveform index mapping is out of bounds")

        offsets = np.asarray(points_waveform_index, dtype=np.uint64) * wave_size_bytes
        self.points.array["wavepacket_offset"] = offsets
        size_dtype = self.points.array["wavepacket_size"].dtype
        self.points.array["wavepacket_size"] = np.full(
            len(self.points), wave_size_bytes, dtype=size_dtype
        )

        self.header.global_encoding.waveform_data_packets_external = True
        if self.header.global_encoding.waveform_data_packets_internal:
            self.header.global_encoding.waveform_data_packets_internal = False
        if self.header.version.minor >= 3:
            self.header.start_of_waveform_data_packet_record = 0

        if isinstance(destination, str):
            destination_path = Path(destination)
            do_compress = destination_path.suffix.lower() == ".laz"
            with destination_path.open(mode="wb+") as out_stream:
                self._write_wdp(destination_path.with_suffix(".wdp"), waveforms)
                self._write_to(
                    out_stream, do_compress=do_compress, laz_backend=laz_backend
                )
        else:
            raise NotImplementedError("Writing to file-like objects is not supported for waveform LAS/LAZ files")

    @staticmethod
    def _write_wdp(path: Path, waveforms: WaveformRecord) -> None:
        samples = np.ascontiguousarray(waveforms.samples)
        with path.open("wb") as out_wdp:
            out_wdp.write(memoryview(samples))


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

    def _compute_valid_descriptor_mask(
        self, points: record.ScaleAwarePointRecord, allow_missing_descriptors: bool
    ) -> tuple[np.ndarray, bool]:
        descriptor_indices = points.array["wavepacket_index"]
        unique_descriptor_indices, first_index = np.unique(
            descriptor_indices, return_index=True
        )

        if not allow_missing_descriptors:
            for idx in unique_descriptor_indices:
                if (
                    WavePacketDescriptorRecordId.from_index(idx)
                    not in self._waveform_descriptors_registry
                ):
                    raise ValueError(
                        f"No matching descriptor found for point {first_index[idx]}.\n"
                        f" Available waveform descriptors record IDs: {list(self._waveform_descriptors_registry.data.keys())}\n"
                        f" Waveform descriptor record ID found: {WavePacketDescriptorRecordId.from_index(idx)}"
                    )
            return np.ones_like(descriptor_indices, dtype=bool), False

        valid_descriptor_indices = np.array(
            [
                record_id - WavePacketDescriptorRecordId.RECORD_ID_OFFSET
                for record_id in self._waveform_descriptors_registry.data.keys()
            ],
            dtype=descriptor_indices.dtype,
        )
        valid_mask = np.isin(descriptor_indices, valid_descriptor_indices)
        missing = not np.all(valid_mask)
        if missing:
            missing_descriptor_indices = np.setdiff1d(
                unique_descriptor_indices, valid_descriptor_indices
            )
            if missing_descriptor_indices.size:
                first_missing_index = first_index[
                    np.isin(unique_descriptor_indices, missing_descriptor_indices)
                ][0]
                logger.warning(
                    "Unknown waveform descriptor(s) found (indices: %s). "
                    "Filling points like %s with zero waveforms.",
                    missing_descriptor_indices.tolist(),
                    int(first_missing_index),
                )
            # Make the point record self-consistent by remapping missing descriptor
            # indices to a known descriptor index (the write path relies on VLRS).
            fallback_descriptor_index = int(valid_descriptor_indices.min())
            points.array["wavepacket_index"][~valid_mask] = fallback_descriptor_index

        return valid_mask, missing

    def _validate_waveform_sizes(
        self, waveform_sizes: np.ndarray, valid_mask: np.ndarray
    ) -> None:
        if not valid_mask.any():
            return
        expected = self._waveform_source.wave_size_bytes
        actual = set(waveform_sizes[valid_mask])
        if actual - {expected}:
            raise ValueError(
                f"Inconsistent waveform sizes in point data: {actual} but descriptor size is {expected}"
            )

    def _runs_for_sorted_offsets(
        self, sorted_offsets: np.ndarray, waveform_size: int
    ) -> list[tuple[int, int]]:
        runs: list[tuple[int, int]] = []
        if sorted_offsets.size == 0:
            return runs

        start = int(sorted_offsets[0])
        last = start
        for offset in sorted_offsets[1:]:
            offset_int = int(offset)
            if offset_int == last + waveform_size:
                last = offset_int
            else:
                runs.append((start, last))
                start = offset_int
                last = offset_int
        runs.append((start, last))
        return runs

    def _read_waveforms_by_runs(
        self, runs: list[tuple[int, int]], waveform_size: int
    ) -> bytearray:
        waveform_data = bytearray()
        for start, end in runs:
            count = (end - start) // waveform_size + 1
            self._waveform_source.seek(start // waveform_size)
            waveform_data.extend(self._waveform_source.read_n_waveforms(count))
        return waveform_data

    def _read_waveforms_for_offsets(
        self, offsets: np.ndarray
    ) -> tuple[WaveformRecord, np.ndarray[Any, np.dtype[np.int64]]]:
        if offsets.size == 0:
            waveforms = WaveformRecord.empty(
                self._waveform_descriptors_registry.dtype(),
                self._waveform_descriptors_registry.number_of_samples,
                self._waveform_descriptors_registry.temporal_sample_spacing,
            )
            return waveforms, np.empty(0, dtype=np.int64)

        waveform_size = self._waveform_source.wave_size_bytes
        unique_offsets, inverse_indices = np.unique(offsets, return_inverse=True)

        sorted_indices = np.argsort(unique_offsets)
        sorted_unique_offsets = unique_offsets[sorted_indices]
        runs = self._runs_for_sorted_offsets(sorted_unique_offsets, waveform_size)
        waveform_data = self._read_waveforms_by_runs(runs, waveform_size)

        waveforms = WaveformRecord.from_buffer(
            waveform_data,
            self._waveform_descriptors_registry.dtype(),
            self._waveform_descriptors_registry.number_of_samples,
            self._waveform_descriptors_registry.temporal_sample_spacing,
            count=len(unique_offsets),
        )

        # np.unique gives indices into unique_offsets; remap those to sorted indices.
        unique_to_sorted = np.empty_like(sorted_indices)
        unique_to_sorted[sorted_indices] = np.arange(len(sorted_indices))
        points_waveform_index = unique_to_sorted[inverse_indices]
        return waveforms, np.asarray(points_waveform_index, dtype=np.int64)

    def _append_zero_waveform(self, waveforms: WaveformRecord) -> tuple[WaveformRecord, int]:
        wave_dtype = self._waveform_descriptors_registry.dtype()
        missing_wave_index = len(waveforms)
        new_samples = np.empty((missing_wave_index + 1,), dtype=wave_dtype)
        if len(waveforms):
            new_samples[:-1] = waveforms.samples
        new_samples["wave"][-1] = 0
        return (
            WaveformRecord(
                new_samples, self._waveform_descriptors_registry.temporal_sample_spacing
            ),
            missing_wave_index,
        )

    def read_points_waveforms(
        self, n: int, allow_missing_descriptors: bool = True
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
        allow_missing_descriptors: If True, points with unknown waveform
            descriptor indices get a zero waveform instead of raising.
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

        valid_mask, has_missing_descriptors = self._compute_valid_descriptor_mask(
            points, allow_missing_descriptors
        )

        # Extract waveform offsets and sizes
        waveform_offsets = points.array["wavepacket_offset"]
        waveform_sizes = points.array["wavepacket_size"]
        self._validate_waveform_sizes(waveform_sizes, valid_mask)

        valid_offsets = waveform_offsets[valid_mask]
        waveforms, valid_points_waveform_index = self._read_waveforms_for_offsets(
            valid_offsets
        )

        points_waveform_index = np.full(len(points), -1, dtype=np.int64)
        points_waveform_index[valid_mask] = valid_points_waveform_index

        if allow_missing_descriptors and has_missing_descriptors:
            waveforms, missing_wave_index = self._append_zero_waveform(waveforms)
            points_waveform_index[~valid_mask] = missing_wave_index

        waveforms = WaveformPointRecord(
            points.array,
            points.point_format,
            points.scales,
            points.offsets,
            waveforms,
            np.asarray(points_waveform_index, dtype=np.int64),
        )
        return points, waveforms

    def read(self, allow_missing_descriptors: bool = True) -> WaveformLasData:
        self._waveform_source.source.seek(0, os.SEEK_SET)
        self.waves_read = 0
        points, waveform_points = self.read_points_waveforms(
            -1, allow_missing_descriptors=allow_missing_descriptors
        )

        return WaveformLasData(
            header=self.header,
            points=points,
            waveform_points=waveform_points,
        )
