import numpy as np
import pytest

import laspy
from laspy import LazBackend
from tests.test_common import test1_4_las, write_then_read_again


@pytest.fixture(scope="session")
def las():
    return laspy.read(test1_4_las)


@pytest.fixture(params=LazBackend.detect_available())
def laz_backend(request):
    return request.param


def test_classification(las):
    las.classification[:] = 234
    assert np.alltrue(las.classification == 234)

    res = write_then_read_again(las)

    assert np.alltrue(las.classification == res.classification)


def test_intensity(las):
    las.intensity[:] = 89
    assert np.alltrue(las.intensity == 89)
    res = write_then_read_again(las)

    assert np.alltrue(las.intensity == res.intensity)


def test_writing_las_with_evlrs():
    las = laspy.read(test1_4_las)
    assert las.evlrs == []

    evlr = laspy.VLR(
        user_id="test",
        record_id=42,
        description="Just a test",
        record_data=b"And so he grinds his own hands",
    )
    las.evlrs.append(evlr)

    las_1 = write_then_read_again(las, do_compress=False)
    assert las_1.evlrs == [evlr]


def test_writing_laz_with_evlrs(laz_backend):
    las = laspy.read(test1_4_las)
    assert las.evlrs == []

    evlr = laspy.VLR(
        user_id="test",
        record_id=42,
        description="Just a test",
        record_data=b"And so he grinds he own hands",
    )
    las.evlrs.append(evlr)

    las_1 = write_then_read_again(las, do_compress=True, laz_backend=laz_backend)
    assert las_1.evlrs == [evlr]
