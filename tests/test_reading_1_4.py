import pytest

import laspy
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
