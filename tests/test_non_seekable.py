import pytest

import laspy
from laspy import VLR

from .conftest import (
    LAS_1_4_WITH_EVLRS_FILE_PATH,
    LAZ_1_4_WITH_EVLRS_FILE_PATH,
    NonSeekableStream,
    las_file_path,
    laz_file_path,
)
from .test_chunk_read_write import check_chunked_reading_gives_expected_points

EXPECTED_EVLRS = [
    VLR(
        user_id="pylastest",
        record_id=42,
        description="just a test evlr",
        record_data=b"Test 1 2 ... 1 2",
    )
]


@pytest.mark.skipif(
    not laspy.LazBackend.Lazrs.is_available(),
    reason="None seekable laz is only supported by lazrs",
)
def test_laz_reading_non_seekable_stream(laz_file_path):
    with open(laz_file_path, mode="rb") as f:
        stream = NonSeekableStream(f)
        laspy.read(stream, closefd=False)


def test_las_reading_non_seekable_stream(las_file_path):
    with open(las_file_path, mode="rb") as f:
        stream = NonSeekableStream(f)
        laspy.read(stream, closefd=False)


@pytest.mark.skipif(
    not laspy.LazBackend.Lazrs.is_available(),
    reason="Non seekable laz is only supported by lazrs",
)
def test_laz_selective_decompression_reading_non_seekable_stream():
    with open(LAZ_1_4_WITH_EVLRS_FILE_PATH, mode="rb") as f:
        stream = NonSeekableStream(f)
        selection = laspy.DecompressionSelection.base()
        las = laspy.read(stream, closefd=False, decompression_selection=selection)
        assert las.evlrs == EXPECTED_EVLRS


@pytest.mark.skipif(
    not laspy.LazBackend.Lazrs.is_available(),
    reason="Non seekable laz is only supported by lazrs",
)
def test_laz_with_evlr_reading_non_seekable_stream():
    with open(LAZ_1_4_WITH_EVLRS_FILE_PATH, mode="rb") as f:
        stream = NonSeekableStream(f)
        las = laspy.read(stream, closefd=False)
        assert las.evlrs == EXPECTED_EVLRS


def test_las_with_evlr_reading_non_seekable_stream(las_file_path):
    with open(LAS_1_4_WITH_EVLRS_FILE_PATH, mode="rb") as f:
        stream = NonSeekableStream(f)
        las = laspy.read(stream, closefd=False)
        assert las.evlrs == EXPECTED_EVLRS


def test_non_seekable_chunked_las_reading(las_file_path):
    ground_truth = laspy.read(las_file_path)
    with open(las_file_path, mode="rb") as raw_file:
        las_reader = laspy.open(NonSeekableStream(raw_file), closefd=False)
        check_chunked_reading_gives_expected_points(
            ground_truth, las_reader, iter_size=130
        )


@pytest.mark.skipif(
    not laspy.LazBackend.Lazrs.is_available(),
    reason="Non seekable laz is only supported by lazrs",
)
def test_non_seekable_chunked_laz_reading(laz_file_path):
    ground_truth = laspy.read(laz_file_path)
    with open(laz_file_path, mode="rb") as raw_file:
        las_reader = laspy.open(NonSeekableStream(raw_file), closefd=False)
        check_chunked_reading_gives_expected_points(
            ground_truth, las_reader, iter_size=130
        )
