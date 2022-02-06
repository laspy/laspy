import pytest
import pyproj

import laspy
from tests.test_common import test1_4_las, autzen_las


@pytest.fixture()
def file_wkt():
    return laspy.read(test1_4_las)


@pytest.fixture()
def file_geotiff():
    return laspy.read(autzen_las)


def test_parse_crs_wkt(file_wkt):
    assert 'Bound CRS' in file_wkt.header.parse_crs().type_name


def test_parse_crs_geotiff(file_geotiff):
    assert 'Projected CRS' in file_geotiff.header.parse_crs().type_name


def test_add_crs_wkt():
    header = laspy.LasHeader(point_format=6, version="1.4")
    crs = pyproj.CRS.from_epsg(6432)
    header.add_crs(crs)

    lasf_proj = header.vlrs.get_by_id('LASF_Projection')

    assert len(lasf_proj) > 0
    assert hasattr(lasf_proj[0], 'string')
    assert lasf_proj[0].string == crs.to_wkt()
    assert header.global_encoding.wkt


def test_add_crs_geotiff():
    header = laspy.LasHeader(point_format=3, version="1.2")
    crs = pyproj.CRS.from_epsg(6432)
    header.add_crs(crs)

    lasf_proj = header.vlrs.get_by_id('LASF_Projection')

    assert len(lasf_proj) > 0
    assert hasattr(lasf_proj[0], 'geo_keys') 
    assert hasattr(lasf_proj[1], 'strings')
    assert header.global_encoding.wkt == False


def test_add_crs_compatibility():
    header = laspy.LasHeader(point_format=3, version="1.4")
    crs = pyproj.CRS.from_epsg(6432)
    header.add_crs(crs, keep_compatibility=False)

    lasf_proj = header.vlrs.get_by_id('LASF_Projection')

    assert len(lasf_proj) > 0
    assert hasattr(lasf_proj[0], 'string')
    assert lasf_proj[0].string == crs.to_wkt()
    assert header.global_encoding.wkt
