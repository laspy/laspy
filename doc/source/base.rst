Base
==================

**Base Module Basics:**

Most of the functionality of laspy is exposed on the file and header modules, 
however it will sometimes be convenient to dig into the base as well. The two
workhorses of the base class are Writer and Reader, and they are both subclasses
of FileManager, which handles a lot of the file initialization logic, as well 
as file reading capability.

.. autoclass:: laspy.base.FileManager
    :members: __init__

.. autoclass:: laspy.base.Reader
    :members: close, get_dimension, get_header, get_header_property, get_padding,get_point, get_points, get_pointrecordscount, get_raw_point,
              get_vlrs, populate_vlrs

.. autoclass:: laspy.base.Writer
    :members: close, pad_file_for_point_recs, _set_datum, set_dimension, set_header_property,set_padding,  set_points, set_vlrs

.. autoclass:: laspy.base.DataProvider
    :members: __getitem__, __setitem__, close,map, open, point_map,get_point_map, remap
