try:
    import rich
    import typer

    HAS_CLI_DEPDS = True
except ModuleNotFoundError:
    HAS_CLI_DEPDS = False


def main():
    if HAS_CLI_DEPDS:
        from .core import app

        app()
    else:
        raise SystemExit(
            """laspy cli needs extra dependencies, install using
`pip install laspy[cli]`
`pip install laspy[cli,lazrs]`
"""
        )


if __name__ == "__main__":
    main()
