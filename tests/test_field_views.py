import numpy as np
import pytest

import laspy
from laspy.point.dims import SubFieldView, ScaledArrayView


def test_sub_field_view_behaves_like_array():
    """This function is used to test if the SubFieldView class
    works & has an API that is similar to np.ndarray
    """
    array = np.zeros(10, np.uint8)

    field = SubFieldView(array, 0b0000_0010)

    assert len(field) == 10
    assert np.all(field == 0)
    assert np.all(field[:] == 0)

    assert field.max() == 0
    assert np.max(field) == 0
    assert field.min() == 0
    assert np.min(field) == 0
    assert np.min(field) == field.min()
    assert np.max(field) == field.max()

    field[:] = 1
    assert np.all(field == 1)
    assert np.all(field[:] == 1)

    assert field.max() == 1
    assert np.max(field) == 1
    assert field.min() == 1
    assert np.min(field) == 1

    assert np.all(field > 0)
    assert not np.all(field < 0)
    assert np.all(field >= 1)
    assert np.all(field <= 1)

    # check that the real array is properly modified
    assert np.all(array == 2)

    with pytest.raises(OverflowError):
        field[4] = 2

    assert np.mean(field) == 1


def test_array_view_int_index_return_singular_elements():
    a = np.array([1, 2, 3, 4], np.int32)
    s = SubFieldView(a, 0x00_00_00_FF)

    for i in range(len(s)):
        assert type(s[i]) in (np.int32, np.int64)
        assert a[i] == s[i]

    s = ScaledArrayView(a, scale=2.0, offset=0.0)
    for i in range(len(s)):
        assert type(s[i]) == np.float64
        assert (a[i] * 2.0) == s[i]


def test_scaled_array_view_ellipsis_indexing(simple_las_path):
    las = laspy.read(simple_las_path)

    las.add_extra_dim(
        laspy.ExtraBytesParams(
            name="test_dim",
            type="3int32",
            scales=np.array([1.0, 2.0, 3.0], np.float64),
            offsets=np.array([10.0, 20.0, 30.0], np.float64),
        )
    )

    # Query all the points in the 2nd dimension
    assert np.all(las.test_dim[..., 2] == 30.0)

    # Query the 10 nth point, we expect all its dimensions
    assert np.all(las.test_dim[10, ...] == [10.0, 20.0, 30.0])


def test_scaled_array_view_indexing_with_array_or_list(simple_las_path):
    las = laspy.read(simple_las_path)

    las.add_extra_dim(
        laspy.ExtraBytesParams(
            name="test_dim",
            type="3int32",
            scales=np.array([1.0, 2.0, 3.0], np.float64),
            offsets=np.array([10.0, 20.0, 30.0], np.float64),
        )
    )

    d = las.test_dim[[0, 1, 10, 12]]
    assert d.ndim == 2
    assert d.shape == (4, 3)
    assert np.all(d[..., 0] == 10.0)
    assert np.all(d[..., 1] == 20.0)
    assert np.all(d[..., 2] == 30.0)

    d2 = las.test_dim[np.array([0, 1, 10, 12])]
    assert np.all(d == d2)


def test_sub_field_view_with_self(simple_las_path):
    las = laspy.read(simple_las_path)

    rn = np.array(las.return_number)
    order = np.argsort(las.return_number)[::-1]

    las.return_number[:] = las.return_number[order]

    assert np.all(las.return_number == rn[order])


def test_can_use_array_func_with_list(simple_las_path):
    las = laspy.read(simple_las_path)

    np.concatenate([las.return_number, las.classification])
    np.concatenate([las.x, las.y])


def test_sub_field_as_array():
    array = np.zeros(10, np.uint8)
    field = SubFieldView(array, 0b0000_0010)

    cpy = np.array(field)

    cpy[:] = 1
    assert np.all(cpy == 1)
    assert np.all(field != 1)

    cpy[:] = 17

    with pytest.raises(OverflowError):
        field[:] = cpy[:]

    # Here we just test that this can run,
    # We had an error about with our __array__ signature
    cpy[:] = field[:]
    assert np.all(cpy == field)


def test_scaled_array_view():
    array = np.zeros(10, np.int32)
    x = ScaledArrayView(array, 0.01, 10)

    assert np.max(x) == 10.0
    assert np.min(x) == 10.0
    assert np.min(x) == x.min()
    assert np.max(x) == x.max()

    assert np.all(x > 0.0)
    assert np.all(x < 18.0)
    assert np.all(x == 10.0)
    assert np.all(x != 17.0)

    assert np.mean(x) == 10.0

    x[:] = 155.0
    x[9] = 42.0
    assert np.all(x[2:5] == 155.0)
    assert x[9] == 42.0

    with pytest.raises(OverflowError):
        x[8] = np.finfo(np.float64).max


def test_array_views_on_empty_things():
    """
    Test that __setitem__ of the Array views do not fail
    when the value is an empty array / sequence,
    to match the behaviour of numpy array
    """
    array = np.zeros(0, np.int32)
    x = ScaledArrayView(array, 0.01, 10)
    # This shall not fail
    x[:] = np.zeros(0)

    array = np.zeros(0, np.uint8)
    field = SubFieldView(array, 0b0000_0010)
    # This shall not fail
    field[:] = np.zeros(0)


def test_scaled_point_record_set_x_y_z():
    record = laspy.ScaleAwarePointRecord.zeros(
        5, point_format=laspy.PointFormat(3), scales=[1.0] * 3, offsets=[0.0] * 3
    )

    assert np.all(record.x == 0.0)
    assert np.all(record.y == 0.0)
    assert np.all(record.z == 0.0)

    record.x = 17.0
    record.y = 17.12
    record.z = np.array([293090.812739] * len(record))

    assert np.all(record.x == 17.0)
    assert np.all(record.y == 17.12)
    assert np.all(record.z == 293090.812739)
