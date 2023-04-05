====================
What is a LAS file ?
====================

LAS is a public file format meant to exchange 3D point data, mostly used to exchange lidar point clouds.
LAZ is a **lossless** compression of the LAS format.

The latest LAS specification is the `LAS 1.4`_. laspy supports LAS files from Version 1.2 to 1.4.

.. _LAS 1.4: https://www.asprs.org/wp-content/uploads/2010/12/LAS_1_4_r13.pdf

LAS files are organized in 3 main parts:

1) Header
2) VLRs
3) Point Records

Header
------

The header contains information about the data such as its version, the point format (which tells the different
dimensions stored for each points).

See :ref:`accessing_header`

VLRs
----

After the header, LAS files may contain VLRs (Variable Length Record).
VLRs are meant to store additional information such as the SRS (Spatial Reference System),
description on extra dimensions added to the points.

VLRs are divided in two parts:

1) header
2) payload

The payload is limited to 65,535 bytes (Because in the header, the length of the payload is stored on a uint16).

See :ref:`manipulating_vlrs`



Point Records
-------------
The last chunk of data (and the biggest one) contains the point records. In a LAS file, points are stored sequentially.

The point records holds the point cloud data the LAS Spec specifies 10 point formats.
A point format describe the dimensions stored for each point in the record.

Each LAS specification added new point formats, the table below describe the compatibility between point formats
and LAS file version.

+-----------------+-----------------------------------+
|LAS file version + Compatible point formats          |
+=================+===================================+
|1.2              | 0, 1, 2, 3                        |
+-----------------+-----------------------------------+
|1.3              | 0, 1, 2, 3, 4, 5                  |
+-----------------+-----------------------------------+
|1.4              | 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10  |
+-----------------+-----------------------------------+

The names written in the tables below are the one you will have to use in
your code.

.. note::

    The dimensions 'X', 'Y', 'Z' are signed integers without the scale and
    offset applied. To access the coordinates as doubles simply use 'x', 'y' , 'z'


Point Format 0
++++++++++++++

+----------------------+-----------+--------------+
| Dimensions           |   Type    |  Size (bit)  |
+======================+===========+==============+
| X                    |  signed   |      32      |
+----------------------+-----------+--------------+
| Y                    |  signed   |      32      |
+----------------------+-----------+--------------+
| Z                    |  signed   |      32      |
+----------------------+-----------+--------------+
| intensity            | unsigned  |      16      |
+----------------------+-----------+--------------+
| return_number        | unsigned  |      3       |
+----------------------+-----------+--------------+
| number_of_returns    | unsigned  |      3       |
+----------------------+-----------+--------------+
| scan_direction_flag  | bool      |      1       |
+----------------------+-----------+--------------+
| edge_of_flight_line  | bool      |      1       |
+----------------------+-----------+--------------+
| classification       | unsigned  |      5       |
+----------------------+-----------+--------------+
| synthetic            | bool      |      1       |
+----------------------+-----------+--------------+
| key_point            | bool      |      1       |
+----------------------+-----------+--------------+
| withheld             | bool      |      1       |
+----------------------+-----------+--------------+
| scan_angle_rank      | signed    |      8       |
+----------------------+-----------+--------------+
| user_data            | unsigned  |      8       |
+----------------------+-----------+--------------+
| point_source_id      | unsigned  |      8       |
+----------------------+-----------+--------------+


The point formats 1, 2, 3, 4, 5 are based on the point format 0, meaning that they have
the same dimensions plus some additional dimensions:

Point Format 1
++++++++++++++

+----------------------+-----------+--------------+
| Added dimensions     |   Type    |  Size (bit)  |
+======================+===========+==============+
| gps_time             |  Floating |      64      |
+----------------------+-----------+--------------+


Point Format 2
++++++++++++++

