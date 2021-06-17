import numpy as np

import laspy


def test_mmap(mmapped_file_path):
    with laspy.mmap(mmapped_file_path) as las:
        las.classification[:] = 25
        assert np.all(las.classification == 25)

    las = laspy.read(mmapped_file_path)
    assert np.all(las.classification == 25)
