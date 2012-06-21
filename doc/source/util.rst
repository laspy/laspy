Util
==================

**The laspy util module holds useful data structures and functions needed in
multiple locations, but not belonging unambiguously to File, Reader/Writer, or
Header**


.. autoclass:: laspy.util.Format
    :members: __init__, __getitem__, __iter__, etree , xml

.. autoclass:: laspy.util.Point
    :members: pack, make_nice

.. autoclass:: laspy.util.Spec
    :members: __init__, etree, xml

.. autoclass:: laspy.util.LaspyException
    :members:

