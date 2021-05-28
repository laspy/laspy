.. _installation:

============
Installation
============

Installing from PyPi
====================

.. note::

    While laspy 2.0 is in alpha / beta (pre release) don't forget the *-\-pre*

.. code-block:: shell

    # To install with lazrs only
    pip install --pre laspy[lazrs]

    # To install with laszip only
    pip install --pre laspy[laszip]

    # To install with both
    pip install --pre laspy[lazrs,laszip]


More information on laz support below

Optional dependencies for LAZ support
=====================================

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


.. _lazrs: https://github.com/tmontaigu/laz-rs
.. _laszip-python: https://github.com/tmontaigu/laszip-python
.. _laszip: https://github.com/LASzip/LASzip
.. _[lazrs PyPi]: https://pypi.org/project/lazrs/





