Header
====================

**Header Module**

The laspy header module holds the :obj:`laspy.header.Header` class, which both stores
header data during a laspy session, and provides a frontend for getting and
setting valid header attributes. This is accessed from a :obj:`laspy.file.File` object as
:obj:`laspy.file.File`.header.<header attribute>.

.. autoclass:: laspy.header.Header
    :members: __init__,data_format_id, data_offset,data_record_length, date, file_signature, file_source_id, global_encoding, guid, header_size, 
              max, major_version,min, minor_version,offset, padding, project_id, point_return_count,scale, schema,software_id, system_id, 
              update_histogram, update_min_max, version, vlrs 

.. autoclass:: laspy.header.VLR
    :members: __init__, __len__, to_byte_string
