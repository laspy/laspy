Laspy
=====

Laspy is a python library for reading, modifying and creating LAS LiDAR
files.

|Build Status|

Introduction
------------

Laspy is a pythonic library for reading, modifying and writing LAS
files. Support for LAZ is limited to reading LAS version 1.0-1.3 files.
Laspy is compatible with Python 2.6+ and 3.5+.

Laspy includes a set of command line tools which can be used to do basic
file operations like format translation and validation as well as
comparing LAS files.

Example
-------

A simple example to show the basics of Laspy. Here we create an output
file that only consists of terrain points from the input file:

.. code:: python

    from laspy.file import File
    import numpy as np

    inFile = File('/path/to/file.las', mode='r')

    I = inFile.Classification == 2

    outFile = File('/path/to/output.las', mode='w', header=inFile.header)
    outFile.points = inFile.points[I]
    outFile.close()

API Documentation and tutorials are available at
`PythonHosted <http://pythonhosted.org/laspy>`__.

Installation
------------

Laspy can be installed either with ``pip``:

::

    pip install laspy

or by running the setup script included in the source distribution:

::

    python setup.py build
    python setup.py install

You may need to run these commands as root/administrator.

Laspy is only dependent on numpy and should therefore work on Linux, OS
X and Windows as long as a working installation of numpy is available.

Changelog
---------

Version 1.5.1
.............
- Bug fixes (`#67 <https://github.com/laspy/laspy/pull/67>`_, `#75 <https://github.com/laspy/laspy/pull/75>`_, `b02b40900b5 <https://github.com/laspy/laspy/commit/b02b40900b5620972930cd0c201b4db1a6a69754>`_)
- Allow usage of `laszip-cli` when working with LAZ files (`#77 <https://github.com/laspy/laspy/pull/77>`_)

Version 1.5.0
.............
- Improved memory handling in base.FileManager (`#48 <https://github.com/laspy/laspy/pull/48>`_)
- Introduced ``r-`` file mode, that only reads the header of as LAS file (`#48 <https://github.com/laspy/laspy/pull/48>`_)
- LAS v. 1.4 bug fixes (`#55 <https://github.com/laspy/laspy/pull/55>`_)
- Python 3 support (`#62 <https://github.com/laspy/laspy/pull/62>`_)


.. |Build Status| image:: https://travis-ci.org/laspy/laspy.svg?branch=master
   :target: https://travis-ci.org/laspy/laspy
