"""Command-line interface for ia-convert."""

import argparse
import sys
from collections.abc import Sequence
from typing import Any

from ia_data_format_converter.automap import STRATEGIES
from ia_data_format_converter.config import ConfigError, load_config
from ia_data_format_converter.converter import convert
from ia_data_format_converter.errors import ConversionError
from ia_data_format_converter.sources import available_sources
from ia_data_format_converter.writers import available_formats

_DEFAULTS: dict[str, Any] = {
    "input": None,
    "source": None,
    "output": None,
    "to": None,
    "sep": ",",
    "encoding": "utf-8",
    "compression": None,
    "overwrite": False,
    "columns": None,
    "trim_whitespace": False,
    "value_mappings": None,
    "add_id": False,
    "auto_mappings": None,
    "mapping_report": None,
}


def _parse_source(value: str) -> dict[str, str]:
    source_type, _, name = value.partition(":")
    if not source_type or not name:
        raise argparse.ArgumentTypeError(
            f"invalid source {value!r}: expected TYPE:NAME (e.g. sklearn:iris)"
        )
    return {"type": source_type, "name": name}


def build_parser() -> argparse.ArgumentParser:
    formats = available_formats()
    parser = argparse.ArgumentParser(
        prog="ia-convert",
        description="Convert a tabular CSV file or a data source into another data format.",
        epilog=(
            f"Available output formats: {', '.join(formats)}. "
            f"Available source types: {', '.join(available_sources())}."
        ),
    )
    # Defaults are None so that values from --config are only overridden when given explicitly.
    parser.add_argument("input", nargs="?", help="input CSV file (header row required)")
    parser.add_argument(
        "--source",
        type=_parse_source,
        metavar="TYPE:NAME",
        help="load a dataset from a data source instead of a CSV file (e.g. sklearn:iris)",
    )
    parser.add_argument("--to", choices=formats, help="output format")
    parser.add_argument(
        "-o",
        "--output",
        help="output file (default: input path with the format extension)",
    )
    parser.add_argument("--sep", help="CSV field separator (default: ',')")
    parser.add_argument("--encoding", help="CSV file encoding (default: utf-8)")
    parser.add_argument(
        "--columns", nargs="+", metavar="NAME", help="columns to include, in order"
    )
    trim_group = parser.add_mutually_exclusive_group()
    trim_group.add_argument(
        "--trim-whitespace", dest="trim_whitespace", action="store_true"
    )
    trim_group.add_argument(
        "--no-trim-whitespace", dest="trim_whitespace", action="store_false"
    )
    parser.set_defaults(trim_whitespace=None)
    id_group = parser.add_mutually_exclusive_group()
    id_group.add_argument("--add-id", dest="add_id", action="store_true")
    id_group.add_argument("--no-add-id", dest="add_id", action="store_false")
    parser.set_defaults(add_id=None)
    parser.add_argument(
        "--auto-map",
        choices=list(STRATEGIES),
        help="encode every string column not in value mappings with this strategy",
    )
    parser.add_argument(
        "--mapping-report",
        metavar="PATH",
        help="write a summary of applied mappings (.md, .yaml, .yml or .json)",
    )
    parser.add_argument(
        "--compression",
        help=(
            "output compression (feather: lz4 [default], zstd, uncompressed; "
            "h5: gzip [default], lzf, uncompressed; csv: none)"
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=None,
        help="replace the output file if it already exists",
    )
    parser.add_argument(
        "--config", help="YAML file providing default values for these options"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.input and args.source:
        parser.error("an input CSV file and --source are exclusive")

    settings = dict(_DEFAULTS)
    try:
        if args.config:
            settings.update(load_config(args.config))
    except ConfigError as exc:
        print(f"ia-convert: error: {exc}", file=sys.stderr)
        return 1
    # An origin given on the command line replaces the one from the configuration.
    if args.input:
        settings["source"] = None
    if args.source:
        settings["input"] = None
    auto_map = vars(args).pop("auto_map")
    settings.update(
        {k: v for k, v in vars(args).items() if k != "config" and v is not None}
    )
    if auto_map is not None:
        settings["auto_mappings"] = [{"strategy": auto_map}]

    if not settings["input"] and not settings["source"]:
        parser.error(
            "an input CSV file or a data source is required "
            "(argument, --source, or 'input'/'source' in --config)"
        )
    if settings["source"] and not settings["output"]:
        parser.error(
            "an output path is required with a data source (-o or 'output' in --config)"
        )
    if not settings["to"]:
        parser.error("an output format is required (--to or 'to' in --config)")

    options = {}
    if settings["compression"] is not None:
        options["compression"] = settings["compression"]
    try:
        output = convert(
            settings["input"],
            settings["output"],
            settings["to"],
            source=settings["source"],
            sep=settings["sep"],
            encoding=settings["encoding"],
            overwrite=settings["overwrite"],
            columns=settings["columns"],
            trim_whitespace=settings["trim_whitespace"],
            value_mappings=settings["value_mappings"],
            add_id=settings["add_id"],
            auto_mappings=settings["auto_mappings"],
            mapping_report=settings["mapping_report"],
            **options,
        )
    except (ConversionError, OSError) as exc:
        print(f"ia-convert: error: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote {output}")
    if settings["mapping_report"]:
        print(f"Wrote {settings['mapping_report']}")
    return 0