+----------------------+-----------+--------------+
| Added dimensions     |   Type    |  Size (bit)  |
+======================+===========+==============+
| red                  |  unsigned |      16      |
+----------------------+-----------+--------------+
| green                |  unsigned |      16      |
+----------------------+-----------+--------------+
| blue                 |  unsigned |      16      |
+----------------------+-----------+--------------+

Point Format 3
++++++++++++++

+----------------------+-----------+--------------+
| Added dimensions     |   Type    |  Size (bit)  |
+======================+===========+==============+
| gps_time             |  Floating |      64      |
+----------------------+-----------+--------------+
| red                  |  unsigned |      16      |
+----------------------+-----------+--------------+
| green                |  unsigned |      16      |
+----------------------+-----------+--------------+
| blue                 |  unsigned |      16      |
+----------------------+-----------+--------------+


Point Format 4
++++++++++++++

+----------------------------+-----------+--------------+
| Added dimensions           |   Type    |  Size (bit)  |
+============================+===========+==============+
| gps_time                   | Floating  |       64     |
+----------------------------+-----------+--------------+
| wavepacket_index           | unsigned  |      8       |
+----------------------------+-----------+--------------+
| wavepacket_offset          | unsigned  |      64      |
+----------------------------+-----------+--------------+
| wavepacket_size            | unsigned  |      32      |
+----------------------------+-----------+--------------+
| return_point_wave_location | floating  |      32      |
+----------------------------+-----------+--------------+
| x_t                        | floating  |      32      |
+----------------------------+-----------+--------------+
| y_t                        | floating  |      32      |
+----------------------------+-----------+--------------+
| z_t                        | floating  |      32      |
+----------------------------+-----------+--------------+

Point Format 5
++++++++++++++

+----------------------------+-----------+--------------+
| Added dimensions           |   Type    |  Size (bit)  |
+============================+===========+==============+
| gps_time                   |  Floating |       64     |
+----------------------------+-----------+--------------+
| red                        |  unsigned |      16      |
+----------------------------+-----------+--------------+
| green                      |  unsigned |      16      |
+----------------------------+-----------+--------------+
| blue                       |  unsigned |      16      |
+----------------------------+-----------+--------------+
| wavepacket_index           | unsigned  |      8       |
+----------------------------+-----------+--------------+
| wavepacket_offset          | unsigned  |      64      |
+----------------------------+-----------+--------------+
| wavepacket_size            | unsigned  |      32      |
+----------------------------+-----------+--------------+
| return_point_wave_location | unsigned  |      32      |
+----------------------------+-----------+--------------+
| x_t                        | floating  |      32      |
+----------------------------+-----------+--------------+
| y_t                        | floating  |      32      |
+----------------------------+-----------+--------------+
| z_t                        | floating  |      32      |
+----------------------------+-----------+--------------+


Point Format 6
++++++++++++++

The Point Format 6, is the new base point format (6, 7, 8, 9, 10) introduced in the LAS specification 1.4.
The main modifications from point format 0 and point format 6 are that now the gps_time is baseline
and some fields takes more bits, for example the classification is now stored on 8 bits (previously 5).


+----------------------+-----------+--------------+
| Dimensions           |   Type    |  Size (bit)  |
+======================+===========+==============+
| X                    |  signed   |      32      |
+----------------------+-----------+--------------+
| Y                    |  signed   |      32      |
+----------------------+-----------+--------------+
| Z                    |  signed   |      32      |
+----------------------+-----------+--------------+
| intensity            | unsigned  |      16      |
+----------------------+-----------+--------------+
| return_number        | unsigned  |      4       |
+----------------------+-----------+--------------+
| number_of_returns    | unsigned  |      4       |
+----------------------+-----------+--------------+
| synthetic            | bool      |      1       |
+----------------------+-----------+--------------+
| key_point            | bool      |      1       |
+----------------------+-----------+--------------+
| withheld             | bool      |      1       |
+----------------------+-----------+--------------+
| overlap              | bool      |      1       |
+----------------------+-----------+--------------+
| scanner_channel      | unsigned  |      2       |
+----------------------+-----------+--------------+
| scan_direction_flag  | bool      |      1       |
+----------------------+-----------+--------------+
| edge_of_flight_line  | bool      |      1       |
+----------------------+-----------+--------------+
| classification       | unsigned  |      8       |
+----------------------+-----------+--------------+
| user_data            | unsigned  |      8       |
+----------------------+-----------+--------------+
| scan_angle           | signed    |      16      |
+----------------------+-----------+--------------+
| point_source_id      | unsigned  |      8       |
+----------------------+-----------+--------------+
| gps_time             | Floating  |      64      |
+----------------------+-----------+--------------+

