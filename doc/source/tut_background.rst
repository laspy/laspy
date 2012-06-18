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
        the original 1.0 specification used a point field called *"File Marker"*, which was
        generally neglected. We will therefore use the more recent *"User Data"* nomenclature.

There are two bytes per point record dedicated to sub-byte length fields, one called by laspy *flag_byte*
and the other called *raw_classification*. These are detailed below, and are available from Laspy
in the same way as full size dimensions:

*Flag Byte*

======================  ====================  ==============================
 Field Name              Laspy Abbreviation    Length(in bits)
======================  ====================  ==============================
 Return Number           return_num            3
 Number of Returns       num_returns           3
 Scan Direction Flag     scan_dir_flag         1
 Edge of Flight Line     edge_flight_line      1
======================  ====================  ==============================


*Classification Byte*

======================  ====================  ==============================
 Field Name              Laspy Abbreviation    Length(in bits)
======================  ====================  ==============================
 Classification          classification        4
 Synthetic               synthetic             1
 Key Point               key_point             1
 Withheld                withheld              1
======================  ====================  ==============================

The five possible point formats are detailed below:

*Point Format 0*

======================  ====================  ==============================
 Field Name              Laspy Abbreviation    File Format[number] (length)
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

*Point Format 1*

======================  ====================  ==============================
 Field Name              Laspy Abbreviation    File Format[number] (length)
======================  ====================  ==============================
 X                       X (x for scaled)      long[1] (4)
 Y                       Y (y for scaled)      long[1] (4)
 Z                       Z (z for scaled)      long[1] (4)
 Intensity               intensity             unsigned short[1] (2)
 (Flag Byte)             flag_byte             unsigned byte[1]  (1)
 (Classification Byte)   raw_classification    unsigned byte[1]  (1)
 User Data               user_data             unsigned char[1]  (1)
 Point Source Id         pt_src_id             unsigned short[1] (2)
 GPS Time                gps_time              double[1] (8)
======================  ====================  ==============================

*Point Format 2*

======================  ====================  ==============================
 Field Name              Laspy Abbreviation    File Format[number] (length)
======================  ====================  ==============================
 X                       X (x for scaled)      long[1] (4)
 Y                       Y (y for scaled)      long[1] (4)
 Z                       Z (z for scaled)      long[1] (4)
 Intensity               intensity             unsigned short[1] (2)
 (Flag Byte)             flag_byte             unsigned byte[1]  (1)
 (Classification Byte)   raw_classification    unsigned byte[1]  (1)
 User Data               user_data             unsigned char[1]  (1)
 Point Source Id         pt_src_id             unsigned short[1] (2)
 Red                     red                   unsigned short[1] (2)
 Green                   green                 unsigned short[1] (2)
 Blue                    blue                  unsigned short[1] (2)
======================  ====================  ==============================

*Point Format 3*

======================  ====================  ==============================
 Field Name              Laspy Abbreviation    File Format[number] (length)
======================  ====================  ==============================
 X                       X (x for scaled)      long[1] (4)
 Y                       Y (y for scaled)      long[1] (4)
 Z                       Z (z for scaled)      long[1] (4)
 Intensity               intensity             unsigned short[1] (2)
 (Flag Byte)             flag_byte             unsigned byte[1]  (1)
 (Classification Byte)   raw_classification    unsigned byte[1]  (1)
 User Data               user_data             unsigned char[1]  (1)
 Point Source Id         pt_src_id             unsigned short[1] (2)
 GPS Time                gps_time              double[1] (8)
 Red                     red                   unsigned short[1] (2)
 Green                   green                 unsigned short[1] (2)
 Blue                    blue                  unsigned short[1] (2)
======================  ====================  ==============================

*Point Format 4* (Not Currently Supported)

===============================  ==============================  ==============================
 Field Name                       Laspy Abbreviation              File Format[number] (length)
===============================  ==============================  ==============================
 X                                X (x for scaled)                long[1] (4)
 Y                                Y (y for scaled)                long[1] (4)
 Z                                Z (z for scaled)                long[1] (4)
 Intensity                        intensity                       unsigned short[1] (2)
 (Flag Byte)                      flag_byte                       unsigned byte[1]  (1)
 (Classification Byte)            raw_classification              unsigned byte[1]  (1)
 User Data                        user_data                       unsigned char[1]  (1)
 Point Source Id                  pt_src_id                       unsigned short[1] (2)
 GPS Time                         gps_time                        double[1] (8)
 Wave Packet Descriptor Index     wavefm_packet_desc_index        unsigned char[1] (1)
 Byte Offset to Waveform Data     byte_offset_to_waveform_data    unsigned long long[1] (8)
 Waveform Packet Size             waveform_packet_size            unsigned long[1] (4)
 Return Point Waveform Location   return_pt_waveform_loc          float[1] (4)
 X(t)                             x_t                             float[1] (4)
 Y(t)                             y_t                             float[1] (4)
 Z(t)                             z_t                             float[1] (4)
===============================  ==============================  ==============================

*Point Format 5* (Not Currently Supported)

===============================  ==============================  ==============================
 Field Name                       Laspy Abbreviation              File Format[number] (length)
===============================  ==============================  ==============================
 X                                X (x for scaled)                long[1] (4)
 Y                                Y (y for scaled)                long[1] (4)
 Z                                Z (z for scaled)                long[1] (4)
 Intensity                        intensity                       unsigned short[1] (2)
 (Flag Byte)                      flag_byte                       unsigned byte[1]  (1)
 (Classification Byte)            raw_classification              unsigned byte[1]  (1)
 User Data                        user_data                       unsigned char[1]  (1)
 Point Source Id                  pt_src_id                       unsigned short[1] (2)
 GPS Time                         gps_time                        double[1] (8)
 Red                              red                             unsigned short[1] (2)
 Green                            green                           unsigned short[1] (2)
 Blue                             blue                            unsigned short[1] (2)
 Wave Packet Descriptor Index     wavefm_packet_desc_index        unsigned char[1] (1)
 Byte Offset to Waveform Data     byte_offset_to_waveform_data    unsigned long long[1] (8)
 Waveform Packet Size             waveform_packet_size            unsigned long[1] (4)
 Return Point Waveform Location   return_pt_waveform_loc          float[1] (4)
 X(t)                             x_t                             float[1] (4)
 Y(t)                             y_t                             float[1] (4)
 Z(t)                             z_t                             float[1] (4)
===============================  ==============================  ==============================



