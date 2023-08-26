import numpy as np
import pytest

import laspy

from ..test_common import skip_if_no_laz_backend
from . import skip_if_cli_deps_are_not_installed

skip_if_cli_deps_are_not_installed()

pytestmark = skip_if_no_laz_backend

from typer.testing import CliRunner

runner = CliRunner()
from laspy.cli.core import app


def test_cli_compress(tmp_path):
    input_path = "tests/data/simple.las"
    output_path = tmp_path / "simple.laz"
    result = runner.invoke(
        app,
        [
            "compress",
            input_path,
            "--output-path",
            str(output_path),
        ],
    )
    assert result.exit_code == 0, "{}".format(result.stdout)

    with laspy.open(output_path) as f:
        assert f.header.are_points_compressed is True

    original_las = laspy.read(input_path)
    compressed_las = laspy.read(output_path)

    assert original_las.point_format == compressed_las.point_format
    assert original_las.vlrs == compressed_las.vlrs
    assert np.all(original_las.points == compressed_las.points)


def test_cli_compress_cannot_overwrite(tmp_path):
    input_path = "tests/data/simple.las"
    output_path = tmp_path / "simple.laz"
    result = runner.invoke(
        app,
        [
            "compress",
            input_path,
            "--output-path",
            input_path,
        ],
    )
    assert result.exit_code != 0, "{}".format(result.stdout)


def test_cli_compress_non_existing_file(tmp_path):
    input_path = "tests/data/i-do-not-exist.las"
    output_path = tmp_path / "i-do-not-exist.laz"
    result = runner.invoke(
        app,
        [
            "compress",
            input_path,
            "--output-path",
            str(output_path),
        ],
    )
    assert result.exit_code != 0, "{}".format(result.stdout)


def test_cli_decompress(tmp_path):
    input_path = "tests/data/simple.laz"
    output_path = tmp_path / "simple.las"
    result = runner.invoke(
        app,
        [
            "decompress",
            input_path,
            "--output-path",
            str(output_path),
        ],
    )
    assert result.exit_code == 0, "{}".format(result.stdout)

    with laspy.open(output_path) as f:
        assert f.header.are_points_compressed is False

    original_las = laspy.read(input_path)
    compressed_las = laspy.read(output_path)

    assert original_las.point_format == compressed_las.point_format
    assert original_las.vlrs == compressed_las.vlrs
    assert np.all(original_las.points == compressed_las.points)


def test_cli_decompress_cannot_overwrite(tmp_path):
    input_path = "tests/data/simple.laz"
    output_path = tmp_path / "simple.las"
    result = runner.invoke(
        app,
        [
            "decompress",
            input_path,
            "--output-path",
            input_path,
        ],
    )
    assert result.exit_code != 0, "{}".format(result.stdout)


def test_cli_decompress_non_existing_file(tmp_path):
    input_path = "tests/data/i-do-not-exist.laz"
    output_path = tmp_path / "i-do-not-exist.las"
    result = runner.invoke(
        app,
        [
            "decompress",
            input_path,
            "--output-path",
            str(output_path),
        ],
    )
    assert result.exit_code != 0, "{}".format(result.stdout)
