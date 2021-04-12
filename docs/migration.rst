.. _migration_guides:

Migration guides
================

From laspy 1.7.x to laspy 2.0.0
-------------------------------


laspy 2.0 is essentially a complete overhaul of the code base so you will probably
have a few changes to make to the parts of your code that uses laspy 1.7.

However there should not be that many, and should hopefully be worth.

The benefits of laspy 2.0 are:
 - Better LAZ support: reading *and* writing of LAZ 1.1 to 1.4 (See the :ref:`installation` section)
 - Support for Chunked / Streaming reading and writing of LAS/LAZ files.
 - Support for reading data coming from other sources than files on disk (bytes or file-objects)


The biggest changes between 1.7 and 2.0 are how files are read and written.



laspy 1.7 had the concept of `laspy.File` with an open mode.
laspy 2.0 does not have the `laspy.File` class anymore but a :class:`.LasData`
class instead which provide access to the `header`, `vlrs` and fields/dimensions.

The `get_*` and `set_*` (eg `get_classification`) of `laspy.File` are not available in the new  :class:`.LasData`.


The following sections should hopefully get you started

Reading a file
______________

.. code-block:: python

    import laspy

    # Opening a file in laspy 1.7
    file = laspy.file.File("somepath.las", mode ="r")

    # Reading a file in laspy 2.0
    las = laspy.read("somepath.las")


Accessing the point fields / dimensions
_______________________________________

.. code-block:: python

     # accessing a field in laspy 1.7:
     classification = file.classification

     # accessing a field in laspy 2.0 (names from 1.7 should be compatible with 2.0):
     classification = las.classification


Writing
_______

.. code-block:: python

    # laspy 1.7:
    file.pt_src_id[:] = 2
    file.close()

    # laspy 2.0
    las.pt_src_id[:] = 2
    las.write("somepath.laz")


Creating a file
_______________

.. code-block:: python

    import laspy

    # laspy 1.7
    new_file = laspy.file.File("new_path.las", header=file.header, mode="w")
    new_file.X = ...
    new_file.Y = ...
    ...
    new_file.close()

    # laspy 2.0
    new_las = laspy.LasData(las.header)
    new_las.X = ...
    new_las.Y = ...
    ...
    new_las.write("new_las.las")

    # if you do not have an existing header:
    new_las = laspy.create(file_version="1.2", point_format=3)
    new_las.X = ...
    new_las.Y = ...
    ...
    new_las.write("new_las.las")

    # or
    new_header = laspy.LasHeader(version="1.2", point_format=3)
    new_las = laspy.LasData(las.header)
    new_las.X = ...
    new_las.Y = ...
    ...
    new_las.write("new_las.las")


Header change
_____________

The `Header` (:class:`.LasHeader`) class was modernized from laspy 1.7 to laspy 2.0,
a few of the field names in the new header class do not have the same name.

+--------------------+------------------------------+
| 1.7 name           |   2.0 name                   |
+====================+==============================+
| max                |  maxs                        |
+--------------------+------------------------------+
| min                |  mins                        |
+--------------------+------------------------------+
| scale              |  scales                      |
+--------------------+------------------------------+
| offset             |  offsets                     |
+--------------------+------------------------------+
| filesource_id      |  file_source_id              |
+--------------------+------------------------------+
| major_version      |  version.major               |
+--------------------+------------------------------+
| minor_version      |  version.minor               |
+--------------------+------------------------------+
| system_id          |  system_identifier           |
+--------------------+------------------------------+
| date               |  creation_date               |
+--------------------+------------------------------+
| point_return_count |  number_of_points_by_return  |
+--------------------+------------------------------+
| software_id        |  generating_software         |
+--------------------+------------------------------+

From pylas 0.4.x to laspy 2.0.0
-------------------------------

laspy 2.0 is essentially pylas, so the core of the library is the same.

Changes in LAZ backend
______________________

With laspy 2.0.0, the lazperf backend
support was dropped, and the laszip backend
changed from using the laszip executable
to using laszip python bindings.

