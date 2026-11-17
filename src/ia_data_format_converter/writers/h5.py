"""HDF5 writer: one 1-D dataset per column at the root, column order in attribute ``columns``."""

from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pyarrow as pa

from ia_data_format_converter.errors import InvalidOptionError

COMPRESSIONS = ("gzip", "lzf", "uncompressed")


def _column_to_numpy(name: str, column: pa.ChunkedArray) -> np.ndarray:
    array = column.combine_chunks()
    kind = array.type
    if pa.types.is_integer(kind) or pa.types.is_floating(kind):
        if array.null_count:
            array = array.cast(pa.float64())
        return array.to_numpy(zero_copy_only=False)
    if array.null_count:
        raise InvalidOptionError(
            f"Column {name!r} contains null values, which h5 only supports in numeric columns"
        )
    if pa.types.is_boolean(kind):
        return array.to_numpy(zero_copy_only=False)
    if pa.types.is_string(kind) or pa.types.is_large_string(kind):
        return np.array(array.to_pylist(), dtype=h5py.string_dtype("utf-8"))
    if pa.types.is_temporal(kind) and not pa.types.is_duration(kind):
        return np.array(
            [value.isoformat() for value in array.to_pylist()],
            dtype=h5py.string_dtype("utf-8"),
        )
    raise InvalidOptionError(f"Column {name!r} has a type not supported by h5: {kind}")


class H5Writer:
    name = "h5"
    extension = ".h5"

    def validate_options(
        self, compression: str | None = None, **extra: Any
    ) -> dict[str, Any]:
        if extra:
            raise InvalidOptionError(
                f"Unsupported option(s) for h5: {', '.join(sorted(extra))}"
            )
        compression = compression or "gzip"
        if compression not in COMPRESSIONS:
            raise InvalidOptionError(
                f"Invalid compression {compression!r}. Accepted values: {', '.join(COMPRESSIONS)}"
            )
        return {"compression": compression}

    def write(self, table: pa.Table, path: Path, **options: Any) -> None:
        compression = self.validate_options(**options)["compression"]
        for name in table.column_names:
            if not name or "/" in name or name == ".":
                raise InvalidOptionError(
                    f"Column name {name!r} is not a valid h5 dataset name"
                )
        arrays = {
            name: _column_to_numpy(name, table[name]) for name in table.column_names
        }
        filters = None if compression == "uncompressed" else compression
        with h5py.File(path, "w") as h5:
            for name, values in arrays.items():
                # Filters require chunking, which h5py cannot set up for empty datasets.
                h5.create_dataset(
                    name, data=values, compression=filters if len(values) else None
                )
            h5.attrs.create(
                "columns", list(table.column_names), dtype=h5py.string_dtype("utf-8")
            )
