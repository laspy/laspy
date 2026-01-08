from collections import UserDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterable, NewType, Protocol, cast

if TYPE_CHECKING:
    from collections.abc import Buffer
else:
    try:
        from collections.abc import Buffer
    except ImportError:  # Python < 3.12

        class Buffer(Protocol):
            """Fallback typing stub for Python < 3.12."""

            ...


import numpy as np

from .vlrs import VLR
from .vlrs.known import WaveformPacketVlr

WavePacketDescriptorIndex = NewType("WavePacketDescriptorIndex", int)


class WavePacketDescriptorRecordId(int):
    RECORD_ID_OFFSET = 99

    @staticmethod
    def from_index(index: WavePacketDescriptorIndex) -> "WavePacketDescriptorRecordId":
        return WavePacketDescriptorRecordId(
            index + WavePacketDescriptorRecordId.RECORD_ID_OFFSET
        )


@dataclass(frozen=True)
class WaveformPacketDescriptor:
    bits_per_sample: int
    waveform_compression_type: int
    number_of_samples: int
    temporal_sample_spacing: int
    digitizer_gain: float
    digitizer_offset: float

    def ensure_supported(self) -> None:
        if self.waveform_compression_type != 0:
            raise NotImplementedError(
                "Only uncompressed waveform packets (compression_type=0) are supported"
            )
        if self.bits_per_sample % 8 != 0:
            raise NotImplementedError(
                "Waveform sample size must be a multiple of 8 bits"
            )

    def dtype(self) -> np.dtype:
        if self.bits_per_sample % 8 != 0:
            raise NotImplementedError(
                "Waveform sample size must be a multiple of 8 bits"
            )
        match self.bits_per_sample:
            case 8:
                base_dtype = np.dtype(np.uint8)
            case 16:
                base_dtype = np.dtype(np.uint16)
            case 32:
                base_dtype = np.dtype(np.uint32)
            case 64:
                base_dtype = np.dtype(np.uint64)
            case _:
                raise NotImplementedError(
                    f"Unsupported waveform sample width: {self.bits_per_sample} bits"
                )
        return np.dtype([("waveform", (base_dtype, (self.number_of_samples,)))])


class WaveformPacketDescriptorRegistry(
    UserDict[WavePacketDescriptorRecordId, WaveformPacketDescriptor]
):
    """Registry of waveform packet descriptors by index."""

    bits_per_sample: int
    number_of_samples: int
    temporal_sample_spacing: int

    @classmethod
    def from_vlrs(cls, vlrs: Iterable[VLR]) -> "WaveformPacketDescriptorRegistry":
        registry = cls()
        waveform_vlrs: list[WaveformPacketVlr] = [
            cast(WaveformPacketVlr, vlr)
            for vlr in vlrs
            if vlr.record_id in WaveformPacketVlr.official_record_ids()
        ]
        if not waveform_vlrs:
            return registry

        waveform_vlrs.sort(key=lambda vlr: vlr.record_id)

        for vlr in waveform_vlrs:
            raw = vlr.parsed_record
            if raw is None:
                raise ValueError(
                    f"Waveform packet VLR with record ID {vlr.record_id} is not parsed"
                )
            descriptor = WaveformPacketDescriptor(
                bits_per_sample=raw.bits_per_sample,
                waveform_compression_type=raw.waveform_compression_type,
                number_of_samples=raw.number_of_samples,
                temporal_sample_spacing=raw.temporal_sample_spacing,
                digitizer_gain=raw.digitizer_gain,
                digitizer_offset=raw.digitizer_offset,
            )
            descriptor.ensure_supported()
            record_id = WavePacketDescriptorRecordId(vlr.record_id)
            registry.data[record_id] = descriptor
        bits_per_sample, number_of_samples, temporal_sample_spacing = (
            registry.ensure_supported()
        )
        registry.bits_per_sample = bits_per_sample
        registry.number_of_samples = number_of_samples
        registry.temporal_sample_spacing = temporal_sample_spacing
        return registry

    def ensure_supported(self) -> tuple[int, int, int]:
        """Ensure that all descriptors in the registry are compatible.

        Currently, this means:
        - same bits_per_sample
        - same number_of_samples
        - same temporal_sample_spacing
        """
        bits_per_sample_set = {desc.bits_per_sample for desc in self.data.values()}
        if len(bits_per_sample_set) != 1:
            raise NotImplementedError(
                "All waveform packet descriptors must have the same bits_per_sample"
            )
        number_of_samples_set = {desc.number_of_samples for desc in self.data.values()}
        if len(number_of_samples_set) != 1:
            raise NotImplementedError(
                "All waveform packet descriptors must have the same number_of_samples"
            )
        temporal_sample_spacing_set = {
            desc.temporal_sample_spacing for desc in self.data.values()
        }
        if len(temporal_sample_spacing_set) != 1:
            raise NotImplementedError(
                "All waveform packet descriptors must have the same temporal_sample_spacing"
            )
        return (
            bits_per_sample_set.pop(),
            number_of_samples_set.pop(),
            temporal_sample_spacing_set.pop(),
        )

    def dtype(self) -> np.dtype | None:
        try:
            descriptor: WaveformPacketDescriptor = next(iter(self.data.values()))
        except StopIteration:
            return None
        return descriptor.dtype()