If you used lazperf or relied on the laszip executable
you'll have to choose between the available backends.
(see Installation section).


Changes in bit fields
_____________________

Some fields in LAS are 'bit fields'.

with laspy 0.4.x, there was a inconsistency between
'normal' fields and 'bit' fields, when getting a bit field,
laspy returned a copy of the values in a new numpy array whereas
when getting a normal field, the array you got acted as a 'view'
on the real array where the values where stored.

That meant that modifying the values of the array you got from
a bit field would no propagate to the real array.

.. code-block:: python

    import laspy
    import numpy as np

    las = laspy.read("tests/simple.las")

    # return number is a bit field
    print(las.return_number)
    # array([1, 1, 1, ..., 1, 1, 1], dtype=uint8)

    ascending_order = np.argsort(las.return_number)[::-1]
    print(las.return_number[ascending_order])
    # array([4, 4, 4, ..., 1, 1, 1], dtype=uint8)
    las.return_number[:] = las.return_number[ascending_order]
    print(las.return_number)
    # array([1, 1, 1, ..., 1, 1, 1], dtype=uint8) # bif oof
    las.return_number[0] = 7
    print(las.return_number)
    # array([1, 1, 1, ..., 1, 1, 1], dtype=uint8) # again value not updated


    # To actually update you have to do
    las.return_number = las.return_number[ascending_order]
    print(las.return_number)
    # array([4, 4, 4, ..., 1, 1, 1], dtype=uint8)

    rn = las.return_number[ascending_order]
    rn[0] = 7
    las.return_number = rn
    print(las.return_number)
    # array([7, 4, 4, ..., 1, 1, 1], dtype=uint8)


In order to try to solve this inconsistency, laspy >= 0.5.0
introduced the :class:`.SubFieldView` class that is meant to propagate
modifications to the real array, and tries to act like a real numpy array.

.. code-block:: python

    import laspy
    import numpy as np

    las = laspy.read("tests/simple.las")

    print(las.return_number)
    # <SubFieldView([1 1 1 ... 1 1 1])>

    ascending_order = np.argsort(las.return_number)[::-1]
    las.return_number[:] = las.return_number[ascending_order]
    print(las.return_number)
    # <SubFieldView([4 4 4 ... 1 1 1])>
    las.return_number[0] = 7
    print(las.return_number)
    # <SubFieldView([7 4 4 ... 1 1 1])>

It may be possible that some operation on SubFieldView fail, in that case
it is easy to copy them to numpy arrays:

.. code-block:: python


    import laspy
    import numpy as np

    las = laspy.read("tests/simple.las")
    print(las.return_number)
    # <SubFieldView([1 1 1 ... 1 1 1])>

    array = np.array(las.return_number)
    # array([1, 1, 1, ..., 1, 1, 1], dtype=uint8)


The logic is also the same for 'Scaled dimensions' such as x, y, z and scaled extra bytes,
where a ScaledArrayView class has been introduced

.. code-block:: python

    import laspy
    import numpy as np

    las = laspy.read("tests/simple.las")
    print(las.x)
    # <ScaledArrayView([637012.24 636896.33 636784.74 ... 637501.67 637433.27 637342.85])>>

    # ScaledArray view should behave as much as possible as a numpy array
    # However if something breaks in your code when upgrading, and / or
    # you need a true numpy array you can get one by doing

    array = np.array(las.x)
    # array([637012.24, 636896.33, 636784.74, ..., 637501.67, 637433.27,
    #        637342.85])



Changes in extra bytes creation
_______________________________

The API to create extra bytes changed slightly, now the parameters needed
(and the optional ones) are coupled into :class:`.ExtraBytesParams`


Other changes
_____________

The `points` attribute of as :class:`.LasData` used to return a numpy array
it now returns a :class:`.PackedPointRecord` to get the same array as before,
use the `array` property of the point record.

.. code-block:: python

    # laspy <= 0.4.3
    las = laspy.read("somefile.las")
    array = las.points

    # laspy 1.0.0
    las = laspy.read("somefile.las")
    array = las.points.array
 