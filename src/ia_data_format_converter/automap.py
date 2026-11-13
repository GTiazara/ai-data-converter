"""Automatic encoding of categorical columns and mapping reports."""

import json
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
import yaml

from ia_data_format_converter.errors import InvalidOptionError

REPORT_FORMATS = {".md": "markdown", ".yaml": "yaml", ".yml": "yaml", ".json": "json"}


def _categories(column: pa.ChunkedArray) -> list[Any]:
    return sorted(pc.unique(column).drop_null().to_pylist())


def _ordinal(table: pa.Table, column: str) -> tuple[pa.Table, dict[Any, Any]]:
    categories = _categories(table[column])
    codes = pc.index_in(
        table[column], value_set=pa.array(categories, table[column].type)
    )
    index = table.column_names.index(column)
    table = table.set_column(index, column, pc.cast(codes, pa.int64()))
    return table, {value: code for code, value in enumerate(categories)}


def _onehot(table: pa.Table, column: str) -> tuple[pa.Table, dict[Any, Any]]:
    source = table[column]
    categories = _categories(source)
    names = [f"{column}_{value}" for value in categories]
    clashes = sorted((set(table.column_names) - {column}).intersection(names))
    if clashes or len(set(names)) != len(names):
        raise InvalidOptionError(
            f"One-hot columns for {column!r} clash with existing names: {clashes or names}"
        )
    index = table.column_names.index(column)
    table = table.remove_column(index)
    for offset, (name, value) in enumerate(zip(names, categories, strict=True)):
        # Nulls encode as all zeros, like OneHotEncoder(handle_unknown="ignore").
        flags = pc.fill_null(pc.equal(source, pa.scalar(value, source.type)), False)
        table = table.add_column(index + offset, name, pc.cast(flags, pa.int8()))
    return table, dict(zip(categories, names, strict=True))


Encoder = Callable[[pa.Table, str], tuple[pa.Table, dict[Any, Any]]]
STRATEGIES: dict[str, Encoder] = {"ordinal": _ordinal, "onehot": _onehot}
_SPEC_KEYS = {"name", "strategy", "columns"}


def _is_categorical(column_type: pa.DataType) -> bool:
    return pa.types.is_string(column_type) or pa.types.is_large_string(column_type)


def auto_map(
    table: pa.Table,
    specs: Sequence[Mapping[str, Any]],
    exclude: Sequence[str] = (),
) -> tuple[pa.Table, dict[str, dict[str, Any]]]:
    """Encode categorical columns according to ``specs`` and return the table and report.

    Each spec is ``{"name": ..., "strategy": "ordinal" | "onehot", "columns": [...]}``.
    One spec may omit ``columns`` to target every remaining string column not in ``exclude``.
    """
    if isinstance(specs, str | Mapping) or not isinstance(specs, Sequence) or not specs:
        raise InvalidOptionError("Auto mappings must be a non-empty list of specs")

    assigned = set(exclude)
    plan: list[tuple[str, str, str]] = []
    catch_all: list[tuple[str, str]] = []
    for spec in specs:
        if not isinstance(spec, Mapping):
            raise InvalidOptionError("Each auto mapping spec must be a mapping")
        unknown = set(spec) - _SPEC_KEYS
        if unknown:
            raise InvalidOptionError(f"Unknown auto mapping keys: {sorted(unknown)}")
        strategy = spec.get("strategy")
        if strategy not in STRATEGIES:
            raise InvalidOptionError(
                f"Unknown auto mapping strategy {strategy!r}. Allowed: {', '.join(STRATEGIES)}"
            )
        name = spec.get("name", strategy)
        if not isinstance(name, str) or not name:
            raise InvalidOptionError("Auto mapping name must be a non-empty string")
        columns = spec.get("columns")
        if columns is None:
            catch_all.append((name, strategy))
            continue
        if (
            isinstance(columns, str)
            or not isinstance(columns, Sequence)
            or not columns
            or any(not isinstance(column, str) or not column for column in columns)
        ):
            raise InvalidOptionError(
                f"Auto mapping {name!r} columns must be a non-empty list of names"
            )
        for column in columns:
            if table.column_names.count(column) != 1:
                raise InvalidOptionError(
                    f"Auto mapping column {column!r} not found or ambiguous"
                )
            if column in assigned:
                raise InvalidOptionError(f"Column {column!r} is mapped more than once")
            assigned.add(column)
            plan.append((name, strategy, column))

    if len(catch_all) > 1:
        raise InvalidOptionError("Only one auto mapping spec may omit 'columns'")
    for name, strategy in catch_all:
        plan.extend(
            (name, strategy, field.name)
            for field in table.schema
            if field.name not in assigned and _is_categorical(field.type)
        )

    report: dict[str, dict[str, Any]] = {}
    for name, strategy, column in plan:
        table, mapping = STRATEGIES[strategy](table, column)
        report[column] = {"name": name, "strategy": strategy, "mapping": mapping}
    return table, report


def report_format(path: str | Path) -> str:
    """Return the report format implied by the file extension of ``path``."""
    fmt = REPORT_FORMATS.get(Path(path).suffix.lower())
    if fmt is None:
        raise InvalidOptionError(
            f"Mapping report must end with one of: {', '.join(REPORT_FORMATS)}"
        )
    return fmt


def _json_key(value: Any) -> Any:
    return (
        value
        if isinstance(value, str | int | float | bool) or value is None
        else str(value)
    )


def _md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _markdown(report: Mapping[str, Mapping[str, Any]]) -> str:
    lines = [
        "# Categorical mapping report",
        "",
        "| Column | Name | Strategy | Categories |",
        "| --- | --- | --- | --- |",
    ]
    lines += [
        f"| {_md_cell(column)} | {_md_cell(entry['name'])} | {entry['strategy']} "
        f"| {len(entry['mapping'])} |"
        for column, entry in report.items()
    ]
    for column, entry in report.items():
        lines += [
            "",
            f"## {_md_cell(column)} ({entry['strategy']})",
            "",
            "| Value | Encoded as |",
            "| --- | --- |",
        ]
        lines += [
            f"| {_md_cell(value)} | {_md_cell(code)} |"
            for value, code in entry["mapping"].items()
        ]
    return "\n".join(lines) + "\n"


def write_mapping_report(
    report: Mapping[str, Mapping[str, Any]], path: str | Path
) -> Path:
    """Write ``report`` as Markdown, YAML or JSON depending on the extension of ``path``."""
    path = Path(path)
    fmt = report_format(path)
    if fmt == "markdown":
        text = _markdown(report)
    elif fmt == "yaml":
        text = yaml.safe_dump(
            {"columns": {column: dict(entry) for column, entry in report.items()}},
            sort_keys=False,
            allow_unicode=True,
        )
    else:
        document = {
            "columns": {
                column: {
                    **entry,
                    "mapping": {_json_key(k): v for k, v in entry["mapping"].items()},
                }
                for column, entry in report.items()
            }
        }
        text = json.dumps(document, indent=2, ensure_ascii=False, default=str) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
