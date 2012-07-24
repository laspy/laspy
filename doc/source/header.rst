Header
====================

**Header Module**

The laspy header module holds the low level :obj:`laspy.header.Header` class, 
which both stores header information during a laspy session, and also provides a 
container for moving header data around. Most of the header API is located in 
the :obj:`laspy.header.HeaderManager` class, which holds a :obj:`laspy.header.Header` instance. 
This is accessed from a :obj:`laspy.file.File` object as :obj:`laspy.file.File`.header

Additionally, this module holds the VLR and EVLR classes, for regular and extended
variable length records as defined in the various LAS specifications. 

Finally, this module provides ExtraBytesStruct, which is a frontend for defining
additional dimensions in the LAS file via an Extra Bytes type VLR. See the tutorial
for an example of this (the LAS specification is also a helpful reference.)

.. autoclass:: laspy.header.ExtraBytesStruct
    :members: __init__, to_byte_string

.. autoclass:: laspy.header.EVLR
    :members: __init__, __len__, parse_data, pack_data,body_summary,to_byte_string

.. autoclass:: laspy.header.Header
    :members: format

.. autoclass:: laspy.header.HeaderManager 
    :members: __init__,data_format_id, data_offset,data_record_length, date, file_signature, file_source_id, global_encoding, guid, header_size, 
              max, major_version,min, minor_version,offset, padding, project_id, point_return_count, save_vlrs, scale, schema,software_id, system_id, 
              update_histogram, update_min_max, version, vlrs 

.. autoclass:: laspy.header.VLR
    :members: __init__, __len__, parse_data, pack_data, body_summary, to_byte_string
