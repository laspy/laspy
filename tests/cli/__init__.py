import pytest


def skip_if_cli_deps_are_not_installed():
    try:
        from laspy.cli.core import app
    except ModuleNotFoundError:
        pytest.skip("skipping cli test (deps not installed)", allow_module_level=True)
