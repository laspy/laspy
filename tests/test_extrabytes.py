"""
Tests related to extra bytes
"""

import numpy as np
import pytest

import laspy
from laspy.lib import write_then_read_again
from tests.conftest import UNREGISTERED_EXTRA_BYTES_LAS, EXTRA_BYTES_LAS_FILE_PATH, SIMPLE_LAS_FILE_PATH


def test_read_example_extra_bytes_las(las_file_path_with_extra_bytes):
    """
    Test that we can read the files with extra bytes with have as examples
    """
    las = laspy.read(las_file_path_with_extra_bytes)
    expected_names = [
        "Colors",
        "Reserved",
        "Flags",
        "Intensity",
        "Time",
    ]
    assert expected_names == list(las.point_format.extra_dimension_names)


def test_read_write_example_extra_bytes_file(las_file_path_with_extra_bytes):
    """
    Test that we can write extra bytes without problem
    """
    original = laspy.read(las_file_path_with_extra_bytes)
    las = write_then_read_again(original)

    for name in original.point_format.dimension_names:
        assert np.allclose(las[name], original[name])


def test_adding_extra_bytes_keeps_values_of_all_existing_fields(
        extra_bytes_params, simple_las_path
):
    """
    Test that when extra bytes are added, the existing fields keep their
    values and then we don't somehow drop them
    """
    las = laspy.read(simple_las_path)
    las.add_extra_dim(extra_bytes_params)

    original = laspy.read(simple_las_path)

    for name in original.point_format.dimension_names:
        assert np.allclose(las[name], original[name])


def test_creating_extra_bytes(extra_bytes_params, simple_las_path):
    """
    Test that we can create extra byte dimensions for each
    data type. And they can be written then read.
    """
    las = laspy.read(simple_las_path)
    las.add_extra_dim(extra_bytes_params)

    assert np.allclose(las[extra_bytes_params.name], 0)

    las[extra_bytes_params.name][:] = 42
    assert np.allclose(las[extra_bytes_params.name], 42)

    las = write_then_read_again(las)
    assert np.allclose(las[extra_bytes_params.name], 42)


def test_creating_scaled_extra_bytes(extra_bytes_params, simple_las_path):
    las = laspy.read(simple_las_path)

    if extra_bytes_params.type.ndim == 1:
        num_elements = extra_bytes_params.type.shape[0]
    else:
        num_elements = 1

    params = laspy.ExtraBytesParams(
        extra_bytes_params.name,
        extra_bytes_params.type,
        offsets=np.array([2.0] * num_elements),
        scales=np.array([1.0] * num_elements),
    )
    las.add_extra_dim(params)

    assert np.allclose(las[extra_bytes_params.name], 2.0)

    las[params.name][:] = 42.0
    assert np.allclose(las[extra_bytes_params.name], 42.0)

    las = write_then_read_again(las)
    assert np.allclose(las[extra_bytes_params.name], 42.0)


def test_scaled_extra_byte_array_type(simple_las_path):
    """
    To make sure we handle scaled extra bytes
    """
    las = laspy.read(simple_las_path)

    las.add_extra_dim(
        laspy.ExtraBytesParams(
            name="test_dim",
            type="3int32",
            scales=np.array([1.0, 2.0, 3.0], np.float64),
            offsets=np.array([10.0, 20.0, 30.0], np.float64),
        )
    )

    assert np.allclose(las.test_dim[..., 0], 10.0)
    assert np.allclose(las.test_dim[..., 1], 20.0)
    assert np.allclose(las.test_dim[..., 2], 30.0)

    las.test_dim[..., 0][:] = 42.0
    las.test_dim[..., 1][:] = 82.0
    las.test_dim[..., 2][:] = 123.0

    assert np.allclose(las.test_dim[..., 0], 42.0)
    assert np.allclose(las.test_dim[..., 1], 82.0)
    assert np.allclose(las.test_dim[..., 2], 123.0)

    las = write_then_read_again(las)
    assert np.allclose(las.test_dim[..., 0], 42.0)
    assert np.allclose(las.test_dim[..., 1], 82.0)
    assert np.allclose(las.test_dim[..., 2], 123.0)


