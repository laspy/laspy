import io
from pathlib import Path

import laspy

simple_1_1 = Path(__file__).parent / "data" / "simple1_1.las"


def test_read_las_1_1():
    las = laspy.read(simple_1_1)


def test_create_las_1_1():
    las = laspy.create(point_format=1, file_version="1.1")


def write_las_1_1():
    las = laspy.create(point_format=1, file_version="1.1")
    with io.BytesIO() as out:
        las.write(out)
        out.seek(0)
        las = las.read(out)
