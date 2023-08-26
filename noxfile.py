import nox


@nox.session(python=["3.8", "3.9", "3.10", "3.11"])
@nox.parametrize("laz_backend", [None, "lazrs", "laszip"])
def tests(session, laz_backend):
    session.install("pytest")
    if laz_backend is None:
        session.install(".")
    else:
        session.install(f".[{laz_backend}]")
    session.run("pytest")


@nox.session
@nox.parametrize(
    "optional_dependencies",
    [None, "laszip", "lazrs", "pyproj", "requests,lazrs", "cli,lazrs"],
)
def coverage(session, optional_dependencies):
    if optional_dependencies is None:
        session.install(".[dev]")
    else:
        session.install(f".[dev,{optional_dependencies}]")

    optional_dependencies = str(optional_dependencies)

    session.run(
        "coverage",
        "run",
        f"--context={optional_dependencies}",
        f"--data-file=.coverage.{optional_dependencies.replace(',', '.')}",
    )
