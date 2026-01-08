from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import io
import logging
import tempfile

import numpy as np
import pytest

import laspy
from laspy.lasfwreader import LasFWReader, WaveformLasData, WaveformPointRecord, WaveReader
from laspy.vlrs.known import WaveformPacketVlr
from laspy.waveform import (
    WavePacketDescriptorRecordId,
    WaveformPacketDescriptorRegistry,
    WavePacketDescriptorIndex,
)

FULLWAVE_LAZ_PATH = Path(__file__).parent / "data" / "fullwave.laz"
FULLWAVE_WDP_PATH = FULLWAVE_LAZ_PATH.with_suffix(".wdp")


@pytest.fixture()
def fullwave_path() -> Path:
    if not FULLWAVE_LAZ_PATH.exists() or not FULLWAVE_WDP_PATH.exists():
        pytest.skip("Missing fullwave test data")
    if len(laspy.LazBackend.detect_available()) == 0:
        pytest.skip("No Laz Backend")
    return FULLWAVE_LAZ_PATH


def test_waveform_packet_vlr_record_data_bytes_handles_unparsed() -> None:
    vlr = WaveformPacketVlr(100)
    assert vlr.record_data_bytes() == b""


def test_waveform_descriptor_registry_matches_points(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points, _ = reader.read_points_waveforms(32)
        registry = WaveformPacketDescriptorRegistry.from_vlrs(reader.header.vlrs)

    assert registry.data

    wave_dtype = registry.dtype()
    assert wave_dtype is not None

    wave_samples = wave_dtype["waveform"].shape[0]
    wave_sample_size = wave_dtype["waveform"].base.itemsize

    wavepacket_size = int(np.unique(points["wavepacket_size"])[0])
    wavepacket_index = int(points["wavepacket_index"][0])

    assert wave_samples == registry.number_of_samples
    assert wave_sample_size * wave_samples == wavepacket_size
    assert registry.bits_per_sample == wave_sample_size * 8

    record_id = WavePacketDescriptorRecordId.from_index(
        WavePacketDescriptorIndex(wavepacket_index)
    )
    assert record_id in registry


def test_fullwave_lazy_load_matches_eager(fullwave_path: Path) -> None:
    n = 256

    with laspy.open(fullwave_path, fullwave="lazy") as lazy_reader:
        lazy_points, lazy_wf_points = lazy_reader.read_points_waveforms(n)
        assert lazy_wf_points._waveforms is None
        assert lazy_wf_points._points_waveform_index is None
        lazy_waves = lazy_wf_points["waveform"]
        assert lazy_wf_points._waveforms is not None
        assert lazy_wf_points._points_waveform_index is not None

    with laspy.open(fullwave_path, fullwave="eager") as eager_reader:
        eager_points, eager_wf_points = eager_reader.read_points_waveforms(n)
        eager_waves = eager_wf_points["waveform"]

    assert np.array_equal(lazy_points.array, eager_points.array)
    assert np.array_equal(lazy_waves, eager_waves)


def test_missing_descriptor_handling(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points, _ = reader.read_points_waveforms(16)
        points.array["wavepacket_index"][0] = 0

        valid_mask, missing = reader._compute_valid_descriptor_mask(
            points, allow_missing_descriptors=True
        )
        assert missing is True
        assert not bool(valid_mask[0])
        assert points.array["wavepacket_index"][0] != 0

        points.array["wavepacket_index"][0] = 0
        with pytest.raises(ValueError):
            reader._compute_valid_descriptor_mask(
                points, allow_missing_descriptors=False
            )


def test_lazy_write_roundtrip(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        las = reader.read()
        indices = np.arange(0, len(las.points), 7)
        subset = las[indices]
        assert subset.waveform_points._waveforms is None

        registry = WaveformPacketDescriptorRegistry.from_vlrs(subset.header.vlrs)
        wave_dtype = registry.dtype()
        assert wave_dtype is not None
        expected_wdp_size = (
            np.unique(subset.points.array["wavepacket_offset"]).size * wave_dtype.itemsize
        )

        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "subset_fullwave.laz"
            subset.write(str(out_path))

            out_wdp = out_path.with_suffix(".wdp")
            assert out_path.exists()
            assert out_wdp.exists()
            assert out_wdp.stat().st_size == expected_wdp_size

            with laspy.open(out_path, fullwave="eager") as roundtrip_reader:
                roundtrip = roundtrip_reader.read()

        with laspy.open(fullwave_path, fullwave="eager") as expected_reader:
            expected = expected_reader.read()

    assert np.array_equal(roundtrip.points.array, subset.points.array)
    assert np.array_equal(
        roundtrip.waveform_points["waveform"], expected.waveform_points["waveform"][indices]
    )


def test_lazy_write_dedup_roundtrip(fullwave_path: Path, tmp_path: Path) -> None:
    n = 2048
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points, wf_points = reader.read_points_waveforms(n)
        las = WaveformLasData(deepcopy(reader.header), points, wf_points)
        las.update_header()
        las.waveform_points._valid_descriptor_mask = None

        wave_size = las.waveform_points._waveform_reader.wave_size_bytes
        unique_offsets = np.unique(las.points.array["wavepacket_offset"])
        expected_wdp_size = int(unique_offsets.size * wave_size)

        out_path = tmp_path / "dedup_fullwave.laz"
        las.write(str(out_path))

        out_wdp = out_path.with_suffix(".wdp")
        assert out_wdp.exists()
        assert out_wdp.stat().st_size == expected_wdp_size
        written_points = las.points.array.copy()

    with laspy.open(out_path, fullwave="eager") as roundtrip_reader:
        roundtrip_points, roundtrip_wf_points = roundtrip_reader.read_points_waveforms(
            n
        )
        roundtrip_waves = roundtrip_wf_points["waveform"]

    with laspy.open(fullwave_path, fullwave="eager") as expected_reader:
        _, expected_wf_points = expected_reader.read_points_waveforms(n)
        expected_waves = expected_wf_points["waveform"]

    assert np.array_equal(roundtrip_points.array, written_points)
    assert np.array_equal(roundtrip_waves, expected_waves)


def test_lazy_write_dedup_missing_descriptor(
    fullwave_path: Path, tmp_path: Path
) -> None:
    n = 256
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points, wf_points = reader.read_points_waveforms(n)
        las = WaveformLasData(deepcopy(reader.header), points, wf_points)
        las.update_header()

        valid_mask = np.ones(len(points), dtype=bool)
        valid_mask[0] = False
        las.waveform_points._valid_descriptor_mask = valid_mask

        wave_size = las.waveform_points._waveform_reader.wave_size_bytes
        unique_offsets = np.unique(las.points.array["wavepacket_offset"][valid_mask])
        expected_wdp_size = int((unique_offsets.size + 1) * wave_size)

        out_path = tmp_path / "dedup_missing.laz"
        las.write(str(out_path))

        out_wdp = out_path.with_suffix(".wdp")
        assert out_wdp.exists()
        assert out_wdp.stat().st_size == expected_wdp_size
        assert (
            las.points.array["wavepacket_offset"][0]
            == unique_offsets.size * wave_size
        )

    with laspy.open(out_path, fullwave="eager") as roundtrip_reader:
        _, roundtrip_wf_points = roundtrip_reader.read_points_waveforms(n)
        waves = roundtrip_wf_points["waveform"]

    assert np.all(waves[0] == 0)


def test_lazy_write_dedup_all_invalid_mask(
    fullwave_path: Path, tmp_path: Path
) -> None:
    n = 8
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points, wf_points = reader.read_points_waveforms(n)
        las = WaveformLasData(deepcopy(reader.header), points, wf_points)
        las.update_header()

        las.waveform_points._valid_descriptor_mask = np.zeros(len(points), dtype=bool)
        wave_size = las.waveform_points._waveform_reader.wave_size_bytes

        out_path = tmp_path / "dedup_all_invalid.laz"
        las._write_wdp_lazy(
            destination=out_path,
            waveform_size=wave_size,
            chunksize=1024,
        )

    out_wdp = out_path.with_suffix(".wdp")
    assert out_wdp.exists()
    assert out_wdp.stat().st_size == wave_size
    assert np.all(las.points.array["wavepacket_offset"] == 0)


def test_waveform_point_record_load_returns_early(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="eager") as reader:
        _, wf_points = reader.read_points_waveforms(4)

    waveforms_id = id(wf_points._waveforms)
    index_id = id(wf_points._points_waveform_index)
    wf_points._load_waveforms_from_source()

    assert id(wf_points._waveforms) == waveforms_id
    assert id(wf_points._points_waveform_index) == index_id


def test_waveform_iter_runs_handles_empty_and_gaps() -> None:
    empty = WaveformLasData._iter_runs(np.array([], dtype=np.uint64))
    assert empty == []

    runs = WaveformLasData._iter_runs(np.array([0, 1, 3, 4, 6], dtype=np.uint64))
    assert runs == [(0, 1), (3, 4), (6, 6)]


def test_write_wdp_lazy_dedup_requires_reader(
    fullwave_path: Path, tmp_path: Path
) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points, wf_points = reader.read_points_waveforms(8)
        las = WaveformLasData(deepcopy(reader.header), points, wf_points)
        las.update_header()
        wave_size = las.waveform_points._waveform_reader.wave_size_bytes
        las.waveform_points._waveform_reader = None

        with pytest.raises(ValueError, match="waveform reader"):
            las._write_wdp_lazy(
                destination=tmp_path / "no_reader.laz",
                waveform_size=wave_size,
                chunksize=1024,
            )


def test_write_wdp_lazy_dedup_rejects_bad_mask(
    fullwave_path: Path, tmp_path: Path
) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points, wf_points = reader.read_points_waveforms(8)
        las = WaveformLasData(deepcopy(reader.header), points, wf_points)
        las.update_header()
        wave_size = las.waveform_points._waveform_reader.wave_size_bytes
        las.waveform_points._valid_descriptor_mask = np.ones(len(points) + 1, dtype=bool)

        with pytest.raises(IndexError, match="index did not match indexed array along axis 0"):
            las._write_wdp_lazy(
                destination=tmp_path / "bad_mask.laz",
                waveform_size=wave_size,
                chunksize=1024,
            )


def test_resolve_valid_mask_rejects_length_mismatch(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points, wf_points = reader.read_points_waveforms(8)
        las = WaveformLasData(deepcopy(reader.header), points, wf_points)
        las.waveform_points._valid_descriptor_mask = np.ones(len(points) + 1, dtype=bool)

        with pytest.raises(ValueError, match="Waveform descriptor mask size"):
            las._resolve_valid_mask(len(points))


def test_waveform_point_record_getitem_and_subset(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="eager") as reader:
        points, wf_points = reader.read_points_waveforms(32)

    subset = wf_points[:10]
    assert subset._waveforms is not None
    assert subset._points_waveform_index is not None

    dims = wf_points[["x", "y", "z"]]
    assert hasattr(dims, "point_format")
    assert "X" in dims.array.dtype.names

    x_values = wf_points["X"]
    assert len(x_values) == len(points)

    wf_points["waveform"]


def test_waveform_point_record_no_waveforms_raises(simple_las_path: Path) -> None:
    las = laspy.read(simple_las_path)
    wf_points = WaveformPointRecord(
        las.points.array,
        las.points.point_format,
        las.points.scales,
        las.points.offsets,
        None,
        None,
        waveform_reader=None,
    )
    with pytest.raises(ValueError):
        wf_points["waveform"]


def test_waveform_lasdata_getitem_and_write_no_waveforms(
    simple_las_path: Path, tmp_path: Path
) -> None:
    las = laspy.read(simple_las_path)
    wf_points = WaveformPointRecord(
        las.points.array,
        las.points.point_format,
        las.points.scales,
        las.points.offsets,
        None,
        None,
        waveform_reader=None,
    )
    wf_las = WaveformLasData(las.header, las.points, wf_points)

    assert wf_las["X"].shape[0] == len(las.points)

    subset = wf_las[0]
    assert isinstance(subset, WaveformLasData)
    assert len(subset.points) == 1

    out_path = tmp_path / "no_waveforms.las"
    wf_las.write(str(out_path))
    assert out_path.exists()
    assert not out_path.with_suffix(".wdp").exists()


def test_waveform_lasdata_write_rejects_binaryio(
    simple_las_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    las = laspy.read(simple_las_path)
    wf_points = WaveformPointRecord(
        las.points.array,
        las.points.point_format,
        las.points.scales,
        las.points.offsets,
        None,
        None,
        waveform_reader=None,
    )
    wf_las = WaveformLasData(las.header, las.points, wf_points)

    import laspy.lasfwreader as lasfwreader

    monkeypatch.setattr(lasfwreader, "BinaryIO", io.BufferedIOBase)
    with pytest.raises(NotImplementedError):
        wf_las.write(io.BytesIO())


def test_waveform_lasdata_write_eager_creates_wdp(
    fullwave_path: Path, tmp_path: Path
) -> None:
    with laspy.open(fullwave_path, fullwave="eager") as reader:
        las = reader.read()
    las.header.global_encoding.waveform_data_packets_internal = True

    waveforms = las.waveform_points._waveforms
    assert waveforms is not None

    out_path = tmp_path / "eager_fullwave.laz"
    las.write(str(out_path))

    out_wdp = out_path.with_suffix(".wdp")
    assert out_wdp.exists()
    assert out_wdp.stat().st_size == len(waveforms) * waveforms.wave_size
    assert las.header.global_encoding.waveform_data_packets_external is True
    assert las.header.global_encoding.waveform_data_packets_internal is False
    if las.header.version.minor >= 3:
        assert las.header.start_of_waveform_data_packet_record == 0


def test_write_wdp_no_waveforms_noop(tmp_path: Path) -> None:
    path = tmp_path / "noop.wdp"
    WaveformLasData._write_wdp(path, None)
    assert not path.exists()


def test_write_wdp_lazy_errors(fullwave_path: Path, tmp_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        las = reader.read()
        wave_size = las.waveform_points._waveform_reader.wave_size_bytes

        with pytest.raises(NotImplementedError):
            las._write_wdp_lazy(
                destination=None,
                waveform_size=wave_size,
                chunksize=1024,
            )

        with pytest.raises(ValueError):
            las._write_wdp_lazy(
                destination=tmp_path / "bad_chunk.laz",
                waveform_size=wave_size,
                chunksize=0,
            )


def test_write_wdp_lazy_inconsistent_sizes(
    fullwave_path: Path, tmp_path: Path
) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        las = reader.read()
        wave_size = las.waveform_points._waveform_reader.wave_size_bytes
        las.waveform_points._valid_descriptor_mask = None
        las.points.array["wavepacket_size"][0] = wave_size + 1
        with pytest.raises(ValueError):
            las._write_wdp_lazy(
                destination=tmp_path / "bad_size.laz",
                waveform_size=wave_size,
                chunksize=1024,
            )


def test_write_wdp_lazy_empty_points(
    fullwave_path: Path, tmp_path: Path
) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        las = reader.read()
        empty = las[:0]
        wave_size = empty.waveform_points._waveform_reader.wave_size_bytes

        out_path = tmp_path / "empty.laz"
        empty._write_wdp_lazy(
            destination=out_path,
            waveform_size=wave_size,
            chunksize=1024,
        )

    out_wdp = out_path.with_suffix(".wdp")
    assert out_wdp.exists()
    assert out_wdp.stat().st_size == 0


def test_write_wdp_lazy_updates_encoding_flags(
    fullwave_path: Path, tmp_path: Path
) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        las = reader.read()
        las.header.global_encoding.waveform_data_packets_internal = True
        wave_size = las.waveform_points._waveform_reader.wave_size_bytes
        out_path = tmp_path / "flags.laz"
        las._write_wdp_lazy(
            destination=out_path,
            waveform_size=wave_size,
            chunksize=1024,
        )

    assert las.header.global_encoding.waveform_data_packets_external is True
    assert las.header.global_encoding.waveform_data_packets_internal is False
    if las.header.version.minor >= 3:
        assert las.header.start_of_waveform_data_packet_record == 0


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


def test_lasfwreader_without_waveform_packets(simple_las_path: Path) -> None:
    with LasFWReader(simple_las_path.open("rb")) as reader:
        assert reader._waveform_source is None
        assert reader.waves_read == 0
        points, wf_points = reader.read_points_waveforms(2)
        assert len(points) == 2
        assert wf_points._waveforms is None
        assert wf_points._waveform_reader is None


def test_lasfwreader_requires_external_waveforms(tmp_path: Path) -> None:
    las = laspy.create(point_format=10, file_version="1.4")
    las.header.global_encoding.waveform_data_packets_external = False
    las.header.global_encoding.waveform_data_packets_internal = True
    path = tmp_path / "internal_only.las"
    las.write(path)

    with path.open("rb") as handle:
        with pytest.raises(ValueError, match="external"):
            LasFWReader(handle)


def test_lasfwreader_requires_waveform_vlrs(tmp_path: Path) -> None:
    las = laspy.create(point_format=10, file_version="1.4")
    las.header.global_encoding.waveform_data_packets_external = True
    las.header.global_encoding.waveform_data_packets_internal = False
    path = tmp_path / "no_vlrs.las"
    las.write(path)
    path.with_suffix(".wdp").write_bytes(b"")

    with pytest.raises(ValueError, match="No waveform packet descriptors"):
        LasFWReader(path.open("rb"))


def test_compute_valid_descriptor_mask_all_valid(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points, _ = reader.read_points_waveforms(8)
        valid_mask, missing = reader._compute_valid_descriptor_mask(
            points, allow_missing_descriptors=False
        )

    assert missing is False
    assert valid_mask.all()


def test_read_points_waveforms_after_exhaustion(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        reader.read_points_waveforms(-1)
        points, wf_points = reader.read_points_waveforms(1)
        assert len(points) == 0
        assert len(wf_points) == 0


def test_read_points_waveforms_empty_file(tmp_path: Path) -> None:
    las = laspy.create(point_format=10, file_version="1.4")
    las.header.global_encoding.waveform_data_packets_external = True
    las.header.global_encoding.waveform_data_packets_internal = False

    vlr = WaveformPacketVlr(100)
    vlr.parsed_record = laspy.vlrs.known.WaveformPacketStruct(
        bits_per_sample=16,
        waveform_compression_type=0,
        number_of_samples=1,
        temporal_sample_spacing=1,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    las.header.vlrs.append(vlr)

    path = tmp_path / "empty_fullwave.las"
    las.write(path)
    path.with_suffix(".wdp").write_bytes(b"")

    with laspy.open(path, fullwave="lazy") as reader:
        points, wf_points = reader.read_points_waveforms(1)
        assert len(points) == 0
        assert len(wf_points) == 0


def test_read_points_waveforms_logs_short_read(
    fullwave_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        original_read = reader.point_source.read_n_points

        def short_read(n: int) -> bytes:
            return original_read(max(0, n - 1))

        reader.point_source.read_n_points = short_read
        caplog.set_level(logging.ERROR, logger="laspy.lasfwreader")
        reader.read_points_waveforms(2)

    assert any("Could only read" in record.message for record in caplog.records)