Point Format 7
++++++++++++++

Add RGB to point format 6.

+----------------------------+-----------+--------------+
| Added dimensions           |   Type    |  Size (bit)  |
+============================+===========+==============+
| red                        |  unsigned |      16      |
+----------------------------+-----------+--------------+
| green                      |  unsigned |      16      |
+----------------------------+-----------+--------------+
| blue                       |  unsigned |      16      |
+----------------------------+-----------+--------------+


Point Format 8
++++++++++++++

Adds RGB and Nir (Near Infrared) to point format 6.

+----------------------------+-----------+--------------+
| Added dimensions           |   Type    |  Size (bit)  |
+============================+===========+==============+
| red                        |  unsigned |      16      |
+----------------------------+-----------+--------------+
| green                      |  unsigned |      16      |
+----------------------------+-----------+--------------+
| blue                       |  unsigned |      16      |
+----------------------------+-----------+--------------+
| nir                        | unsigned  |      16      |
+----------------------------+-----------+--------------+


Point Format 9
++++++++++++++

Add waveform data to points

+----------------------------+-----------+--------------+
| Added dimensions           |   Type    |  Size (bit)  |
+============================+===========+==============+
| wavepacket_index           | unsigned  |      8       |
+----------------------------+-----------+--------------+
| wavepacket_offset          | unsigned  |      64      |
+----------------------------+-----------+--------------+
| wavepacket_size            | unsigned  |      32      |
+----------------------------+-----------+--------------+
| return_point_wave_location | unsigned  |      32      |
+----------------------------+-----------+--------------+
| x_t                        | floating  |      32      |
+----------------------------+-----------+--------------+
| y_t                        | floating  |      32      |
+----------------------------+-----------+--------------+
| z_t                        | floating  |      32      |
+----------------------------+-----------+--------------+


Point Format 10
+++++++++++++++

Adds RGB, Nir (near infrared), waveform data to point format 6

+----------------------------+-----------+--------------+
| Added dimensions           |   Type    |  Size (bit)  |
+============================+===========+==============+
| red                        |  unsigned |      16      |
+----------------------------+-----------+--------------+
| green                      |  unsigned |      16      |
+----------------------------+-----------+--------------+
| blue                       |  unsigned |      16      |
+----------------------------+-----------+--------------+
| nir                        | unsigned  |      16      |
+----------------------------+-----------+--------------+
| wavepacket_index           | unsigned  |      8       |
+----------------------------+-----------+--------------+
| wavepacket_offset          | unsigned  |      64      |
+----------------------------+-----------+--------------+
| wavepacket_size            | unsigned  |      32      |
+----------------------------+-----------+--------------+
| return_point_wave_location | unsigned  |      32      |
+----------------------------+-----------+--------------+
| x_t                        | floating  |      32      |
+----------------------------+-----------+--------------+
| y_t                        | floating  |      32      |
+----------------------------+-----------+--------------+
| z_t                        | floating  |      32      |
+----------------------------+-----------+--------------+


EVLRs
-----

Version 1.4 of the LAS specification added a last block following the point records: EVLRs (Extended Variable
Length Record) which are the same thing as VLRs but they can carry a higher payload (length of the payload is stored
on a uint64)
