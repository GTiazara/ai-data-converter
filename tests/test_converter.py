from pathlib import Path

import pyarrow as pa
import pytest
from pyarrow import csv, feather

from ia_data_format_converter import (
    InputFileError,
    InvalidOptionError,
    OutputExistsError,
    UnknownFormatError,
    convert,
)


def test_convert_csv_to_feather(sample_csv: Path, tmp_path: Path):
    output = convert(sample_csv, tmp_path / "out.feather", "feather")

    result = feather.read_table(output)
    assert result.column_names == ["id", "score", "label"]
    assert result.num_rows == 3
    assert result.equals(csv.read_csv(sample_csv))


def test_default_output_path(sample_csv: Path):
    output = convert(sample_csv, None, "feather")
    assert output == sample_csv.with_suffix(".feather")
    assert output.exists()


def test_existing_output_is_kept(sample_csv: Path, tmp_path: Path):
    output = tmp_path / "out.feather"
    output.write_bytes(b"original")

    with pytest.raises(OutputExistsError):
        convert(sample_csv, output, "feather")
    assert output.read_bytes() == b"original"


def test_overwrite_replaces_output(sample_csv: Path, tmp_path: Path):
    output = tmp_path / "out.feather"
    output.write_bytes(b"original")

    convert(sample_csv, output, "feather", overwrite=True)

    assert feather.read_table(output).num_rows == 3


def test_unknown_format_creates_nothing(sample_csv: Path, tmp_path: Path):
    output = tmp_path / "out.parquet"
    with pytest.raises(UnknownFormatError):
        convert(sample_csv, output, "parquet")
    assert list(tmp_path.iterdir()) == [sample_csv]


def test_invalid_compression_creates_nothing(sample_csv: Path, tmp_path: Path):
    with pytest.raises(InvalidOptionError):
        convert(sample_csv, tmp_path / "out.feather", "feather", compression="gzip")
    assert list(tmp_path.iterdir()) == [sample_csv]


def test_malformed_csv_leaves_no_output(tmp_path: Path):
    bad = tmp_path / "bad.csv"
    bad.write_text("a,b\n1,2\n3,4,5\n", encoding="utf-8")

    with pytest.raises(InputFileError):
        convert(bad, tmp_path / "out.feather", "feather")
    assert list(tmp_path.iterdir()) == [bad]


def test_zstd_compression(sample_csv: Path, tmp_path: Path):
    output = convert(
        sample_csv, tmp_path / "out.feather", "feather", compression="zstd"
    )
    assert feather.read_table(output).num_rows == 3


def test_select_columns_in_requested_order(sample_csv: Path, tmp_path: Path):
    output = convert(
        sample_csv, tmp_path / "out.feather", "feather", columns=["label", "id"]
    )

    table = feather.read_table(output)
    assert table.column_names == ["label", "id"]
    assert table.to_pydict() == {"label": ["cat", "dog", "bird"], "id": [1, 2, 3]}


def test_trim_whitespace_allows_selecting_padded_column_names(tmp_path: Path):
    source = tmp_path / "padded.csv"
    source.write_text(' "duration" ; "y"\n 261 ; "no" \n', encoding="utf-8")
    output = tmp_path / "selected.feather"

    convert(
        source,
        output,
        "feather",
        sep=";",
        columns=["duration", "y"],
        trim_whitespace=True,
    )

    result = feather.read_table(output)
    assert result.column_names == ["duration", "y"]
    assert result.to_pydict() == {"duration": [261], "y": ["no"]}


@pytest.mark.parametrize("columns", [["missing"], [], ["id", "id"], [""], "id"])
def test_invalid_columns_leave_no_output(sample_csv: Path, tmp_path: Path, columns):
    output = tmp_path / "out.feather"
    with pytest.raises(InvalidOptionError, match="[Cc]olumn"):
        convert(sample_csv, output, "feather", columns=columns)
    assert not output.exists()


def test_maps_string_values_to_integers(sample_csv: Path, tmp_path: Path):
    output = convert(
        sample_csv,
        tmp_path / "mapped.feather",
        "feather",
        value_mappings={"label": {"cat": 0, "dog": 1, "bird": 2}},
    )

    result = feather.read_table(output)
    assert result.column("label").type == pa.int64()
    assert result.column("label").to_pylist() == [0, 1, 2]


def test_mapping_keeps_nulls(sample_csv: Path, tmp_path: Path):
    output = convert(
        sample_csv,
        tmp_path / "mapped.feather",
        "feather",
        value_mappings={"score": {0.5: 1, 1.25: 2}},
    )
    assert feather.read_table(output).column("score").to_pylist() == [1, 2, None]


def test_unmapped_value_fails_without_output(sample_csv: Path, tmp_path: Path):
    output = tmp_path / "mapped.feather"
    with pytest.raises(InvalidOptionError, match="bird"):
        convert(
            sample_csv,
            output,
            "feather",
            value_mappings={"label": {"cat": 0, "dog": 1}},
        )
    assert not output.exists()


def test_add_id_column_is_first_and_zero_based(sample_csv: Path, tmp_path: Path):
    output = convert(
        sample_csv,
        tmp_path / "with-id.feather",
        "feather",
        columns=["label", "score"],
        add_id=True,
    )

    result = feather.read_table(output)
    assert result.column_names == ["id", "label", "score"]
    assert result.column("id").type == pa.int64()
    assert result.column("id").to_pylist() == [0, 1, 2]


def test_add_id_rejects_existing_output_column(sample_csv: Path, tmp_path: Path):
    output = tmp_path / "with-id.feather"
    with pytest.raises(InvalidOptionError, match="already exists"):
        convert(sample_csv, output, "feather", add_id=True)
    assert not output.exists()
