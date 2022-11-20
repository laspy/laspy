import io
import subprocess

import laspy
import pytest
from pathlib import Path
import sys

SIMPLE_COPC_FILE = Path(__file__).parent / "data" / "simple.copc.laz"

try:
    import requests
except ModuleNotFoundError:
    requests = None

try:
    import RangeHTTPServer
except ModuleNotFoundError:
    RangeHTTPServer = None


@pytest.mark.parametrize(
    "backend",
    [
        pytest.param(
            laspy.LazBackend.Laszip,
            marks=pytest.mark.skipif("not laspy.LazBackend.Laszip.is_available()"),
        ),
        pytest.param(
            laspy.LazBackend.Lazrs,
            marks=pytest.mark.skipif("not laspy.LazBackend.Lazrs.is_available()"),
        ),
        pytest.param(
            laspy.LazBackend.LazrsParallel,
            marks=pytest.mark.skipif("not laspy.LazBackend.Lazrs.is_available()"),
        ),
    ],
)
def test_reading_copc_file_normal_laz_file(backend):
    # COPC files are LAZ files with data arranged
    # in a special way that is still compatible with
    # standard file.
    # So we must be able to read a copc file as if it was
    # a classical LAZ

    las = laspy.read(SIMPLE_COPC_FILE, laz_backend=backend)
    assert las.header.version == "1.4"
    assert las.header.point_format == laspy.PointFormat(7)
    assert len(las) == 1065


@pytest.mark.skipif("not laspy.LazBackend.Lazrs.is_available()")
def test_querying_copc_local_file():
    with laspy.CopcReader.open(SIMPLE_COPC_FILE) as copc_reader:
        assert copc_reader.header.version == "1.4"
        assert copc_reader.header.point_format == laspy.PointFormat(7)
        points = copc_reader.query(resolution=50)
        assert len(points) == 24


@pytest.mark.skipif("laspy.LazBackend.Lazrs.is_available()")
def test_querying_copc_local_file_proper_error_if_no_lazrs():
    with pytest.raises(laspy.errors.LazError):
        with laspy.CopcReader.open(SIMPLE_COPC_FILE) as _:
            pass


@pytest.mark.skipif(
    not (
        laspy.LazBackend.Lazrs.is_available()
        and requests is not None
        and RangeHTTPServer is not None
    ),
    reason="neither lazrs, nor requests, nor RangeHTTPServer are installed",
)
def test_copc_over_http():
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "RangeHTTPServer"], cwd=str(Path(__file__).parent)
    )

    with laspy.CopcReader.open(
        "http://localhost:8000/data/simple.copc.laz"
    ) as copc_reader:
        assert copc_reader.header.version == "1.4"
        assert copc_reader.header.point_format == laspy.PointFormat(7)
        points = copc_reader.query(resolution=50)
        assert len(points) == 24

    server_proc.terminate()


@pytest.mark.parametrize(
    "exc_type,backend",
    [
        pytest.param(
            laspy.LaspyException,
            laspy.LazBackend.Laszip,
            marks=pytest.mark.skipif("not laspy.LazBackend.Laszip.is_available()"),
        ),
        pytest.param(
            NotImplementedError,
            laspy.LazBackend.Lazrs,
            marks=pytest.mark.skipif("not laspy.LazBackend.Lazrs.is_available()"),
        ),
        pytest.param(
            NotImplementedError,
            laspy.LazBackend.LazrsParallel,
            marks=pytest.mark.skipif("not laspy.LazBackend.Lazrs.is_available()"),
        ),
    ],
)
def test_writing_copc_file_fails(exc_type, backend):
    las = laspy.read(SIMPLE_COPC_FILE, laz_backend=backend)

    with pytest.raises(exc_type):
        with io.BytesIO() as output:
            las.write(output, laz_backend=backend)
