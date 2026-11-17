import datetime
from pathlib import Path

import h5py
import numpy as np
import pyarrow as pa
import pytest
from pyarrow import csv, feather

from ia_data_format_converter.errors import InvalidOptionError, UnknownFormatError
from ia_data_format_converter.writers import available_formats, get_writer


@pytest.fixture
def table() -> pa.Table:
    return pa.table({"x": [1, 2, None], "y": ["a", "b", "c"]})


def test_available_formats():
    assert available_formats() == ["csv", "feather", "h5"]


def test_unknown_format_lists_available():
    with pytest.raises(UnknownFormatError, match="parquet.*feather"):
        get_writer("parquet")


@pytest.mark.parametrize("compression", [None, "lz4", "zstd", "uncompressed"])
def test_feather_roundtrip(tmp_path: Path, table: pa.Table, compression: str | None):
    path = tmp_path / "out.feather"
    options = {} if compression is None else {"compression": compression}

    get_writer("feather").write(table, path, **options)

    assert feather.read_table(path).equals(table)


def test_feather_default_compression_is_lz4():
    assert get_writer("feather").validate_options() == {"compression": "lz4"}


def test_feather_invalid_compression(tmp_path: Path, table: pa.Table):
    path = tmp_path / "out.feather"
    with pytest.raises(InvalidOptionError, match="gzip.*lz4, zstd, uncompressed"):
        get_writer("feather").write(table, path, compression="gzip")
    assert not path.exists()


def test_csv_roundtrip(tmp_path: Path, table: pa.Table):
    path = tmp_path / "out.csv"

    get_writer("csv").write(table, path)

    assert csv.read_csv(path).equals(table)
    assert path.read_text(encoding="utf-8").splitlines()[3].startswith(",")


def test_csv_rejects_compression(tmp_path: Path, table: pa.Table):
    path = tmp_path / "out.csv"
    with pytest.raises(InvalidOptionError, match="compression.*"):
        get_writer("csv").write(table, path, compression="gzip")
    assert not path.exists()


def test_h5_types_and_order(tmp_path: Path):
    table = pa.table(
        {
            "i": [1, 2, 3],
            "f": [0.5, 1.5, 2.5],
            "b": [True, False, True],
            "s": ["été", "b", "c"],
            "d": pa.array(
                [datetime.date(2024, 1, d) for d in (1, 2, 3)], type=pa.date32()
            ),
        }
    )
    path = tmp_path / "out.h5"

    get_writer("h5").write(table, path)

    with h5py.File(path, "r") as h5:
        assert list(h5.attrs["columns"]) == ["i", "f", "b", "s", "d"]
        assert h5["i"].dtype.kind == "i"
        assert list(h5["i"][()]) == [1, 2, 3]
        assert h5["f"].dtype.kind == "f"
        assert h5["b"].dtype == np.bool_
        assert list(h5["b"][()]) == [True, False, True]
        assert list(h5["s"].asstr()[()]) == ["été", "b", "c"]
        assert list(h5["d"].asstr()[()]) == ["2024-01-01", "2024-01-02", "2024-01-03"]
        assert h5["i"].compression == "gzip"


def test_h5_integer_nulls_become_nan(tmp_path: Path, table: pa.Table):
    path = tmp_path / "out.h5"

    get_writer("h5").write(table, path)

    with h5py.File(path, "r") as h5:
        values = h5["x"][()]
        assert values.dtype.kind == "f"
        assert values[:2].tolist() == [1.0, 2.0]
        assert np.isnan(values[2])


def test_h5_string_nulls_refused(tmp_path: Path):
    table = pa.table({"label": ["a", None]})
    with pytest.raises(InvalidOptionError, match="'label'"):
        get_writer("h5").write(table, tmp_path / "out.h5")


def test_h5_invalid_column_name(tmp_path: Path):
    table = pa.table({"a/b": [1]})
    with pytest.raises(InvalidOptionError, match="'a/b'"):
        get_writer("h5").write(table, tmp_path / "out.h5")
    assert not (tmp_path / "out.h5").exists()


def test_h5_lzf_compression(tmp_path: Path, table: pa.Table):
    path = tmp_path / "out.h5"

    get_writer("h5").write(table, path, compression="lzf")

    with h5py.File(path, "r") as h5:
        assert h5["x"].compression == "lzf"
        assert list(h5["y"].asstr()[()]) == ["a", "b", "c"]


def test_h5_uncompressed(tmp_path: Path, table: pa.Table):
    path = tmp_path / "out.h5"

    get_writer("h5").write(table, path, compression="uncompressed")

    with h5py.File(path, "r") as h5:
        assert h5["x"].compression is None


def test_h5_invalid_compression(tmp_path: Path, table: pa.Table):
    path = tmp_path / "out.h5"
    with pytest.raises(InvalidOptionError, match="lz4.*gzip, lzf, uncompressed"):
        get_writer("h5").write(table, path, compression="lz4")
    assert not path.exists()
