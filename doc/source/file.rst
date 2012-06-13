Laspy: File Module
==================

Dimensions:
    In addition to grabbing file points, as documented below, it is possible 
    to obtain and set individuals dimensions as well. The dimensions available
    to a particular file depend on the point format, a summary of which is 
    available via the get_xml_point_format_summary method. Dimensions might
    be used as follows: ::
        # Flip the X and Y Dimensions
        >>> FileObject = file.File("./path_to_file", mode = "rw")
        >>> X = FileObject.X
        >>> Y = FileObject.Y
        >>> FileObject.X = Y
        >>> FileObject.Y = X
        >>> FileObject.close()


.. autoclass:: laspy.file.File
    :members: __init__, open, close, __len__, __getitem__, __iter__, get_points, set_points, get_xml_point_format_summary, get_xml_header_format_summary
