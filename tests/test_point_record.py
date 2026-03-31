import numpy as np
import pytest

from laspy import PointFormat
from laspy.point.record import (
    EagerWaveformState,
    LazyWaveformState,
    PackedPointRecord,
    ScaleAwarePointRecord,
    scale_dimension,
)
from laspy.waveform.record import WaveformRecord


class DummyWaveformReader:
    def __init__(self, waveforms: np.ndarray | None = None, wave_size_bytes: int = 2):
        if waveforms is None:
            waveforms = np.zeros(
                0,
                dtype=np.dtype([("waveform", np.uint8, (wave_size_bytes,))]),
            )
        self._waveforms = waveforms
        self.wave_dtype = waveforms.dtype
        self.number_of_samples = waveforms.dtype["waveform"].shape[0]
        self.temporal_sample_spacing = 1
        self.wave_size_bytes = waveforms.dtype.itemsize
        self._pos = 0

    def seek(self, waveform_index: int) -> None:
        self._pos = waveform_index

    def read_n_waveforms(self, n: int) -> bytearray:
        return bytearray(self._waveforms[self._pos : self._pos + n].tobytes())


def make_waveform_record(values: list[list[int]]) -> WaveformRecord:
    samples = np.zeros(
        len(values),
        dtype=np.dtype([("waveform", np.uint8, (len(values[0]),))]),
    )
    samples["waveform"] = values
    return WaveformRecord(samples, sample_spacing_ps=1)


def make_record_with_eager_waveforms() -> PackedPointRecord:
    point_format = PointFormat(0)
    array = np.zeros(4, point_format.dtype())
    waveforms = make_waveform_record([[10, 11], [20, 21], [30, 31]])
    points_waveform_index = np.array([0, 1, 1, 2], dtype=np.int64)
    return PackedPointRecord(
        array,
        point_format,
        waveform_state=EagerWaveformState(waveforms, points_waveform_index),
    )


def make_waveform_capable_record_with_eager_waveforms() -> (
    tuple[PackedPointRecord, np.ndarray, np.ndarray]
):
    point_format = PointFormat(4)
    expected_waveforms = np.array([[10, 11], [20, 21], [30, 31]], dtype=np.uint8)
    expected_points_waveform_index = np.array([0, 1, 1, 2], dtype=np.int64)
    waveforms = make_waveform_record(expected_waveforms.tolist())
    array = np.zeros(4, point_format.dtype())
    array["wavepacket_index"] = 1
    array["wavepacket_size"] = waveforms.wave_size
    array["wavepacket_offset"] = np.array([0, 2, 2, 4], dtype=np.uint64)
    return (
        PackedPointRecord(
            array,
            point_format,
            waveform_state=EagerWaveformState(
                waveforms, expected_points_waveform_index
            ),
        ),
        expected_waveforms,
        expected_points_waveform_index,
    )


def make_record_with_lazy_waveforms() -> (
    tuple[PackedPointRecord, np.ndarray, np.ndarray]
):
    point_format = PointFormat(4)
    array = np.zeros(3, point_format.dtype())
    expected_waveforms = np.array([[10, 11], [20, 21], [30, 31]], dtype=np.uint8)
    expected_points_waveform_index = np.array([0, 1, 2], dtype=np.int64)
    waveforms = make_waveform_record(expected_waveforms.tolist())
    array["wavepacket_index"] = 1
    array["wavepacket_size"] = waveforms.wave_size
    array["wavepacket_offset"] = np.array([0, 2, 4], dtype=np.uint64)
    reader = DummyWaveformReader(waveforms.samples)
    record = PackedPointRecord(
        array,
        point_format,
        waveform_state=LazyWaveformState(reader),
    )
    return record, expected_waveforms, expected_points_waveform_index


def test_scale_dimension_used() -> None:
    assert scale_dimension(4, 2, 1) == 9


def test_resize_and_getitem_list_hits_subset_path() -> None:
    pf = PointFormat(0)
    record = PackedPointRecord.zeros(3, pf)
    record.resize(1)
    assert len(record) == 1

    subset = record[0]
    assert isinstance(subset, PackedPointRecord)


def test_len_scalar_record_is_one() -> None:
    pf = PointFormat(0)
    record = PackedPointRecord.zeros(1, pf)

    scalar = record[0]

    assert len(scalar) == 1


def test_setitem_tuple_value_as_list_and_index_set() -> None:
    pf = PointFormat(0)
    record = PackedPointRecord.zeros(2, pf)

    record[("X", "Y")] = [[1, 2], [3, 4]]
    assert np.array_equal(record["X"], [1, 3])

    record[0] = record.array[0]


