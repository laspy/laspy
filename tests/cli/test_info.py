import pytest

from . import skip_if_cli_deps_are_not_installed

skip_if_cli_deps_are_not_installed()

from typer.testing import CliRunner

from laspy.cli.core import app

runner = CliRunner()

EXPECTED_HEADER_INFO_SIMPLE_LAS = (
    "                                 Header                                  \n"
    " Version                     1.2                                         \n"
    " Point Format Id             3                                           \n"
    " Point Format Size           34                                          \n"
    " Extra Bytes                 0                                           \n"
    " Point Count                 1065                                        \n"
    " Compressed                  False                                       \n"
    " System Identifier           ''                                          \n"
    " Generating Software         'TerraScan'                                 \n"
    " Number Of VLRs              0                                           \n"
    " UUID                        '00000000-0000-0000-0000-000000000000'      \n"
    " File Source Id              0                                           \n"
    " Creation Date               None                                        \n"
    " Scales                      [0.01 0.01 0.01]                            \n"
    " Offsets                     [-0. -0. -0.]                               \n"
    " Mins                        [6.3561985e+05 8.4889970e+05 4.0659000e+02] \n"
    " Maxs                        [6.3898255e+05 8.5353543e+05 5.8638000e+02] \n"
    " Number Of Points By Return  [925 114  21   5   0]                       \n"
)

EXPECTED_VLR_INFO_SIMPLE_LAS = ""

EXPECTED_POINTS_INFO_SIMPLE_LAS = (
    "\n"
    "                            Stats                            \n"
    " Dimension Name       Min                 Max                \n"
    " X                    63561985            63898255           \n"
    " Y                    84889970            85353543           \n"
    " Z                    40659               58638              \n"
    " intensity            0                   254                \n"
    " return_number        1                   4                  \n"
    " number_of_returns    1                   4                  \n"
    " scan_direction_flag  0                   1                  \n"
    " edge_of_flight_line  0                   0                  \n"
    " classification       1                   2                  \n"
    " synthetic            0                   0                  \n"
    " key_point            0                   0                  \n"
    " withheld             0                   0                  \n"
    " scan_angle_rank      -19                 18                 \n"
    " user_data            117                 149                \n"
    " point_source_id      7326                7334               \n"
    " gps_time             245370.41706455982  249783.16215837188 \n"
    " red                  39                  249                \n"
    " green                57                  239                \n"
    " blue                 56                  249                \n"
)

EXPECTED_INFO_SIMPLE_LAS = (
    f"{EXPECTED_HEADER_INFO_SIMPLE_LAS}"
    "--------------------------------------------------\n"
    f"{EXPECTED_VLR_INFO_SIMPLE_LAS}"
    "--------------------------------------------------\n"
    f"{EXPECTED_POINTS_INFO_SIMPLE_LAS}"
)

EXPECTED_VLR_INFO_AUTZEN_LAS = (
    "                            VLRs                            \n"
    " User ID          Record ID  Description                    \n"
    " liblas           2112       OGR variant of OpenGIS WKT SRS \n"
    " LASF_Projection  34735      GeoTIFF GeoKeyDirectoryTag     \n"
    " LASF_Projection  34737      GeoTIFF GeoAsciiParamsTag      \n"
    " liblas           2112       OGR variant of OpenGIS WKT SRS \n"
)


def test_header_info():
    result = runner.invoke(app, ["info", "--header", "tests/data/simple.las"])
    assert result.exit_code == 0

    output = result.stdout
    assert output == EXPECTED_HEADER_INFO_SIMPLE_LAS


def test_vlr_info():
    result = runner.invoke(app, ["info", "--vlrs", "tests/data/simple.las"])
    assert result.exit_code == 0
    assert result.stdout == EXPECTED_VLR_INFO_SIMPLE_LAS

    result = runner.invoke(app, ["info", "--vlrs", "tests/data/autzen.las"])
    assert result.exit_code == 0

    assert result.stdout == EXPECTED_VLR_INFO_AUTZEN_LAS


def test_point_info():
    result = runner.invoke(app, ["info", "--points", "tests/data/simple.las"])
    assert result.exit_code == 0

    assert result.stdout == EXPECTED_POINTS_INFO_SIMPLE_LAS


def test_complete_info():
    result = runner.invoke(app, ["info", "tests/data/simple.las"])
    assert result.exit_code == 0

    assert result.stdout == EXPECTED_INFO_SIMPLE_LAS


def test_info_non_existant_file():
    result = runner.invoke(
        app, ["info", "--header", "tests/data/this_does_not_exist.las"]
    )
    assert result.exit_code != 0
    assert (
        result.output
        == """Error:
[Errno 2] No such file or directory: 'tests/data/this_does_not_exist.las'
"""
        or result.output  # Windows paths...
        == """Error:
[Errno 2] No such file or directory: 'tests\\\\data\\\\this_does_not_exist.las'
"""
    )
