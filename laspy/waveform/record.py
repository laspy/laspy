import abc
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np

from .utils import deduplicate_waveform_indices, iter_runs

if TYPE_CHECKING:
    from collections.abc import Buffer
else:
    try:
        from collections.abc import Buffer
    except ImportError:  # Python < 3.12

        class Buffer(Protocol):
            """Fallback typing stub for Python < 3.12."""

            ...


class IWaveformReader(abc.ABC):
    @property
    @abc.abstractmethod
    def temporal_sample_spacing(self) -> int: ...

    @property
    @abc.abstractmethod
    def wave_dtype(self) -> np.dtype: ...

    @property
    @abc.abstractmethod
    def wave_size_bytes(self) -> int: ...

    @abc.abstractmethod
    def read_n_waveforms(self, n: int) -> bytearray: ...

    @abc.abstractmethod
    def seek(self, waveform_index: int) -> None: ...

    @abc.abstractmethod
    def close(self) -> None: ...


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
        waveform_reader: IWaveformReader,
    ) -> tuple["WaveformRecord", np.ndarray[Any, np.dtype[np.int64]]]:
        wave_dtype = waveform_reader.wave_dtype
        temporal_sample_spacing = waveform_reader.temporal_sample_spacing
        waveform_size = waveform_reader.wave_size_bytes
        point_count = len(points_array)

        sizes = np.asarray(points_array["wavepacket_size"], dtype=np.uint64)
        if "wavepacket_index" in points_array.dtype.names:
            no_waveform_mask = np.asarray(
                points_array["wavepacket_index"] == 0, dtype=bool
            )
        else:
            no_waveform_mask = np.zeros(point_count, dtype=bool)
        has_waveform_mask = ~no_waveform_mask

        if point_count == 0:
            return (
                cls(np.empty((0,), dtype=wave_dtype), temporal_sample_spacing),
                np.empty((0,), dtype=np.int64),
            )

        if not has_waveform_mask.any():
            return (
                cls(np.zeros((1,), dtype=wave_dtype), temporal_sample_spacing),
                np.zeros(point_count, dtype=np.int64),
            )

        actual = set(sizes[has_waveform_mask])
        if actual - {waveform_size}:
            raise ValueError(
                f"Inconsistent waveform sizes in point data: {actual} but descriptor size is {waveform_size}"
            )

        offsets = np.asarray(points_array["wavepacket_offset"], dtype=np.uint64)
        unique_indices, inverse_indices = deduplicate_waveform_indices(
            offsets, has_waveform_mask, waveform_size
        )

        runs = iter_runs(unique_indices)

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

        points_waveform_index = np.full(point_count, -1, dtype=np.int64)
        points_waveform_index[has_waveform_mask] = inverse_indices

        if not np.all(has_waveform_mask):
            missing_wave_index = len(waveforms)
            new_samples = np.empty((missing_wave_index + 1,), dtype=wave_dtype)
            if len(waveforms):
                new_samples[:-1] = waveforms.samples
            new_samples["waveform"][-1] = 0
            waveforms = cls(new_samples, temporal_sample_spacing)
            points_waveform_index[~has_waveform_mask] = missing_wave_index

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
