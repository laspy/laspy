# Laspy

Laspy is a python library for reading, modifying and creating LAS LiDAR
files.

## Introduction

Laspy is a pythonic library for reading, modifying and writing LAS
files. Support for LAZ files rely on the external libraries LASzip and LAStools and is limited to reading LAS version 1.0-1.3 files.
Laspy is compatible with Python 2.6+ and 3.5+.

Laspy includes a set of command line tools which can be used to do basic
file operations like format translation and validation as well as
comparing LAS files.

## Example

A simple example to show the basics of Laspy. Here we create an output
file that only consists of terrain points from the input file:

```python

from laspy.file import File
import numpy as np

inFile = File('/path/to/file.las', mode='r')

I = inFile.Classification == 2

outFile = File('/path/to/output.las', mode='w', header=inFile.header)
outFile.points = inFile.points[I]
outFile.close()
```

API Documentation and tutorials are available at
[PythonHosted](http://pythonhosted.org/laspy).

## Installation

Laspy can be installed either with `pip`:

```
pip install laspy
```

or by running the setup script included in the source distribution:

```
python setup.py build --user
python setup.py install --user
```

Laspy is only dependent on numpy and should therefore work on Linux, OS
X and Windows as long as a working installation of numpy is available.

To install LASzip and LAStools for LAZ support on Unix systems:
```
git clone https://github.com/LASzip/LASzip.git
cd LASzip
git checkout 3.4.3
cmake .
make
sudo make install
```
and
```
wget http://lastools.org/download/LAStools.zip
unzip LAStools.zip
cd LAStools
make
sudo cp bin/laszip /usr/local/bin
sudo ln -s /usr/local/bin/laszip /usr/local/bin laszip-cli
```

## Changelog

### Version 1.7.0

- Fixed bug in point record format 5, 9 and 10 [#105](https://github.com/laspy/laspy/issues/105)
- Return explicit msg if laszip executable was not found [#110](https://github.com/laspy/laspy/issues/110)
- Supprt numpy 1.17 [#122](https://github.com/laspy/laspy/issues/122)



### Version 1.6.0

- Bug fix  [#92](https://github.com/laspy/laspy/issues/92)
- Test creation of all valid custom dimension data types
- Modify handling of extra bytes to be char data instead of numeric byte data

### Version 1.5.1

- Bug fixes [#67](https://github.com/laspy/laspy/pull/67), [#75](https://github.com/laspy/laspy/pull/75), [b02b40900b5](https://github.com/laspy/laspy/commit/b02b40900b5620972930cd0c201b4db1a6a69754)
- Allow usage of `laszip-cli` when working with LAZ files [#77](https://github.com/laspy/laspy/pull/77)

### Version 1.5.0

- Improved memory handling in base.FileManager [#48](https://github.com/laspy/laspy/pull/48)
- Introduced `r-` file mode, that only reads the header of as LAS file [#48](https://github.com/laspy/laspy/pull/48)
- LAS v. 1.4 bug fixes [#55](https://github.com/laspy/laspy/pull/55)
- Python 3 support [#62](https://github.com/laspy/laspy/pull/62)

