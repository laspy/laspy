import copy
import sys
from contextlib import ExitStack
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import rich
import typer
from rich.console import Console, Group
from rich.live import Live
from rich.progress import MofNCompleteColumn, Progress, TaskID
from rich.table import Table

import laspy
from laspy.header import Version

from .. import PackedPointRecord, PointFormat
from ..point import dims
from ..vlrs.vlrlist import VLRList
from . import copc

DEFAULT_ITER_CHUNK_SIZE: int = 10_000_000
ITER_CHUNK_SIZE_HELP_STR: str = """Number of points processed at once.

To avoid loading the whole file in memory points are processed in batch.

-1 means all the points will be processed at once
"""
ITER_CHUNK_SIZE_OPTION = typer.Option(
    DEFAULT_ITER_CHUNK_SIZE, help=ITER_CHUNK_SIZE_HELP_STR
)

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(help="CLI tool using laspy")

app.add_typer(copc.app, name="copc")


def print_header(hdr: laspy.LasHeader):
    """
    Prints the header information in a pretty table
    """
    table = Table(title="Header", show_header=False, box=None)
    table.add_row("Version", f"[cyan]{hdr.version}")
    table.add_row("Point Format Id", f"[cyan]{hdr.point_format.id}")
    table.add_row("Point Format Size", f"[cyan]{hdr.point_format.size}")
    table.add_row("Extra Bytes", f"[cyan]{hdr.point_format.num_extra_bytes}")
    table.add_row("Point Count", f"[cyan]{hdr.point_count}")
    table.add_row("Compressed", f"[cyan]{hdr.are_points_compressed}")
    table.add_row("System Identifier", f"[cyan]'{hdr.system_identifier}'")
    table.add_row("Generating Software", f"[cyan]'{hdr.generating_software}'")
    table.add_row("Number Of VLRs", f"[cyan]{len(hdr.vlrs)}")
    if hdr.version >= Version(1, 4):
        table.add_row("Number Of EVLRs", f"[cyan]{hdr.number_of_evlrs}")

    table.add_row("UUID", f"[cyan]'{hdr.uuid}'")
    table.add_row("File Source Id", f"[cyan]{hdr.file_source_id}")
    table.add_row("Creation Date", f"[cyan]{hdr.creation_date}")
    table.add_row("Scales", f"[blue]{hdr.scales}")
    table.add_row("Offsets", f"[blue]{hdr.offsets}")
    table.add_row("Mins", f"[blue]{hdr.mins}")
    table.add_row("Maxs", f"[blue]{hdr.maxs}")
    if hdr.version <= Version(1, 2):
        table.add_row(
            "Number Of Points By Return",
            f"[blue]{hdr.number_of_points_by_return[:5]}",
        )
    else:
        values_str = ", ".join(str(n) for n in hdr.number_of_points_by_return)
        table.add_row("Number Of Points By Return", f"[blue][{values_str}]")

    console.print(table)


def print_points_stats(reader: laspy.LasReader):
    """
    Computes and prints stats about dimensions in the file
    """
    stats_record = laspy.PackedPointRecord.zeros(2, reader.header.point_format)

    with Progress(transient=True) as progress:
        task = progress.add_task(
            "[cyan]Procession points...", total=reader.header.point_count
        )
        for chunk in reader.chunk_iterator(10_000_000):

            for dimension_name in reader.header.point_format.dimension_names:
                stats_record[dimension_name][0] = np.minimum(
                    stats_record[dimension_name][0], np.min(chunk[dimension_name])
                )
                stats_record[dimension_name][1] = np.maximum(
                    stats_record[dimension_name][1], np.max(chunk[dimension_name])
                )

            progress.update(task, advance=len(chunk))

    table = Table(title="Stats", show_header=True, box=None)
    table.add_column("Dimension Name")
    table.add_column("Min")
    table.add_column("Max")
    for dimension_name in reader.header.point_format.dimension_names:
        r = stats_record[dimension_name]
        table.add_row(dimension_name, str(r[0]), str(r[1]))

    console.print(table)