def test_extra_bytes_description_is_ok(extra_bytes_params, simple_las_path):
    """
    Test that the description in ok
    """
    las = laspy.read(simple_las_path)
    las.add_extra_dim(extra_bytes_params)

    extra_dim_info = list(las.point_format.extra_dimensions)
    assert len(extra_dim_info) == 1
    assert extra_dim_info[0].description == extra_bytes_params.description

    las = write_then_read_again(las)

    extra_dim_info = list(las.point_format.extra_dimensions)
    assert len(extra_dim_info) == 1
    assert extra_dim_info[0].description == extra_bytes_params.description


def test_extra_bytes_with_spaces_in_name(simple_las_path):
    """
    Test that we can create extra bytes with spaces in their name
    and that they can be accessed using __getitem__ ( [] )
    as de normal '.name' won't work
    """
    las = laspy.read(simple_las_path)
    las.add_extra_dim(laspy.ExtraBytesParams(name="Name With Spaces", type="int32"))

    assert np.alltrue(las["Name With Spaces"] == 0)
    las["Name With Spaces"][:] = 789_464

    las = write_then_read_again(las)
    np.alltrue(las["Name With Spaces"] == 789_464)


def test_conversion_keeps_eb(las_file_path_with_extra_bytes):
    """
    Test that converting point format does not lose extra bytes
    """
    original = laspy.read(las_file_path_with_extra_bytes)
    converted_las = laspy.convert(original, point_format_id=0)

    assert len(list(original.point_format.extra_dimension_names)) == 5
    assert list(converted_las.point_format.extra_dimension_names) == list(
        original.point_format.extra_dimension_names
    )
    for name in converted_las.point_format.extra_dimension_names:
        assert np.allclose(converted_las[name], original[name])

    converted_las = laspy.lib.write_then_read_again(converted_las)
    assert list(converted_las.point_format.extra_dimension_names) == list(
        original.point_format.extra_dimension_names
    )
    for name in converted_las.point_format.extra_dimension_names:
        assert np.allclose(converted_las[name], original[name])


def test_creating_bytes_with_name_too_long(simple_las_path):
    """
    Test error thrown when creating extra bytes with a name that is too long
    """
    las = laspy.read(simple_las_path)
    with pytest.raises(ValueError) as error:
        las.add_extra_dim(
            laspy.ExtraBytesParams(
                name="Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed non risus",
                type="int32",
            )
        )

    assert str(error.value) == "bytes too long (70, maximum length 32)"


def test_creating_bytes_with_description_too_long(simple_las_path):
    """
    Test error thrown when creating extra bytes with a name that is too long
    """
    las = laspy.read(simple_las_path)
    with pytest.raises(ValueError) as error:
        las.add_extra_dim(
            laspy.ExtraBytesParams(
                name="a fine name",
                type="int32",
                description="Lorem ipsum dolor sit amet, consectetur adipiscing elit."
                            " Sed non risus",
            )
        )

    assert str(error.value) == "bytes too long (70, maximum length 32)"


def test_creating_extra_byte_with_invalid_type(simple_las_path):
    """
    Test the error message when creating extra bytes with invalid type
    """
    las = laspy.read(simple_las_path)
    with pytest.raises(TypeError):
        las.add_extra_dim(laspy.ExtraBytesParams("just_a_test", "i16"))


def test_cant_create_scaled_extra_bytes_without_both_offsets_and_scales():
    las = laspy.create()
    with pytest.raises(ValueError):
        las.add_extra_dim(
            laspy.ExtraBytesParams("must fail", "int64", scales=np.array([0.1]))
        )

    with pytest.raises(ValueError):
        las.add_extra_dim(
            laspy.ExtraBytesParams("must fail", "int64", offsets=np.array([0.1]))
        )


@pytest.mark.parametrize("num_elements", [1, 2, 3])
def test_cant_create_scaled_extra_bytes_with_offsets_array_smaller(num_elements):
    las = laspy.create()
    with pytest.raises(ValueError) as error:
        las.add_extra_dim(
            laspy.ExtraBytesParams(
                "must fail",
                f"{num_elements}int64",
                scales=np.array([0.1] * num_elements),
                offsets=np.array([0.0] * (num_elements - 1)),
            )
        )
    assert (
            str(error.value)
            == f"len(offsets) ({num_elements - 1}) is not the same as the number of elements ({num_elements})"
    )


