import io
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pytest

import laspy
from laspy import LasData, LasHeader, ScaleAwarePointRecord
from tests.conftest import SIMPLE_LAZ_FILE_PATH, NonSeekableStream
from tests.test_common import simple_laz


def test_append(file_path):
    """
    Test appending
    """
    if file_path.suffix == ".laz" and not laspy.LazBackend.Lazrs.is_available():
        pytest.skip("Only Lazrs backed supports appending")
    append_self_and_check(file_path)


def test_raises_for_laszip_backend():
    with pytest.raises(laspy.LaspyException):
        with laspy.open(simple_laz, mode="a", laz_backend=laspy.LazBackend.Laszip):
            ...


def test_append_las_with_evlrs():
    las = append_self_and_check(os.path.dirname(__file__) + "/data/1_4_w_evlr.las")

    expected_evlr = laspy.VLR(
        user_id="pylastest", record_id=42, description="just a test evlr"
    )
    expected_evlr.record_data = b"Test 1 2 ... 1 2"

    assert len(las.evlrs) == 1
    evlr = las.evlrs[0]
    assert evlr.description == expected_evlr.description
    assert evlr.record_id == expected_evlr.record_id
    assert evlr.user_id == expected_evlr.user_id
    assert evlr.record_data == expected_evlr.record_data


@pytest.mark.skipif(
    not laspy.LazBackend.Lazrs.is_available(), reason="Lazrs is not installed"
)
def test_append_laz_with_evlrs():
    las = append_self_and_check(os.path.dirname(__file__) + "/data/1_4_w_evlr.laz")

    expected_evlr = laspy.VLR(
        user_id="pylastest", record_id=42, description="just a test evlr"
    )
    expected_evlr.record_data = b"Test 1 2 ... 1 2"

    assert len(las.evlrs) == 1
    evlr = las.evlrs[0]
    assert evlr.description == expected_evlr.description
    assert evlr.record_id == expected_evlr.record_id
    assert evlr.user_id == expected_evlr.user_id
    assert evlr.record_data == expected_evlr.record_data


