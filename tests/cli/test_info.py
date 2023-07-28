import pytest

try:
    from typer.testing import CliRunner

    runner = CliRunner()
    from laspy.cli.core import app

    HAS_CLI = True
except ModuleNotFoundError:
    HAS_CLI = False


@pytest.mark.skipif(
    not HAS_CLI,
    reason="Dependencies for CLI are not installed",
)
def test_header_info():
    result = runner.invoke(app, ["info", "--header", "tests/data/simple.las"])
    assert result.exit_code == 0
    expected = """                                 Header                                  
 Version                     1.2                                         
 Point Format Id             3                                           
 Point Format Size           34                                          
 Extra Bytes                 0                                           
 Point Count                 1065                                        
 Compressed                  False                                       
 System Identifier           ''                                          
 Generating Software         'TerraScan'                                 
 Number Of VLRs              0                                           
 UUID                        '00000000-0000-0000-0000-000000000000'      
 File Source Id              0                                           
 Creation Date               None                                        
 Scales                      [0.01 0.01 0.01]                            
 Offsets                     [-0. -0. -0.]                               
 Mins                        [6.3561985e+05 8.4889970e+05 4.0659000e+02] 
 Maxs                        [6.3898255e+05 8.5353543e+05 5.8638000e+02] 
 Number Of Points By Return  [925 114  21   5   0]                       
"""

    output = result.stdout
    assert output == expected


@pytest.mark.skipif(
    not HAS_CLI,
    reason="Dependencies for CLI are not installed",
)
def test_vlr_info():
    result = runner.invoke(app, ["info", "--vlrs", "tests/data/simple.las"])
    assert result.exit_code == 0
    expected = """"""
    assert result.stdout == expected

    result = runner.invoke(app, ["info", "--vlrs", "tests/data/autzen.las"])
    assert result.exit_code == 0
    expected = """                            VLRs                            
 User ID          Record ID  Description                    
 liblas           2112       OGR variant of OpenGIS WKT SRS 
 LASF_Projection  34735      GeoTIFF GeoKeyDirectoryTag     
 LASF_Projection  34737      GeoTIFF GeoAsciiParamsTag      
 liblas           2112       OGR variant of OpenGIS WKT SRS 
"""
    assert result.stdout == expected


@pytest.mark.skipif(
    not HAS_CLI,
    reason="Dependencies for CLI are not installed",
)
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
