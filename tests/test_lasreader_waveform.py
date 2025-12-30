from __future__ import annotations

import io
import logging
import warnings
from pathlib import Path

import numpy as np
import pytest

import laspy
import laspy.lasreader as lasreader_module
from laspy.lasreader import LasReader, WaveformMode
from laspy.point.record import EagerWaveformState, LazyWaveformState
from laspy.vlrs.known import WaveformPacketStruct, WaveformPacketVlr
from laspy.waveform.descriptor import (
    WaveformPacketDescriptorRegistry,
    WavePacketDescriptorIndex,
    WavePacketDescriptorRecordId,
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
        points = reader.read_points(32)
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
        lazy_points = lazy_reader.read_points(n)
        assert isinstance(lazy_points._waveform_state, LazyWaveformState)
        lazy_waves = lazy_points["waveform"]
        assert isinstance(lazy_points._waveform_state, EagerWaveformState)

    with laspy.open(fullwave_path, fullwave="eager") as eager_reader:
        eager_points = eager_reader.read_points(n)
        eager_waves = eager_points["waveform"]

    assert np.array_equal(lazy_points.array, eager_points.array)
    assert np.array_equal(lazy_waves, eager_waves)


def test_lazy_waveform_load_rejects_unaligned_offsets(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points = reader.read_points(8)
        points.array["wavepacket_offset"][0] += 1

        with pytest.raises(NotImplementedError, match="byte offset"):
            _ = points["waveform"]


def test_waveform_lasdata_getitem_waveform(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="eager") as reader:
        las = reader.read()

    expected_waveforms = las.points["waveform"]
    result = las["waveform"]

    assert np.array_equal(result, expected_waveforms)


def test_lasfwreader_without_waveform_packets(simple_las_path: Path) -> None:
    with LasReader(
        simple_las_path.open("rb"), waveform_mode=WaveformMode.NEVER
    ) as reader:
        assert reader._waveform_source is None
        points = reader.read_points(2)
        assert len(points) == 2
        assert points._waveform_state is None


def test_lasfwreader_lazy_mode_without_waveform_packets(
    simple_las_path: Path,
) -> None:
    with LasReader(
        simple_las_path.open("rb"), waveform_mode=WaveformMode.LAZY
    ) as reader:
        points = reader.read_points(2)
        assert len(points) == 2
        assert points._waveform_state is None
        with pytest.raises(ValueError, match="No waveform data available"):
            _ = points["waveform"]


def test_lasfwreader_requires_external_waveforms(tmp_path: Path) -> None:
    las = laspy.create(point_format=10, file_version="1.4")
    las.header.global_encoding.waveform_data_packets_external = False
    las.header.global_encoding.waveform_data_packets_internal = True
    path = tmp_path / "internal_only.las"
    las.write(str(path))

    with path.open("rb") as handle:
        with LasReader(handle, waveform_mode=WaveformMode.LAZY) as reader:
            with pytest.raises(ValueError, match="external"):
                reader.read_points(1)


def test_lasfwreader_requires_waveform_vlrs(tmp_path: Path) -> None:
    las = laspy.create(point_format=10, file_version="1.4")
    las.header.global_encoding.waveform_data_packets_external = True
    las.header.global_encoding.waveform_data_packets_internal = False
    path = tmp_path / "no_vlrs.las"
    las.write(str(path))
    path.with_suffix(".wdp").write_bytes(b"")

    with LasReader(path.open("rb"), waveform_mode=WaveformMode.LAZY) as reader:
        with pytest.raises(ValueError, match="No waveform packet descriptors"):
            reader.read_points(1)


def test_lasreader_does_not_open_wdp_when_descriptor_loading_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    las = laspy.create(point_format=10, file_version="1.4")
    las.header.global_encoding.waveform_data_packets_external = True
    las.header.global_encoding.waveform_data_packets_internal = False

    las_path = tmp_path / "missing_waveform_descriptors.las"
    las.write(str(las_path))

    wdp_path = las_path.with_suffix(".wdp")
    wdp_path.write_bytes(b"waveform bytes")

    opened_wdp_count = 0
    original_path_open = Path.open

    def raising_from_vlrs(_cls, _vlrs):
        raise ValueError("descriptor loading failed")

    def counting_open(self: Path, *args, **kwargs):
        nonlocal opened_wdp_count
        mode = args[0] if args else kwargs.get("mode", "r")
        if self == wdp_path and mode == "rb":
            opened_wdp_count += 1
        return original_path_open(self, *args, **kwargs)

    with las_path.open("rb") as source:
        monkeypatch.setattr(Path, "open", counting_open)
        monkeypatch.setattr(
            lasreader_module.WaveformPacketDescriptorRegistry,
            "from_vlrs",
            classmethod(raising_from_vlrs),
        )

        with LasReader(source, waveform_mode=WaveformMode.LAZY) as reader:
            with pytest.raises(ValueError, match="descriptor loading failed"):
                reader.read_points(1)

    assert opened_wdp_count == 0


def test_read_override_loads_waveforms_when_reader_mode_is_never(
    fullwave_path: Path,
) -> None:
    with LasReader(
        fullwave_path.open("rb"), waveform_mode=WaveformMode.NEVER
    ) as reader:
        las = reader.read(waveform_mode=WaveformMode.EAGER)

    assert isinstance(las.points._waveform_state, EagerWaveformState)


def test_lasreader_waveform_read_requires_source_name(fullwave_path: Path) -> None:
    stream = io.BytesIO(fullwave_path.read_bytes())
    with LasReader(stream, waveform_mode=WaveformMode.LAZY) as reader:
        with pytest.raises(
            ValueError, match="Cannot locate the external waveform .wdp file"
        ):
            reader.read_points(1)


def test_read_seeks_waveform_source_when_already_initialized(
    fullwave_path: Path,
) -> None:
    with LasReader(fullwave_path.open("rb"), waveform_mode=WaveformMode.LAZY) as reader:
        # First eager waveform read initializes and advances waveform source;
        # read() must rewind it before reading remaining points.
        first = reader.read_points(1, waveform_mode=WaveformMode.EAGER)
        first_waveforms = first["waveform"]
        assert reader._waveform_source is not None
        assert len(first_waveforms) == 1
        las = reader.read(waveform_mode=WaveformMode.EAGER)
        assert len(las.points) == reader.header.point_count - 1
        read_waveforms = las.points["waveform"]

    with LasReader(
        fullwave_path.open("rb"), waveform_mode=WaveformMode.EAGER
    ) as expected_reader:
        expected = expected_reader.read()

    assert np.array_equal(las.points.array, expected.points.array[1:])
    assert np.array_equal(read_waveforms, expected.points["waveform"][1:])


@pytest.mark.parametrize("fullwave", ["lazyy", "EAGER", "", "true", True, False, None])
def test_open_las_rejects_invalid_fullwave_values(
    simple_las_path: Path, fullwave: object
) -> None:
    with pytest.raises(ValueError, match="valid WaveformMode"):
        laspy.open(simple_las_path, fullwave=fullwave)


def test_open_las_accepts_never_fullwave(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="never") as reader:
        points = reader.read_points(8)
        assert points._waveform_state is None


def test_lasreader_rejects_invalid_waveform_mode(simple_las_path: Path) -> None:
    with simple_las_path.open("rb") as stream:
        with pytest.raises(ValueError, match="valid WaveformMode"):
            LasReader(stream, waveform_mode="yoshi")  # type: ignore[arg-type]


def test_lasreader_accepts_string_waveform_mode(simple_las_path: Path) -> None:
    with simple_las_path.open("rb") as stream:
        with LasReader(stream, waveform_mode="never") as reader:  # type: ignore[arg-type]
            assert reader._waveform_mode is WaveformMode.NEVER


def test_read_points_after_exhaustion(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        reader.read_points(-1)
        points = reader.read_points(1)
        assert len(points) == 0


def test_read_points_empty_file(tmp_path: Path) -> None:
    las = laspy.create(point_format=10, file_version="1.4")
    las.header.global_encoding.waveform_data_packets_external = True
    las.header.global_encoding.waveform_data_packets_internal = False

    vlr = WaveformPacketVlr(100)
    vlr.parsed_record = WaveformPacketStruct(
        bits_per_sample=16,
        waveform_compression_type=0,
        number_of_samples=1,
        temporal_sample_spacing=1,
        digitizer_gain=1.0,
        digitizer_offset=0.0,
    )
    las.header.vlrs.append(vlr)

    path = tmp_path / "empty_fullwave.las"
    las.write(str(path))
    path.with_suffix(".wdp").write_bytes(b"")

    with laspy.open(path, fullwave="lazy") as reader:
        points = reader.read_points(1)
        assert len(points) == 0


def test_read_points_logs_short_read(
    fullwave_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        original_read = reader.point_source.read_n_points

        def short_read(n: int) -> bytes:
            return original_read(max(0, n - 1))

        reader.point_source.read_n_points = short_read
        caplog.set_level(logging.ERROR, logger="laspy.lasreader")
        reader.read_points(2)

    assert any("Could only read" in record.message for record in caplog.records)


# Private API coverage for descriptor validation helpers.
def test_missing_descriptor_handling(fullwave_path: Path) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points = reader.read_points(16)
        points.array["wavepacket_index"][0] = 200

        with pytest.raises(ValueError, match="No matching descriptor found"):
            reader._ensure_points_have_valid_waveform_descriptors(points)
        assert points.array["wavepacket_index"][0] == 200


def test_ensure_points_have_valid_waveform_descriptors_all_valid(
    fullwave_path: Path,
) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points = reader.read_points(8)
        reader._ensure_points_have_valid_waveform_descriptors(points)
        valid_mask = np.asarray(points.array["wavepacket_index"] != 0, dtype=bool)

    assert valid_mask.all()


def test_ensure_points_have_valid_waveform_descriptors_missing_with_empty_registry_raises(
    fullwave_path: Path,
) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points = reader.read_points(8)
        points.array["wavepacket_index"][0] = 200
        reader._waveform_descriptors_registry = WaveformPacketDescriptorRegistry()

        with pytest.raises(ValueError, match="No waveform packet descriptors found"):
            reader._ensure_points_have_valid_waveform_descriptors(points)


def test_ensure_points_have_valid_waveform_descriptors_reports_invalid_nonzero_index(
    fullwave_path: Path,
) -> None:
    with laspy.open(fullwave_path, fullwave="lazy") as reader:
        points = reader.read_points(8)
        points.array["wavepacket_index"][0] = 200

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with pytest.raises(ValueError, match="No matching descriptor found"):
                reader._ensure_points_have_valid_waveform_descriptors(points)

    assert not caught
