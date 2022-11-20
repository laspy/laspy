.. laspy documentation master file, created by
   sphinx-quickstart on Wed Mar 28 09:00:58 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

===========================================
laspy: Python library for lidar LAS/LAZ IO.
===========================================

`LAS`_ (and its compressed counterpart LAZ), is a popular format for lidar pointcloud and full waveform,
laspy reads and writes these formats and provides a Python API via Numpy Arrays.

.. _LAS: https://www.asprs.org/committee-general/laser-las-file-format-exchange-activities.html


Here is an example of reading in LAZ data and getting some simple summaries of the pointcloud:

.. testcode::

    import numpy as np
    import laspy

    with laspy.open('laspytests/data/simple.laz') as fh:
        print('Points from Header:', fh.header.point_count)
        las = fh.read()
        print(las)
        print('Points from data:', len(las.points))
        ground_pts = las.classification == 2
        bins, counts = np.unique(las.return_number[ground_pts], return_counts=True)
        print('Ground Point Return Number distribution:')
        for r,c in zip(bins,counts):
            print('    {}:{}'.format(r,c))
        

Would output:

.. testoutput::

    Points from Header: 1065
    <LasData(1.2, point fmt: <PointFormat(3)>, 1065 points, 0 vlrs)>
    Points from data: 1065
    Ground Point Return Number distribution:
        1:239
        2:25
        3:11
        4:1


User Guide
==========

.. toctree::
    :maxdepth: 2

    installation
    intro
    basic
    examples
    complete_tutorial
    lessbasic
    migration
    changelog
    contributing


API Documentation
=================

.. toctree::
   :maxdepth: 2

   api/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