def test_getitem_tuple_of_indices_matches_list_subset() -> None:
    pf = PointFormat(0)
    record = PackedPointRecord.zeros(5, pf)
    record["X"] = np.arange(5)

    subset_from_tuple = record[(0, 2, 4)]
    subset_from_list = record[[0, 2, 4]]

    assert isinstance(subset_from_tuple, PackedPointRecord)
    assert np.array_equal(subset_from_tuple.array, subset_from_list.array)


def test_getitem_tuple_and_list_of_field_names() -> None:
    pf = PointFormat(0)
    record = PackedPointRecord.zeros(2, pf)
    record["X"] = [10, 20]
    record["Y"] = [11, 21]

    tuple_subset = record[("X", "Y")]
    list_subset = record[["X", "Y"]]

    assert tuple_subset.array.dtype.names == ("X", "Y")
    assert list_subset.array.dtype.names == ("X", "Y")
    assert np.array_equal(tuple_subset.array["X"], [10, 20])
    assert np.array_equal(list_subset.array["Y"], [11, 21])


def test_scaleaware_getitem_normalizes_xyz_field_names() -> None:
    pf = PointFormat(0)
    record = ScaleAwarePointRecord.zeros(
        point_count=2,
        point_format=pf,
        scales=[1.0, 1.0, 1.0],
        offsets=[0.0, 0.0, 0.0],
    )
    record["X"] = [10, 20]
    record["Y"] = [11, 21]

    subset = record[("x", "y")]

    assert isinstance(subset, ScaleAwarePointRecord)
    assert subset.array.dtype.names == ("X", "Y")
    assert np.array_equal(subset.array["X"], [10, 20])


def test_scaleaware_getitem_non_field_list_uses_normalized_values() -> None:
    pf = PointFormat(0)
    record = ScaleAwarePointRecord.zeros(
        point_count=3,
        point_format=pf,
        scales=[1.0, 1.0, 1.0],
        offsets=[0.0, 0.0, 0.0],
    )

    with pytest.raises(KeyError) as expected_exc:
        _ = record.array[np.asarray(["X", 1])]

    with pytest.raises(KeyError) as actual_exc:
        _ = record[["x", 1]]

    assert str(actual_exc.value) == str(expected_exc.value)


def test_getitem_tuple_with_slice_and_empty_list_subset() -> None:
    pf = PointFormat(0)
    record = PackedPointRecord.zeros(3, pf)

    tuple_subset = record[(slice(None),)]
    assert isinstance(tuple_subset, PackedPointRecord)
    assert len(tuple_subset) == 3

    empty_subset = record[[]]
    assert isinstance(empty_subset, PackedPointRecord)
    assert len(empty_subset) == 0


def test_scaleaware_getitem_tuple_and_empty_list_subset() -> None:
    pf = PointFormat(0)
    record = ScaleAwarePointRecord.zeros(
        point_count=3,
        point_format=pf,
        scales=[1.0, 1.0, 1.0],
        offsets=[0.0, 0.0, 0.0],
    )
    record["X"] = [1, 2, 3]
    record["Y"] = [4, 5, 6]

    names_subset = record[("x", "y")]
    assert isinstance(names_subset, ScaleAwarePointRecord)
    assert names_subset.array.dtype.names == ("X", "Y")

    tuple_subset = record[(slice(0, 2),)]
    assert isinstance(tuple_subset, ScaleAwarePointRecord)
    assert len(tuple_subset) == 2

    empty_subset = record[[]]
    assert isinstance(empty_subset, ScaleAwarePointRecord)
    assert len(empty_subset) == 0


def test_packed_getitem_tuple_slice_matches_numpy_tuple_indexing() -> None:
    pf = PointFormat(0)
    record = PackedPointRecord.zeros(5, pf)
    record["X"] = np.arange(5)

    expected = record.array[(slice(0, 3),)]
    result = record[(slice(0, 3),)]

    assert isinstance(result, PackedPointRecord)
    assert np.array_equal(result.array, expected)


def test_packed_getitem_tuple_array_matches_numpy_tuple_indexing() -> None:
    pf = PointFormat(0)
    record = PackedPointRecord.zeros(5, pf)
    record["X"] = np.arange(5)
    point_indices = np.array([0, 2, 4], dtype=np.intp)

    expected = record.array[(point_indices,)]
    result = record[(point_indices,)]

    assert isinstance(result, PackedPointRecord)
    assert np.array_equal(result.array, expected)


