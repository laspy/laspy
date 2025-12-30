from __future__ import annotations

import numpy as np
import pytest

from laspy.waveform.record import WaveformRecord


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


def make_points(
    waveform_size: int, offsets: np.ndarray, wavepacket_index: np.ndarray | None = None
) -> np.ndarray:
    points_dtype = np.dtype(
        [
            ("wavepacket_size", np.uint32),
            ("wavepacket_offset", np.uint64),
            ("wavepacket_index", np.uint8),
        ]
    )
    points = np.zeros((len(offsets),), dtype=points_dtype)
    points["wavepacket_size"] = waveform_size
    points["wavepacket_offset"] = offsets
    if wavepacket_index is None:
        points["wavepacket_index"] = 1
    else:
        points["wavepacket_index"] = wavepacket_index
    return points


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

    offsets = np.array([0, waveform_size * 2, waveform_size * 3, 0], dtype=np.uint64)
    points = make_points(waveform_size, offsets)

    wave_record, index = WaveformRecord.from_points(points, reader)
    assert len(wave_record) == 3
    assert wave_record.sample_spacing_ps == 10
    assert np.array_equal(
        wave_record.samples["waveform"], waveforms["waveform"][[0, 2, 3]]
    )
    assert np.array_equal(index, np.array([0, 1, 2, 0], dtype=np.int64))


def test_waveform_record_from_points_without_wavepacket_index_dimension() -> None:
    waveforms = make_waveforms(np.uint8, 2, 3)
    wave_dtype = waveforms.dtype
    reader = DummyWaveformReader(waveforms, wave_dtype, spacing=7)
    waveform_size = wave_dtype.itemsize

    points_dtype = np.dtype(
        [("wavepacket_size", np.uint32), ("wavepacket_offset", np.uint64)]
    )
    points = np.zeros((3,), dtype=points_dtype)
    points["wavepacket_size"] = waveform_size
    points["wavepacket_offset"] = np.array(
        [0, waveform_size, waveform_size * 2], dtype=np.uint64
    )

    wave_record, index = WaveformRecord.from_points(points, reader)
    assert len(wave_record) == 3
    assert np.array_equal(index, np.array([0, 1, 2], dtype=np.int64))


def test_waveform_record_from_points_size_mismatch_raises() -> None:
    waveforms = make_waveforms(np.uint8, 2, 2)
    wave_dtype = waveforms.dtype
    reader = DummyWaveformReader(waveforms, wave_dtype, spacing=1)
    waveform_size = wave_dtype.itemsize

    offsets = np.array([0, waveform_size], dtype=np.uint64)
    points = make_points(waveform_size, offsets)
    points["wavepacket_size"][1] = waveform_size + 1

    with np.testing.assert_raises_regex(ValueError, "Inconsistent waveform sizes"):
        WaveformRecord.from_points(points, reader)


def test_waveform_record_from_points_rejects_unaligned_offsets() -> None:
    waveforms = make_waveforms(np.uint8, 2, 2)
    wave_dtype = waveforms.dtype
    reader = DummyWaveformReader(waveforms, wave_dtype, spacing=1)
    waveform_size = wave_dtype.itemsize

    points = make_points(
        waveform_size,
        np.array([0, waveform_size + 1], dtype=np.uint64),
    )

    with pytest.raises(NotImplementedError, match="byte offset"):
        WaveformRecord.from_points(points, reader)


def test_waveform_record_from_points_no_waveform_points_appends_zero() -> None:
    waveforms = make_waveforms(np.uint8, 2, 2)
    wave_dtype = waveforms.dtype
    reader = DummyWaveformReader(waveforms, wave_dtype, spacing=1)
    waveform_size = wave_dtype.itemsize

    offsets = np.array([0, waveform_size, 0], dtype=np.uint64)
    wavepacket_index = np.array([1, 0, 1], dtype=np.uint8)
    points = make_points(waveform_size, offsets, wavepacket_index=wavepacket_index)

    wave_record, index = WaveformRecord.from_points(points, reader)
    assert len(wave_record) == 2
    assert np.array_equal(
        wave_record.samples["waveform"][-1], np.zeros(2, dtype=np.uint8)
    )
    assert np.array_equal(index, np.array([0, 1, 0], dtype=np.int64))


def test_waveform_record_from_points_all_no_waveform_points() -> None:
    waveforms = make_waveforms(np.uint8, 2, 1)
    wave_dtype = waveforms.dtype
    reader = DummyWaveformReader(waveforms, wave_dtype, spacing=1)
    waveform_size = wave_dtype.itemsize

    offsets = np.array([0, waveform_size], dtype=np.uint64)
    wavepacket_index = np.array([0, 0], dtype=np.uint8)
    points = make_points(waveform_size, offsets, wavepacket_index=wavepacket_index)

    wave_record, index = WaveformRecord.from_points(points, reader)
    assert len(wave_record) == 1
    assert np.array_equal(
        wave_record.samples["waveform"][0], np.zeros(2, dtype=np.uint8)
    )
    assert np.array_equal(index, np.array([0, 0], dtype=np.int64))


def test_waveform_record_from_points_empty_points() -> None:
    waveforms = make_waveforms(np.uint8, 2, 1)
    wave_dtype = waveforms.dtype
    reader = DummyWaveformReader(waveforms, wave_dtype, spacing=1)
    waveform_size = wave_dtype.itemsize

    points = make_points(waveform_size, np.array([], dtype=np.uint64))

    wave_record, index = WaveformRecord.from_points(points, reader)
    assert len(wave_record) == 0
    assert wave_record.samples.shape == (0,)
    assert index.shape == (0,)
