from __future__ import annotations

import numpy as np

from laspy.waveform.utils import deduplicate_waveform_indices, iter_runs


def test_iter_runs_handles_empty_and_gaps() -> None:
    empty = iter_runs(np.array([], dtype=np.uint64))
    assert empty == []

    runs = iter_runs(np.array([0, 1, 3, 4, 6], dtype=np.uint64))
    assert runs == [(0, 1), (3, 4), (6, 6)]


def test_deduplicate_waveform_indices_keeps_unique_order_mapping() -> None:
    offsets = np.array([12, 12, 20, 28, 20], dtype=np.uint64)
    has_waveform_mask = np.array([True, True, True, True, True], dtype=bool)

    unique_indices, inverse_indices = deduplicate_waveform_indices(
        offsets, has_waveform_mask, waveform_size=8
    )

    assert np.array_equal(unique_indices, np.array([1, 2, 3], dtype=np.uint64))
    assert np.array_equal(inverse_indices, np.array([0, 0, 1, 2, 1], dtype=np.int64))


def test_deduplicate_waveform_indices_rejects_mixed_remainders() -> None:
    offsets = np.array([8, 13], dtype=np.uint64)
    has_waveform_mask = np.array([True, True], dtype=bool)

    with np.testing.assert_raises(NotImplementedError):
        deduplicate_waveform_indices(offsets, has_waveform_mask, waveform_size=8)