@pytest.mark.parametrize("num_elements", [1, 2, 3])
def test_cant_create_scaled_extra_bytes_with_scales_array_smaller(num_elements):
    las = laspy.create()
    with pytest.raises(ValueError) as error:
        las.add_extra_dim(
            laspy.ExtraBytesParams(
                "must fail",
                f"{num_elements}int64",
                scales=np.array([0.1] * (num_elements - 1)),
                offsets=np.array([0.0] * num_elements),
            )
        )
    assert (
            str(error.value)
            == f"len(scales) ({num_elements - 1}) is not the same as the number of elements ({num_elements})"
    )


def test_handle_unregistered_extra_bytes():
    # Test that if the point size in the header is bigger
    # than the expected point size of the point format
    # and no extra bytes vlr is present, we can still read and
    # write the file

    def check_file(las):
        assert las.point_format.id == 6
        assert las.point_format.size == 34
        assert las.point_format.num_extra_bytes == 4
        assert np.all(las.x == np.array([1, 2, 3, 4]))
        assert np.all(las.y == np.array([1, 2, 3, 4]))
        assert np.all(las.z == np.array([1, 2, 3, 4]))
        assert list(las.point_format.extra_dimension_names) == ["ExtraBytes"]
        assert las.vlrs == []

    las = laspy.read(UNREGISTERED_EXTRA_BYTES_LAS)
    check_file(las)

    las = laspy.lib.write_then_read_again(las)
    check_file(las)


def test_remove_standard_dimension_fails():
    """
    Test we cannot remove non-extra dimension
    """
    las = laspy.read(SIMPLE_LAS_FILE_PATH)
    for name in las.point_format.standard_dimension_names:
        with pytest.raises(laspy.LaspyException):
            las.remove_extra_dims(name)


def test_remove_all_extra_dimensions():
    """
    Test that if we remove all extra bytes of a file,
    the values of standard fields are not altered

    This also test that writing files from which we deleted extra bytes works
    """
    las = laspy.read(EXTRA_BYTES_LAS_FILE_PATH)

    extra_dimension_names = list(las.point_format.extra_dimension_names)
    assert len(extra_dimension_names) > 0, "If the input file has no extra dimension, " \
                                           "this test is useless"

    copied_standard_values = [(name, np.copy(las[name])) for name in las.point_format.standard_dimension_names]

    las.remove_extra_dims(extra_dimension_names)

    for name, copied_value in copied_standard_values:
        assert np.all(las[name] == copied_value)

    new_las = laspy.lib.write_then_read_again(las)
    assert new_las.point_format == las.point_format
    for name, copied_value in copied_standard_values:
        assert np.all(new_las[name] == copied_value)


def test_remove_some_extra_dimensions():
    """
    Test that if we remove some extra bytes of a file,
    the values of standard fields as well as kept extra bytes are not altered

    This also test that writing files from which we deleted extra bytes works
    """
    las = laspy.read(EXTRA_BYTES_LAS_FILE_PATH)

    extra_dimension_names = list(las.point_format.extra_dimension_names)
    assert len(extra_dimension_names) > 0, "If the input file has no extra dimension, " \
                                           "this test is useless"

    extra_dimensions_to_keep = ["Colors", "Time"]
    dims_to_copy = list(las.point_format.standard_dimension_names) + extra_dimensions_to_keep
    copied_standard_values = [(name, np.copy(las[name])) for name in dims_to_copy]

    extra_dims_to_remove = [name for name in las.point_format.extra_dimension_names if
                            name not in extra_dimensions_to_keep]

    las.remove_extra_dims(extra_dims_to_remove)

    for name, copied_value in copied_standard_values:
        assert np.all(las[name] == copied_value)

    new_las = laspy.lib.write_then_read_again(las)
    assert new_las.point_format == las.point_format
    for name, copied_value in copied_standard_values:
        assert np.all(new_las[name] == copied_value)
