==================
Examples
==================


Filtering
---------

This example shows how you can extract points from a file and write them into a new one.
We use the classification field to filter points, but this can work with the other fields.

.. code-block:: python

    import laspy

    las = laspy.read('tests/data/simple.las')

    new_file = las[las.classification == 1]

    new_file.write('extracted_points.las')

Selecting from ``las`` copies its header, including the coordinate scales and
offsets, VLRs (such as coordinate reference system information), and extra
point-dimension definitions. The point count and bounds are updated for the
selected points. Creating a new file with only the point format and version
does not preserve the rest of this metadata.

The boolean mask in this example also copies the selected point data, so
editing the selected points or their dimension definitions does not change
``las``. A slice such as ``las[:100]`` instead shares its point-data array with
``las``; changes to those point values affect the original. The header is copied
in both cases.

Waveform samples are not loaded by default. If you need to preserve them too,
see :doc:`waveform` for the loading modes and storage requirements.



Creating from scratch
---------------------

There are multiple ways to create new las files.

Creating a new LasData
______________________

.. code-block:: python

    import laspy
    import numpy as np

    # 0. Creating some dummy data
    my_data_xx, my_data_yy = np.meshgrid(np.linspace(-20, 20, 15), np.linspace(-20, 20, 15))
    my_data_zz = my_data_xx ** 2 + 0.25 * my_data_yy ** 2
    my_data = np.hstack((my_data_xx.reshape((-1, 1)), my_data_yy.reshape((-1, 1)), my_data_zz.reshape((-1, 1))))

    # 1. Create a new header
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.add_extra_dim(laspy.ExtraBytesParams(name="random", type=np.int32))
    header.offsets = np.min(my_data, axis=0)
    header.scales = np.array([0.1, 0.1, 0.1])

    # 2. Create a Las
    las = laspy.LasData(header)

    las.x = my_data[:, 0]
    las.y = my_data[:, 1]
    las.z = my_data[:, 2]
    las.random = np.random.randint(-1503, 6546, len(las.points), np.int32)

    las.write("new_file.las")

Using LasWriter
_______________

.. code-block:: python

    import laspy
    import numpy as np

    # 0. Creating some dummy data
    my_data_xx, my_data_yy = np.meshgrid(np.linspace(-20, 20, 15), np.linspace(-20, 20, 15))
    my_data_zz = my_data_xx ** 2 + 0.25 * my_data_yy ** 2
    my_data = np.hstack((my_data_xx.reshape((-1, 1)), my_data_yy.reshape((-1, 1)), my_data_zz.reshape((-1, 1))))

    # 1. Create a new header
    header = laspy.LasHeader(point_format=3, version="1.2")
    header.offsets = np.min(my_data, axis=0)
    header.scales = np.array([0.1, 0.1, 0.1])

    # 3. Create a LasWriter and a point record, then write it
    with laspy.open("somepath.las", mode="w", header=header) as writer:
        point_record = laspy.ScaleAwarePointRecord.zeros(my_data.shape[0], header=header)
        point_record.x = my_data[:, 0]
        point_record.y = my_data[:, 1]
        point_record.z = my_data[:, 2]

        writer.write_points(point_record)


Using chunked reading & writing
-------------------------------

This example shows how to use the 'chunked' reading and writing feature
to split potentially large LAS/LAZ file into multiple smaller file.

.. literalinclude:: ../examples/recursive-split.py
    :language: Python


COPC
----


.. literalinclude:: ../examples/copc.py
