.. laspy documentation master file, created by
   sphinx-quickstart on Wed Mar 28 09:00:58 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

===========================================
laspy: Python library for lidar LAS/LAZ IO.
===========================================

`LAS`_ (and it's compressed counterpart LAZ), is a popular format for lidar pointcloud and full waveform,
laspy reads and writes these formats and provides a Python API via Numpy Arrays.

.. _LAS: https://www.asprs.org/committee-general/laser-las-file-format-exchange-activities.html


.. important::

   laspy 2.0 is in alpha, it has some changes and improvements

   Context:
      In 2018 a new python libray to manage LAS/LAZ file was created under the name of pylas
      as improving the laspy code base seemed to big of a challenge.

      However today, the current plan is to merge pylas back into laspy and release it as
      the version 2.0 of laspy.

      As the bump in major version suggests, there are important changes that will require
      user code to be changed. These changes should be easy to apply and hopefully the
      improvements are worth the adaptation.

      If there are some regressions do no hesitate to open an issue on Github_


   See :ref:`installation` to see how to install the new version.

   See :ref:`migration_guides` to get informations on how to update your code.

   And look at the rest of the documentation.

.. _Github: https://github.com/laspy/laspy

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