class WaveformRecord:
    samples: np.ndarray
    sample_spacing_ps: int

    @property
    def wave_size(self) -> int:
        return self.samples.dtype.itemsize

    def __init__(self, data: np.ndarray, sample_spacing_ps: int):
        self.samples = data
        self.sample_spacing_ps = sample_spacing_ps

    @classmethod
    def from_buffer(
        cls,
        buffer: Buffer,
        wave_dtype: np.dtype,
        temporal_sample_spacing: int,
        count=-1,
        offset=0,
    ) -> "WaveformRecord":
        data = np.frombuffer(buffer, dtype=wave_dtype, offset=offset, count=count)
        return cls(data, temporal_sample_spacing)

    @classmethod
    def from_points(
        cls,
        points_array: np.ndarray,
        waveform_reader: Any,
        valid_descriptor_mask: np.ndarray | None = None,
    ) -> tuple["WaveformRecord", np.ndarray[Any, np.dtype[np.int64]]]:
        wave_dtype = waveform_reader.wave_dtype
        temporal_sample_spacing = waveform_reader.temporal_sample_spacing
        waveform_size = waveform_reader.wave_size_bytes

        sizes = np.asarray(points_array["wavepacket_size"], dtype=np.uint64)
        if valid_descriptor_mask is None:
            valid_descriptor_mask = np.ones(len(points_array), dtype=bool)
        else:
            valid_descriptor_mask = np.asarray(valid_descriptor_mask, dtype=bool)
            if len(valid_descriptor_mask) != len(points_array):
                raise ValueError(
                    "Waveform descriptor mask size does not match number of points"
                )

        if valid_descriptor_mask.any():
            actual = set(sizes[valid_descriptor_mask])
            if actual - {waveform_size}:
                raise ValueError(
                    f"Inconsistent waveform sizes in point data: {actual} but descriptor size is {waveform_size}"
                )

        offsets = np.asarray(points_array["wavepacket_offset"], dtype=np.uint64)
        valid_offsets = offsets[valid_descriptor_mask]
        valid_indices = valid_offsets // waveform_size
        unique_indices, inverse_indices = np.unique(valid_indices, return_inverse=True)
        sorted_indices = np.argsort(unique_indices)
        sorted_unique_indices = unique_indices[sorted_indices]

        runs: list[tuple[int, int]] = []
        if sorted_unique_indices.size:
            start = int(sorted_unique_indices[0])
            last = start
            for idx in sorted_unique_indices[1:]:
                idx_int = int(idx)
                if idx_int == last + 1:
                    last = idx_int
                else:
                    runs.append((start, last))
                    start = idx_int
                    last = idx_int
            runs.append((start, last))

        waveform_data = bytearray()
        for start, end in runs:
            count = int(end - start + 1)
            waveform_reader.seek(int(start))
            waveform_data.extend(waveform_reader.read_n_waveforms(count))

        waveforms = cls.from_buffer(
            waveform_data,
            wave_dtype,
            temporal_sample_spacing,
            count=len(unique_indices),
        )

        unique_to_sorted = np.empty_like(sorted_indices)
        unique_to_sorted[sorted_indices] = np.arange(len(sorted_indices))
        points_waveform_index = np.full(len(points_array), -1, dtype=np.int64)
        points_waveform_index[valid_descriptor_mask] = unique_to_sorted[inverse_indices]

        if not np.all(valid_descriptor_mask):
            missing_wave_index = len(waveforms)
            new_samples = np.empty((missing_wave_index + 1,), dtype=wave_dtype)
            if len(waveforms):
                new_samples[:-1] = waveforms.samples
            new_samples["waveform"][-1] = 0
            waveforms = cls(new_samples, temporal_sample_spacing)
            points_waveform_index[~valid_descriptor_mask] = missing_wave_index

        return waveforms, np.asarray(points_waveform_index, dtype=np.int64)

    def __len__(self):
        if self.samples.ndim == 0:
            return 1
        return self.samples.shape[0]

    def __repr__(self):
        return f"<{self.__class__.__name__}(len: {len(self)}, num samples: {self.samples.dtype['waveform'].shape[0]}, type: {self.samples.dtype['waveform'].base}, size: {self.wave_size} bytes)>"

    def __getitem__(self, item):
        """Gives access to the underlying numpy array
        Unpack the dimension if item is the name a sub-field
        """
        if isinstance(item, (int, slice, np.ndarray, list, tuple)):
            return WaveformRecord(self.samples[item], self.sample_spacing_ps)

        return self.samples[item]
