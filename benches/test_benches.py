import numpy as np

import laspy


def test_bench_sub_field_view_comparison(benchmark):
    las = laspy.create()
    las.x = np.zeros(10**6, np.float64)
    benchmark(lambda: las.classification == 4)


def test_bench_scaled_array_comparison(benchmark):
    las = laspy.create()
    las.x = np.zeros(10**6, np.float64)
    benchmark(lambda: las.x >= 140.7329047)


def test_bench_normal_field_comparison(benchmark):
    las = laspy.create()
    las.x = np.zeros(10**6, np.float64)
    benchmark(lambda: las.X >= 779012)
