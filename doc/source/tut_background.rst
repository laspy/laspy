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

**Point Formats**

======================  =========================
 LAS Format              Point Formats Supported
======================  =========================
 Version 1.0             0, 1
 Version 1.1             0, 1
 Version 1.2             0, 1, 2, 3
 Version 1.3             0, 1, 2, 3, 4, 5
======================  ========================= 

    .. note::
        Where there exist discrepencies between the use of point fields between
        LAS versions, we will assume that the more recent version is used. For example,
        the original 1.0 specification used a point field called "File Marker", which was
        generally neglected. We will therefore use the more recent "User Data" nomenclature.

*Point Format 0*

======================  ====================  ==============================
 Feild Name              Laspy Abbreviation    File Format[number] (length)
======================  ====================  ==============================
 X                       X (x for scaled)      long[1] (4)
 Y                       Y (y for scaled)      long[1] (4)
 Z                       Z (z for scaled)      long[1] (4)
 Intensity               intensity             unsigned short[1] (2)
 (Flag Byte)             flag_byte             unsigned byte[1]  (1)
 (Classification Byte)   raw_classification    unsigned byte[1]  (1)
 User Data               user_data             unsigned char[1]  (1)
 Point Source Id         pt_src_id             unsigned short[1] (2)
======================  ====================  ==============================


