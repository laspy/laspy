from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest

from laspy.lasreader import WaveReader


def test_wave_reader_close_closes_source() -> None:
    buffer = io.BytesIO(b"abcd")
    wave_dtype = np.dtype([("waveform", np.uint8, (1,))])
    reader = WaveReader(
        buffer,
        bits_per_sample=8,
        number_of_samples=1,
        temporal_sample_spacing=1,
        wave_dtype=wave_dtype,
        closefd=True,
    )
    reader.close()
    assert buffer.closed


def test_wave_reader_closed_source_without_path_raises() -> None:
    buffer = io.BytesIO(b"abcd")
    wave_dtype = np.dtype([("waveform", np.uint8, (1,))])
    reader = WaveReader(
        buffer,
        bits_per_sample=8,
        number_of_samples=1,
        temporal_sample_spacing=1,
        wave_dtype=wave_dtype,
        closefd=True,
        source_path=None,
    )
    reader.close()
    with pytest.raises(ValueError, match="Waveform source is closed"):
        reader.read_n_waveforms(1)


def test_wave_reader_read_n_waveforms_short_read_raises() -> None:
    wave_dtype = np.dtype([("waveform", np.uint8, (2,))])
    reader = WaveReader(
        io.BytesIO(b"\x00\x01\x02\x03\x04\x05"),
        bits_per_sample=8,
        number_of_samples=2,
        temporal_sample_spacing=1,
        wave_dtype=wave_dtype,
        closefd=True,
    )

    first = reader.read_n_waveforms(2)
    assert first == bytearray(b"\x00\x01\x02\x03")

    with pytest.raises(ValueError, match="failed to fill whole waveform buffer"):
        reader.read_n_waveforms(2)


def test_wave_reader_reopens_closed_source_from_source_path(tmp_path: Path) -> None:
    wave_dtype = np.dtype([("waveform", np.uint8, (1,))])
    source_path = tmp_path / "waveforms.wdp"
    source_path.write_bytes(b"\x00\x01")

    source = source_path.open("rb")
    reader = WaveReader(
        source,
        bits_per_sample=8,
        number_of_samples=1,
        temporal_sample_spacing=1,
        wave_dtype=wave_dtype,
        closefd=False,
        source_path=source_path,
    )

    source.close()

    assert reader.read_n_waveforms(1) == bytearray(b"\x00")
    assert not reader.source.closed
