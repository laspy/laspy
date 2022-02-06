from pathlib import Path

import numpy as np
import pytest

import laspy
from laspy.lib import write_then_read_again
from . import conftest

simple_las = conftest.SIMPLE_LAS_FILE_PATH
simple_laz = conftest.SIMPLE_LAZ_FILE_PATH
vegetation1_3_las = conftest.VEGETATION1_3_LAS_FILE_PATH
test1_4_las = conftest.TEST1_4_LAS_FILE_PATH
extra_bytes_las = conftest.EXTRA_BYTES_LAS_FILE_PATH
extra_bytes_laz = conftest.EXTRA_BYTES_LAZ_FILE_PATH
plane_laz = conftest.PLANE_LAZ_FILE_PATH
autzen_las = conftest.AUTZEN_FILE_PATH

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
            "lol", "uint64", scales=np.array([2.0]), offsets=np.array([0.0])
        )
    )

    new_values = np.ones(len(las.points)) * 4
    las.lol = new_values

    assert np.allclose(las.lol, new_values)


def test_laspy_file_raises():
    with pytest.raises(laspy.errors.LaspyException):
        laspy.file.File("some path")


def test_lasdata_setitem_xyz_with_2d_array():
    las = laspy.read(simple_las)

    xyz = np.ones(len(las), dtype='3f8')
    xyz[..., 1] = 2.0
    xyz[..., 2] = 3.0

    las[['x', 'y', 'z']] = xyz

    assert np.all(las.x == xyz[..., 0])
    assert np.all(las.y == xyz[..., 1])
    assert np.all(las.z == xyz[..., 2])


def test_lasdata_setitem_xyz_with_structured_array():
    las = laspy.read(simple_las)

    xyz = np.ones(len(las), dtype=[('x', 'f8'), ('y', 'f8'), ('z', 'f8')])
    xyz['y'] = 2.0
    xyz['z'] = 3.0

    las[['x', 'y', 'z']] = xyz

    assert np.all(las.x == xyz['x'])
    assert np.all(las.y == xyz['y'])
    assert np.all(las.z == xyz['z'])


def test_lasdata_setitem_one_dimension():
    las = laspy.read(simple_las)

    las[['x']] = np.ones(len(las), 'f8') * 17.0
    assert np.all(las.x == 17.0)


def test_lasdata_setitem_works_with_subfields():
    las = laspy.read(simple_las)

    new_values = np.ones(len(las), dtype=[('classification', 'u1'), ('return_number', 'u1')])
    new_values['classification'] = 23
    new_values['return_number'] = 2

    las[['classification', 'return_number']] = new_values
    assert np.all(las.classification == 23)
    assert np.all(las.return_number == 2)


def test_las_data_getitem_indices():
    las = laspy.read(simple_las)
    las.classification[:] = 0

    indices = np.array([1, 2, 3, 4])
    sliced_las = las[indices]
    sliced_las.classification[:] = 1

    assert np.all(sliced_las.classification == 1)
    # We expect sliced_las to give us a copy,
    # So original las is no modified
    assert np.all(las.classification == 0)


def test_las_data_getitem_slice():
    las = laspy.read(simple_las)
    las.classification[:] = 0

    sliced_las = las[0:10]
    sliced_las.classification[:] = 1

    assert np.all(sliced_las.classification == 1)
    # Slicing does not trigger, advanced indexing
    # so the underlying array is not a copy
    # https://numpy.org/doc/stable/reference/arrays.indexing.html
    assert np.all(las.classification[:10] == 1)
    assert np.all(las.classification[10:] == 0)


def test_change_scaling():
    """ Check our change scaling method.

    We expect the scaled x,y,z not to change
    while the unscaled (integers) X,Y,Z should change.
    """
    hdr = laspy.LasHeader()
    hdr.offsets = np.array([0.0, 0.0, 0.0])
    hdr.scales = np.array([1.0, 1.0, 1.0])

    las = laspy.LasData(hdr)

    las['x'] = np.array([1, 2, 3, 4])
    las['y'] = np.array([1, 2, 3, 4])
    las['z'] = np.array([1, 2, 3, 4])

    assert np.all(las.x == [1, 2, 3, 4])
    assert np.all(las.y == [1, 2, 3, 4])
    assert np.all(las.z == [1, 2, 3, 4])

    assert np.all(las.X == [1, 2, 3, 4])
    assert np.all(las.Y == [1, 2, 3, 4])
    assert np.all(las.Z == [1, 2, 3, 4])

    saved_offsets = las.header.offsets.copy()
    las.change_scaling(scales=[0.5, 0.1, 0.01])

    assert np.all(las.header.scales == [0.5, 0.1, 0.01])
    assert np.all(las.header.offsets == saved_offsets)

    assert np.all(las.x == [1, 2, 3, 4])
    assert np.all(las.y == [1, 2, 3, 4])
    assert np.all(las.z == [1, 2, 3, 4])

    assert np.all(las.X == [2, 4, 6, 8])
    assert np.all(las.Y == [10, 20, 30, 40])
    assert np.all(las.Z == [100, 200, 300, 400])

    saved_scales = las.header.scales.copy()
    las.change_scaling(offsets=[1, 20, 30])

    assert np.all(las.header.scales == saved_scales)
    assert np.all(las.header.offsets == [1, 20, 30])

    assert np.all(las.x == [1, 2, 3, 4])
    assert np.all(las.y == [1, 2, 3, 4])
    assert np.all(las.z == [1, 2, 3, 4])

    assert np.all(las.X == [0, 2, 4, 6])
    assert np.all(las.Y == [-190, -180, -170, -160])
    assert np.all(las.Z == [-2900, -2800, -2700, -2600])


def test_setting_x_y_z_on_las_data():
    """
    The goal of this test if to make sure that when setting the `x`,`y` and `z`
    attribute of a LasData object, the X,Y,Z version of the coordinates
    are properly set in the inner point record
    """
    las = laspy.read(simple_las)

    new_las = laspy.create()

    new_las.x = las.x
    new_las.y = las.y
    new_las.z = las.z

    assert np.all(new_las.x == las.x)
    assert np.all(new_las.X == las.X)
    assert np.all(new_las.y == las.y)
    assert np.all(new_las.Y == las.Y)
    assert np.all(new_las.z == las.z)
    assert np.all(new_las.Z == las.Z)


    new_las = laspy.lib.write_then_read_again(new_las)

    assert np.all(new_las.x == las.x)
    assert np.all(new_las.X == las.X)
    assert np.all(new_las.y == las.y)
    assert np.all(new_las.Y == las.Y)
    assert np.all(new_las.z == las.z)
    assert np.all(new_las.Z == las.Z)


def test_setting_xyz_on_las_data():
    """
    The goal of this test if to make sure that when setting the `xyz`
    attribute of a LasData object, the X,Y,Z version of the coordinates
    are properly set in the inner point record
    """
    las = laspy.read(simple_las)

    new_las = laspy.create()

    new_las.xyz = las.xyz

    assert np.all(new_las.x == las.x)
    assert np.all(new_las.X == las.X)
    assert np.all(new_las.y == las.y)
    assert np.all(new_las.Y == las.Y)
    assert np.all(new_las.z == las.z)
    assert np.all(new_las.Z == las.Z)

    new_las = laspy.lib.write_then_read_again(new_las)

    assert np.all(new_las.x == las.x)
    assert np.all(new_las.X == las.X)
    assert np.all(new_las.y == las.y)
    assert np.all(new_las.Y == las.Y)
    assert np.all(new_las.z == las.z)
    assert np.all(new_las.Z == las.Z)
