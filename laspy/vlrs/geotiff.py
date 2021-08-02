import logging
from collections import namedtuple
from typing import List, Optional

from . import vlrlist
from .known import GeoAsciiParamsVlr, GeoDoubleParamsVlr, GeoKeyDirectoryVlr

GeoTiffKey = namedtuple("GeoTiffKey", ("id", "value"))

logger = logging.getLogger(__name__)

GTModelTypeGeoKey = 1024
GTRasterTypeGeoKey = 1025
GTCitationGeoKey = 1026
GeogCitationGeoKey = 2049
GeogAngularUnitsGeoKey = 2054
ProjectedCSTypeGeoKey = 3072
ProjLinearUnitsGeoKey = 3076


def parse_geo_tiff_keys_from_vlrs(vlr_list: vlrlist.VLRList) -> List[GeoTiffKey]:
    """Gets the 3 GeoTiff vlrs from the vlr_list and parse them into
    a nicer structure

    Parameters
    ----------
    vlr_list: laspy.vrls.vlrslist.VLRList list of vlrs from a las file

    Raises
    ------
        IndexError if any of the needed GeoTiffVLR is not found in the list

    Returns
    -------
    List of GeoTiff keys parsed from the VLRs

    """
    geo_key_dir = vlr_list.get_by_id(
        GeoKeyDirectoryVlr.official_user_id(), GeoKeyDirectoryVlr.official_record_ids()
    )[0]

    try:
        geo_doubles = vlr_list.get_by_id(
            GeoDoubleParamsVlr.official_user_id(),
            GeoDoubleParamsVlr.official_record_ids(),
        )[0]
    except IndexError:
        geo_doubles = None

    try:
        geo_ascii = vlr_list.get_by_id(
            GeoAsciiParamsVlr.official_user_id(),
            GeoAsciiParamsVlr.official_record_ids(),
        )[0]
    except IndexError:
        geo_ascii = None
    return parse_geo_tiff(geo_key_dir, geo_doubles, geo_ascii)


def parse_geo_tiff(
    key_dir_vlr: GeoKeyDirectoryVlr,
    double_vlr: Optional[GeoDoubleParamsVlr],
    ascii_vlr: Optional[GeoAsciiParamsVlr],
) -> List[GeoTiffKey]:
    """Parses the GeoTiff VLRs information into nicer structs"""
    geotiff_keys = []

    for k in key_dir_vlr.geo_keys:
        if k.tiff_tag_location == 0:
            value = k.value_offset
        elif k.tiff_tag_location == 34736:
            if double_vlr is None:
                raise RuntimeError(
                    "Geotiff tag location points to GeoDoubleParams, "
                    "but it does not exists"
                )
            value = double_vlr.doubles[k.value_offset]
        elif k.tiff_tag_location == 34737:
            if ascii_vlr is None:
                raise RuntimeError(
                    "Geotiff tag location points to GeoAsciiParams, "
                    "but it does not exists"
                )
            value = ascii_vlr.string(k.value_offset, k.count)
        else:
            logger.warning(
                "GeoTiffKey with unknown tiff tag location ({})".format(
                    k.tiff_tag_location
                )
            )
            continue

        geotiff_keys.append(GeoTiffKey(k.id, value))
    return geotiff_keys
