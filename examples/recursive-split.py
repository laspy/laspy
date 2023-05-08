import argparse
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np

import laspy


def recursive_split(x_min, y_min, x_max, y_max, max_x_size, max_y_size):
    x_size = x_max - x_min
    y_size = y_max - y_min

    if x_size > max_x_size:
        left = recursive_split(
            x_min, y_min, x_min + (x_size // 2), y_max, max_x_size, max_y_size
        )
        right = recursive_split(
            x_min + (x_size // 2), y_min, x_max, y_max, max_x_size, max_y_size
        )
        return left + right
    elif y_size > max_y_size:
        up = recursive_split(
            x_min, y_min, x_max, y_min + (y_size // 2), max_x_size, max_y_size
        )
        down = recursive_split(
            x_min, y_min + (y_size // 2), x_max, y_max, max_x_size, max_y_size
        )
        return up + down
    else:
        return [(x_min, y_min, x_max, y_max)]


def tuple_size(string):
    try:
        return tuple(map(float, string.split("x")))
    except:
        raise ValueError("Size must be in the form of numberxnumber eg: 50.0x65.14")


def main():
    parser = argparse.ArgumentParser(
        "LAS recursive splitter", description="Splits a las file bounds recursively"
    )
    parser.add_argument("input_file")
    parser.add_argument("output_dir")
    parser.add_argument("size", type=tuple_size, help="eg: 50x64.17")
    parser.add_argument("--points-per-iter", default=10**6, type=int)

    args = parser.parse_args()

    with laspy.open(sys.argv[1]) as file:
        sub_bounds = recursive_split(
            file.header.x_min,
            file.header.y_min,
            file.header.x_max,
            file.header.y_max,
            args.size[0],
            args.size[1],
        )

        writers: List[Optional[laspy.LasWriter]] = [None] * len(sub_bounds)
        try:
            count = 0
            for points in file.chunk_iterator(args.points_per_iter):
                print(f"{count / file.header.point_count * 100}%")

                # For performance we need to use copy
                # so that the underlying arrays are contiguous
                x, y = points.x.copy(), points.y.copy()

                point_piped = 0

                for i, (x_min, y_min, x_max, y_max) in enumerate(sub_bounds):
                    mask = (x >= x_min) & (x <= x_max) & (y >= y_min) & (y <= y_max)

                    if np.any(mask):
                        if writers[i] is None:
                            output_path = Path(sys.argv[2]) / f"output_{i}.laz"
                            writers[i] = laspy.open(
                                output_path, mode="w", header=file.header
                            )
                        sub_points = points[mask]
                        writers[i].write_points(sub_points)

                    point_piped += np.sum(mask)
                    if point_piped == len(points):
                        break
                count += len(points)
            print(f"{count / file.header.point_count * 100}%")
        finally:
            for writer in writers:
                if writer is not None:
                    writer.close()


if __name__ == "__main__":
    main()
