import numpy as np
import pytest

import laspy
from laspy.point.dims import SubFieldView, ScaledArrayView


def test_sub_field_view_behaves_like_array():
    """ This function is used to test if the SubFieldView class
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


def test_scaled_array_view():
    array = np.zeros(10, np.int32)
    x = ScaledArrayView(array, 0.01, 10)

    assert np.max(x) == 10.0
    assert np.min(x) == 10.0

    assert np.all(x > 0.0)
    assert np.all(x < 18.0)
    assert np.all(x == 10.0)
    assert np.all(x != 17.0)

    assert np.mean(x) == 10.0

    x[:] = 155.0
    x[9] = 42.0
    assert np.all(x[2:5] == 155.0)
    assert x[9] == 42.0
