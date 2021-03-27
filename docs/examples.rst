==================
Examples
==================


Filtering
---------

This example shows how you can extract points from a file and write them into a new one.
We use the classification field to filter points, but this can work with the other fields.

.. code-block:: python

    import pylas

    las = pylas.read('pylastests/simple.las')

    new_file = pylas.create(point_format=las.header.point_format_id, file_version=las.header.version)
    new_file.points = las.points[las.classification == 1]

    new_file.write('extracted_points.las')



Creating from scratch
---------------------

This example shows how you can create a new LAS file from scratch.

.. code-block:: python

    import pylas
    import numpy as np

    las = pylas.create()

    array = np.linspace(0.0, 15.0, 10000)
    las.x = array
    las.y = array
    las.z = array

    las.write('diagonal.las')


Using chunked reading & writing
-------------------------------

This example shows how to use the 'chunked' reading and writing feature
to split potentially large LAS/LAZ file into multiple smaller file.

.. literalinclude:: ../examples/recursive-split.py
    :language: Python
