import json
import os
import subprocess
from pathlib import Path
from typing import Dict

import pytest

import laspy
from laspy.vlrs.geotiff import GeographicTypeGeoKey, ProjectedCSTypeGeoKey
from laspy.vlrs.known import GeoKeyDirectoryVlr
from tests.test_common import autzen_geo_proj_las, autzen_las, test1_4_las

try:
    import pyproj
except ModuleNotFoundError:
    pyproj = None


@pytest.fixture()
def file_wkt():
    return laspy.read(test1_4_las)


@pytest.fixture()
def file_geotiff():
    return laspy.read(autzen_las)


@pytest.fixture()
def file_geotiff_geo_proj():
    return laspy.read(autzen_geo_proj_las)


@pytest.fixture()
def file_with_both_wkt_and_geotiff_vlrs():
    path = Path(__file__).parent / "data" / "file_with_both_wkt_and_geotiff_vlrs.las"
    return laspy.read(path)


def has_pyproj() -> bool:
    return pyproj is not None


@pytest.mark.skipif(not has_pyproj(), reason="pyproj not installed")
def test_parse_crs_wkt(file_wkt):
    assert "Bound CRS" in file_wkt.header.parse_crs().type_name


@pytest.mark.skipif(not has_pyproj(), reason="pyproj not installed")
def test_parse_crs_geotiff(file_geotiff, file_geotiff_geo_proj):
    assert "Projected CRS" in file_geotiff.header.parse_crs().type_name
    assert (
        file_geotiff.header.parse_crs().to_epsg()
        == file_geotiff_geo_proj.header.parse_crs().to_epsg()
        == 2994
    )

    geokeys1 = get_geokeys(file_geotiff.header)
    geokeys2 = get_geokeys(file_geotiff_geo_proj.header)

    assert (
        geokeys1[ProjectedCSTypeGeoKey.id] == geokeys2[ProjectedCSTypeGeoKey.id] == 2994
    )
    assert GeographicTypeGeoKey.id not in geokeys1
    assert geokeys2[GeographicTypeGeoKey.id] == 4152


def get_geokeys(header: laspy.LasHeader) -> Dict:
    geo_vlr = header.vlrs.get_by_id("LASF_Projection")
    for rec in geo_vlr:
        if isinstance(rec, GeoKeyDirectoryVlr):
            return {k.id: k.value_offset for k in rec.geo_keys}

    return {}


@pytest.mark.skipif(not has_pyproj(), reason="pyproj not installed")
def test_add_crs_wkt():
    header = laspy.LasHeader(point_format=6, version="1.4")
    crs = pyproj.CRS.from_epsg(6432)
    header.add_crs(crs)

    lasf_proj = header.vlrs.get_by_id("LASF_Projection")

    assert len(lasf_proj) > 0
    assert hasattr(lasf_proj[0], "string")
    assert lasf_proj[0].string == crs.to_wkt()
    assert header.global_encoding.wkt


@pytest.mark.skipif(not has_pyproj(), reason="pyproj not installed")
def test_handle_empty_crs_wkt_string():
    header = laspy.LasHeader(point_format=6, version="1.4")
    empty_wkt_crs = laspy.vlrs.known.WktCoordinateSystemVlr(wkt_string="")
    header.vlrs.append(empty_wkt_crs)

    crs = header.parse_crs()
    assert crs is None


@pytest.mark.skipif(not has_pyproj(), reason="pyproj not installed")
def test_add_crs_geotiff():
    """
    Test adding geotiff crs seems ok
    """
    header = laspy.LasHeader(point_format=3, version="1.2")
    crs = pyproj.CRS.from_epsg(6432)
    header.add_crs(crs)

    lasf_proj = header.vlrs.get_by_id("LASF_Projection")

    assert len(lasf_proj) > 0
    assert hasattr(lasf_proj[0], "geo_keys")
    assert hasattr(lasf_proj[1], "strings")
    assert header.global_encoding.wkt == False

    las = laspy.LasData(header=header)
    las = laspy.lib.write_then_read_again(las)
    epsg = las.header.parse_crs().to_epsg()
    assert epsg == 6432, "epsg after read-write is not the same"


