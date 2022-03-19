"""
Tests related to the 'chunked' reading and writing
"""
import io
import math

import numpy as np
import pytest

import laspy


def test_chunked_las_reading_gives_expected_points(las_file_path):
    """
    Test chunked LAS reading
    """
    with laspy.open(las_file_path) as las_reader:
        with laspy.open(las_file_path) as reader:
            las = las_reader.read()
            check_chunked_reading_is_gives_expected_points(las, reader, iter_size=50)


def test_chunked_laz_reading_gives_expected_points(laz_file_path, laz_backend):
    """
    Test LAZ reading in chunked mode with different backends
    """
    with laspy.open(laz_file_path) as las_reader:
        with laspy.open(laz_file_path, laz_backend=laz_backend) as laz_reader:
            expected_las = las_reader.read()
            check_chunked_reading_is_gives_expected_points(
                expected_las, laz_reader, iter_size=50
            )


@pytest.mark.parametrize("backend", laspy.LazBackend.detect_available() + (None,))
def test_chunked_writing_gives_expected_points(file_path, backend):
    """
    Write in chunked mode then test that the points are correct
    """
    original_las = laspy.read(file_path)
    iter_size = 51

    do_compress = True if backend is not None else False

    with io.BytesIO() as tmp_output:
        with laspy.open(
            tmp_output,
            mode="w",
            closefd=False,
            header=original_las.header,
            do_compress=do_compress,
            laz_backend=backend,
        ) as las:
            for i in range(int(math.ceil(len(original_las.points) / iter_size))):
                original_points = original_las.points[
                    i * iter_size : (i + 1) * iter_size
                ]
                las.write_points(original_points)

        tmp_output.seek(0)
        with laspy.open(tmp_output, closefd=False) as reader:
            check_chunked_reading_is_gives_expected_points(
                original_las, reader, iter_size
            )


def check_chunked_reading_is_gives_expected_points(
    groundtruth_las: laspy.LasData, reader: laspy.LasReader, iter_size: int
):
    """Checks that the points read by the reader are the same as groundtruth points."""
    assert groundtruth_las.point_format == reader.header.point_format
    for i, points in enumerate(reader.chunk_iterator(iter_size)):
        expected_points = groundtruth_las.points[i * iter_size : (i + 1) * iter_size]
        for dim_name in points.array.dtype.names:
            assert np.allclose(
                expected_points[dim_name], points[dim_name]
            ), f"{dim_name} not equal"


@pytest.mark.parametrize("backend", laspy.LazBackend.detect_available() + (None,))
def test_chunked_dimension_modification(file_path, backend):
    """
    Test that when using chunked mode, if we modify the values in the chunks
    before writing them the values are actually modified.
    """

    mem_dest = io.BytesIO()

    # Read of file in chunked mode modify some values before writing them
    # to a new file
    with laspy.open(file_path, laz_backend=backend) as reader:
        with laspy.open(
            mem_dest, mode="w", laz_backend=backend, header=reader.header, closefd=False
        ) as dest:
            for points in reader.chunk_iterator(50):
                # try a sub field
                points.classification += 1
                # try a normal field
                points.user_data += 2
                # try a scaled field
                points.x += 10.0

                dest.write_points(points)

    mem_dest.seek(0)

    # Prepare out ground truth
    ground_truth_las = laspy.read(file_path)
    ground_truth_las.classification += 1
    ground_truth_las.user_data += 2
    ground_truth_las.x += 10.0

    reader = laspy.open(mem_dest, laz_backend=backend)
    check_chunked_reading_is_gives_expected_points(ground_truth_las, reader, 42)
