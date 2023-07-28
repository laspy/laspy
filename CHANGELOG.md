# Changelog

## Version 2.5.1 (28/07/2023)

### Fixed
- Fixed bug in laz backend handling in the CLI

## Version 2.5.0 (23/07/2023)

### Added
- Added optional CLI. It can be installed using the `cli` extra
(`pip install laspy[cli]`). It has `info`, `compress`, `decompress`, `convert`
and `copc query` commands.
- Added a `prefer_wkt` option to `LasHeader.parse_crs`
(true by default) to prefer (or not) WKT VLR over Geotiff VLR
in case both are present in the file.

### Fixed
- laspy.open will now properly close the opened file
if an exception is raised.
- Wavepackets's `return_point_wave_location` is now
properly returned as as float32 and not an uint32.
- `parse_crs` properly checks that ProjectedCRSGeoKey/GeodeticCRSGeoKey
is in range of EPSG code before using pyproj to parse it.
- Missing `super.__init__()` in `CopcHierarchyVlr`.
- Copc no longer include the hierarchy page twice
- A LasHeader with a custom `creation_date`/`date` will
no longer be reset to `date.today` upon writing.

---


## Version 2.4.1 (20/02/2022)

### Fixed
- Removed spurious `print` in copc.py and compression.py

## Version 2.4.0 (11/02/2022)

## Added
- `read_evlrs` option (default true) to `laspy.open`, `laspy.LasReader.__init__` and `laspy.LasHeader.read_from`
  Which allows to skip reading the EVLRs when opening a file. This can be useful when
  opening a LAS file from a non seekable source / where seeking is expensive as reading
  EVLRs requires seeking to the end of the file.
- Selective decompression feature that allows to select in a LAS 1.4 (fmt >= 6 && <= 10)
  which fields should be decompressed allowing to save time by decompressing only the fields
  that are needed. Works with LAZ and COPC files.

## Changed
- The internal point reader is lazily created when the first point is actually read

## Fixed
- LasAppender when input file's last chunk is complete
- Handle redundant CSs in GeoKeyDirectoryVlr

## Version 2.3.0 (25/10/2022)

