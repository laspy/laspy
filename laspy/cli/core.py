import copy
import enum
import sys
import typing
from collections import deque
from contextlib import ExitStack
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

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
    return input_files, output_files


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
            raise typer.Abort()
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
# Create and use a different enum for LAZ backend management in the CLI
# as typer only supports enum where variants value are str,
# Changing the laspy.LazBackend would be technically breaking.
#
# Having an Enum(str) allows to have --laz-backend=lazrs or laz-backend=laszip
# and not --laz-backend=1 --laz-backend=0 as command line arguments
CliLazBackend = Enum(
    "CliLazBackend",
    {
        str(variant).split(".")[-1]: backend_to_cli_name[variant]
        for variant in laspy.LazBackend
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
        help="Directory where converted file will be written, or filename of the converted file(s)",
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


def parse_float_or_int(string: str) -> Union[float, int]:
    """
    Parses an string as either an int or float.
    """
    value = None
    try:
        value = int(string)
    except ValueError:
        pass

    if value is None:
        try:
            value = float(string)
        except ValueError:
            pass

    if value is None:
        raise ValueError(f"string '{string}' is neither an int nor a float")
    return value


def parse_list_of_numbers(string: str) -> List[Union[float, int]]:
    """
    Parses a string representing a list of number in the form
    "[1, 2]" or "(1, 2)".
    """
    string = string.strip()
    first_char = string[0]
    last_char = string[-1]

    if (first_char, last_char) not in (("[", "]"), ("(", ")")):
        raise ValueError(
            f"'{string}' does not represent a list (missing '[' and/or ']')"
        )

    string = string[1:-1]
    values = []
    for value_str in string.split(","):
        values.append(parse_float_or_int(value_str))
    return values


T = TypeVar("T")


class PeekIterator(Generic[T]):
    """
    Iterator that allows to 'peek' values, that is,
    get the next value without advancing the iterator
    """

    def __init__(self, iterable: Iterable[T]):
        self.iterator = iter(iterable)
        self.peeked = deque()

    def __iter__(self):
        return self

    def __next__(self) -> T:
        if self.peeked:
            return self.peeked.popleft()
        return next(self.iterator)

    def peek(self, ahead=0) -> T:
        while len(self.peeked) <= ahead:
            self.peeked.append(next(self.iterator))
        return self.peeked[ahead]

    def peek_safe(self, default, ahead=0) -> T:
        try:
            return self.peek()
        except StopIteration:
            return default


@dataclass
class Token:
    """
    Token for our mini expression filter language
    """

    class Kind(enum.IntEnum):
        OpenParen = enum.auto()
        CloseParen = enum.auto()
        Bang = enum.auto()  # `!`
        EqEq = enum.auto()
        NotEq = enum.auto()
        Less = enum.auto()
        LessEq = enum.auto()
        Greater = enum.auto()
        GreaterEq = enum.auto()
        In = enum.auto()
        AmpAmp = enum.auto()  # `&&`
        PipePipe = enum.auto()  # `||`
        And = enum.auto()  # `and` keyword
        Or = enum.auto()  # `or` keyword
        Not = enum.auto()  # `not` keyword
        LiteralStr = enum.auto()

    kind: Kind
    value: str

    def is_comparator(self) -> bool:
        return {
            Token.Kind.OpenParen: False,
            Token.Kind.CloseParen: False,
            Token.Kind.Bang: False,
            Token.Kind.EqEq: True,
            Token.Kind.NotEq: True,
            Token.Kind.Less: True,
            Token.Kind.LessEq: True,
            Token.Kind.Greater: True,
            Token.Kind.GreaterEq: True,
            Token.Kind.In: True,
            Token.Kind.AmpAmp: True,
            Token.Kind.PipePipe: True,
            Token.Kind.And: False,
            Token.Kind.Or: False,
            Token.Kind.LiteralStr: False,
        }[self.kind]

    def is_binary_logical_operator(self) -> bool:
        return {
            Token.Kind.OpenParen: False,
            Token.Kind.CloseParen: False,
            Token.Kind.Bang: False,
            Token.Kind.EqEq: False,
            Token.Kind.NotEq: False,
            Token.Kind.Less: False,
            Token.Kind.LessEq: False,
            Token.Kind.Greater: False,
            Token.Kind.GreaterEq: False,
            Token.Kind.In: False,
            Token.Kind.AmpAmp: True,
            Token.Kind.PipePipe: True,
            Token.Kind.And: True,
            Token.Kind.Or: True,
            Token.Kind.LiteralStr: False,
        }[self.kind]


class Lexer:
    """
    The lexer that transform a string that is a represent a
    filter expression into a list of tokens
    """

    _keywords: Dict[str, Token] = {
        "and": Token(Token.Kind.And, "and"),
        "or": Token(Token.Kind.Or, "or"),
        "in": Token(Token.Kind.In, "in"),
        "not": Token(Token.Kind.Not, "not"),
    }

    def __init__(self, char_iter: PeekIterator[str]):
        self.char_iter: PeekIterator[str] = char_iter
        self.tokens: List[Token] = []
        self.current_literal: str = ""

    @staticmethod
    def tokenize_string(string: str) -> List[Token]:
        lexer = Lexer(PeekIterator(string))
        return lexer.tokenize()

    def tokenize(self) -> List[Token]:
        new_token: Optional[Token] = None
        while (char := next(self.char_iter, None)) is not None:
            if char == " ":
                self._flush_current_literal()
                continue

            if char == "(":
                new_token = Token(Token.Kind.OpenParen, "(")
            elif char == ")":
                new_token = Token(Token.Kind.CloseParen, ")")
            elif char == "[":
                # This is a bit of a hack but works for our simplistic
                # language. It is made to still consider things like "[1,2 ,3]"
                # as a single literal token.
                # And not have to have it considered as:
                # OpenBracket, LiteralInt, Comma, LiteralInt, Comma, LiteralInt, CloseBracket
                self.current_literal += char
                while True:
                    nc = next(self.char_iter, None)
                    if nc is None:
                        break
                    self.current_literal += nc
                    if nc == "]":
                        break
            elif char == "!":
                nchar = self.char_iter.peek()
                if nchar == "=":
                    _ = next(self.char_iter)
                    new_token = Token(Token.Kind.NotEq, "!=")
                else:
                    new_token = Token(Token.Kind.Bang, "!")
            elif char == "=" and self.char_iter.peek() == "=":
                _ = next(self.char_iter)
                new_token = Token(Token.Kind.EqEq, "==")
            elif char == "&" and self.char_iter.peek() == "&":
                _ = next(self.char_iter)
                new_token = Token(Token.Kind.AmpAmp, "&&")
            elif char == "|" and self.char_iter.peek() == "|":
                _ = next(self.char_iter)
                new_token = Token(Token.Kind.PipePipe, "||")
            elif char == "<":
                nchar = self.char_iter.peek()
                if nchar == "=":
                    _ = next(self.char_iter)
                    new_token = Token(Token.Kind.LessEq, "<=")
                else:
                    new_token = Token(Token.Kind.Less, "<")
            elif char == ">":
                nchar = self.char_iter.peek()
                if nchar == "=":
                    _ = next(self.char_iter)
                    new_token = Token(Token.Kind.GreaterEq, ">=")
                else:
                    new_token = Token(Token.Kind.Greater, ">")
            else:
                self.current_literal += char

            if new_token is not None:
                self._flush_current_literal()
                self.tokens.append(new_token)
                new_token = None

        self._flush_current_literal()

        return self.tokens

    def _flush_current_literal(self) -> None:
        if not self.current_literal:
            return
        current_literal = self.current_literal.strip()

        try:
            token = self._keywords[current_literal]
        except KeyError:
            token = Token(Token.Kind.LiteralStr, current_literal)

        self.current_literal = ""
        self.tokens.append(token)


def tokenize(string: str) -> List[Token]:
    return Lexer.tokenize_string(string)


class Condition(enum.Enum):
    """
    Possible conditions to 'merge' results
    from two filter action
    """

    And = "and"
    Or = "or"


# enum.StrEnum exists only since 3.11
class Comparator(enum.Enum):
    """
    The different comparators that can be used to filter points
    depending on field values
    """

    # Note that order of these is important,
    # >= and <= must be before < and >

    Equality = "=="
    Difference = "!="
    GreaterOrEqual = ">="
    LessOrEqual = "<="
    LessThan = "<"
    GreaterThan = ">"
    In = "in"


@dataclass
class FilteringAction:
    """
    An applicable filtering action.

    It containts the name of the field used in the comparison
    the comparator to apply and the value(s) to compare with
    """

    field_name: str
    comparator: Comparator
    value: str  # Parsed to a concrete type when actually used

    # Translate some pdal names to laspy names
    _pdal_name_to_laspy: ClassVar[Dict[str, str]] = {
        "Classification": "classification",
        "Intensity": "intensity",
        "PointSourceId": "point_source_id",
        "ReturnNumber": "return_number",
        "NumberOfReturns": "number_of_returns",
        "ScanDirectionFlag": "scan_direction_flag",
        "EdgeOfFlightLine": "edge_of_flight_line",
        "ScanAngleRank": "scan_angle_rank",
        "UserData": "user_data",
        "Red": "red",
        "Green": "green",
        "Blue": "blue",
        "GpsTime": "gps_time",
        "Infrared": "nir",
        "ClassFlags": "classification_flags",
    }

    # Translate a comparator token into the corresponding Comparator
    _comparator_token_to_comparator: ClassVar[Dict[Token.Kind, Comparator]] = {
        Token.Kind.EqEq: Comparator.Equality,
        Token.Kind.NotEq: Comparator.Difference,
        Token.Kind.Less: Comparator.LessThan,
        Token.Kind.LessEq: Comparator.LessOrEqual,
        Token.Kind.Greater: Comparator.GreaterThan,
        Token.Kind.GreaterEq: Comparator.GreaterOrEqual,
        Token.Kind.In: Comparator.In,
    }

    @classmethod
    def parse_string(cls, string: str) -> "FilteringAction":
        tokens = tokenize(string)
        return cls.parse_tokens(PeekIterator(tokens))

    @classmethod
    def parse_tokens(cls, tokens: PeekIterator[Token]) -> "FilteringAction":
        try:
            field_name_tok = next(tokens)
            cmp_tok = next(tokens)
            value_tok = next(tokens)
        except StopIteration:
            raise ValueError(f"'could not be parsed as a filtering action") from None

        if field_name_tok.kind != Token.Kind.LiteralStr:
            raise ValueError(f"expected field_name found '{field_name_tok.value}'")

        if not cmp_tok.is_comparator():
            raise ValueError(f"'{cmp_tok.value}' is not a comparator")

        if value_tok.kind != Token.Kind.LiteralStr:
            raise ValueError(f"expected value found '{value_tok.value}'")

        comparator = cls._comparator_token_to_comparator.get(cmp_tok.kind, None)
        assert (
            comparator is not None
        ), "Internal error: unhandled token to comparator conversion"

        return cls(
            field_name=field_name_tok.value,
            comparator=comparator,
            value=value_tok.value,
        )

    def apply(self, points: laspy.ScaleAwarePointRecord) -> np.array:
        """
        Computes the filtering.

        Returns a numpy array of boolean values.
        """

        field_name = self._pdal_name_to_laspy.get(self.field_name, self.field_name)

        try:
            field_values = points[field_name]
        except ValueError:
            print(f"No field named '{field_name}' in the file")
            print(f"Available fields are {list(points.point_format.dimension_names)}")
            raise typer.Abort()

        comparator_to_processing: Dict[Comparator, Callable[[Any, Any], np.array]] = {
            Comparator.Equality: np.equal,
            Comparator.Difference: np.not_equal,
            Comparator.LessThan: np.less,
            Comparator.LessOrEqual: np.less_equal,
            Comparator.GreaterThan: np.greater,
            Comparator.GreaterOrEqual: np.greater_equal,
            Comparator.In: np.isin,
        }
        comparator_to_parse_func: Dict[Comparator, Callable[[str], Any]] = {
            Comparator.Equality: parse_float_or_int,
            Comparator.Difference: parse_float_or_int,
            Comparator.LessThan: parse_float_or_int,
            Comparator.LessOrEqual: parse_float_or_int,
            Comparator.GreaterThan: parse_float_or_int,
            Comparator.GreaterOrEqual: parse_float_or_int,
            Comparator.In: parse_list_of_numbers,
        }
        try:
            cmp_func = comparator_to_processing[self.comparator]
            parse_func = comparator_to_parse_func[self.comparator]
        except KeyError:
            raise RuntimeError(
                f"Internal error: invalid comparator: {self.comparator}"
            ) from None

        cmp_value = parse_func(self.value)
        return cmp_func(field_values, cmp_value)


# This could have been a UnaryExpression class
# But the only unary operator we have is `not`
@dataclass
class NegatedFilteringExpression:
    expr: "FilteringExpression"


@dataclass
class BinaryFilteringExpression:
    condition: Condition
    lhs: "FilteringExpression"
    rhs: "FilteringExpression"


class FilteringExpressionKind(enum.IntEnum):
    Action = enum.auto()
    Negated = enum.auto()
    Binary = enum.auto()


@dataclass
class FilteringExpression:
    kind: FilteringExpressionKind
    data: Union[FilteringAction, NegatedFilteringExpression, BinaryFilteringExpression]

    @classmethod
    def parse_string(cls, string: str) -> "FilteringExpression":
        tokens = tokenize(string)
        tokens = PeekIterator(tokens)
        return cls.parse_tokens(tokens)

    @classmethod
    def parse_tokens(cls, tokens: PeekIterator[Token]) -> "FilteringExpression":
        condition_tok_to_condition: Dict[Token.Kind, Condition] = {
            Token.Kind.AmpAmp: Condition.And,
            Token.Kind.PipePipe: Condition.Or,
            Token.Kind.And: Condition.And,
            Token.Kind.Or: Condition.Or,
        }

        tok = tokens.peek()

        if tok.kind == Token.Kind.OpenParen:
            _ = next(tokens)
            expr = cls.parse_tokens(tokens)
            tok = next(tokens)
            if tok.kind != Token.Kind.CloseParen:
                raise ValueError("Unmatched Open Paren")

            tok = next(tokens, None)
            if tok is None:
                return expr

            if not tok.is_binary_logical_operator():
                raise ValueError(
                    f"Failed to parse expresion, expected a logical operator found {tok.value}"
                )

            condition = condition_tok_to_condition.get(tok.kind, None)
            assert (
                condition is not None
            ), "Internal error: unhandled convertion from token to condition"

            rhs = cls.parse_tokens(tokens)
            return cls(
                kind=FilteringExpressionKind.Binary,
                data=BinaryFilteringExpression(condition, expr, rhs),
            )

        if tok.kind == Token.Kind.Not or tok.kind == tok.kind.Bang:
            _ = next(tokens)  # consume the not token
            expr = cls.parse_tokens(tokens)
            return cls(
                kind=FilteringExpressionKind.Negated,
                data=NegatedFilteringExpression(expr),
            )

        lhs = FilteringAction.parse_tokens(tokens)
        tok = tokens.peek_safe(default=None)
        if tok is None:
            return cls(kind=FilteringExpressionKind.Action, data=lhs)
        if tok.kind == Token.Kind.CloseParen:
            # TODO this feels dirty, needs better grammar definition
            return cls(kind=FilteringExpressionKind.Action, data=lhs)

        tok = next(tokens)  # now we can consumme the token
        if not tok.is_binary_logical_operator():
            raise ValueError(
                f"Failed to parse expresion, expected a logical operator found {tok.value}"
            )

        condition = condition_tok_to_condition.get(tok.kind, None)
        assert (
            condition is not None
        ), "Internal error: unhandled convertion from token to condition"

        rhs = cls.parse_tokens(tokens)

        expr = cls(
            kind=FilteringExpressionKind.Binary,
            data=BinaryFilteringExpression(
                condition=condition,
                lhs=FilteringExpression(kind=FilteringExpressionKind.Action, data=lhs),
                rhs=rhs,
            ),
        )
        return expr

    def apply(self, points: laspy.ScaleAwarePointRecord) -> np.array:
        """Recursively applies the expression and returns an array of bool"""

        if self.kind == FilteringExpressionKind.Action:
            action = typing.cast(FilteringAction, self.data)
            return action.apply(points)
        elif self.kind == FilteringExpressionKind.Negated:
            data = typing.cast(NegatedFilteringExpression, self.data)
            return np.logical_not(data.expr.apply(points))
        elif self.kind == FilteringExpressionKind.Binary:
            data = typing.cast(BinaryFilteringExpression, self.data)
            lhs_result = data.lhs.apply(points)
            rhs_result = data.rhs.apply(points)
            if data.condition == Condition.And:
                return np.logical_and(lhs_result, rhs_result)
            elif data.condition == Condition.Or:
                return np.logical_or(lhs_result, rhs_result)
            else:
                raise RuntimeError("Internal error: invalid condition")
        else:
            raise RuntimeError(f"Internal error: invalid kind {self.kind}")


def _filter_file_at_path(
    input_path: Path,
    output_path: Path,
    filter_expression: FilteringExpression,
    laz_backend: Optional[CliLazBackend],
    iter_chunk_size: int,
    progress: Progress,
    task: TaskID,
):
    with ExitStack() as stack:
        reader = laspy.open(input_path, laz_backend=cli_name_to_backend[laz_backend])
        reader = stack.enter_context(reader)

        progress.update(task, total=reader.header.point_count)

        header = copy.deepcopy(reader.header)

        writer = laspy.open(
            output_path, mode="w", laz_backend=laz_backend, header=header
        )
        writer = stack.enter_context(writer)

        for chunk in reader.chunk_iterator(iter_chunk_size):
            mask = filter_expression.apply(chunk)
            writer.write_points(chunk[mask])
            progress.update(task, advance=len(chunk))


@app.command()
def filter(
    input_path: Path = typer.Argument(
        ...,
        help="Path to file or directory of files to filter",
    ),
    output_path: Path = typer.Argument(
        ...,
        help="Directory where converted file will be written, or filename of the filtered file(s)",
    ),
    filter_expression: str = typer.Argument(
        ..., help="The expresion to use as the filter"
    ),
    laz_backend: Optional[CliLazBackend] = typer.Option(
        None, help="The Laz backend to use."
    ),
    iter_chunk_size: int = ITER_CHUNK_SIZE_OPTION,
):
    """
    Filters LAS/LAZ file(s)

    Examples:


    laspy filter file.las ground.las "classification == 2"

    ---

    laspy filter file.las filtered.las "classification in [2, 3] and x > 10.0"

    ___

    laspy filter file.las filtered.las "(intensity >= 128 and intensity <= 256) and classification == 2"
    """
    try:
        filter_expression = FilteringExpression.parse_string(filter_expression)
    except Exception as e:
        print(str(e))
        print(f"Failed to parse filter expression")
        raise typer.Abort()

    laz_backend = cli_name_to_backend[laz_backend] if laz_backend is not None else None
    input_paths, output_paths = _list_input_and_ouput_files(input_path, output_path)

    if len(input_paths) > len(output_paths):
        rich.print(f"[bold red]Cannot filter many files into one")
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
                _filter_file_at_path(
                    input_path,
                    output_path,
                    filter_expression,
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