@pytest.mark.skipif(not has_pyproj(), reason="pyproj not installed")
def test_add_crs_compatibility():
    header = laspy.LasHeader(point_format=3, version="1.4")
    crs = pyproj.CRS.from_epsg(6432)
    header.add_crs(crs, keep_compatibility=False)

    lasf_proj = header.vlrs.get_by_id("LASF_Projection")

    assert len(lasf_proj) > 0
    assert hasattr(lasf_proj[0], "string")
    assert lasf_proj[0].string == crs.to_wkt()
    assert header.global_encoding.wkt


def has_pdal():
    try:
        subprocess.run(["pdal", "--version"], capture_output=True, check=True)
    except:
        return False
    else:
        return True


def get_pdal_srs(filename):
    process = subprocess.run(
        ["pdal", "info", "--metadata", filename], capture_output=True, check=True
    )
    json_output = json.loads(process.stdout.decode("utf-8"))["metadata"]["srs"]
    return json_output["wkt"], json_output["proj4"]


def geotiff_crs_pdal_test(crs):
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.add_crs(crs)

    tmp_filename = f"delete_me_pdal_test_cs_{crs.to_epsg()}.las"

    las = laspy.LasData(header=header)
    las.write(tmp_filename)

    try:
        pdal_wkt, _ = get_pdal_srs(tmp_filename)

    finally:
        os.remove(tmp_filename)

    # We don't use pdal's proj4 as its seems not complete enough
    # to be 100% equal, while the wkt seems ok
    assert pyproj.CRS.from_wkt(pdal_wkt) == crs


@pytest.mark.skipif(
    not (has_pdal() and has_pyproj()), reason="PDAL and/or pyproj not found"
)
def test_pdal_understands_our_geotiff_derived_projected_cs():
    crs = pyproj.CRS.from_epsg(3945)
    geotiff_crs_pdal_test(crs)


@pytest.mark.skipif(
    not (has_pdal() and has_pyproj()), reason="PDAL and/or pyproj not found"
)
def test_pdal_understands_our_geotiff_geographic_cs():
    crs = pyproj.CRS.from_epsg(4326)
    geotiff_crs_pdal_test(crs)


@pytest.mark.skipif(
    not (has_pdal() and has_pyproj()), reason="PDAL and/or pyproj not found"
)
def test_pdal_understands_our_geotiff_projected_cs():
    crs = pyproj.CRS.from_epsg(6432)
    geotiff_crs_pdal_test(crs)


@pytest.mark.skipif(not has_pyproj(), reason="pyproj not installed")
def test_preference_option(file_with_both_wkt_and_geotiff_vlrs):
    header = file_with_both_wkt_and_geotiff_vlrs.header

    expected_wkt_crs = """PROJCS["NAD83_2011_Nebraska_ft",GEOGCS["GCS_NAD_1983_2011",DATUM["D_NAD83_NATIONAL_SPATIAL_REFERENCE_SYSTEM_2011",SPHEROID["GRS_1980",6378137,298.257222101]],PRIMEM["Greenwich",0],UNIT["Degree",0.017453292519943295]],PROJECTION["Lambert_Conformal_Conic"],PARAMETER["scale_factor",1],PARAMETER["standard_parallel_1",40],PARAMETER["standard_parallel_2",43],PARAMETER["central_meridian",-100],PARAMETER["latitude_of_origin",39.83333333333334],PARAMETER["false_easting",1640416.666666667],PARAMETER["false_northing",0],UNIT["Foot_US",0.30480060960121924]]"""
    expected_geotiff_crs = "epsg:32104"

    crs = header.parse_crs()
    assert str(crs) == expected_wkt_crs

    crs = header.parse_crs(prefer_wkt=True)
    assert str(crs) == expected_wkt_crs

    crs = header.parse_crs(prefer_wkt=False)
    assert str(crs).lower() == expected_geotiff_crs
