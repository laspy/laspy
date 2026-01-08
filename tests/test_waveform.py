from __future__ import annotations

import numpy as np
import pytest

from laspy.vlrs.known import WaveformPacketStruct, WaveformPacketVlr
from laspy.waveform import (
    WavePacketDescriptorIndex,
    WavePacketDescriptorRecordId,
    WaveformPacketDescriptor,
    WaveformPacketDescriptorRegistry,
    WaveformRecord,
)


class DummyWaveformReader:
    def __init__(self, waveforms: np.ndarray, wave_dtype: np.dtype, spacing: int):
        self._waveforms = waveforms
        self.wave_dtype = wave_dtype
        self.number_of_samples = wave_dtype["waveform"].shape[0]
        self.temporal_sample_spacing = spacing
        self.wave_size_bytes = wave_dtype.itemsize
        self._pos = 0

    def seek(self, waveform_index: int) -> None:
        self._pos = waveform_index

    def read_n_waveforms(self, n: int) -> bytearray:
        return bytearray(self._waveforms[self._pos : self._pos + n].tobytes())


def make_wave_dtype(base: np.dtype, samples: int) -> np.dtype:
    return np.dtype([("waveform", base, (samples,))])


def make_waveforms(base: np.dtype, samples: int, count: int) -> np.ndarray:
    wave_dtype = make_wave_dtype(base, samples)
    waveforms = np.zeros((count,), dtype=wave_dtype)
    values = np.arange(count * samples, dtype=base).reshape(count, samples)
    waveforms["waveform"] = values
    return waveforms


def make_points(waveform_size: int, offsets: np.ndarray) -> np.ndarray:
    points_dtype = np.dtype([("wavepacket_size", np.uint32), ("wavepacket_offset", np.uint64)])
    points = np.zeros((len(offsets),), dtype=points_dtype)
    points["wavepacket_size"] = waveform_size
    points["wavepacket_offset"] = offsets
    return points


def test_wave_packet_descriptor_record_id_from_index() -> None:
    record_id = WavePacketDescriptorRecordId.from_index(WavePacketDescriptorIndex(1))
    assert isinstance(record_id, WavePacketDescriptorRecordId)
    assert int(record_id) == 100


def test_waveform_packet_descriptor_ensure_supported_checks_compression_and_bits() -> None:
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
def test_waveform_packet_descriptor_dtype_supported(bits_per_sample: int, expected_base: np.dtype) -> None:
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


def test_waveform_record_from_buffer_and_getitem() -> None:
    wave_dtype = make_wave_dtype(np.uint8, 2)
    raw = make_waveforms(np.uint8, 2, 3)
    buffer = raw.tobytes()
    record = WaveformRecord.from_buffer(
        buffer,
        wave_dtype,
        temporal_sample_spacing=7,
        count=1,
        offset=wave_dtype.itemsize,
    )
    assert len(record) == 1
    assert record.sample_spacing_ps == 7
    assert record.samples["waveform"][0].tolist() == [2, 3]
    assert record.wave_size == wave_dtype.itemsize

    parent = WaveformRecord(raw, 7)
    first = parent[0]
    assert isinstance(first, WaveformRecord)
    assert first.sample_spacing_ps == 7
    assert np.array_equal(first.samples["waveform"], raw["waveform"][0])
    assert np.array_equal(parent["waveform"], raw["waveform"])


def test_waveform_record_len_and_repr_scalar() -> None:
    wave_dtype = make_wave_dtype(np.uint16, 1)
    scalar = np.zeros((), dtype=wave_dtype)
    record = WaveformRecord(scalar, 3)
    assert len(record) == 1
    assert "len: 1" in repr(record)


def test_waveform_record_from_points_reads_runs_and_indexes() -> None:
    waveforms = make_waveforms(np.uint8, 2, 4)
    wave_dtype = waveforms.dtype
    reader = DummyWaveformReader(waveforms, wave_dtype, spacing=10)
    waveform_size = wave_dtype.itemsize

    offsets = np.array(
        [0, waveform_size * 2, waveform_size * 3, 0], dtype=np.uint64
    )
    points = make_points(waveform_size, offsets)

    wave_record, index = WaveformRecord.from_points(points, reader)
    assert len(wave_record) == 3
    assert wave_record.sample_spacing_ps == 10
    assert np.array_equal(
        wave_record.samples["waveform"], waveforms["waveform"][[0, 2, 3]]
    )
    assert np.array_equal(index, np.array([0, 1, 2, 0], dtype=np.int64))


def test_waveform_record_from_points_size_mismatch_raises() -> None:
    waveforms = make_waveforms(np.uint8, 2, 2)
    wave_dtype = waveforms.dtype
    reader = DummyWaveformReader(waveforms, wave_dtype, spacing=1)
    waveform_size = wave_dtype.itemsize

    offsets = np.array([0, waveform_size], dtype=np.uint64)
    points = make_points(waveform_size, offsets)
    points["wavepacket_size"][1] = waveform_size + 1

    with pytest.raises(ValueError, match="Inconsistent waveform sizes"):
        WaveformRecord.from_points(points, reader)


def test_waveform_record_from_points_valid_descriptor_mask_mismatch_raises() -> None:
    waveforms = make_waveforms(np.uint8, 1, 1)
    wave_dtype = waveforms.dtype
    reader = DummyWaveformReader(waveforms, wave_dtype, spacing=1)
    waveform_size = wave_dtype.itemsize

    points = make_points(waveform_size, np.array([0], dtype=np.uint64))
    with pytest.raises(ValueError, match="mask size"):
        WaveformRecord.from_points(
            points, reader, valid_descriptor_mask=np.array([True, False])
        )


def test_waveform_record_from_points_missing_descriptors_appends_zero() -> None:
    waveforms = make_waveforms(np.uint8, 2, 2)
    wave_dtype = waveforms.dtype
    reader = DummyWaveformReader(waveforms, wave_dtype, spacing=1)
    waveform_size = wave_dtype.itemsize

    offsets = np.array([0, waveform_size, 0], dtype=np.uint64)
    points = make_points(waveform_size, offsets)
    valid_descriptor_mask = np.array([True, False, True])

    wave_record, index = WaveformRecord.from_points(
        points,
        reader,
        valid_descriptor_mask=valid_descriptor_mask,
    )
    assert len(wave_record) == 2
    assert np.array_equal(wave_record.samples["waveform"][-1], np.zeros(2, dtype=np.uint8))
    assert np.array_equal(index, np.array([0, 1, 0], dtype=np.int64))


def test_waveform_record_from_points_all_missing_descriptors() -> None:
    waveforms = make_waveforms(np.uint8, 2, 1)
    wave_dtype = waveforms.dtype
    reader = DummyWaveformReader(waveforms, wave_dtype, spacing=1)
    waveform_size = wave_dtype.itemsize

    points = make_points(waveform_size, np.array([0, waveform_size], dtype=np.uint64))
    valid_descriptor_mask = np.array([False, False])

    wave_record, index = WaveformRecord.from_points(
        points,
        reader,
        valid_descriptor_mask=valid_descriptor_mask,
    )
    assert len(wave_record) == 1
    assert np.array_equal(wave_record.samples["waveform"][0], np.zeros(2, dtype=np.uint8))
    assert np.array_equal(index, np.array([0, 0], dtype=np.int64))
