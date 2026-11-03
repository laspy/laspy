import operator

import numpy as np
import pytest

import laspy
from laspy.point.dims import SubFieldView


@pytest.mark.parametrize("op", [operator.lt, operator.le, operator.gt, operator.ge])
@pytest.mark.parametrize("threshold", [4, 128, -1, np.uint8(128)])
def test_subfield_ordering_matches_decoded_values(op, threshold):
    field = SubFieldView(np.array([0, 2, 4, 6], dtype=np.uint8), 6)
    np.testing.assert_array_equal(
        op(field, threshold), op(np.asarray(field), threshold)
    )


def test_filter_return_numbers_above_field_range():
    points = laspy.create(point_format=0)
    points.return_number = np.array([1, 2, 3], dtype=np.uint8)
    selected = points.points[points.return_number < 8]
    assert len(selected) == 3


def test_subfield_array_thresholds_do_not_overflow_when_shifted():
    field = SubFieldView(np.array([0, 2, 4, 6], dtype=np.uint8), 6)
    thresholds = np.array([128, 128, 128, 128], dtype=np.uint8)
    np.testing.assert_array_equal(field < thresholds, np.ones(4, dtype=bool))
