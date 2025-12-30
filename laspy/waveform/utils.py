from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def iter_runs(indices: np.ndarray) -> list[tuple[int, int]]:
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


def deduplicate_waveform_indices(
    offsets: NDArray[np.uint64],
    has_waveform_mask: NDArray[np.bool_],
    waveform_size: int,
) -> tuple[NDArray[np.uint64], NDArray[np.int64]]:
    if not has_waveform_mask.any():
        return np.array([], dtype=np.uint64), np.array([], dtype=np.int64)

    valid_offsets = offsets[has_waveform_mask]
    offset_remainder = np.remainder(valid_offsets, waveform_size)
    base_remainder = offset_remainder[0]
    if np.any(offset_remainder != base_remainder):
        raise NotImplementedError(
            "Unsupported waveform byte offset layout; "
            "laspy currently requires a single fixed byte-offset remainder "
            "for all waveform packets"
        )

    valid_indices = (valid_offsets - base_remainder) // waveform_size
    return np.unique(valid_indices, return_inverse=True)