def test_packed_getitem_mixed_tuple_matches_numpy_error() -> None:
    pf = PointFormat(0)
    record = PackedPointRecord.zeros(3, pf)

    with pytest.raises(IndexError, match="only integers, slices"):
        _ = record.array[(0, "X")]

    with pytest.raises(IndexError, match="only integers, slices"):
        _ = record[(0, "X")]


def test_scaleaware_getitem_list_slice_is_invalid_like_numpy() -> None:
    pf = PointFormat(0)
    record = ScaleAwarePointRecord.zeros(
        point_count=5,
        point_format=pf,
        scales=[1.0, 1.0, 1.0],
        offsets=[0.0, 0.0, 0.0],
    )

    with pytest.raises(IndexError):
        _ = record[[slice(0, 3)]]


def test_scaleaware_getitem_list_of_indices_matches_numpy_fancy_indexing() -> None:
    pf = PointFormat(0)
    record = ScaleAwarePointRecord.zeros(
        point_count=5,
        point_format=pf,
        scales=[1.0, 1.0, 1.0],
        offsets=[0.0, 0.0, 0.0],
    )
    record["X"] = np.arange(5)

    expected = record.array[[0, 2, 4]]
    result = record[[0, 2, 4]]

    assert isinstance(result, ScaleAwarePointRecord)
    assert np.array_equal(result.array, expected)


def test_getattr_invalid_dimension_raises() -> None:
    pf = PointFormat(0)
    record = PackedPointRecord.zeros(1, pf)
    with pytest.raises(AttributeError):
        _ = record.not_a_dimension


def test_setattr_unsupported_dimension_raises() -> None:
    pf = PointFormat(0)
    record = PackedPointRecord.zeros(1, pf)
    with pytest.raises(ValueError, match="does not support gps_time"):
        record.gps_time = 5


def test_scaleaware_init_shape_errors() -> None:
    pf = PointFormat(3)
    with pytest.raises(ValueError, match="scales must be"):
        ScaleAwarePointRecord(np.zeros(1, pf.dtype()), pf, [1.0, 1.0], [0.0, 0.0, 0.0])

    with pytest.raises(ValueError, match="offsets must be"):
        ScaleAwarePointRecord(np.zeros(1, pf.dtype()), pf, [1.0, 1.0, 1.0], [0.0, 0.0])


def test_waveform_getitem_without_waveforms_raises() -> None:
    points = PackedPointRecord.zeros(2, PointFormat(0))

    with pytest.raises(ValueError, match="No waveform data available"):
        points["waveform"]


def test_eager_waveform_subset_rebuilds_waveform_state() -> None:
    points = make_record_with_eager_waveforms()

    subset = points[[0, 2, 3]]

    eager_state = subset._waveform_state
    assert isinstance(eager_state, EagerWaveformState)
    assert np.array_equal(
        eager_state.points_waveform_index, np.array([0, 1, 2], dtype=np.int64)
    )
    assert np.array_equal(
        eager_state.waveforms.samples["waveform"],
        np.array([[10, 11], [20, 21], [30, 31]], dtype=np.uint8),
    )


def test_lazy_waveform_subset_keeps_lazy_state() -> None:
    points, _, _ = make_record_with_lazy_waveforms()

    subset = points[[0, 2]]

    assert isinstance(subset._waveform_state, LazyWaveformState)
    assert subset._waveform_state is points._waveform_state


def test_eager_waveform_resize_shrink_rebuilds_waveform_state() -> None:
    points, expected_waveforms, expected_points_waveform_index = (
        make_waveform_capable_record_with_eager_waveforms()
    )

    points.resize(2)

    assert len(points) == 2
    expected_shrunk_indices = expected_points_waveform_index[:2]
    unique_waveform_indices, inverse_indices = np.unique(
        expected_shrunk_indices, return_inverse=True
    )
    expected_shrunk_waveforms = expected_waveforms[unique_waveform_indices]

    assert np.array_equal(points["waveform"], expected_waveforms[:2])
    eager_state = points._waveform_state
    assert isinstance(eager_state, EagerWaveformState)
    assert np.array_equal(eager_state.points_waveform_index, inverse_indices)
    assert np.array_equal(
        eager_state.waveforms.samples["waveform"], expected_shrunk_waveforms
    )


