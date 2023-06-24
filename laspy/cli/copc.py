from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import numpy as np
import typer

import laspy

from ..copc import Bounds, CopcReader

app = typer.Typer(help="COPC related commands")


@dataclass
class Level:
    inner: Union[int, range]

    @classmethod
    def parse(cls, value_string: str) -> "Level":
        if ".." in value_string:
            # range rust-style
            start_str, end_str = value_string.split("..")
            start = int(start_str)
            if end_str.startswith("="):
                end = int(end_str[1:]) + 1
            else:
                end = int(end_str)

            inner = range(start, end)
        elif ":" in value_string:
            # range python style
            start, end = map(int, value_string.split(":"))
            inner = range(start, end)
        else:
            inner = int(value_string)

        return cls(inner)


def parse_bounds(value_string: str) -> Bounds:
    first_closing_bracket = value_string.find("]")
    second_opening_bracket = value_string[first_closing_bracket:].find("[")

    mins_str = value_string[1:first_closing_bracket]
    maxes_str = value_string[first_closing_bracket + second_opening_bracket + 1 : -1]

    mins = np.array(mins_str.split(","), dtype=np.float64)
    maxes = np.array(maxes_str.split(","), dtype=np.float64)

    return Bounds(mins, maxes)


@app.command()
def query(
    source: str = typer.Argument(
        ..., help="The COPC ressource, can be a path or a url"
    ),
    dest: Path = typer.Option(
        ...,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    bounds: Optional[Bounds] = typer.Option(
        None,
        parser=parse_bounds,
        help="""
                The bounds for which you wish to aquire points.
                If None, the whole file's bounds will be considered
                2D bounds are suported, (No point will be filtered on its Z coordinate)
""",
    ),
    resolution: Optional[float] = typer.Option(
        None,
        help=""" Limits the octree levels to be queried in order to have
                a point cloud with the requested resolution.

                - The unit is the one of the data.

                - If None, the resulting cloud will be at the
                  full resolution offered by the COPC source

                - Mutually exclusive with level parameter
""",
    ),
    level: Optional[Level] = typer.Option(
        None,
        parser=Level.parse,
        help=""" Level of detail (LOD)
                By default all levels are considered.

               - If it is an int, only points that are of the requested LOD
                 will be returned.
               - If it is a range, points for which the LOD is within the range
                 will be returned
""",
    ),
    safe_guard: bool = typer.Option(
        True,
        help="""
            Enable / Disable the safeguard that prevents downloading
            the whole COPC file when the option was provided
""",
    ),
):
    """
    Query the COPC file to retrieve the points matching the
    requested bounds and level/resolution


    Examples:



    laspy COPC "https://s3.amazonaws.com/hobu-lidar/melbourne-2018.copc.laz"
        output.laz
        --bounds "[3.1e+05, 5.8+06, -2.0e+01], [3.17e+05, 5.81e+06, 3.0e+02]"

    ---


    laspy COPC "https://s3.amazonaws.com/hobu-lidar/melbourne-2018.copc.laz"
        output.laz
        --bounds "[3.1e+05, 5.8+06], [3.17e+05, 5.81e+06]"

    ---

    laspy COPC "https://s3.amazonaws.com/hobu-lidar/melbourne-2018.copc.laz"
        output.laz
        --bounds "[3.1e+05, 5.8+06], [3.17e+05, 5.81e+06]"
        --resolution 2

    ---

    laspy COPC "https://s3.amazonaws.com/hobu-lidar/melbourne-2018.copc.laz"
        output.laz
        --bounds "[3.1e+05, 5.8+06], [3.17e+05, 5.81e+06]"
        --level 1

    ---

    # Level can be a range (here [0, 2[)

    laspy COPC "https://s3.amazonaws.com/hobu-lidar/melbourne-2018.copc.laz"
        output.laz
        --bounds "[3.1e+05, 5.8+06], [3.17e+05, 5.81e+06]"
        --level 0:2

    ---

    # Level can be a range (here [0, 2[)

    laspy COPC "https://s3.amazonaws.com/hobu-lidar/melbourne-2018.copc.laz"
        output.laz
        --bounds "[3.1e+05, 5.8+06], [3.17e+05, 5.81e+06]"
        --level 0..2

    laspy COPC "https://s3.amazonaws.com/hobu-lidar/melbourne-2018.copc.laz"
        output.laz
        --bounds "[3.1e+05, 5.8+06], [3.17e+05, 5.81e+06]"
        --level 0..=2
    """

    level = None if level is None else level.inner

    with CopcReader.open(source) as crdr:
        if safe_guard is True and all(
            map(lambda x: x is None, (level, bounds, resolution))
        ):
            print(
                "You did not specify any of --bounds, --level or --resolution options"
            )
            print(
                f"The command is going to download the whole COPC resource ({crdr.header.point_count}) points"
            )
            anwser = input("Do you really want to continue ? [y/N]")
            if anwser not in ("y", "Y", "yes"):
                return

        points = crdr.query(bounds=bounds, resolution=resolution, level=level)
        pct = len(points) / crdr.header.point_count * 100
        print(
            f"{len(points)} points downloaded\n{pct}% of the total number of points in COPC resource"
        )

        new_header = laspy.LasHeader(
            version=crdr.header.version, point_format=crdr.header.point_format
        )
        new_header.offsets = crdr.header.offsets
        new_header.scales = crdr.header.scales

        with laspy.open(dest, mode="w", header=new_header) as f:
            f.write_points(points)
