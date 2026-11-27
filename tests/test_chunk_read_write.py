"""
Tests related to the 'chunked' reading and writing
"""

import io
import math
from pathlib import Path

import numpy as np
import pytest

import laspy
from laspy.vlrs.known import WktCoordinateSystemVlr
from laspy.vlrs.vlrlist import VLRList

try:
    import pyproj
except ModuleNotFoundError:
    pyproj = None


def check_chunked_reading_gives_expected_points(
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


def test_chunked_las_reading_gives_expected_points(las_file_path):
    """
    Test chunked LAS reading
    """
    with laspy.open(las_file_path) as las_reader:
        with laspy.open(las_file_path) as reader:
            las = las_reader.read()
            check_chunked_reading_gives_expected_points(las, reader, iter_size=50)


def test_chunked_laz_reading_gives_expected_points(laz_file_path, laz_backend):
    """
    Test LAZ reading in chunked mode with different backends
    """
    with laspy.open(laz_file_path) as las_reader:
        with laspy.open(laz_file_path, laz_backend=laz_backend) as laz_reader:
            expected_las = las_reader.read()
            check_chunked_reading_gives_expected_points(
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
            check_chunked_reading_gives_expected_points(original_las, reader, iter_size)


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
    check_chunked_reading_gives_expected_points(ground_truth_las, reader, 42)


def _stream_copy(source_path, dest, extra=None):
    with laspy.open(source_path) as reader:
        with laspy.open(dest, mode="w", header=reader.header, closefd=False) as writer:
            for points in reader.chunk_iterator(50):
                writer.write_points(points)
            if extra is not None:
                extra(writer)


def test_chunked_writing_preserves_header_evlrs():
    """
    EVLRs carried by the header given to the streaming writer must be
    written when the writer is closed, without an explicit write_evlrs call.
    """
    source_path = Path(__file__).parent / "data" / "1_4_w_evlr.las"
    original_las = laspy.read(source_path)
    assert len(original_las.header.evlrs) == 1

    mem_dest = io.BytesIO()
    _stream_copy(source_path, mem_dest)

    mem_dest.seek(0)
    written_las = laspy.read(mem_dest)
    assert written_las.header.number_of_evlrs == 1
    assert written_las.header.evlrs == original_las.header.evlrs


def test_chunked_writing_does_not_duplicate_explicitly_written_evlrs():
    """
    When the caller already called write_evlrs, close() must not write
    the header's EVLRs a second time.
    """
    source_path = Path(__file__).parent / "data" / "1_4_w_evlr.las"

    explicit_evlr = laspy.VLR(
        user_id="pylastest",
        record_id=43,
        description="explicitly written evlr",
        record_data=b"written explicitly",
    )

    mem_dest = io.BytesIO()
    _stream_copy(
        source_path,
        mem_dest,
        extra=lambda writer: writer.write_evlrs(VLRList([explicit_evlr])),
    )

    mem_dest.seek(0)
    written_las = laspy.read(mem_dest)
    assert written_las.header.number_of_evlrs == 1
    assert written_las.header.evlrs == [explicit_evlr]


@pytest.mark.skipif(pyproj is None, reason="pyproj not installed")
def test_chunked_writing_preserves_crs_stored_in_evlr(tmp_path):
    """
    A CRS stored in an EVLR (the only CRS record, with the header's
    WKT global-encoding bit set) must survive a streaming copy:
    parse_crs() on the output must not return None.
    """
    crs = pyproj.CRS.from_epsg(2903)

    header = laspy.LasHeader(point_format=6, version="1.4")
    header.offsets = np.array([0.0, 0.0, 0.0])
    header.scales = np.array([0.001, 0.001, 0.001])
    source_las = laspy.LasData(header=header)
    source_las.x = np.array([1.0, 2.0, 3.0])
    source_las.y = np.array([1.0, 2.0, 3.0])
    source_las.z = np.array([1.0, 2.0, 3.0])
    source_las.evlrs = VLRList([WktCoordinateSystemVlr(wkt_string=crs.to_wkt())])
    source_las.header.global_encoding.wkt = True
    source_path = tmp_path / "crs_in_evlr.las"
    source_las.write(source_path)

    mem_dest = io.BytesIO()
    _stream_copy(source_path, mem_dest)

    mem_dest.seek(0)
    written_las = laspy.read(mem_dest)
    assert written_las.header.global_encoding.wkt
    assert written_las.header.number_of_evlrs == 1
    parsed_crs = written_las.header.parse_crs()
    assert parsed_crs is not None
    assert parsed_crs.to_epsg() == 2903
