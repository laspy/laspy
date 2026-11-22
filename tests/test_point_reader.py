"""Regression tests for laspy#378.

A LAS header's point count is not trustworthy: a tiny crafted file could
claim billions of points and make the uncompressed reader allocate a
buffer proportional to the claim (a ~300 byte file asking for ~80 GB)
before any byte was read. The reader must bound its allocation by the
number of bytes actually remaining in the source.
"""

import io
import struct

import numpy as np
import pytest

import laspy
from laspy.lasreader import UncompressedPointReader


def make_las_bytes(point_count=3):
    header = laspy.LasHeader(point_format=0, version="1.2")
    header.scales = [0.001, 0.001, 0.001]
    header.offsets = [0.0, 0.0, 0.0]
    las = laspy.LasData(header)
    las.x = np.arange(point_count, dtype=np.float64)
    las.y = np.arange(point_count, dtype=np.float64)
    las.z = np.arange(point_count, dtype=np.float64)
    stream = io.BytesIO()
    las.write(stream)
    return bytearray(stream.getvalue())


def forge_point_count(las_bytes, claimed_count):
    # Legacy number_of_point_records: uint32 at offset 107 in the LAS header.
    struct.pack_into("<I", las_bytes, 107, claimed_count)
    return las_bytes


class RecordingBytesIO(io.BytesIO):
    """BytesIO that records the largest buffer handed to readinto."""

    def __init__(self, data):
        super().__init__(data)
        self.largest_readinto_buffer = 0

    def readinto(self, buffer):
        self.largest_readinto_buffer = max(
            self.largest_readinto_buffer, len(buffer)
        )
        return super().readinto(buffer)


def test_forged_huge_point_count_does_not_drive_allocation():
    claimed = 25_000_000  # 25M points * 20 bytes = 500 MB of claimed data
    raw = forge_point_count(make_las_bytes(3), claimed)
    assert len(raw) < 1024  # the whole file is a few hundred bytes

    source = RecordingBytesIO(bytes(raw))
    header = laspy.LasHeader.read_from(source)
    assert header.point_count == claimed

    reader = UncompressedPointReader(source, header)
    data = reader.read_n_points(claimed)

    # Only the 3 real points (60 bytes) are returned, as before the fix...
    assert len(data) == 3 * header.point_format.size
    # ...but the allocation was bounded by the real file size, not the claim.
    assert source.largest_readinto_buffer <= len(raw)


def test_forged_huge_point_count_reads_real_points_end_to_end(tmp_path):
    claimed = 4_000_000_000  # would ask for ~80 GB unpatched
    path = tmp_path / "crafted.las"
    path.write_bytes(bytes(forge_point_count(make_las_bytes(3), claimed)))

    las = laspy.read(str(path))
    assert len(las.points) == 3
    assert list(las.x) == [0.0, 1.0, 2.0]


def test_normal_file_still_reads_all_points(tmp_path):
    path = tmp_path / "normal.las"
    path.write_bytes(bytes(make_las_bytes(3)))

    las = laspy.read(str(path))
    assert len(las.points) == 3
    assert list(las.z) == [0.0, 1.0, 2.0]
