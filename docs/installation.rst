.. _installation:

============
Installation
============

Installing from PyPi
====================

Pip
____

.. code-block:: shell

    # To install with lazrs only
    pip install laspy[lazrs]

    # To install with laszip only
    pip install laspy[laszip]

    # To install with both
    pip install laspy[lazrs,laszip]

Conda
_____

A conda build of laspy is available and maintained (but not by laspy)

.. code-block:: shell

    conda install -c conda-forge laspy

However, ``lazrs`` and ``laszip`` [#f1]_ are not available via conda, so to have LAZ support, you will
still need to install a LAZ backend via ``pip``



Optional dependencies  / features
=================================


LAZ support
___________

laspy does not support LAZ (.laz) file by itself but can use one of several optional dependencies
to support compressed LAZ files.

The 2 supported options are:

1) `lazrs`_ `[lazrs PyPi]`_

2) `laszip-python`_ (bindings to `laszip`_)

When encountering LAZ data, laspy will try to use one of the backend in the order described above.
(Example: if lazrs is not installed or if it fails during, the process, laspy will try laszip)

`lazrs`_ is a Rust port of the laszip compression and decompression.
Its main advantage is that it is able to compress/decompress using multiple threads which can
greatly speed up things. However it does not supports points with waveforms.

`laszip`_  is the official and original LAZ implementation by Martin Isenburg.
The advantage of the `laszip` backend is that its the official implementation, it supports points
with waveform but does not offer multi-threaded compression/decompression.


Both the laszip bindings and lazrs are available on pip.

To install laspy with one of its supported backend use one of the following commands


CRS / SRS
_________

LAS files allows to define the CRS / SRS in which the points coordinates are.
When `pyproj` is installed, you can use the :meth:`.LasHeader.add_crs` to add 
CRS information to a file, or you can use :meth:`.LasHeader.parse_crs` to get 
`pyproj.CRS`.


.. _lazrs: https://github.com/tmontaigu/laz-rs
.. _laszip-python: https://github.com/tmontaigu/laszip-python
.. _laszip: https://github.com/LASzip/LASzip
.. _[lazrs PyPi]: https://pypi.org/project/lazrs/


Cloud Optimized Point Cloud (COPC)
__________________________________

`laspy` supports `COPC`_ files via its :class:`.CopcReader` class.
This features **requires** the optional dependency ``lazrs`` to be installed.

Optionaly, when python package `requests`_ is installed the :class:`.CopcReader`
can handle COPC that are in a HTTP server.


.. _COPC: https://github.com/copcio/copcio.github.io
.. _requests: https://docs.python-requests.org/en/latest


.. rubric:: Footnotes.

.. [#f1] A ``laszip`` package exists on conda-forge, but it only includes the C++ library, not the the Python
         bindings, which means that installing it won't give you a LAZ capable laspy installation.


