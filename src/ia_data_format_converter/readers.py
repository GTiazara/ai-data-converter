"""Readers turning input files into Arrow tables."""

import csv as stdlib_csv
from io import StringIO
from pathlib import Path

import pyarrow as pa
from pyarrow import csv

from ia_data_format_converter.errors import InputFileError, InvalidOptionError


def read_csv(
    path: str | Path,
    sep: str = ",",
    encoding: str = "utf-8",
    trim_whitespace: bool = False,
) -> pa.Table:
    """Read a CSV file with a header row into an Arrow table with inferred column types."""
    path = Path(path)
    if len(sep) != 1:
        raise InvalidOptionError(f"Separator must be a single character, got {sep!r}")
    if not path.is_file():
        raise InputFileError(f"Input file not found: {path}")
    if path.stat().st_size == 0:
        raise InputFileError(f"Input file is empty: {path}")

    try:
        source = path
        if trim_whitespace:
            normalized = StringIO(newline="")
            with path.open(encoding=encoding, newline="") as input_file:
                rows = stdlib_csv.reader(input_file, delimiter=sep, skipinitialspace=True)
                writer = stdlib_csv.writer(normalized, delimiter=sep)
                for row in rows:
                    writer.writerow([value.strip() for value in row])
            source = pa.BufferReader(normalized.getvalue().encode("utf-8"))
        return csv.read_csv(
            source,
            read_options=csv.ReadOptions(encoding="utf-8" if trim_whitespace else encoding),
            parse_options=csv.ParseOptions(delimiter=sep),
        )
    except LookupError as exc:
        raise InvalidOptionError(f"Unknown encoding: {encoding!r}") from exc
    except (pa.ArrowInvalid, UnicodeDecodeError, stdlib_csv.Error) as exc:
        raise InputFileError(f"Cannot read CSV file {path}: {exc}") from exc
