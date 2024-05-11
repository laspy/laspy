import os
from pathlib import Path

import numpy as np
import pytest

import laspy
from laspy import LazBackend
from tests.test_common import test1_4_las


@pytest.fixture()
def file():
    return laspy.read(test1_4_las)


def test_unscaled_x(file):
    assert file.X.max() == 1751224820
    assert file.X.min() == 1320803567


def test_unscaled_y(file):
    assert file.Y.max() == -860121188
    assert file.Y.min() == -864646690


def test_unscaled_z(file):
    assert file.Z.max() == -1745638014
    assert file.Z.min() == -1751937981


def test_intensity(file):
    assert file.intensity.max() == 68
    assert file.intensity.min() == 2


def test_return_number(file):
    assert file.return_number.max() == 4
    assert file.return_number.min() == 1


def test_number_of_returns(file):
    assert file.number_of_returns.max() == 4
    assert file.number_of_returns.min() == 1


def test_edge_of_flight_line(file):
    assert file.edge_of_flight_line.max() == 1
    assert file.edge_of_flight_line.min() == 0


def scan_direction_flag(file):
    assert file.scan_direction_flag.max() == 1
    assert file.scan_direction_flag.min() == 0


def test_classification(file):
    assert file.classification.max() == 2
    assert file.classification.min() == 2


def test_scan_angle_rank(file):
    assert file.scan_angle.max() == 3173
    assert file.scan_angle.min() == 1837


def test_user_data(file):
    assert file.user_data.max() == 0
    assert file.user_data.min() == 0


def test_point_source_id(file):
    assert file.point_source_id.max() == 202
    assert file.point_source_id.min() == 202


def test_gps_time(file):
    assert file.gps_time.max() == pytest.approx(83177420.601045)
    assert file.gps_time.min() == pytest.approx(83177420.534005)


def test_scanner_channel(file):
    assert file.scanner_channel.max() == 0
    assert file.scanner_channel.min() == 0


def test_we_read_evlrs_when_simply_opening():
    file_with_evlrs = os.path.dirname(__file__) + "/data/1_4_w_evlr.las"
    expected_evlrs = laspy.VLR(
        user_id="pylastest",
        record_id=42,
        description="just a test evlr",
        record_data=b"Test 1 2 ... 1 2",
    )
    with laspy.open(file_with_evlrs) as reader:
        assert reader.evlrs == [expected_evlrs]


def test_we_dont_read_evlrs_when_opening_if_user_does_not_want():
    file_with_evlrs = os.path.dirname(__file__) + "/data/1_4_w_evlr.las"
    with laspy.open(file_with_evlrs, read_evlrs=False) as reader:
        assert reader.evlrs is None


def test_reader_read_reads_evlrs_even_if_skipped_at_opening():
    file_with_evlrs = os.path.dirname(__file__) + "/data/1_4_w_evlr.las"
    expected_evlrs = [
        laspy.VLR(
            user_id="pylastest",
            record_id=42,
            description="just a test evlr",
            record_data=b"Test 1 2 ... 1 2",
        )
    ]
    with laspy.open(file_with_evlrs, read_evlrs=False) as reader:
        assert reader.evlrs is None
        las = reader.read()
        assert las.evlrs == expected_evlrs
        assert reader.evlrs == expected_evlrs


@pytest.mark.parametrize(
    "file,backend",
    [
        ("/data/1_4_w_evlr.las", None),
        pytest.param(
            "/data/1_4_w_evlr.laz",
            LazBackend.Laszip,
            marks=pytest.mark.skipif(
                not LazBackend.Laszip.is_available(), reason="laszip is not installed"
            ),
        ),
        pytest.param(
            "/data/1_4_w_evlr.laz",
            LazBackend.Lazrs,
            marks=pytest.mark.skipif(
                not LazBackend.Lazrs.is_available(), reason="lazrs is not installed"
            ),
        ),
        pytest.param(
            "/data/1_4_w_evlr.laz",
            LazBackend.LazrsParallel,
            marks=pytest.mark.skipif(
                not LazBackend.LazrsParallel.is_available(),
                reason="lazrs is not installed",
            ),
        ),
    ],
)
def test_manually_reading_evlrs(file, backend):
    # The goal is to test we can read evlrs
    # in between reading points, as reading evlrs
    # will require to seek to them, so this is to make sure
    # we correctly reseek to the previous position
    # and that we can continue to read points

    file_with_evlrs = os.path.dirname(__file__) + file
    expected_evlrs = [
        laspy.VLR(
            user_id="pylastest",
            record_id=42,
            description="just a test evlr",
            record_data=b"Test 1 2 ... 1 2",
        )
    ]

    expected_points = laspy.read(file_with_evlrs, laz_backend=backend).points

    with laspy.open(file_with_evlrs, read_evlrs=False, laz_backend=backend) as reader:
        points = laspy.ScaleAwarePointRecord.empty(header=reader.header)

        assert reader.evlrs is None

        chunk_size = 100

        iter = reader.chunk_iterator(chunk_size)
        chunk1 = next(iter)
        assert np.all(chunk1 == expected_points[:chunk_size])

        reader.read_evlrs()
        assert reader.evlrs == expected_evlrs

        for i, chunk in enumerate(iter):
            assert np.all(
                chunk == expected_points[(i + 1) * chunk_size : (i + 2) * chunk_size]
            )


@pytest.mark.parametrize(
    "backend",
    [
        pytest.param(
            laspy.LazBackend.Laszip,
            marks=pytest.mark.skipif(
                not laspy.LazBackend.Laszip.is_available(),
                reason="Laszip not installed",
            ),
        ),
        pytest.param(
            laspy.LazBackend.Lazrs,
            marks=pytest.mark.skipif(
                not laspy.LazBackend.Lazrs.is_available(), reason="lazrs not installed"
            ),
        ),
        pytest.param(
            laspy.LazBackend.LazrsParallel,
            marks=pytest.mark.skipif(
                not laspy.LazBackend.Lazrs.is_available(), reason="lazrs not installed"
            ),
        ),
    ],
)
def test_selective_decompression(backend):
    # We only decompress X,Y, return number, number of returns, intensity
    selection = laspy.DecompressionSelection.base().decompress_intensity()

    simple1_4 = Path(__file__).parent / "data" / "1_4_w_evlr.laz"

    fully_decompressed_laz = laspy.read(simple1_4, laz_backend=backend)
    partially_decompressed_laz = laspy.read(
        simple1_4, laz_backend=backend, decompression_selection=selection
    )

    assert fully_decompressed_laz.point_format.id >= 6

    assert np.all(fully_decompressed_laz.X == partially_decompressed_laz.X)
    assert np.all(fully_decompressed_laz.Y == partially_decompressed_laz.Y)
    assert np.all(
        fully_decompressed_laz.return_number == partially_decompressed_laz.return_number
    )
    assert np.all(
        fully_decompressed_laz.number_of_returns
        == partially_decompressed_laz.number_of_returns
    )
    assert np.all(
        fully_decompressed_laz.intensity == partially_decompressed_laz.intensity
    )

    # This is the chunk size of the chunks inside the .laz
    chunk_size = 50_000
    # In selective decompression, the bytes which are not decompressed are set to the value
    # of the first point of the LAZ chunk
    for i in range((len(fully_decompressed_laz) // chunk_size) + 1):
        start, end = i, (i + 1) * chunk_size
        assert np.all(
            # 12
            fully_decompressed_laz.classification[start]
            == partially_decompressed_laz.classification[start:end]
        )
        assert np.all(
            fully_decompressed_laz.Z[start] == partially_decompressed_laz.Z[start:end]
        )
