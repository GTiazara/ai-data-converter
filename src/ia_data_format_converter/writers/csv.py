"""CSV writer."""

from pathlib import Path
from typing import Any

import pyarrow as pa
from pyarrow import csv

from ia_data_format_converter.errors import InvalidOptionError


class CsvWriter:
    name = "csv"
    extension = ".csv"

    def validate_options(self, **options: Any) -> dict[str, Any]:
        if options:
            raise InvalidOptionError(f"Unsupported option(s) for csv: {', '.join(sorted(options))}")
        return {}

    def write(self, table: pa.Table, path: Path, **options: Any) -> None:
        self.validate_options(**options)
        csv.write_csv(table, path)
