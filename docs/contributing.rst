Contributing
============

Setup
-----

To work on laspy, as it often recommended in python projects,
a virtual env should be used, eg:

.. code-block:: console

    python -m venv .venv
    source .venv/bin/activate # bash/zsh
    .venv/Scripts/Activate.ps1 # windows powershell

To install ``laspy`` in *development mode*:

.. code-block:: console

    pip install -e .[dev]

The ``[dev]`` option will install all the extra tools needed
to run tests, format files and get coverage.

To install with optional dependencies

.. code-block:: console

    pip install -e .[dev,lazrs,pyproj]


Commands
--------

Running Tests
_____________

.. code-block:: console

    pytest


Formatting
__________

.. code-block:: console

    black .

Coverage
_________

.. code-block:: console

    coverage run

    # get report in the CLI
    coverage report

    # get report as a nice navigable html
    coverage html

However, the commands above will only give the coverage for
the set of optional dependencies installed.

Getting a more complete is possible (but takes more time);



.. code-block:: console

    nox -s coverage
    coverage combine

    # get report in the CLI
    coverage report

    # get report as a nice navigable html
    coverage html


