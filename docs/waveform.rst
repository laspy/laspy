Waveform Support
================

laspy can read and write LAS waveform point formats, but the current
implementation intentionally supports only a subset of the LAS 1.4 waveform
specification.

API
---

Use ``fullwave`` when opening a file for reading:

The default is ``fullwave="never"`` (no waveform samples are loaded unless you
opt in).

.. code-block:: python

   import laspy

   with laspy.open("example.laz", fullwave="never") as reader:
       las = reader.read()

   with laspy.open("example.laz", fullwave="lazy") as reader:
       points = reader.read_points(1024)
       waveforms = points["waveform"]

   with laspy.open("example.laz", fullwave="eager") as reader:
       las = reader.read()
       waveforms = las.points["waveform"]

``fullwave="never"``
   Do not load waveform samples.

``fullwave="lazy"``
   Keep waveform samples in the external ``.wdp`` file until
   ``points["waveform"]`` is accessed.

``fullwave="eager"``
   Load waveform samples while reading points.

Writing
-------

When waveform data is present, writing to a filesystem path will emit a sibling
``.wdp`` file next to the ``.las`` or ``.laz`` file.

Writing waveform-enabled data to a file-like object is not supported.

Current Scope
-------------

The current implementation supports:

- External waveform storage in a sibling ``.wdp`` file.
- Uncompressed waveform packets only.
- Byte-aligned sample widths only.
- A single waveform layout across all waveform descriptors in the file.
- Waveform packets addressed as fixed-size records.

Unsupported LAS 1.4 Features
----------------------------

The LAS 1.4 specification allows more than the current implementation supports.
laspy currently raises ``NotImplementedError`` or ``ValueError`` for these
cases.

- Internal waveform storage in the LAS EVLR area is not supported.
- Non-byte-aligned waveform sample widths are not supported.
- Multiple waveform descriptor layouts in one file are not supported.
- General byte-offset-based packet layouts are not supported when they do not
  behave like fixed-size records.