@app.command()
def info(
    file_path: Path,
    header: Optional[bool] = typer.Option(
        None, "--header", help="Whether header information should be printed"
    ),
    vlrs: Optional[bool] = typer.Option(
        None, "--vlrs", help="Whether vlrs information should be printed"
    ),
    points: Optional[bool] = typer.Option(
        None, "--points", help="Whether points information should be printed"
    ),
    evlrs: Optional[bool] = typer.Option(
        None, "--evlrs", help="Whether evlrs information should be printed"
    ),
):
    """
    Print information about a LAS/LAZ file

    By default every part of the file are printed (header, vlrs, points, evlrs)

    If any of the option (e.g: --header) is used, then only that part will be displayed

    It it possible to combine many options to select what should be printed


    Examples:


    # Only prints header

    laspy info file.las --header

    ---

    # Prints header and VLRs

    laspy info file.laz --header --vlrs
    """
    if all(option is None for option in (header, vlrs, points, evlrs)):
        header, vlrs, points, evlrs = True, True, True, True
    else:
        header = header or False
        vlrs = vlrs or False
        points = points or False
        evlrs = evlrs or False

    try:
        with laspy.open(file_path) as reader:
            if header:
                print_header(reader.header)

            if vlrs:
                if header:
                    rich.print(50 * "-")

                table = Table(title=f"VLRs", show_header=True, box=None)
                table.add_column("User ID")
                table.add_column("Record ID")
                table.add_column("Description")
                for vlr in reader.header.vlrs:
                    table.add_row(
                        str(vlr.user_id), str(vlr.record_id), str(vlr.description)
                    )

                if table.rows:
                    console.print(table)

            if points:
                if vlrs:
                    rich.print(50 * "-")
                print_points_stats(reader)

            if evlrs and reader.header.evlrs is not None:
                table = Table(title=f"EVLRs", show_header=True, box=None)
                table.add_column("User ID")
                table.add_column("Record ID")
                table.add_column("Description")
                for vlr in reader.header.evlrs:
                    table.add_row(
                        str(vlr.user_id), str(vlr.record_id), str(vlr.description)
                    )

                if table.rows:
                    console.print(table)
    except Exception as e:
        rich.print("[bold red]Error:")
        rich.print(e)
        raise typer.Exit(code=1)


def _copy_from_reader_to_writer(
    reader: laspy.LasReader,
    writer: laspy.LasWriter,
    iter_chunk_size: int,
    progress_and_task: Optional[Tuple[Progress, TaskID]] = None,
):
    """
    Copies points from the reader to the writer
    """
    progress, task = progress_and_task or (None, None)
    if progress is not None:
        progress.update(task, total=reader.header.point_count)

    for chunk in reader.chunk_iterator(iter_chunk_size):
        writer.write_points(chunk)
        if progress is not None:
            progress.update(task, advance=len(chunk))


def _copy(
    input_path: Path,
    output_path: Path,
    laz_backend: laspy.LazBackend,
    iter_chunk_size: int,
    progress: Progress,
    task: TaskID,
):
    """
    Copies points from the file at input_path to a new file at
    output_path
    """
    with ExitStack() as stack:
        reader = stack.enter_context(laspy.open(input_path, laz_backend=laz_backend))
        writer = stack.enter_context(
            laspy.open(
                output_path, mode="w", header=reader.header, laz_backend=laz_backend
            )
        )

        _copy_from_reader_to_writer(reader, writer, iter_chunk_size, (progress, task))


def _list_input_and_ouput_files(
    input_path: Path,
    output_path: Optional[Path] = None,
    glob_pattern: str = "*.la[sz]",
    output_ext: str = ".las",
) -> Tuple[List[Path], List[Path]]:
    """
    List some input LAS/LAZ file paths and their corresponding output LAS/LAZ paths.

    If input_path points to a file, then output_path can be either None or a file
    path (with different path) or folder path.

    If input_path points to a folder, then output_path maybe be None or
    a path to a folder
    """
    input_files = (
        [input_path] if input_path.is_file() else list(input_path.glob(glob_pattern))
    )
    if output_path is not None:
        output_path = output_path.expanduser()
        if output_path.is_dir():
            output_files = [output_path / input_path.name for input_path in input_files]
        else:
            output_files = [output_path]
    else:
        output_files = [
            input_path.with_suffix(output_ext) for input_path in input_files
        ]
    return (input_files, output_files)


