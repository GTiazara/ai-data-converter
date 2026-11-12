"""Conversion orchestration."""

import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa

from ia_data_format_converter.errors import InvalidOptionError, OutputExistsError
from ia_data_format_converter.readers import read_csv
from ia_data_format_converter.writers import get_writer


def default_output_path(input_path: str | Path, fmt: str) -> Path:
    """Return the input path with the extension of the target format."""
    return Path(input_path).with_suffix(get_writer(fmt).extension)


def convert(
    input_path: str | Path,
    output_path: str | Path | None,
    fmt: str,
    *,
    sep: str = ",",
    encoding: str = "utf-8",
    overwrite: bool = False,
    columns: Sequence[str] | None = None,
    trim_whitespace: bool = False,
    value_mappings: Mapping[str, Mapping[Any, Any]] | None = None,
    add_id: bool = False,
    **options: Any,
) -> Path:
    """Convert a CSV file to ``fmt`` and return the written output path.

    The output is written atomically: on failure no partial file is left behind.
    """
    writer = get_writer(fmt)
    options = writer.validate_options(**options)
    output = (
        Path(output_path)
        if output_path is not None
        else default_output_path(input_path, fmt)
    )
    if output.exists() and not overwrite:
        raise OutputExistsError(
            f"Output file already exists: {output} (use overwrite to replace)"
        )

    table = read_csv(
        input_path, sep=sep, encoding=encoding, trim_whitespace=trim_whitespace
    )

    if columns is not None:
        if (
            isinstance(columns, str)
            or not columns
            or any(not isinstance(column, str) or not column for column in columns)
        ):
            raise InvalidOptionError("Columns must be a non-empty list of column names")
        if len(set(columns)) != len(columns):
            raise InvalidOptionError("Columns must not contain duplicate names")
        for column in columns:
            count = table.column_names.count(column)
            if count != 1:
                raise InvalidOptionError(
                    f"Column {column!r} {'not found' if count == 0 else 'is ambiguous'}"
                )
        table = table.select(columns)

    if value_mappings is not None:
        if not isinstance(value_mappings, Mapping) or not value_mappings:
            raise InvalidOptionError(
                "Value mappings must be a non-empty mapping of columns"
            )
        for column, mapping in value_mappings.items():
            if (
                not isinstance(column, str)
                or not column
                or not isinstance(mapping, Mapping)
                or not mapping
            ):
                raise InvalidOptionError(
                    "Value mappings must map column names to non-empty value mappings"
                )
            if table.column_names.count(column) != 1:
                raise InvalidOptionError(
                    f"Mapping column {column!r} not found or ambiguous"
                )
            if any(
                isinstance(value, Mapping | list | tuple | set)
                for pair in mapping.items()
                for value in pair
            ):
                raise InvalidOptionError(
                    f"Mapping for column {column!r} must use scalar values"
                )

            source_values = table[column].to_pylist()
            unmapped = {
                value
                for value in source_values
                if value is not None and value not in mapping
            }
            if unmapped:
                raise InvalidOptionError(
                    f"Mapping for column {column!r} has no entries for values: "
                    f"{sorted(unmapped, key=str)!r}"
                )
            try:
                mapped_values = [
                    None if value is None else mapping[value] for value in source_values
                ]
                mapped_array = pa.array(mapped_values)
            except (TypeError, ValueError, pa.ArrowException) as exc:
                raise InvalidOptionError(
                    f"Mapping for column {column!r} cannot be represented as one column type: {exc}"
                ) from exc
            table = table.set_column(
                table.column_names.index(column), column, mapped_array
            )

    if not isinstance(add_id, bool):
        raise InvalidOptionError("add_id must be a boolean")
    if add_id:
        if "id" in table.column_names:
            raise InvalidOptionError(
                "Cannot add generated 'id' column: an 'id' column already exists"
            )
        table = table.add_column(
            0, "id", pa.array(range(table.num_rows), type=pa.int64())
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        writer.write(table, tmp_path, **options)
        os.replace(tmp_path, output)
    finally:
        tmp_path.unlink(missing_ok=True)
    return output
