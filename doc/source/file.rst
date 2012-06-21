File
==================

The File class is the core laspy tool. It provides access to point records and 
dimensions via the :obj:`laspy.base.reader` and :obj:`laspy.base.writer` classes, 
and holds a reference to a :obj:`laspy.header.HeaderManager` instance to provide
heade reading and modifying capability. It is also iterable and sliceable.

**Dimensions:**
    In addition to grabbing whole point records, it is possible 
    to obtain and set individuals dimensions as well. The dimensions available
    to a particular file depend on the point format, a summary of which is 
    available via the File.point_format.xml() method. Dimensions might
    be used as follows: ::

        # Flip the X and Y Dimensions
        >>> FileObject = file.File("./path_to_file", mode = "rw")
        >>> X = FileObject.X
        >>> Y = FileObject.Y
        >>> FileObject.X = Y
        >>> FileObject.Y = X
        >>> FileObject.close()


.. autoclass:: laspy.file.File
    :members: __init__, __iter__, __getitem__, __len__,close, header, open, points, 
             point_format, reader, writer
