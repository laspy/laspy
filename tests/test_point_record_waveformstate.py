import numpy as np
import pytest

from laspy import PointFormat
from laspy.point.record import EagerWaveformState, LazyWaveformState, PackedPointRecord
from laspy.waveform.record import WaveformRecord


class DummyWaveformReader:
    def __init__(self, wave_size_bytes: int = 2):
        self.wave_size_bytes = wave_size_bytes


def make_waveform_record(values: list[list[int]]) -> WaveformRecord:
    samples = np.zeros(
        len(values),
        dtype=np.dtype([("waveform", np.uint8, (len(values[0]),))]),
    )
    samples["waveform"] = values
    return WaveformRecord(samples, sample_spacing_ps=1)


def test_packed_point_record_waveform_state_accessors_and_mutators() -> None:
    pf = PointFormat(0)
    array = np.zeros(2, pf.dtype())
    reader = DummyWaveformReader()
    replacement_reader = DummyWaveformReader()
    waveforms = make_waveform_record([[1, 2], [3, 4]])
    replacement_waveforms = make_waveform_record([[5, 6], [7, 8]])
    points_waveform_index = np.array([0, 1], dtype=np.int64)
    replacement_index = np.array([1, 0], dtype=np.int64)

    record = PackedPointRecord(array, pf, waveform_state=LazyWaveformState(reader))
    assert isinstance(record._waveform_state, LazyWaveformState)

    record._set_waveform_state(EagerWaveformState(waveforms, points_waveform_index))
    assert isinstance(record._waveform_state, EagerWaveformState)
    eager_state = record._waveform_state
    assert np.array_equal(eager_state.points_waveform_index, points_waveform_index)

    record._set_waveform_state(
        EagerWaveformState(
            replacement_waveforms,
            replacement_index,
        )
    )
    eager_state = record._waveform_state
    assert isinstance(eager_state, EagerWaveformState)
    assert np.array_equal(eager_state.points_waveform_index, replacement_index)

    record._set_waveform_state(LazyWaveformState(replacement_reader))
    assert isinstance(record._waveform_state, LazyWaveformState)

    record._set_waveform_state(None)
    assert record._waveform_state is None


def test_packed_point_record_normalizes_eager_waveform_state_index() -> None:
    pf = PointFormat(0)
    array = np.zeros(2, pf.dtype())
    waveforms = make_waveform_record([[1, 2], [3, 4]])
    points_waveform_index = np.array([0, 1], dtype=np.int32)

    record = PackedPointRecord(
        array,
        pf,
        waveform_state=EagerWaveformState(waveforms, points_waveform_index),
    )

    eager_state = record._waveform_state
    assert isinstance(eager_state, EagerWaveformState)
    assert eager_state.points_waveform_index.dtype == np.int64


def test_packed_point_record_rejects_invalid_waveform_state_assignment() -> None:
    pf = PointFormat(0)
    array = np.zeros(2, pf.dtype())
    waveforms = make_waveform_record([[1, 2], [3, 4]])
    valid_state = EagerWaveformState(
        waveforms,
        np.array([0, 1], dtype=np.int64),
    )
    record = PackedPointRecord(array, pf, waveform_state=valid_state)

    with pytest.raises(TypeError, match="waveform_state must be"):
        record._set_waveform_state("lazy")  # type: ignore[arg-type]

    eager_state = record._waveform_state
    assert isinstance(eager_state, EagerWaveformState)
    assert np.array_equal(
        eager_state.points_waveform_index,
        valid_state.points_waveform_index,
    )

    with pytest.raises(TypeError, match="waveform_state must be"):
        PackedPointRecord(array, pf, waveform_state="lazy")  # type: ignore[arg-type]
