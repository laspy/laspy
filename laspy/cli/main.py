import importlib


def main():
    has_rich = importlib.util.find_spec("rich") is not None
    has_typer = importlib.util.find_spec("typer") is not None
    has_cli_deps = has_rich and has_typer
    if has_cli_deps:
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
