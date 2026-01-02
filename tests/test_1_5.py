import io

import numpy as np
import pytest

import laspy


def test_convert_1_5_write_read_las():
    las = laspy.read("tests/data/simple.las")

    for fmt in range(6):
        with pytest.raises(laspy.LaspyException):
            converted = laspy.convert(las, point_format_id=fmt, file_version="1.5")

    with io.BytesIO() as stream:
        for fmt in range(6, 11):
            stream.seek(0)
            converted = laspy.convert(las, point_format_id=fmt, file_version="1.5")
            converted.write(stream, do_compress=False)
            stream.seek(0)

            las2 = laspy.read(stream, closefd=False)
            assert np.allclose(las2.header.max_gps_time, las.gps_time.max())
            assert np.allclose(las2.header.min_gps_time, las.gps_time.min())

            for dim_name in las2.point_format.dimension_names:
                try:
                    expected = las[dim_name]
                except ValueError:
                    # The dimension may not exist in the old point format
                    continue

                assert np.allclose(
                    las2[dim_name], expected
                ), f"Dimenion {dim_name} is not as expected"


@pytest.mark.parametrize("laz_backend", laspy.LazBackend.detect_available())
def test_convert_1_5_write_read_laz(laz_backend):
    las = laspy.read("tests/data/simple.las")

    for fmt in range(6):
        with pytest.raises(laspy.LaspyException):
            converted = laspy.convert(las, point_format_id=fmt, file_version="1.5")

    with io.BytesIO() as stream:
        for fmt in range(6, 11):
            stream.seek(0)
            converted = laspy.convert(las, point_format_id=fmt, file_version="1.5")
            converted.write(stream, do_compress=True, laz_backend=laz_backend)
            stream.seek(0)

            las2 = laspy.read(stream, closefd=False, laz_backend=laz_backend)
            assert np.allclose(las2.header.max_gps_time, las.gps_time.max())
            assert np.allclose(las2.header.min_gps_time, las.gps_time.min())

            for dim_name in las2.point_format.dimension_names:
                try:
                    expected = las[dim_name]
                except ValueError:
                    # The dimension may not exist in the old point format
                    continue

                assert np.allclose(
                    las2[dim_name], expected
                ), f"Dimenion {dim_name} is not as expected"
