import json
from pathlib import Path

import pyarrow as pa
import pytest
import yaml
from pyarrow import feather

from ia_data_format_converter import (
    InvalidOptionError,
    OutputExistsError,
    auto_map,
    convert,
)
from ia_data_format_converter.cli import main


@pytest.fixture
def table() -> pa.Table:
    return pa.table(
        {
            "job": ["b", "a", None, "b"],
            "y": ["no", "yes", "no", "no"],
            "age": [30, 40, 50, 60],
        }
    )


def test_ordinal_sorts_categories_and_keeps_nulls(table: pa.Table):
    result, report = auto_map(table, [{"strategy": "ordinal", "columns": ["job"]}])

    assert result["job"].to_pylist() == [1, 0, None, 1]
    assert result["job"].type == pa.int64()
    assert report["job"] == {
        "name": "ordinal",
        "strategy": "ordinal",
        "mapping": {"a": 0, "b": 1},
    }


def test_onehot_replaces_column_in_place(table: pa.Table):
    result, report = auto_map(
        table, [{"name": "categorical", "strategy": "onehot", "columns": ["job"]}]
    )

    assert result.column_names == ["job_a", "job_b", "y", "age"]
    assert result["job_a"].to_pylist() == [0, 1, 0, 0]
    assert result["job_b"].to_pylist() == [1, 0, 0, 1]
    assert report["job"]["name"] == "categorical"
    assert report["job"]["mapping"] == {"a": "job_a", "b": "job_b"}


def test_catch_all_targets_remaining_string_columns(table: pa.Table):
    result, report = auto_map(
        table,
        [{"strategy": "onehot", "columns": ["job"]}, {"strategy": "ordinal"}],
    )

    assert list(report) == ["job", "y"]
    assert result["y"].to_pylist() == [0, 1, 0, 0]
    assert result["age"].to_pylist() == [30, 40, 50, 60]


def test_exclude_skips_columns_for_catch_all(table: pa.Table):
    _, report = auto_map(table, [{"strategy": "ordinal"}], exclude=["y"])
    assert list(report) == ["job"]


@pytest.mark.parametrize(
    "specs",
    [
        [],
        [{"strategy": "target"}],
        [{"strategy": "ordinal", "columns": ["missing"]}],
        [{"strategy": "ordinal", "columns": "job"}],
        [
            {"strategy": "ordinal", "columns": ["job"]},
            {"strategy": "onehot", "columns": ["job"]},
        ],
        [{"strategy": "ordinal"}, {"strategy": "onehot"}],
        [{"strategy": "ordinal", "extra": 1}],
    ],
)
def test_invalid_specs(table: pa.Table, specs):
    with pytest.raises(InvalidOptionError):
        auto_map(table, specs)


def test_onehot_name_clash():
    clash = pa.table({"c": ["x"], "c_x": [1]})
    with pytest.raises(InvalidOptionError, match="clash"):
        auto_map(clash, [{"strategy": "onehot", "columns": ["c"]}])


@pytest.mark.parametrize("suffix", [".json", ".yaml", ".md"])
def test_convert_writes_report(sample_csv: Path, tmp_path: Path, suffix: str):
    report_path = tmp_path / f"report{suffix}"

    output = convert(
        sample_csv,
        tmp_path / "out.feather",
        "feather",
        value_mappings={"id": {1: 10, 2: 20, 3: 30}},
        auto_mappings=[{"strategy": "onehot"}],
        mapping_report=report_path,
    )

    assert feather.read_table(output).column_names == [
        "id",
        "score",
        "label_bird",
        "label_cat",
        "label_dog",
    ]
    text = report_path.read_text(encoding="utf-8")
    if suffix == ".json":
        columns = json.loads(text)["columns"]
        assert columns["id"]["mapping"] == {"1": 10, "2": 20, "3": 30}
        assert columns["label"]["mapping"]["cat"] == "label_cat"
    elif suffix == ".yaml":
        columns = yaml.safe_load(text)["columns"]
        assert columns["id"]["strategy"] == "manual"
        assert columns["label"]["mapping"] == {
            "bird": "label_bird",
            "cat": "label_cat",
            "dog": "label_dog",
        }
    else:
        assert "| label | onehot | onehot | 3 |" in text
        assert "| cat | label_cat |" in text


def test_report_invalid_extension(sample_csv: Path, tmp_path: Path):
    with pytest.raises(InvalidOptionError):
        convert(
            sample_csv,
            tmp_path / "out.feather",
            "feather",
            mapping_report=tmp_path / "r.txt",
        )
    assert not (tmp_path / "out.feather").exists()


def test_existing_report_is_kept(sample_csv: Path, tmp_path: Path):
    report_path = tmp_path / "r.json"
    report_path.write_text("original")

    with pytest.raises(OutputExistsError):
        convert(
            sample_csv, tmp_path / "out.feather", "feather", mapping_report=report_path
        )
    assert report_path.read_text() == "original"


def test_cli_auto_map(sample_csv: Path, tmp_path: Path):
    output = tmp_path / "out.feather"
    report_path = tmp_path / "r.yaml"

    code = main(
        [
            str(sample_csv),
            "--to",
            "feather",
            "-o",
            str(output),
            "--auto-map",
            "ordinal",
            "--mapping-report",
            str(report_path),
        ]
    )

    assert code == 0
    assert feather.read_table(output)["label"].to_pylist() == [1, 2, 0]
    assert (
        yaml.safe_load(report_path.read_text())["columns"]["label"]["strategy"]
        == "ordinal"
    )


def test_cli_config_auto_mappings(sample_csv: Path, tmp_path: Path):
    config = tmp_path / "c.yaml"
    config.write_text(
        f"input: {sample_csv.name}\nto: feather\noutput: out.feather\n"
        "auto_mappings:\n  - name: categorical\n    strategy: onehot\n    columns: [label]\n"
        "mapping_report: report.md\n"
    )

    assert main(["--config", str(config)]) == 0
    assert "label_cat" in feather.read_table(tmp_path / "out.feather").column_names
    assert (tmp_path / "report.md").exists()


def test_cli_invalid_strategy_in_config(sample_csv: Path, tmp_path: Path, capsys):
    config = tmp_path / "c.yaml"
    config.write_text(
        f"input: {sample_csv.name}\nto: feather\nauto_mappings:\n  - strategy: magic\n"
    )

    assert main(["--config", str(config)]) != 0
    assert "magic" in capsys.readouterr().err
