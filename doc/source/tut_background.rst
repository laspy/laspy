Background: What are LAS Files?
===============================

**LIDAR Data**

LIDAR data is analogous to RADAR with LASERs, and is short for Light Detection
and Ranging. This library provides a python API to read, write, and manipulate one popular 
format for storing LIDAR data, the .LAS file.

LAS files are binary files packed according to several specifications. 

**LAS Specifications**

laspy 1.0 supports LAS formats 1.0 to 1.2, and provides preliminary support for formats 1.3 and 1.4. 

http://www.asprs.org/a/society/committees/standards/asprs_las_format_v10.pdf 
http://www.asprs.org/a/society/committees/standards/asprs_las_format_v11.pdf 
http://www.asprs.org/a/society/committees/standards/asprs_las_format_v12.pdf 
http://www.asprs.org/a/society/committees/standards/LAS_1_3_r11.pdf
http://www.asprs.org/a/society/committees/standards/LAS_1_4_r11.pdf
There is also a version 1.4 specification, but support for it is not yet complete.

.. note::
    If you have access to good version 1.3 or version 1.4 LAS files, or feedback on any
    of the features of laspy, shoot us an email:
    grant.brown73@gmail.com

Much of the data required for laspy to know how to read the LAS file is present 
in the header, which laspy interacts with according to the pattern below. There are 
some minor departures from the raw specification for convenience, namely combining
the Day+Year fields into a python :obj:`datetime.datetime` object, and placing
the X Y and Z scale and offset values together. 


**Version 1.0 - 1.2**

===============================  ==============================  ==============================
 Field Name                       Laspy Abbreviation              File Format[number] (length)
===============================  ==============================  ==============================
 File Signature                   file_signature                  char[4] (4)
 File Source Id                   file_source_id                  unsigned short[1] (2)
 (Reserved or Global Encoding)    global_encoding                 unsigned short[1] (2)
 Gps Time Type                    gps_time_type                   Part of Global Encoding
 Project Id (4 combined fields)   guid                            ulong+ushort+ushort+char[8] (16)
 Verion Major                     version_major                   unsigned char[1] (1)
 Version Minor                    version_minor                   unsigned char[1] (1)
 Version Major + Minor            version                         (see above)
 System Identifier                system_id                       char[32] (32)
 Generating Software              software_id                     char[32] (32)
 File Creation Day of Year        (handled internally)            unsigned short[1] (2)
 File Creation Year               (handled internally)            unsigned short[1] (2)
 Creation Day + Year              date                            (see above)
 Header Size                      header_size                     unsigned short[1] (2)
 Offset to Point Data             data_offset                     unsigned long[1] 4
 Number of Variable Length Recs   (handled internally)            unsigned long[1] 4
 Point Data Format Id             data_format_id                  unsigned char[1] (1)
 Data Record Length               data_record_length              unsigned short[1] (2)
 Number of point records          records_count                   unsigned long[1] (4)
 Number of Points by Return Ct.   point_return_count              unsigned long[5 or 7] (20 or 28)
 Scale Factor (X, Y, Z)           scale                           double[3] (24)
 Offset (X, Y, Z)                 offset                          double[3] (24)
 Max (X, Y, Z)                    max                             double[3] (24)
 Min (X, Y, Z)                    min                             double[3] (24)
===============================  ==============================  ==============================

**Version 1.3 (appended)**

===============================  ==============================  ==============================
 Start of waveform data record    start_waveform_data_rec         unsigned long long[1] (8)
===============================  ==============================  ==============================

**Version 1.4 (appended)**

===============================  ==============================  ==============================
 Start of first EVLR              start_first_evlr                unsigned long long[1] (8) 
 Number of EVLRs                  num_evlrs                       unsigned long[1] (4)
 Number of point records          point_records_count             unsigned long long[1] (8)
 Number of points by return ct.   point_return_count              unsigned long long[15] (120)
===============================  ==============================  ==============================


In addition, the LAS 1.4 specification replaces the point_records_count and point_return_count
fields present in previous versions with legacy_point_records_count and legacy_point_return_count, 
which match the specification of their original counterparts. 

Therefore broadly speaking, with the exception of the 1.4 legacy fields and format changes, these 
specifications are cumulative - each adds more potential configurations to the last, 
while (mostly) avoiding backwards incompatability. 

**Point Formats**

======================  ==================================
 LAS Format              Point Formats Supported
======================  ==================================
 Version 1.0             0, 1
 Version 1.1             0, 1
 Version 1.2             0, 1, 2, 3
 Version 1.3             0, 1, 2, 3, 4, 5
 Version 1.4             0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
======================  ==================================

    .. note::
        Where there exist discrepencies between the use of point fields between
        LAS versions, we will assume that the more recent version is used. For example,
        the original 1.0 specification used a point field called *"File Marker"*, which was
        generally neglected. We will therefore use the more recent *"User Data"* nomenclature.


**Point Formats 0-5**

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


**Point Formats 6-10**

The new point formats introduced by LAS specification 1.4 shuffle the bit fields 
around a bit. 

*Flag Byte*

======================  ====================  ==============================
 Field Name              Laspy Abbreviation    Length(in bits)
======================  ====================  ==============================
 Return Number           return_num            4
 Number of Returns       num_returns           4
======================  ====================  ==============================

*Classification Flags*

======================  =====================  ==============================
 Field Name              Laspy Abbreviation     Length(in bits)
======================  =====================  ==============================
 Classification Flags    classification_flags   4
 Scanner Channel         scanner_channel        2
 Scan Direction Flag     scan_dir_flag          1
 Edge of Flight Line     edge_flight_line       1
======================  ====================  ==============================

*Classification Byte*

LAS 1.4 introduces a byte sized classification field, and this is interpreted 
as an integer. For information on the interpretation of the Classification Byte
field, see the LAS specification. This dimension is accessable in laspy as simply
:obj:`laspy.file.File`.classification for files which make the field available. 
In files without the full byte classification, this property provides the 4 bit 
classification field which becomes "classification_flags" in 1.4. 

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



