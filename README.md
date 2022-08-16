# Laspy

Laspy is a python library for reading, modifying and creating LAS LiDAR
files.

Laspy is compatible with Python  3.7+.

## Features

- LAS support.
- LAZ support via `lazrs` or `laszip` backend.
- LAS/LAZ streamed/chunked reading/writting.
- [COPC] support over files.
- [COPC] support over https with `requests` package.
- CRS support via `pyproj` package.


[COPC]: https://github.com/copcio/copcio.github.io


## Examples

Directly read and write las
```Python
import laspy

las = laspy.read('filename.las')
las.points = las.points[las.classification == 2]
las.write('ground.laz')
```


Open data to inspect header (opening only reads the header and vlrs)

```Python
import laspy

with laspy.open('filename.las') as f:
    print(f"Point format:       {f.header.point_format}")
    print(f"Number of points:   {f.header.point_count}")
    print(f"Number of vlrs:     {len(f.header.vlrs)}")
```
Use the 'chunked' reading & writing features

```Python
import laspy

with laspy.open('big.laz') as input_las:
    with laspy.open('ground.laz', mode="w", header=input_las.header) as ground_las:
        for points in input_las.chunk_iterator(2_000_000):
            ground_las.write_points(points[points.classification == 2])

```

Appending points to existing file

```Python
import laspy

with laspy.open('big.laz') as input_las:
    with laspy.open('ground.laz', mode="a") as ground_las:
        for points in input_las.chunk_iterator(2_000_000):
            ground_las.append_points(points[points.classification == 2])
```

API Documentation and tutorials are available at
[ReadTheDocs](https://laspy.readthedocs.io/en/latest/).

## Installation

Laspy can be installed either with `pip`:

```
pip install laspy # without LAZ support
# Or
pip install laspy[laszip] # with LAZ support via LASzip
# Or
pip install laspy[lazrs] # with LAZ support via lazrs
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md)