def _copy_files(
    action: str,
    input_path: Path,
    output_path: Optional[Path] = None,
    laz_backend: laspy.LazBackend = Optional[None],
    iter_chunk_size: int = DEFAULT_ITER_CHUNK_SIZE,
):
    if action == "compress":
        input_ext, output_ext = ".las", ".laz"
    elif action == "decompress":
        input_ext, output_ext = ".laz", ".las"
    else:
        raise RuntimeError(f"Invalid action {action}")

    input_files, output_files = _list_input_and_ouput_files(
        input_path, output_path, glob_pattern=f"*.{input_ext}", output_ext=output_ext
    )
    if len(input_files) > len(output_files):
        rich.print(f"[bold red]Cannot {action} many files into one")
        raise typer.Exit(code=1)

    if len(input_files) == 1:
        if input_files[0] == output_files[0]:
            rich.print("[bold red]Cannot have same file as input and output")
            raise typer.Exit(code=1)

        if output_files[0].suffix.lower() != output_ext:
            rich.print(f"[bold red]Extension of output file must {output_ext}")
            raise typer.Exit(code=1)

    overall_progress = Progress(
        *Progress.get_default_columns(), MofNCompleteColumn(), transient=False
    )

    file_progress = Progress(
        *Progress.get_default_columns(), MofNCompleteColumn(), transient=False
    )

    group = Group(file_progress, overall_progress)

    num_fails = 0
    with Live(group):
        overall_task = overall_progress.add_task(
            "Processing files...", total=len(input_files)
        )
        for input, output in zip(input_files, output_files):
            task = file_progress.add_task(f"[cyan]{input.name}")
            try:
                _copy(input, output, laz_backend, iter_chunk_size, file_progress, task)
            except Exception as e:
                file_progress.update(
                    task,
                    description=f"[bold red]{input.name}",
                )
                file_progress.console.print(
                    f"[bold red]{input} -> Failed with error: '{e}'"
                )
                num_fails += 1

            overall_progress.update(overall_task, advance=1)

        if num_fails == len(input_files):
            overall_progress.update(overall_task, description=f"[red] Failed all tasks")
        elif num_fails == 0:
            overall_progress.update(
                overall_task,
                description=f"[green]Completed {len(input_files)} with success",
            )
        else:
            overall_progress.update(
                overall_task,
                description=f"[dark_orange]Completed {len(input_files) - num_fails} with success, {num_fails} failed",
            )


backend_to_cli_name: Dict[laspy.LazBackend, str] = {
    laspy.LazBackend.LazrsParallel: "lazrs-parallel",
    laspy.LazBackend.Lazrs: "lazrs",
    laspy.LazBackend.Laszip: "laszip",
}
CliLazBackend = Enum(
    "CliLazBackend",
    {
        str(variant).split(".")[-1]: backend_to_cli_name[variant]
        for variant in laspy.LazBackend.detect_available()
    },
)
cli_name_to_backend: Dict[CliLazBackend, Optional[laspy.LazBackend]] = {
    CliLazBackend.LazrsParallel: laspy.LazBackend.LazrsParallel,
    CliLazBackend.Lazrs: laspy.LazBackend.Lazrs,
    CliLazBackend.Laszip: laspy.LazBackend.Laszip,
    None: None,
}


@app.command()
def decompress(
    input_path: Path = typer.Argument(
        ...,
        help="Path to file or directory of files to decompress",
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        help="Directory where decompressed file will be written, or filename of the decompressed file",
    ),
    laz_backend: Optional[CliLazBackend] = typer.Option(
        None, help="The Laz backend to use."
    ),
    iter_chunk_size: int = ITER_CHUNK_SIZE_OPTION,
):
    """Decompress LAZ file(s)

    - If input_path is a directory, all .laz files will be decompressed.
    - If input_path is a file it will be decompressed

    """
    if input_path is None:
        with ExitStack() as stack:
            try:
                reader = laspy.open(sys.stdin.buffer, closefd=False)
            except Exception as e:
                err_console.print(f"Failed to create reader: {e}")
                return
            else:
                reader = stack.enter_context(reader)

            try:
                writer = laspy.open(
                    sys.stdout.buffer, mode="w", header=reader.header, closefd=False
                )
            except Exception as e:
                err_console.print(f"Failed to create writer: {e}")
                return
            else:
                writer = stack.enter_context(writer)

            _copy_from_reader_to_writer(reader, writer, iter_chunk_size=iter_chunk_size)
    else:
        laz_backend = (
            cli_name_to_backend[laz_backend] if laz_backend is not None else None
        )
        _copy_files("decompress", input_path, output_path, laz_backend, iter_chunk_size)


@app.command()
def compress(
    input_path: Path = typer.Argument(
        ...,
        help="Path to file or directory of files to compress",
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        help="Directory where decompressed file will be written, or filename of the decompressed file",
    ),
    laz_backend: Optional[CliLazBackend] = typer.Option(
        None, help="The Laz backend to use."
    ),
    iter_chunk_size: int = ITER_CHUNK_SIZE_OPTION,
):
    """Compress LAS file(s)

    - If input_path is a directory, all .las files will be compressed.
    - If input_path is a file it will be compressed

    """
    laz_backend = cli_name_to_backend[laz_backend] if laz_backend is not None else None
    _copy_files("compress", input_path, output_path, laz_backend, iter_chunk_size)


