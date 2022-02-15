import nox


@nox.session(python=["3.7", "3.8", "3.9", "3.10"])
@nox.parametrize("laz_backend", [None, "lazrs", "laszip"])
def tests(session, laz_backend):
    session.install("pytest")
    if laz_backend is None:
        session.install(".")
    else:
        session.install(f".[{laz_backend}]")
    session.run("pytest", "-q", "tests")