def append_self_and_check(las_path_fixture):
    with open(las_path_fixture, mode="rb") as f:
        file = io.BytesIO(f.read())
    las = laspy.read(las_path_fixture)
    with laspy.open(file, mode="a", closefd=False) as laz_file:
        laz_file.append_points(las.points)
    file.seek(0, io.SEEK_SET)
    rlas = laspy.read(file)
    assert rlas.header.point_count == 2 * las.header.point_count
    assert rlas.points[: rlas.header.point_count // 2] == las.points
    assert rlas.points[rlas.header.point_count // 2 :] == las.points

    return rlas


def test_trying_to_append_in_non_seekable_raises():
    with pytest.raises(TypeError):
        with open(simple_laz, mode="rb") as f:
            stream = NonSeekableStream(f)
            with laspy.open(stream, mode="a") as lasf:
                pass


@pytest.mark.parametrize(
    "points_read_counts",
    [
        [-1],
        [1, -1],
        [49_999, -1],
        [50_000, -1],
        [50_001, -1],
    ],
)
@pytest.mark.skipif(
    not laspy.LazBackend.Lazrs.is_available(), reason="Lazrs is not installed"
)
def test_write_then_append_produces_valid_cloud(points_read_counts: List[int]) -> None:
    """
    In this test we read a LAZ file into chunks dictated by `points_read_counts`,
    then we reconstruct it by first writting the first chunk into a new file using write mode
    then we append the remaining chunks to that newly created file.

    At the end the input file and the one we patchworked must be the same
    """

    def iter_points(
        points_list: List[ScaleAwarePointRecord],
    ) -> Tuple[ScaleAwarePointRecord, slice]:
        """
        Returns a tuple that associates each point record in the input list
        with the slice to be used to recover the same chunk from
        the input file.
        """
        offset: int = 0

        for points in points_list:
            yield points, slice(offset, offset + len(points))
            offset += len(points)

    def check_write_append_read(
        points_list: List[ScaleAwarePointRecord], header: LasHeader
    ) -> None:
        """
        Implements the logic of first using write mode for the first
        chunk, then appending the remaining chunks.

        Checks result at the end
        """
        with io.BytesIO() as tmp_output:
            with laspy.open(
                tmp_output, "w", header=header, closefd=False, do_compress=True
            ) as las_writer:
                las_writer.write_points(points_list[0])

            for points in points_list[1:]:
                tmp_output.seek(0)
                if points:
                    with laspy.open(tmp_output, "a", closefd=False) as las_appender:
                        las_appender.append_points(points)

            tmp_output.seek(0)
            final_cloud: LasData = laspy.read(tmp_output)

            for points, selector in iter_points(points_list):
                assert final_cloud.points[selector] == points

    input_cloud_path = Path(__file__).parent / "data" / "autzen_trim.laz"

    with laspy.open(input_cloud_path) as las_reader:
        points_list: List[ScaleAwarePointRecord] = [
            las_reader.read_points(points_read_count)
            for points_read_count in points_read_counts
        ]

    check_write_append_read(points_list, las_reader.header)


@pytest.mark.parametrize(
    "input_file",
    [SIMPLE_LAZ_FILE_PATH, Path(__file__).parent / "data" / "simple1_4.las"],
)
@pytest.mark.skipif(
    not laspy.LazBackend.Lazrs.is_available(), reason="Lazrs is not installed"
)
def test_append_to_empty_file(input_file: Path) -> None:
    """
    Test that one can create an empty LAZ file, and then re-open it to append to it
    """
    laz_backends = laspy.LazBackend.detect_available()
    input_las = laspy.read(input_file)

    for creating_backend in laz_backends:
        for appending_backend in laz_backends:
            if appending_backend == laspy.LazBackend.Laszip:
                continue

            for checking_backend in laz_backends:
                print(
                    f"Creating Backend: {creating_backend},",
                    f"Appending Backend: {appending_backend},",
                    f"Checking Backend: {checking_backend}",
                )
                with tempfile.TemporaryDirectory() as dir_path:
                    dir_path = Path(dir_path)
                    las_path = dir_path / "to_be_appended.laz"

                    header = input_las.header.copy()

                    # Create empty laz
                    with laspy.open(
                        las_path, "w", header=header, laz_backend=creating_backend
                    ) as las_writer:
                        pass

                    # Append points to empty laz
                    with laspy.open(
                        las_path, "a", laz_backend=appending_backend
                    ) as las_appender:
                        las_appender.append_points(input_las.points)

                    # Try to read laz
                    with laspy.open(
                        las_path, "r", laz_backend=checking_backend
                    ) as las_reader:
                        point_count = las_reader.header.point_count
                        points = las_reader.read_points(point_count)
                        assert points == input_las.points


@pytest.mark.skipif(
    not laspy.LazBackend.Lazrs.is_available(), reason="Lazrs is not installed"
)
def test_append_issue_that_requires_passing_point_count():
    """The input file in this test is composed of only one LAZ chunk.

    LazAppend from used to decompress the last chunk until reaching the end
    of its declared bytes.
    However, in this file, the number of declared bytes is such that decompressing
    all of it made laz-rs decompress on more point than expexted.

    This point, which is not a real point, was then written back as part of the
    standard appending preparation, however it was not registered in the point_count
    that laspy was awere of.

    All this lead to the fact that after appending some points and closing the file,
    when reading it back to read the appended points, the first appended point was not
    the one expected but it was the gargabe point mentionned above, and the last appended
    point was not read (although it was in the file, just that the point_count was not correct)

    The fix for this was to make the appenders from laz-rs require the caller (i.e laspy here)
    to give point_count of the file, so that the correct number of points was decompressed
    when doing the appender initialization
    """
    input_las = Path(__file__).parent / "data" / "append-bug.laz"
    output_las = Path(__file__).parent / "data" / "append-bug-cpy.laz"

    # check ini
    las_input = laspy.read(input_las)
    arr_ini = las_input.points.array
    print("\nChecking initial points")
    print("Input ", len(arr_ini), " points total ")
    print("last point input ", arr_ini[len(arr_ini) - 1])

    assert las_input.header.point_count == 37_805

    shutil.copy2(input_las, output_las)
    print("\nAdding points")
    with laspy.open(
        output_las, mode="a", laz_backend=laspy.LazBackend.Lazrs
    ) as las:  # mode `a` for adding points
        new_points = laspy.ScaleAwarePointRecord.zeros(
            2, header=las.header
        )  # use header for input_las
        new_points.classification = [88, 89]
        las.append_points(new_points)

    # Check the result
    las = laspy.read(output_las)
    arr_end = las.points.array
    assert len(arr_end) == 37_807

    assert np.all(arr_end[-2:] == new_points.array)
