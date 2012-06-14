Header
====================

**Header Module**

The laspy header module holds the :obj:`laspy.header.Header` class, which both stores
header data during a laspy session, and provides a frontend for getting and
setting valid header attributes. This is accessed from a :obj:`laspy.file.File` object as
:obj:`laspy.file.File`.header.<header attribute>.

.. autoclass:: laspy.header.Header
    :members: __init__, file_signature, file_source_id,
                project_id, global_encoding, guid, major_version, minor_version, version,
                system_id, software_id, date, header_size, data_offset,
                padding, records_count, data_format_id, data_record_length,
                schema, point_return_count,scale,offset,min, max,vlrs,
                update_histogram, update_min_max

.. autoclass:: laspy.header.VLR
    :members: __init__, __len__, __to_byte_string__
