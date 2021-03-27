from pathlib import Path

import numpy as np
import pytest

import laspy
from laspy.lib import write_then_read_again

simple_las = Path(__file__).parent / "simple.las"
simple_laz = Path(__file__).parent / "simple.laz"
vegetation1_3_las = Path(__file__).parent / "vegetation_1_3.las"
test1_4_las = Path(__file__).parent / "test1_4.las"
extra_bytes_las = Path(__file__).parent / "extrabytes.las"
extra_bytes_laz = Path(__file__).parent / "extra.laz"
plane_laz = Path(__file__).parent / "plane.laz"

if not laspy.LazBackend.detect_available():
    do_compression = [False]
    all_file_paths = [simple_las, vegetation1_3_las, test1_4_las, extra_bytes_las]
else:
    do_compression = [False, True]
    all_file_paths = [
        simple_las,
        simple_laz,
        vegetation1_3_las,
        test1_4_las,
        plane_laz,
        extra_bytes_laz,
        extra_bytes_las,
    ]


@pytest.fixture(params=all_file_paths)
def las(request):
    return laspy.read(request.param)


@pytest.fixture(params=[simple_las, vegetation1_3_las])
def all_las_but_1_4(request):
    return laspy.read(request.param)


@pytest.fixture(params=[simple_las, vegetation1_3_las, test1_4_las, extra_bytes_las])
def las_path_fixture(request):
    return request.param


@pytest.fixture(params=[simple_laz, extra_bytes_laz, plane_laz])
def all_laz_path(request):
    return request.param


def dim_does_not_exists(las, dim_name):
    try:
        _ = getattr(las, dim_name)
    except AttributeError:
        return True
    return False


def dim_does_exists(las, dim_name):
    try:
        _ = getattr(las, dim_name)
    except AttributeError:
        return False
    return True


def test_change_format(las):
    in_version = las.header.version

    las = laspy.convert(las, point_format_id=2)
    las = write_then_read_again(las)
    assert las.points.point_format.id == 2
    assert las.header.point_format.id == 2
    assert las.header.version == in_version
    assert dim_does_not_exists(las, "gps_time")

    las = laspy.convert(las, point_format_id=1)
    las = write_then_read_again(las)
    assert las.points.point_format.id == 1
    assert las.header.point_format.id == 1
    assert las.header.version == in_version
    assert dim_does_not_exists(las, "red")
    assert dim_does_not_exists(las, "green")
    assert dim_does_not_exists(las, "blue")

    las = laspy.convert(las, point_format_id=0)
    las = write_then_read_again(las)
    assert las.points.point_format.id == 0
    assert las.header.point_format.id == 0
    assert las.header.version == in_version
    assert dim_does_not_exists(las, "red")
    assert dim_does_not_exists(las, "green")
    assert dim_does_not_exists(las, "blue")
    assert dim_does_not_exists(las, "gps_time")

    las = laspy.convert(las, point_format_id=8)
    las = write_then_read_again(las)
    assert str(las.header.version) == "1.4"
    assert las.points.point_format.id == 8
    assert las.header.point_format.id == 8
    assert dim_does_exists(las, "red")
    assert dim_does_exists(las, "green")
    assert dim_does_exists(las, "blue")
    assert dim_does_exists(las, "nir")

    las = laspy.convert(las, point_format_id=7)
    las = write_then_read_again(las)
    assert str(las.header.version) == "1.4"
    assert las.points.point_format.id == 7
    assert las.header.point_format.id == 7
    assert dim_does_exists(las, "red")
    assert dim_does_exists(las, "green")
    assert dim_does_exists(las, "blue")
    assert dim_does_not_exists(las, "nir")

    las = laspy.convert(las, point_format_id=6)
    las = write_then_read_again(las)
    assert str(las.header.version) == "1.4"
    assert las.points.point_format.id == 6
    assert las.header.point_format.id == 6
    assert dim_does_not_exists(las, "red")
    assert dim_does_not_exists(las, "green")
    assert dim_does_not_exists(las, "blue")
    assert dim_does_not_exists(las, "nir")


def test_rw_all_set_one(las):
    for dim_name in las.point_format.dimension_names:
        las[dim_name][:] = 1

    for dim_name in las.point_format.dimension_names:
        assert np.alltrue(las[dim_name] == 1), "{} not equal".format(dim_name)

    las2 = write_then_read_again(las)

    for dim_name in las.point_format.dimension_names:
        assert np.alltrue(las[dim_name] == las2[dim_name]), "{} not equal".format(
            dim_name
        )


def test_coords_do_not_break(las):
    xs, ys, zs = las.x, las.y, las.z

    las.x = xs
    las.y = ys
    las.z = zs

    assert np.allclose(xs, las.x)
    assert np.allclose(ys, las.y)
    assert np.allclose(zs, las.z)


def test_coords_when_setting_offsets_and_scales(las):
    new_las = laspy.create()

    new_las.header.offsets = las.header.offsets
    new_las.header.scales = las.header.scales

    new_las.x = las.x
    new_las.y = las.y
    new_las.z = las.z

    assert np.allclose(las.x, new_las.x)
    assert np.allclose(las.y, new_las.y)
    assert np.allclose(las.z, new_las.z)


def test_coords_when_using_create_from_header(las):
    new_las = laspy.LasData(las.header)

    new_las.x = las.x
    new_las.y = las.y
    new_las.z = las.z

    assert np.allclose(las.x, new_las.x)
    assert np.allclose(las.y, new_las.y)
    assert np.allclose(las.z, new_las.z)


def test_slicing(las):
    las.points = las.points[len(las.points) // 2:]


@pytest.mark.parametrize("do_compress", do_compression)
def test_can_write_then_re_read_files(las, do_compress):
    _las = write_then_read_again(las, do_compress=do_compress)


def test_point_record_setitem_scaled_view():
    las = laspy.read(simple_las)
    las.add_extra_dim(
        laspy.ExtraBytesParams(
            'lol',
            'uint64',
            scales=np.array([2.0]),
            offsets=np.array([0.0])
        )
    )

    new_values = np.ones(len(las.points)) * 4
    las.lol = new_values

    assert np.allclose(las.lol, new_values)
