Base
==================

**Base Module Basics:**

Most of the functionality of laspy is exposed on the file and header modules, 
however it will sometimes be convenient to dig into the base as well. The two
workhorses of the base class are Writer and Reader, and they are both subclasses
of FileManager, which handles a lot of the file initialization logic, as well 
as file reading capability.

.. autoclass:: FileManager
    :members: __init__

.. autoclass:: laspy.base.Reader
    :members: get_dimension, get_header, populate_vlrs, get_vlrs, get_padding, get_pointrecordscount, get_points, get_point, get_raw_point, get_header_property, close

.. autoclass:: laspy.base.Writer
    :members: set_dimension, set_vlrs, set_padding, pad_file_for_point_recs, set_points, set_header_property, set_datum.close

.. autoclass:: laspy.base.DataProvider
    :members: open, close, map, point_map, remap, __getitem__, __setitem__ 


