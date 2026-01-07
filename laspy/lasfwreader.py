from copy import deepcopy
import logging
import os
from .waveform import (
    WaveformPacketDescriptorRegistry,
    WaveformRecord,
    WavePacketDescriptorRecordId,
)
from pathlib import Path
from ._compression.selection import DecompressionSelection
from collections.abc import Iterable, Sequence
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
        waveforms: WaveformRecord | None,
        points_waveform_index: np.ndarray[Any, np.dtype[np.int64]] | None,
        *,
        waveform_reader: Optional["WaveReader"] = None,
        valid_descriptor_mask: np.ndarray[Any, np.dtype[np.bool_]] | None = None,
        allow_missing_descriptors: bool = True,
    ):
        super().__init__(array, point_format, scales, offsets)
        self._waveforms = waveforms
        self._points_waveform_index = (
            points_waveform_index  # maps each point to its waveform index in waveforms
        )
        self._waveform_reader = waveform_reader
        self._valid_descriptor_mask = valid_descriptor_mask
        self._allow_missing_descriptors = allow_missing_descriptors

    def __getitem__(self, item):
        if isinstance(item, (int, slice, np.ndarray, list, tuple)):
            if isinstance(item, (list, tuple)):
                item = [
                    item if item not in ("x", "y", "z") else item.upper()
                    for item in item
                ]
            elif isinstance(item, (int, slice, np.ndarray)):
                if self._points_waveform_index is None or self._waveforms is None:
                    waveforms_subset = None
                    points_waveform_index = None
                else:
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
                valid_descriptor_mask = (
                    self._valid_descriptor_mask[item]
                    if self._valid_descriptor_mask is not None
                    else None
                )
                return WaveformPointRecord(
                    self.array[item],
                    self.point_format,
                    self.scales,
                    self.offsets,
                    waveforms_subset,
                    points_waveform_index,
                    waveform_reader=self._waveform_reader,
                    valid_descriptor_mask=valid_descriptor_mask,
                    allow_missing_descriptors=self._allow_missing_descriptors,
                )
        if item == "wave":
            if self._waveforms is None or self._points_waveform_index is None:
                self._load_waveforms_from_source()
            return self._waveforms.samples["wave"][self._points_waveform_index]
        return super().__getitem__(item)

    def _load_waveforms_from_source(self) -> None:
        if self._waveforms is not None and self._points_waveform_index is not None:
            return
        if self._waveform_reader is None:
            raise ValueError("No waveform data available")

        self._waveforms, self._points_waveform_index = WaveformRecord.from_points(
            self.array,
            self._waveform_reader,
            self._valid_descriptor_mask,
            self._allow_missing_descriptors,
        )


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
            las = WaveformLasData(
                deepcopy(self.header),
                points=self.points[item],
                waveform_points=self.waveform_points[item],
            )
            las.update_header()
            return las

    def __repr__(self) -> str:
        return "<WaveformLasData({}.{}, point fmt: {}, {} points, {} vlrs, {} waveforms)>".format(
            self.header.version.major,
            self.header.version.minor,
            self.points.point_format,
            len(self.points),
            len(self.vlrs),
            len(self.waveform_points._waveforms)
            if self.waveform_points._waveforms is not None
            else 0,
        )

    def write(
        self,
        destination: Union[str, BinaryIO],
        do_compress: Optional[bool] = None,
        laz_backend: Optional[Union[LazBackend, Sequence[LazBackend]]] = None,
        *,
        waveform_chunksize: int = 64 * 1024 * 1024,
    ):
        if isinstance(destination, BinaryIO):
            raise NotImplementedError

        waveforms = self.waveform_points._waveforms
        points_waveform_index = self.waveform_points._points_waveform_index
        destination_path = Path(destination)
        if points_waveform_index is not None and waveforms is not None:
            wave_size_bytes = waveforms.wave_size
            offsets = (
                np.asarray(points_waveform_index, dtype=np.uint64) * wave_size_bytes
            )
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
            self._write_wdp(destination_path.with_suffix(".wdp"), waveforms)

        elif waveforms is None and self.waveform_points._waveform_reader is not None:
            self._write_wdp_lazy(
                destination=destination_path,
                waveform_size=self.waveform_points._waveform_reader.wave_size_bytes,
                chunksize=waveform_chunksize,
            )

        else:
            pass  # no waveform data to write

        # Now write the las/laz file
        do_compress = destination_path.suffix.lower() == ".laz"
        with destination_path.open(mode="wb+") as out_stream:
            self._write_to(out_stream, do_compress=do_compress, laz_backend=laz_backend)

    @staticmethod
    def _write_wdp(path: Path, waveforms: WaveformRecord | None) -> None:
        if waveforms is None:
            return
        samples = np.ascontiguousarray(waveforms.samples)
        with path.open("wb") as out_wdp:
            out_wdp.write(memoryview(samples))

    def _write_wdp_lazy(
        self,
        *,
        destination: Path | None,
        waveform_size: int,
        chunksize: int,
    ) -> None:
        if destination is None:
            raise NotImplementedError(
                "Writing to file-like objects is not supported for waveform LAS/LAZ files"
            )
        self._validate_waveform_sizes(
            waveform_size, self.waveform_points._valid_descriptor_mask
        )

        point_count = len(self.points)
        if point_count == 0:
            destination.with_suffix(".wdp").open("wb").close()
            return

        points_per_chunk = self._points_per_chunk(waveform_size, chunksize)

        wdp_path = destination.with_suffix(".wdp")
        self._write_wdp_lazy_dedup(
            wdp_path,
            waveform_size,
            points_per_chunk,
        )
        self._finalize_waveform_write(waveform_size)

    def _validate_waveform_sizes(
        self, waveform_size: int, valid_mask: np.ndarray[Any, np.dtype[np.bool_]] | None
    ) -> None:
        sizes = np.asarray(self.points.array["wavepacket_size"], dtype=np.uint64)
        if valid_mask is not None and self.waveform_points._allow_missing_descriptors:
            mask = np.asarray(valid_mask, dtype=bool)
            sizes_to_check = sizes[mask]
        else:
            sizes_to_check = sizes

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

    def _resolve_valid_mask(self, point_count: int) -> tuple[np.ndarray, bool]:
        valid_mask = self.waveform_points._valid_descriptor_mask
        if valid_mask is None:
            mask = np.ones(point_count, dtype=bool)
        else:
            mask = np.asarray(valid_mask, dtype=bool)
            if len(mask) != point_count:
                raise ValueError(
                    "Waveform descriptor mask size does not match number of points"
                )
            if not self.waveform_points._allow_missing_descriptors and not np.all(mask):
                raise ValueError("Missing waveform descriptors are not allowed")
        missing = self.waveform_points._allow_missing_descriptors and not np.all(mask)
        return mask, missing

    @staticmethod
    def _iter_runs(indices: np.ndarray) -> list[tuple[int, int]]:
        if indices.size == 0:
            return []
        runs: list[tuple[int, int]] = []
        start = int(indices[0])
        last = start
        for idx in indices[1:]:
            idx_int = int(idx)
            if idx_int == last + 1:
                last = idx_int
            else:
                runs.append((start, last))
                start = idx_int
                last = idx_int
        runs.append((start, last))
        return runs

    def _write_wdp_lazy_dedup(
        self,
        wdp_path: Path,
        waveform_size: int,
        points_per_chunk: int,
    ) -> None:
        waveform_reader = self.waveform_points._waveform_reader
        if waveform_reader is None:
            raise ValueError("No waveform reader available for deduplication")

        point_count = len(self.points)
        valid_mask, missing = self._resolve_valid_mask(point_count)
        offsets = np.asarray(self.points.array["wavepacket_offset"], dtype=np.uint64)
        if valid_mask.any():
            valid_indices = offsets[valid_mask] // waveform_size
            unique_indices, inverse_indices = np.unique(
                valid_indices, return_inverse=True
            )
        else:
            unique_indices = np.array([], dtype=np.uint64)
            inverse_indices = np.array([], dtype=np.int64)

        with wdp_path.open("wb") as dst:
            for run_start, run_end in self._iter_runs(unique_indices):
                count = int(run_end - run_start + 1)
                waveform_reader.seek(run_start)
                while count > 0:
                    chunk_count = min(points_per_chunk, count)
                    dst.write(waveform_reader.read_n_waveforms(int(chunk_count)))
                    count -= chunk_count
            if missing:
                dst.write(bytes(waveform_size))

        offset_dtype = self.points.array["wavepacket_offset"].dtype
        new_offsets = np.zeros(point_count, dtype=offset_dtype)
        if valid_mask.any():
            new_offsets[valid_mask] = (
                inverse_indices.astype(np.uint64) * waveform_size
            ).astype(offset_dtype, copy=False)
        if missing:
            new_offsets[~valid_mask] = np.array(
                len(unique_indices) * waveform_size, dtype=offset_dtype
            )
        self.points.array["wavepacket_offset"] = new_offsets

    def _finalize_waveform_write(self, waveform_size: int) -> None:
        size_dtype = self.points.array["wavepacket_size"].dtype
        self.points.array["wavepacket_size"] = np.full(
            len(self.points), waveform_size, dtype=size_dtype
        )

        self.header.global_encoding.waveform_data_packets_external = True
        if self.header.global_encoding.waveform_data_packets_internal:
            self.header.global_encoding.waveform_data_packets_internal = False
        if self.header.version.minor >= 3:
            self.header.start_of_waveform_data_packet_record = 0


