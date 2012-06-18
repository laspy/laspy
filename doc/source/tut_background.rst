Background: What are LAS Files?
===============================

**LIDAR Data**

LIDAR data is analogous to RADAR with LASERs, and is short for Light Detection
and Ranging. This library provides a python API to read, write, and manipulate one popular 
format for storing LIDAR data: the .LAS file, and provides the data as numpy arrays. 

LAS files are binary files packed according to several specifications. 

**LAS Specifications**

Currently, laspy supports LAS formats 1.0 to 1.2, although support for 1.3 formatted files
is a definite, and mostly complete, next step. The specifications are detailed below:

http://www.asprs.org/a/society/committees/standards/asprs_las_format_v10.pdf 
http://www.asprs.org/a/society/committees/standards/asprs_las_format_v11.pdf 
http://www.asprs.org/a/society/committees/standards/asprs_las_format_v12.pdf 
http://www.asprs.org/a/society/committees/standards/asprs_las_spec_v13.pdf

There is also a version 1.4 specification, but it is not much used in practice yet, and laspy does not
currently support it.

Broadly speaking, these three specifications are cumulative - each adds more potential 
configurations to the last, while (mostly) avoiding backwards incompatability. 







