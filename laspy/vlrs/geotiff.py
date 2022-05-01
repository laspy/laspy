import logging
from typing import Tuple, Optional

from .known import (
    GeoAsciiParamsVlr,
    GeoKeyDirectoryVlr,
    GeoKeyEntryStruct,
)
from copy import copy

try:
    import pyproj
except ModuleNotFoundError:
    pass


logger = logging.getLogger(__name__)


# GeoTIFF Configuration GeoKeys
"""
GeoTIFF defined CS Model Type Codes:
   ModelTypeProjected   = 1   /* Projection Coordinate System         */
   ModelTypeGeographic  = 2   /* Geographic latitude-longitude System */
   ModelTypeGeocentric  = 3   /* Geocentric (X,Y,Z) Coordinate System */

Notes:
   1. ModelTypeGeographic and ModelTypeProjected
      correspond to the FGDC metadata Geographic and
      Planar-Projected coordinate system types.

http://geotiff.maptools.org/spec/geotiff6.html#6.3.1.1
"""
ModelTypeProjected = 1
ModelTypeGeographic = 2
GTModelTypeGeoKey = GeoKeyEntryStruct(
    id=1024,
    tiff_tag_location=0,
    count=1,
)
"""
Values:
0 => Undefined
1 => RasterPixelIsArea
2 => RasterPixelIsPoint

http://geotiff.maptools.org/spec/geotiff6.html#6.3.1.2
"""
GTRasterTypeGeoKey = GeoKeyEntryStruct(
    id=1025,
    tiff_tag_location=0,
    count=1,
)
"""
'ASCII reference to published documentation on the overall configuration
of this GeoTIFF file.'
"""
GTCitationGeoKey = GeoKeyEntryStruct(
    id=1026,
    tiff_tag_location=GeoAsciiParamsVlr.official_record_ids()[0],
)

# Geographic CS Parameter GeoKeys

GeographicTypeGeoKey = GeoKeyEntryStruct(
    id=2048,
    tiff_tag_location=0,
    count=1,
)

"""
General citation and reference for all Geographic CS parameters.
"""
GeogCitationGeoKey = GeoKeyEntryStruct(
    id=2049,
    tiff_tag_location=GeoAsciiParamsVlr.official_record_ids()[0],
)

# Projected CS Parameter GeoKeys

ProjectedCSTypeGeoKey = GeoKeyEntryStruct(
    id=3072,
    tiff_tag_location=0,
    count=1,
)

"""
'ASCII reference to published documentation on the 
Projected Coordinate System particularly if this is a "user-defined" PCS'
"""
PCSCitationGeoKey = GeoKeyEntryStruct(
    id=3073,
    tiff_tag_location=GeoAsciiParamsVlr.official_record_ids()[0],
)

# Geographic CS Parameter GeoKeys


def create_geotiff_projection_vlrs(
    crs: "pyproj.CRS",
) -> Tuple[GeoKeyDirectoryVlr, GeoAsciiParamsVlr]:
    # 'Cookbook' from the geotiff spec
    # http://geotiff.maptools.org/spec/geotiff2.7.html#2.7

    if crs.is_projected:
        model_key = copy(GTModelTypeGeoKey)
        model_key.value_offset = ModelTypeProjected

        epsg_code = crs.to_epsg()
        if epsg_code is None:
            raise RuntimeError("Projected CRS without epsg is not supported")

        projected_crs_key = copy(ProjectedCSTypeGeoKey)
        projected_crs_key.value_offset = epsg_code

        # Citation Keys for which data is stored in the Ascii Param
        pcs_citation = crs.name.encode("ascii")

        ascii_params = b"|".join([pcs_citation])

        pcs_citation_key = copy(PCSCitationGeoKey)
        pcs_citation_key.value_offset = 0
        pcs_citation_key.count = len(pcs_citation)

        keys = [model_key, projected_crs_key, pcs_citation_key]
        geo_key_vlr = GeoKeyDirectoryVlr()
        geo_key_vlr.geo_keys_header.number_of_keys = len(keys)
        geo_key_vlr.geo_keys = keys

        ascii_vlr = GeoAsciiParamsVlr()
        ascii_vlr.strings = [ascii_params.decode("ascii")]

        return geo_key_vlr, ascii_vlr
    if crs.is_geographic or crs.is_geocentric:
        model_key = copy(GTModelTypeGeoKey)
        model_key.value_offset = ModelTypeGeographic

        epsg_code = crs.to_epsg()
        if epsg_code is None:
            raise RuntimeError("Geographic CRS without epsg is not supported")

        geographic_crs_key = copy(GeographicTypeGeoKey)
        geographic_crs_key.value_offset = epsg_code

        geodetic_citation = crs.geodetic_crs.name.encode("ascii")
        ascii_params = b"|".join([geodetic_citation])

        geodetic_citation_key = copy(GeogCitationGeoKey)
        geodetic_citation_key.value_offset = 0
        geodetic_citation_key.count = len(geodetic_citation)

        keys = [model_key, geographic_crs_key, geodetic_citation_key]
        geo_key_vlr = GeoKeyDirectoryVlr()
        geo_key_vlr.geo_keys_header.number_of_keys = len(keys)
        geo_key_vlr.geo_keys = keys

        ascii_vlr = GeoAsciiParamsVlr()
        ascii_vlr.strings = [ascii_params.decode("ascii")]
        return geo_key_vlr, ascii_vlr

    else:
        raise RuntimeError(f"CRS of type {crs.type_name} is not supported")