def test_eager_waveform_resize_grow_appends_zero_waveform_points() -> None:
    points, expected_waveforms, expected_points_waveform_index = (
        make_waveform_capable_record_with_eager_waveforms()
    )

    points.resize(6)

    zero_waveform = np.zeros(
        (1, expected_waveforms.shape[1]), dtype=expected_waveforms.dtype
    )
    expected_resized_waveforms = np.concatenate((expected_waveforms, zero_waveform))
    expected_resized_points_waveform_index = np.concatenate(
        (
            expected_points_waveform_index,
            np.full(2, len(expected_waveforms), dtype=np.int64),
        )
    )

    assert len(points) == 6
    assert np.array_equal(
        points["waveform"],
        expected_resized_waveforms[expected_resized_points_waveform_index],
    )
    eager_state = points._waveform_state
    assert isinstance(eager_state, EagerWaveformState)
    assert np.array_equal(
        eager_state.points_waveform_index,
        expected_resized_points_waveform_index,
    )
    assert np.array_equal(
        eager_state.waveforms.samples["waveform"],
        expected_resized_waveforms,
    )
    assert np.array_equal(
        points.array["wavepacket_index"],
        np.concatenate((np.ones(4, dtype=np.uint8), np.zeros(2, dtype=np.uint8))),
    )


def test_setitem_growth_keeps_eager_waveform_state_consistent() -> None:
    points, expected_waveforms, _ = make_waveform_capable_record_with_eager_waveforms()

    points["X"] = np.arange(6)

    zero_waveforms = np.zeros(
        (2, expected_waveforms.shape[1]), dtype=expected_waveforms.dtype
    )

    assert len(points) == 6
    assert np.array_equal(points["X"], np.arange(6))
    assert np.array_equal(points["waveform"][-2:], zero_waveforms)


def test_lazy_waveform_resize_keeps_lazy_state_until_access() -> None:
    points, expected_waveforms, _ = make_record_with_lazy_waveforms()

    points.resize(5)

    zero_waveforms = np.zeros(
        (2, expected_waveforms.shape[1]), dtype=expected_waveforms.dtype
    )

    assert isinstance(points._waveform_state, LazyWaveformState)
    assert np.array_equal(
        points["waveform"],
        np.concatenate((expected_waveforms, zero_waveforms)),
    )
    assert isinstance(points._waveform_state, EagerWaveformState)


# Private API tests


def test_waveform_load_returns_early() -> None:
    points = make_record_with_eager_waveforms()
    waveform_state = points._waveform_state
    assert isinstance(waveform_state, EagerWaveformState)
    waveforms_id = id(waveform_state.waveforms)
    index_id = id(waveform_state.points_waveform_index)
    points._load_waveforms_from_source()

    waveform_state = points._waveform_state
    assert isinstance(waveform_state, EagerWaveformState)
    assert id(waveform_state.waveforms) == waveforms_id
    assert id(waveform_state.points_waveform_index) == index_id


def test_lazy_waveform_load_materializes_eager_state() -> None:
    points, expected_waveforms, expected_points_waveform_index = (
        make_record_with_lazy_waveforms()
    )

    points._load_waveforms_from_source()

    waveform_state = points._waveform_state
    assert isinstance(waveform_state, EagerWaveformState)
    assert np.array_equal(
        waveform_state.waveforms.samples["waveform"],
        expected_waveforms,
    )
    assert np.array_equal(
        waveform_state.points_waveform_index,
        expected_points_waveform_index,
    )


def test_subset_preserves_eager_waveform_state() -> None:
    points = make_record_with_eager_waveforms()
    subset = points[:10]
    assert isinstance(subset._waveform_state, EagerWaveformState)


def test_list_subset_keeps_waveforms() -> None:
    points = make_record_with_eager_waveforms()
    indices = np.array([0, 2, 3], dtype=np.int64)
    expected = points["waveform"][indices]

    for item in (indices.tolist(), tuple(indices.tolist())):
        subset = points[item]
        assert isinstance(subset._waveform_state, EagerWaveformState)
        assert np.array_equal(subset["waveform"], expected)


def test_copy_preserves_eager_waveform_state_without_aliasing() -> None:
    points = make_record_with_eager_waveforms()

    copied = points.copy()

    assert isinstance(copied._waveform_state, EagerWaveformState)
    assert np.array_equal(copied["waveform"], points["waveform"])

    copied_state = copied._waveform_state
    original_state = points._waveform_state
    assert isinstance(copied_state, EagerWaveformState)
    assert isinstance(original_state, EagerWaveformState)
    assert copied_state.waveforms is not original_state.waveforms
    assert (
        copied_state.points_waveform_index is not original_state.points_waveform_index
    )


def test_copy_preserves_lazy_waveform_state() -> None:
    points, expected_waveforms, _ = make_record_with_lazy_waveforms()

    copied = points.copy()

    assert isinstance(copied._waveform_state, LazyWaveformState)
    assert np.array_equal(copied["waveform"], expected_waveforms)
