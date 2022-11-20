==================
Basic Manipulation
==================

Opening & Reading
=================

Reading
-------

Reading is done using :func:`laspy.read` function.
This function will read everything in the file (Header, vlrs, point records, ...) and return an object
that you can use to access to the data.

.. code-block:: python

    import laspy

    las = laspy.read('somefile.las')
    print(np.unique(las.classification))

Opening
-------

laspy can also :func:`laspy.open` files reading just the header and vlrs but not the points, this is useful
if you are interested in metadata that are contained in the header and do not need to read the points.

.. code-block:: python

    import s3fs
    import laspy

    fs = s3fs.S3FileSystem()
    with fs.open('my-bucket/some_file.las', 'rb') as f:
         if f.header.point_count < 100_000_000:
             las = laspy.read(f)

Chunked reading
---------------

Sometimes files are big, too big to be read entirely and fit into your RAM.
The object returned by the :func:`laspy.open` function, :class:`.LasReader`
can also be used to read points chunk by chunk by using :meth:`.LasReader.chunk_iterator`, which will allow you to do some
processing on large files (splitting, filtering, etc)

.. code-block:: python

    import laspy

    with laspy.open("some_big_file.laz") as f:
        for points in f.chunk_iterator(1_000_000):
            do_something_with(points)


Writing
=======


To be able to write a las file you will need a :class:`.LasData`.
You obtain this type of object by using one of the function described in the section above
use its method :meth:`.LasData.write` to write to a file or a stream.


.. code-block:: python

    import laspy

    las = laspy.read("some_file.laz")
    las.points[las.classification == 2]
    las.write("ground.laz")

Chunked Writing
---------------

Similar to :class:`.LasReader` there exists a way to write a file
chunk by chunk.

.. code-block:: python

    import laspy

    with laspy.open("some_big_file.laz") as f:
        with laspy.open("grounds.laz", mode="w", header=f.header) as writer:
            for points in f.chunk_iterator(1_234_567):
                writer.write_points(points[points.classification == 2]


Creating
========

Creating a new Las from scratch is hopefully simple:

Use :func:`laspy.create`.

Or the :class:`.LasData` constructor which requires a :class:`.LasHeader`.

You can get a header from a file or creating a new one.

.. code-block:: python

    import laspy
    import numpy as np

    las = laspy.read("some_file.laz")

    new_las = laspy.LasData(las.header)
    new_las.points[las.classification == 2].copy()
    new_las.write("ground.laz")

    new_hdr = laspy.LasHeader(version="1.4", point_format=6)
    # You can set the scales and offsets to values tha suits your data
    new_hdr.scales = np.array([1.0, 0.5, 0.1])
    new_las = laspy.LasData(new_hdr)

Converting
==========

laspy also offers the ability to convert a file between the different version and point format available
(as long as they are compatible).

To convert, use the :func:`laspy.convert`

.. _accessing_header:

Accessing the file header
=========================

You can access the header of a las file you read or opened by retrieving the 'header' attribute:

>>> import laspy
>>> las = laspy.read('tests/data/simple.las')
>>> las.header
<LasHeader(1.2, <PointFormat(3, 0 bytes of extra dims)>)>
>>> las.header.point_count
1065


>>> with laspy.open('tests/data/simple.las') as f:
...     f.header.point_count
1065



you can see the accessible fields in :class:`.LasHeader`.


Accessing Points Records
========================

To access point records using the dimension name, you have 2 options:

1) regular attribute access using the `las.dimension_name` syntax
2) dict-like attribute access `las[dimension_name]`.

>>> import numpy as np
>>> las = laspy.read('tests/data/simple.las')
>>> np.all(las.user_data == las['user_data'])
True

Point Format
------------

The dimensions available in a file are dictated by the point format.
The tables in the introduction section contains the list of dimensions for each of the
point format.
To get the point format of a file you have to access it through the las object:

>>> point_format = las.point_format
>>> point_format
<PointFormat(3, 0 bytes of extra dims)>
>>> point_format.id
3

If you don't want to remember the dimensions for each point format,
you can access the list of available dimensions in the file you read just like that:

>>> list(point_format.dimension_names)
['X', 'Y', 'Z', 'intensity', 'return_number', 'number_of_returns', 'scan_direction_flag', 'edge_of_flight_line', 'classification', 'synthetic', 'key_point', 'withheld', 'scan_angle_rank', 'user_data', 'point_source_id', 'gps_time', 'red', 'green', 'blue']

This gives you all the dimension names, including extra dimensions if any.
If you wish to get only the extra dimension names the point format can give them to you:

>>> list(point_format.standard_dimension_names)
['X', 'Y', 'Z', 'intensity', 'return_number', 'number_of_returns', 'scan_direction_flag', 'edge_of_flight_line', 'classification', 'synthetic', 'key_point', 'withheld', 'scan_angle_rank', 'user_data', 'point_source_id', 'gps_time', 'red', 'green', 'blue']
>>> list(point_format.extra_dimension_names)
[]
>>> las = laspy.read('tests/data/extrabytes.las')
>>> list(las.point_format.extra_dimension_names)
['Colors', 'Reserved', 'Flags', 'Intensity', 'Time']

You can also have more information:

>>> point_format[3].name
'intensity'
>>> point_format[3].num_bits
16
>>> point_format[3].kind
<DimensionKind.UnsignedInteger: 1>
>>> point_format[3].max
65535





.. _manipulating_vlrs:

Manipulating VLRs
=================

To access the VLRs stored in a file, simply access the `vlr` member of the las object.

>>> las = laspy.read('tests/data/extrabytes.las')
>>> las.vlrs
[<ExtraBytesVlr(extra bytes structs: 5)>]

>>> with laspy.open('tests/data/extrabytes.las') as f:
...     f.header.vlrs
[<ExtraBytesVlr(extra bytes structs: 5)>]


To retrieve a particular vlr from the list there are 2 ways: :meth:`.VLRList.get` and
:meth:`.VLRList.get_by_id`