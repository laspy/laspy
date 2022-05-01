import pytest
import subprocess
import os
import json

import laspy
from tests.test_common import test1_4_las, autzen_las

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

def has_pyproj() -> bool:
    return pyproj is not None


@pytest.mark.skipif(
    not has_pyproj(), reason="pyproj not installed"
)
def test_parse_crs_wkt(file_wkt):
    assert 'Bound CRS' in file_wkt.header.parse_crs().type_name


@pytest.mark.skipif(
    not has_pyproj(), reason="pyproj not installed"
)
def test_parse_crs_geotiff(file_geotiff):
    assert 'Projected CRS' in file_geotiff.header.parse_crs().type_name


@pytest.mark.skipif(
    not has_pyproj(), reason="pyproj not installed"
)
def test_add_crs_wkt():
    header = laspy.LasHeader(point_format=6, version="1.4")
    crs = pyproj.CRS.from_epsg(6432)
    header.add_crs(crs)

    lasf_proj = header.vlrs.get_by_id('LASF_Projection')

    assert len(lasf_proj) > 0
    assert hasattr(lasf_proj[0], 'string')
    assert lasf_proj[0].string == crs.to_wkt()
    assert header.global_encoding.wkt


@pytest.mark.skipif(
    not has_pyproj(), reason="pyproj not installed"
)
def test_add_crs_geotiff():
    """
    Test adding geotiff crs seems ok
    """
    header = laspy.LasHeader(point_format=3, version="1.2")
    crs = pyproj.CRS.from_epsg(6432)
    header.add_crs(crs)

    lasf_proj = header.vlrs.get_by_id('LASF_Projection')

    assert len(lasf_proj) > 0
    assert hasattr(lasf_proj[0], 'geo_keys') 
    assert hasattr(lasf_proj[1], 'strings')
    assert header.global_encoding.wkt == False


    las = laspy.LasData(header=header)
    las = laspy.lib.write_then_read_again(las)
    epsg = las.header.parse_crs().to_epsg()
    assert epsg == 6432, "epsg after read-write is not the same"


@pytest.mark.skipif(
    not has_pyproj(), reason="pyproj not installed"
)
def test_add_crs_compatibility():
    header = laspy.LasHeader(point_format=3, version="1.4")
    crs = pyproj.CRS.from_epsg(6432)
    header.add_crs(crs, keep_compatibility=False)

    lasf_proj = header.vlrs.get_by_id('LASF_Projection')

    assert len(lasf_proj) > 0
    assert hasattr(lasf_proj[0], 'string')
    assert lasf_proj[0].string == crs.to_wkt()
    assert header.global_encoding.wkt

def has_pdal():
    try:
        subprocess.run(['pdal', '--version'], capture_output=True, check=True)
    except:
        return False
    else:
        return True


def get_pdal_srs(filename):
    process = subprocess.run(['pdal', 'info', '--metadata', filename], capture_output=True, check=True)
    json_output = json.loads(process.stdout.decode('utf-8'))['metadata']['srs']
    return json_output['wkt'], json_output['proj4']
    

def geotiff_crs_pdal_test(crs):
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.add_crs(crs)

    tmp_filename = f'delete_me_pdal_test_cs_{crs.to_epsg()}.las'

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