### Changed
- EVLRs are now read during the file opening part.
- EVLRs are now part of the `LasHeader` class, but are still accesible
  via `LasReader.evlrs` or `LasData.evlrs.

### Fixed
- Fixed CRS parsing on fiels with both `GeoKeyDirectoryVlr` and `WktCoordinateSystemVlr` and the first one is empty
- `LasHeader.parse_crs` also looks for the CRS VLRs in the EVLRs of the file.
- Fixed `LasHeader.generating_software` and `LasHeader.system_id` being limited to 31
  bytes instead of 32.
- Fixed `laspy.convert` to ensure the returng `LasData.evlrs` is a `Vlrlist` and
  no simply a `list`

---

## Version 2.2.0 (29/06/2022)

### Added
- Added support for querying COPC LAZ files via a new class `CopcReader`.
- Added new optional feature to support adding CRS / SRS to a LAS file from a `pyproj.CRS` as
  well as reading the CRS / SRS information from a LAS file to a `pyproj.CRS`. 

### Fixed
- Fixed support for stream / source that are not `seekable`.

### Changed
- Support for Python3.6 removed.

---

## Version 2.2.0 beta 1 (14/06/2022)

### Added
- Added support for querying COPC LAZ files via a new class `CopcReader`.

### Fixed
- Fixed support for stream / source that are not `seekable`.

---

## Version 2.2.0 beta 0 (03/05/2022)

### Added
- Added new optional feature to support adding CRS / SRS to a LAS file from a `pyproj.CRS` as 
  well as reading the CRS / SRS information from a LAS file to a `pyproj.CRS`. 

### Changed
- Support for Python3.6 removed.

---
  
## Version 2.1.2 (18/02/2022)


### Fixed
- Fixed `LasHeader.update` (thus fixing `LasData.update_header`) computation of x,y,z mins and maxs
- Fixed regression introduced in 2.1.0 where changing the `header.scales` and/or `header.offsets`
  on a `LasData` newly created  and then setting `x` `y` or `z` would produce incorrect result.

---

## Version 2.1.1 (23/01/2022)

### Fixed
- Fixed regression introduced in 2.1.0 where setting the x, y or z value would not properly set the corresponding
  X, Y or Z value.
- Fixed `LasData.change_scaling` setting the header's `offsets` and/or `scales` to `None`
  if the corresponding optionnal argument was not given to the `change_scaling` method.
  The header will now correctly keep the corresponding value unchanged.

---

## Version 2.1.0 (09/01/2022)

### Added
- Added a better error message when reading empty files
- Added a new `xyz` attribute to `LasData` that returns x, y, z as a new numpy array or sets the x, y, z from an array
- Added `LasData.remove_extra_dim` and `LasData.remove_extra_dims` to allow the removal of extra dimensions (__only__)

### Changed
- Minimum `lazrs` version updated to 0.4.0 to bring support for LAZ with variable size chunks
  (used in [COPC](https://copc.io) files). the `laszip` backend already supported variable size chunks LAZ.
- Improved assigning to multiple dimensions at once (`las[['x', 'y', 'z']] = ...`)
- `laspy` will no longer raise encoding errors when reading files for which the header's `generating_software` or
  `system_identifier` as well as the vlr's `description` is not `ascii` encoded as the spec mandates.
  However, an encoding error will be raised when writing such files.
- `LasData.__getitem__` will now return a `LasData` when indexing with slice or numpy array.
   `assert isinstance(las[[1, 2, 3, 4]], laspy.LasData)`
 
### Fixed
- Fix `PackedPointRecord.__len__` when array has no dim
- Fix scaled extra byte creation when the offsets/scales given to `ExtraBytesParam` where of type `list` or `tuple`
- Fix `ScaledArrayView` to allow indexing with `list` or `numpy.array`.

---

## Version 2.0.3 (16/09/2021)

### Fixed
- Fix function that parses geotiff VLRs
- Fix handling of points with 'unregistered' extra bytes (PR #158)
- Fix to handle empty LAS/LAZ more robustly

---

## Version 2.0.2 (23/07/2021)

### Changed
- Update minimum lazrs version which allows to:
  - Fix Appending in LAZ files.
  - Improve memory usage when reading/writing. (issue #152)

### Fixed
- Fix `system_identifier` reading by ignoring non ascii characters instead of erroring ,(issue #148, PR #149).
- Fix `LasData.change_scaling` method.

---

## Version 2.0.1 (29/06/2021)

### Fixed
- Fix `.min` `.max` methods of array views
- Ship the tests as part of the source distribution (But they won't be installed with `pip install`)

---

## Version 2.0.0 (15/06/2021)

- Overhaul of the internals by essentially incorporating pylas into laspy,
  while the API to retrieve and set dimensions stayed the same, other parts changed
  and will require adaptation.
- Better LAZ support
    * Added support for writing LAZ
    * Changed decompression mechanism by using either `laszip` python bindings (and not laszip-cli)
      or `lazrs`
- Added ability to read and write LAS/LAS in `stream` / `chunked` mode.
- Changed laspy to support the reading and writing of LAS/LAZ data from and to `file-objects` and `bytes`
- Dropped support for python2.7, python3.6+ is supported.

---

## Version 1.7.0 (13/03/2020)

- Fixed bug in point record format 5, 9 and 10 [#105](https://github.com/laspy/laspy/issues/105)
- Return explicit msg if laszip executable was not found [#110](https://github.com/laspy/laspy/issues/110)
- Supprt numpy 1.17 [#122](https://github.com/laspy/laspy/issues/122)

## Version 1.6.0 (11/10/2018)

- Bug fix  [#92](https://github.com/laspy/laspy/issues/92)
- Test creation of all valid custom dimension data types
- Modify handling of extra bytes to be char data instead of numeric byte data

## Version 1.5.1 (5/12/2017)

- Bug fixes [#67](https://github.com/laspy/laspy/pull/67), [#75](https://github.com/laspy/laspy/pull/75), [b02b40900b5](https://github.com/laspy/laspy/commit/b02b40900b5620972930cd0c201b4db1a6a69754)
- Allow usage of `laszip-cli` when working with LAZ files [#77](https://github.com/laspy/laspy/pull/77)

## Version 1.5.0 (30/03/2017)

- Improved memory handling in base.FileManager [#48](https://github.com/laspy/laspy/pull/48)
- Introduced `r-` file mode, that only reads the header of as LAS file [#48](https://github.com/laspy/laspy/pull/48)
- LAS v. 1.4 bug fixes [#55](https://github.com/laspy/laspy/pull/55)
- Python 3 support [#62](https://github.com/laspy/laspy/pull/62)

