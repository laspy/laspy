from collections import UserDict
from dataclasses import dataclass
from typing import Iterable, NewType, cast

import numpy as np

from ..vlrs import VLR
from ..vlrs.known import WaveformPacketVlr

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