class WaveReader:
    def __init__(
        self,
        source: BinaryIO,
        bits_per_sample: int,
        number_of_samples: int,
        temporal_sample_spacing: int,
        wave_dtype: np.dtype,
        closefd: bool = True,
    ):
        self._source = source
        self.bits_per_sample = bits_per_sample
        self.number_of_samples = number_of_samples
        self.temporal_sample_spacing = temporal_sample_spacing
        self.wave_dtype = wave_dtype
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
    _waveform_source: Optional[WaveReader]
    _waveform_descriptors_registry: WaveformPacketDescriptorRegistry
    waves_read: int

    def __init__(
        self,
        source: BinaryIO,
        closefd: bool = True,
        laz_backend: Optional[Union[LazBackend, Iterable[LazBackend]]] = None,
        read_evlrs: bool = True,
        decompression_selection: DecompressionSelection = DecompressionSelection.all(),
        read_waveforms: bool = True,
    ):
        super().__init__(
            source,
            closefd=closefd,
            laz_backend=laz_backend,
            read_evlrs=read_evlrs,
            decompression_selection=decompression_selection,
        )
        self._read_waveforms_default = read_waveforms
        if not self.header.point_format.has_waveform_packet:
            self._waveform_descriptors_registry = WaveformPacketDescriptorRegistry()
            self._waveform_source = None
            self.waves_read = 0
            return

        if not self.header.global_encoding.waveform_data_packets_external:
            raise ValueError(
                "This reader expects waveform data to live in an external .wdp file"
            )

        las_path = Path(source.name)
        waveform_file = las_path.with_suffix(".wdp").open("rb")
        self._waveform_descriptors_registry = (
            WaveformPacketDescriptorRegistry.from_vlrs(self.header.vlrs)
        )
        wave_dtype = self._waveform_descriptors_registry.dtype()
        if wave_dtype is None:
            raise ValueError("No waveform packet descriptors found in VLRs")
        self._waveform_source = WaveReader(
            waveform_file,
            bits_per_sample=self._waveform_descriptors_registry.bits_per_sample,
            number_of_samples=self._waveform_descriptors_registry.number_of_samples,
            temporal_sample_spacing=self._waveform_descriptors_registry.temporal_sample_spacing,
            wave_dtype=wave_dtype,
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

    def read_points_waveforms(
        self,
        n: int,
        allow_missing_descriptors: bool = True,
        *,
        read_waveforms: bool | None = None,
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
            empty_points = record.ScaleAwarePointRecord.empty(
                self.header.point_format,
                self.header.scales,
                self.header.offsets,
            )
            waveform_points = WaveformPointRecord(
                empty_points.array,
                empty_points.point_format,
                empty_points.scales,
                empty_points.offsets,
                None,
                None,
                waveform_reader=None,
                allow_missing_descriptors=allow_missing_descriptors,
            )
            return empty_points, waveform_points

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

        if read_waveforms is None:
            read_waveforms = self._read_waveforms_default

        if self._waveform_source is None:
            waveform_points = WaveformPointRecord(
                points.array,
                points.point_format,
                points.scales,
                points.offsets,
                None,
                None,
                waveform_reader=None,
                allow_missing_descriptors=allow_missing_descriptors,
            )
            return points, waveform_points

        valid_mask, _ = self._compute_valid_descriptor_mask(
            points, allow_missing_descriptors
        )

        if not read_waveforms:
            waveform_points = WaveformPointRecord(
                points.array,
                points.point_format,
                points.scales,
                points.offsets,
                None,
                None,
                waveform_reader=self._waveform_source,
                valid_descriptor_mask=np.asarray(valid_mask, dtype=bool),
                allow_missing_descriptors=allow_missing_descriptors,
            )
            return points, waveform_points

        waveforms, points_waveform_index = WaveformRecord.from_points(
            points.array,
            self._waveform_source,
            valid_mask,
            allow_missing_descriptors,
        )

        waveforms = WaveformPointRecord(
            points.array,
            points.point_format,
            points.scales,
            points.offsets,
            waveforms,
            np.asarray(points_waveform_index, dtype=np.int64),
            waveform_reader=self._waveform_source,
            valid_descriptor_mask=np.asarray(valid_mask, dtype=bool),
            allow_missing_descriptors=allow_missing_descriptors,
        )
        return points, waveforms

    def read(
        self,
        allow_missing_descriptors: bool = True,
        *,
        read_waveforms: bool | None = None,
    ) -> WaveformLasData:
        if self._waveform_source is not None:
            self._waveform_source.source.seek(0, os.SEEK_SET)
        self.waves_read = 0
        points, waveform_points = self.read_points_waveforms(
            -1,
            allow_missing_descriptors=allow_missing_descriptors,
            read_waveforms=read_waveforms,
        )

        return WaveformLasData(
            header=self.header,
            points=points,
            waveform_points=waveform_points,
        )
