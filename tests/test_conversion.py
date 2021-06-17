import numpy as np
import pytest

import laspy
from laspy.lib import write_then_read_again


@pytest.mark.parametrize("target_point_format_id", [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
def test_point_format_conversion_copies_field_values(file_path, target_point_format_id):
    original = laspy.read(file_path)
    converted = laspy.convert(original, point_format_id=target_point_format_id)
    converted = write_then_read_again(converted)

    converted_dimension_names = set(converted.point_format.dimension_names)
    dimension_expected_to_be_kept = [
        dim_name
        for dim_name in original.point_format.dimension_names
        if dim_name in converted_dimension_names
    ]

    for dim_name in dimension_expected_to_be_kept:
        assert np.allclose(
            converted[dim_name], original[dim_name]
        ), "{} not equal".format(dim_name)
