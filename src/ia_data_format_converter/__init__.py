"""Convert tabular data (CSV files, data sources) into formats for ML/AI workloads."""

from ia_data_format_converter.automap import auto_map, write_mapping_report
from ia_data_format_converter.converter import convert, default_output_path
from ia_data_format_converter.errors import (
    ConversionError,
    InputFileError,
    InvalidOptionError,
    OutputExistsError,
    SourceError,
    UnknownFormatError,
    UnknownSourceError,
)
from ia_data_format_converter.readers import read_csv
from ia_data_format_converter.sources import available_sources
from ia_data_format_converter.writers import available_formats

__all__ = [
    "ConversionError",
    "InputFileError",
    "InvalidOptionError",
    "OutputExistsError",
    "SourceError",
    "UnknownFormatError",
    "UnknownSourceError",
    "auto_map",
    "available_formats",
    "available_sources",
    "convert",
    "default_output_path",
    "read_csv",
    "write_mapping_report",
]
