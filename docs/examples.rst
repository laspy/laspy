==================
Examples
==================


Filtering
---------

This example shows how you can extract points from a file and write them into a new one.
We use the classification field to filter points, but this can work with the other fields.

.. code-block:: python

    import laspy

    las = laspy.read('tests/simple.las')

    new_file = laspy.create(point_format=las.header.point_format_id, file_version=las.header.version)
    new_file.points = las.points[las.classification == 1]

    new_file.write('extracted_points.las')



Creating from scratch
---------------------

This example shows how you can create a new LAS file from scratch.

.. code-block:: python

    import laspy
    import numpy as np

    my_data_xx, my_data_yy = np.meshgrid(np.linspace(-20, 20, 15), np.linspace(-20, 20, 15))
    my_data_zz = my_data_xx ** 2 + 0.25 * my_data_yy ** 2

    my_data = np.hstack((my_data_xx.reshape((-1, 1)), my_data_yy.reshape((-1, 1)), my_data_zz.reshape((-1, 1))))


    las = laspy.create(file_version="1.2", point_format=3)

    las.header.offsets = np.min(my_data, axis=0)
    las.header.scales = [0.1, 0.1, 0.1]

    las.x = my_data[:, 0]
    las.y = my_data[:, 1]
    las.z = my_data[:, 2]

    las.write("new_file.las")



Using chunked reading & writing
-------------------------------

This example shows how to use the 'chunked' reading and writing feature
to split potentially large LAS/LAZ file into multiple smaller file.

.. literalinclude:: ../examples/recursive-split.py
    :language: Python
