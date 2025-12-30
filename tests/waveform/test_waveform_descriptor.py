from __future__ import annotations

import numpy as np
import pytest

from laspy.vlrs.known import WaveformPacketStruct, WaveformPacketVlr
from laspy.waveform.descriptor import (
    WaveformPacketDescriptor,
    WaveformPacketDescriptorRegistry,
    WavePacketDescriptorIndex,
    WavePacketDescriptorRecordId,
)


def test_wave_packet_descriptor_record_id_from_index() -> None:
    record_id = WavePacketDescriptorRecordId.from_index(WavePacketDescriptorIndex(1))
    assert isinstance(record_id, WavePacketDescriptorRecordId)
    assert int(record_id) == 100


def test_waveform_packet_descriptor_ensure_supported_checks_compression_and_bits() -> (
    None
):
    descriptor = WaveformPacketDescriptor(
        bits_per_sample=8,
        waveform_compression_type=1,
        number_of_samples=1,
        temporal_sample_spacing=1,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    with pytest.raises(NotImplementedError, match="compression_type=0"):
        descriptor.ensure_supported()

    descriptor = WaveformPacketDescriptor(
        bits_per_sample=12,
        waveform_compression_type=0,
        number_of_samples=1,
        temporal_sample_spacing=1,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    with pytest.raises(NotImplementedError, match="multiple of 8"):
        descriptor.ensure_supported()


@pytest.mark.parametrize(
    ("bits_per_sample", "expected_base"),
    [
        (8, np.uint8),
        (16, np.uint16),
        (32, np.uint32),
        (64, np.uint64),
    ],
)
def test_waveform_packet_descriptor_dtype_supported(
    bits_per_sample: int, expected_base: np.dtype
) -> None:
    descriptor = WaveformPacketDescriptor(
        bits_per_sample=bits_per_sample,
        waveform_compression_type=0,
        number_of_samples=3,
        temporal_sample_spacing=1,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    dtype = descriptor.dtype()
    assert dtype["waveform"].base == np.dtype(expected_base)
    assert dtype["waveform"].shape == (3,)


def test_waveform_packet_descriptor_dtype_rejects_invalid_sizes() -> None:
    descriptor = WaveformPacketDescriptor(
        bits_per_sample=12,
        waveform_compression_type=0,
        number_of_samples=1,
        temporal_sample_spacing=1,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    with pytest.raises(NotImplementedError, match="multiple of 8"):
        descriptor.dtype()

    descriptor = WaveformPacketDescriptor(
        bits_per_sample=24,
        waveform_compression_type=0,
        number_of_samples=1,
        temporal_sample_spacing=1,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    with pytest.raises(NotImplementedError, match="Unsupported waveform sample width"):
        descriptor.dtype()


def test_waveform_packet_descriptor_registry_from_vlrs_empty() -> None:
    registry = WaveformPacketDescriptorRegistry.from_vlrs([])
    assert registry.data == {}
    assert registry.dtype() is None


def test_waveform_packet_descriptor_registry_from_vlrs_requires_parsed() -> None:
    vlr = WaveformPacketVlr(100)
    with pytest.raises(ValueError, match="not parsed"):
        WaveformPacketDescriptorRegistry.from_vlrs([vlr])


def test_waveform_packet_descriptor_registry_from_vlrs_populates() -> None:
    record = WaveformPacketStruct(
        bits_per_sample=16,
        waveform_compression_type=0,
        number_of_samples=2,
        temporal_sample_spacing=5,
        digitizer_gain=1.5,
        digitizer_offset=0.25,
    )
    vlr_a = WaveformPacketVlr(100)
    vlr_a.parsed_record = record
    vlr_b = WaveformPacketVlr(101)
    vlr_b.parsed_record = record

    registry = WaveformPacketDescriptorRegistry.from_vlrs([vlr_b, vlr_a])

    assert registry.bits_per_sample == 16
    assert registry.number_of_samples == 2
    assert registry.temporal_sample_spacing == 5
    assert WavePacketDescriptorRecordId(100) in registry
    assert WavePacketDescriptorRecordId(101) in registry
    dtype = registry.dtype()
    assert dtype is not None
    assert dtype["waveform"].base == np.dtype(np.uint16)
    assert dtype["waveform"].shape == (2,)


def test_waveform_packet_descriptor_registry_ensure_supported_mismatches() -> None:
    registry = WaveformPacketDescriptorRegistry()
    registry.data[WavePacketDescriptorRecordId(100)] = WaveformPacketDescriptor(
        bits_per_sample=8,
        waveform_compression_type=0,
        number_of_samples=2,
        temporal_sample_spacing=1,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    registry.data[WavePacketDescriptorRecordId(101)] = WaveformPacketDescriptor(
        bits_per_sample=16,
        waveform_compression_type=0,
        number_of_samples=2,
        temporal_sample_spacing=1,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    with pytest.raises(NotImplementedError, match="bits_per_sample"):
        registry.ensure_supported()

    registry = WaveformPacketDescriptorRegistry()
    registry.data[WavePacketDescriptorRecordId(100)] = WaveformPacketDescriptor(
        bits_per_sample=8,
        waveform_compression_type=0,
        number_of_samples=2,
        temporal_sample_spacing=1,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    registry.data[WavePacketDescriptorRecordId(101)] = WaveformPacketDescriptor(
        bits_per_sample=8,
        waveform_compression_type=0,
        number_of_samples=3,
        temporal_sample_spacing=1,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    with pytest.raises(NotImplementedError, match="number_of_samples"):
        registry.ensure_supported()

    registry = WaveformPacketDescriptorRegistry()
    registry.data[WavePacketDescriptorRecordId(100)] = WaveformPacketDescriptor(
        bits_per_sample=8,
        waveform_compression_type=0,
        number_of_samples=2,
        temporal_sample_spacing=1,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    registry.data[WavePacketDescriptorRecordId(101)] = WaveformPacketDescriptor(
        bits_per_sample=8,
        waveform_compression_type=0,
        number_of_samples=2,
        temporal_sample_spacing=2,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    with pytest.raises(NotImplementedError, match="temporal_sample_spacing"):
        registry.ensure_supported()


def test_waveform_packet_descriptor_registry_ensure_supported_success() -> None:
    registry = WaveformPacketDescriptorRegistry()
    registry.data[WavePacketDescriptorRecordId(100)] = WaveformPacketDescriptor(
        bits_per_sample=8,
        waveform_compression_type=0,
        number_of_samples=4,
        temporal_sample_spacing=12,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    bits, samples, spacing = registry.ensure_supported()
    assert bits == 8
    assert samples == 4
    assert spacing == 12
    assert registry.dtype() is not None