def _convert_file_at_path(
    input_path: Path,
    output_path: Path,
    point_format_id: Optional[int],
    version: Optional[str],
    laz_backend: Optional[CliLazBackend],
    iter_chunk_size: int,
    progress: Progress,
    task: TaskID,
):
    with ExitStack() as stack:
        reader = laspy.open(input_path, laz_backend=cli_name_to_backend[laz_backend])
        reader = stack.enter_context(reader)

        progress.update(task, total=reader.header.point_count)

        # Prepare PointFormat and Version of new file
        target_point_format_id = point_format_id
        if target_point_format_id is None:
            target_point_format_id = reader.header.point_format.id

        target_file_version = version
        if target_file_version is None:
            target_file_version = max(
                str(reader.header.version),
                dims.preferred_file_version_for_point_format(target_point_format_id),
            )
        dims.raise_if_version_not_compatible_with_fmt(
            target_point_format_id, target_file_version
        )
        target_file_version = Version.from_str(target_file_version)
        point_format = PointFormat(target_point_format_id)
        point_format.dimensions.extend(reader.header.point_format.extra_dimensions)

        # Copy headers, vlrs, evlrs
        # TODO if target version does not suppot evlr
        # try to convert some to vlrs, and/or warn
        header = copy.deepcopy(reader.header)
        header.set_version_and_point_format(target_file_version, point_format)

        writer = laspy.open(
            output_path, mode="w", laz_backend=laz_backend, header=header
        )
        writer = stack.enter_context(writer)

        # Convert and write points
        target_point_record = PackedPointRecord.zeros(iter_chunk_size, point_format)
        for chunk in reader.chunk_iterator(iter_chunk_size):
            sub_slice = target_point_record[: len(chunk)]
            sub_slice.copy_fields_from(chunk)
            writer.write_points(sub_slice)
            progress.update(task, advance=len(sub_slice))


@app.command()
def convert(
    input_path: Path = typer.Argument(
        ...,
        help="Path to file or directory of files to convert",
    ),
    output_path: Path = typer.Argument(
        ...,
        help="Directory where converted file will be written, or filename of the converted file",
    ),
    point_format_id: Optional[int] = typer.Option(
        None,
        help="The target point format id",
    ),
    version: Optional[str] = typer.Option(
        None,
        help="The target version",
    ),
    laz_backend: Optional[CliLazBackend] = typer.Option(
        None, help="The Laz backend to use."
    ),
    iter_chunk_size: int = ITER_CHUNK_SIZE_OPTION,
):
    """Convert LAS/LAZ files

    Convert file(s) to a desired point format / version

    - If input_path is a directory, all .laz files will be converted.
    - If input_path is a file it will be converted

    """
    laz_backend = cli_name_to_backend[laz_backend] if laz_backend is not None else None
    input_paths, output_paths = _list_input_and_ouput_files(input_path, output_path)

    if len(input_paths) > len(output_paths):
        rich.print(f"[bold red]Cannot convert many files into one")
        raise typer.Exit(code=1)

    if len(input_paths) == 1 and input_paths[0] == output_paths[0]:
        rich.print("[bold red]Cannot have same file as input and output")
        raise typer.Exit(code=1)

    overall_progress = Progress(
        *Progress.get_default_columns(), MofNCompleteColumn(), transient=False
    )
    file_progress = Progress(
        *Progress.get_default_columns(), MofNCompleteColumn(), transient=False
    )
    group = Group(file_progress, overall_progress)

    num_fails = 0
    with Live(group):
        overall_task = overall_progress.add_task(
            "Processing files...", total=len(input_paths)
        )

        for input_path, output_path in zip(input_paths, output_paths):
            task = file_progress.add_task(f"[cyan]{input_path.name}")
            try:
                _convert_file_at_path(
                    input_path,
                    output_path,
                    point_format_id,
                    version,
                    laz_backend,
                    iter_chunk_size,
                    file_progress,
                    task,
                )
            except Exception as e:
                file_progress.update(
                    task,
                    description=f"[bold red]{input_path.name}",
                )
                file_progress.console.print(
                    f"[bold red]{input_path} -> Failed with error: '{e}'"
                )
                num_fails += 1

        if num_fails == len(input_paths):
            overall_progress.update(overall_task, description=f"[red] Failed all tasks")
        elif num_fails == 0:
            overall_progress.update(
                overall_task,
                description=f"[green]Completed {len(input_paths)} with success",
            )
        else:
            overall_progress.update(
                overall_task,
                description=f"[dark_orange]Completed {len(input_paths) - num_fails} with success, {num_fails} failed",
            )


def version_callback(value: bool):
    if value:
        print(f"{laspy.__version__}")
        raise typer.Exit()


@app.command()
def version():
    """
    Print version information
    """
    version_callback(True)


@app.callback()
def app_main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Print version and exit",
    )
):
    # Silence warning
    _ = version


def main():
    app()


if __name__ == "__main__":
    app()
