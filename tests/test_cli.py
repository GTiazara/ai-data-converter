from pathlib import Path

import h5py
import pytest
from pyarrow import csv, feather

from ia_data_format_converter.cli import main


def test_convert_success(sample_csv: Path, tmp_path: Path, capsys):
    output = tmp_path / "out.feather"

    assert main([str(sample_csv), "--to", "feather", "-o", str(output)]) == 0
    assert feather.read_table(output).num_rows == 3
    assert str(output) in capsys.readouterr().out


def test_help_lists_formats(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "feather" in capsys.readouterr().out


def test_implicit_output(sample_csv: Path):
    assert main([str(sample_csv), "--to", "feather"]) == 0
    assert sample_csv.with_suffix(".feather").exists()


def test_overwrite_refused(sample_csv: Path, tmp_path: Path, capsys):
    output = tmp_path / "out.feather"
    output.write_bytes(b"original")

    assert main([str(sample_csv), "--to", "feather", "-o", str(output)]) != 0
    assert "already exists" in capsys.readouterr().err
    assert output.read_bytes() == b"original"


def test_overwrite_allowed(sample_csv: Path, tmp_path: Path):
    output = tmp_path / "out.feather"
    output.write_bytes(b"original")

    assert (
        main([str(sample_csv), "--to", "feather", "-o", str(output), "--overwrite"])
        == 0
    )
    assert feather.read_table(output).num_rows == 3


def test_missing_input(tmp_path: Path, capsys):
    missing = tmp_path / "missing.csv"

    assert main([str(missing), "--to", "feather"]) != 0
    err = capsys.readouterr().err
    assert "missing.csv" in err
    assert "Traceback" not in err


def test_unknown_format(sample_csv: Path, capsys):
    with pytest.raises(SystemExit) as exc:
        main([str(sample_csv), "--to", "zarr"])
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "zarr" in err
    assert "feather" in err


def test_unknown_format_from_config(sample_csv: Path, tmp_path: Path, capsys):
    conf = tmp_path / "c.yaml"
    conf.write_text("to: zarr\n")

    assert main([str(sample_csv), "--config", str(conf)]) != 0
    err = capsys.readouterr().err
    assert "zarr" in err
    assert "feather" in err


def test_sep_and_compression_from_config(tmp_path: Path, monkeypatch):
    (tmp_path / "data.csv").write_text("a;b\n1;x\n", encoding="utf-8")
    conf = tmp_path / "c.yaml"
    conf.write_text("input: data.csv\nto: feather\nsep: ';'\ncompression: zstd\n")
    calls = {}

    import ia_data_format_converter.cli as cli

    real_convert = cli.convert

    def spy(*args, **kwargs):
        calls.update(kwargs)
        return real_convert(*args, **kwargs)

    monkeypatch.setattr(cli, "convert", spy)

    assert main(["--config", str(conf)]) == 0
    assert calls["sep"] == ";"
    assert calls["compression"] == "zstd"
    assert feather.read_table(tmp_path / "data.feather").column_names == ["a", "b"]


def test_cli_overrides_config(sample_csv: Path, tmp_path: Path, monkeypatch):
    conf = tmp_path / "c.yaml"
    conf.write_text("to: feather\ncompression: zstd\n")
    calls = {}

    import ia_data_format_converter.cli as cli

    real_convert = cli.convert

    def spy(*args, **kwargs):
        calls.update(kwargs)
        return real_convert(*args, **kwargs)

    monkeypatch.setattr(cli, "convert", spy)

    assert main([str(sample_csv), "--config", str(conf), "--compression", "lz4"]) == 0
    assert calls["compression"] == "lz4"


def test_invalid_config(sample_csv: Path, tmp_path: Path, capsys):
    conf = tmp_path / "c.yaml"
    conf.write_text("compresion: zstd\n")

    assert main([str(sample_csv), "--to", "feather", "--config", str(conf)]) != 0
    assert "compresion" in capsys.readouterr().err


def test_columns_from_config_and_cli_override(sample_csv: Path, tmp_path: Path):
    conf = tmp_path / "c.yaml"
    conf.write_text("to: feather\ncolumns: [score, id]\n")
    output = tmp_path / "out.feather"

    assert main([str(sample_csv), "--config", str(conf), "-o", str(output)]) == 0
    assert feather.read_table(output).column_names == ["score", "id"]

    assert (
        main(
            [
                str(sample_csv),
                "--config",
                str(conf),
                "-o",
                str(output),
                "--overwrite",
                "--columns",
                "label",
                "id",
            ]
        )
        == 0
    )
    assert feather.read_table(output).column_names == ["label", "id"]


def test_missing_column_reports_error(sample_csv: Path, tmp_path: Path, capsys):
    output = tmp_path / "out.feather"
    assert (
        main(
            [
                str(sample_csv),
                "--to",
                "feather",
                "-o",
                str(output),
                "--columns",
                "missing",
            ]
        )
        != 0
    )
    assert "missing" in capsys.readouterr().err
    assert not output.exists()


def test_value_mappings_from_config(sample_csv: Path, tmp_path: Path):
    conf = tmp_path / "c.yaml"
    conf.write_text(
        'to: feather\nvalue_mappings:\n  label:\n    "cat": 0\n    "dog": 1\n    "bird": 2\n'
    )
    output = tmp_path / "mapped.feather"

    assert main([str(sample_csv), "--config", str(conf), "-o", str(output)]) == 0

    result = feather.read_table(output)
    assert result.column("label").to_pylist() == [0, 1, 2]
    assert str(result.column("label").type) == "int64"


def test_add_id_from_config_and_cli_override(sample_csv: Path, tmp_path: Path):
    conf = tmp_path / "c.yaml"
    conf.write_text("to: feather\ncolumns: [label, score]\nadd_id: true\n")
    output = tmp_path / "with-id.feather"

    assert main([str(sample_csv), "--config", str(conf), "-o", str(output)]) == 0
    assert feather.read_table(output).column_names == ["id", "label", "score"]

    assert (
        main(
            [
                str(sample_csv),
                "--config",
                str(conf),
                "-o",
                str(output),
                "--overwrite",
                "--no-add-id",
            ]
        )
        == 0
    )
    assert feather.read_table(output).column_names == ["label", "score"]


def test_source_to_h5(tmp_path: Path):
    output = tmp_path / "iris.h5"

    assert main(["--source", "sklearn:iris", "--to", "h5", "-o", str(output)]) == 0
    with h5py.File(output, "r") as h5:
        assert h5["target"].shape == (150,)


def test_malformed_source(tmp_path: Path, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--source", "iris", "--to", "csv", "-o", str(tmp_path / "iris.csv")])
    assert exc.value.code != 0
    assert "TYPE:NAME" in capsys.readouterr().err


def test_source_and_input_exclusive(sample_csv: Path, tmp_path: Path, capsys):
    output = str(tmp_path / "o.csv")
    with pytest.raises(SystemExit) as exc:
        main([str(sample_csv), "--source", "sklearn:iris", "--to", "csv", "-o", output])
    assert exc.value.code != 0
    assert "exclusive" in capsys.readouterr().err


def test_source_from_config(tmp_path: Path):
    conf = tmp_path / "c.yaml"
    conf.write_text("source: {type: sklearn, name: wine}\nto: csv\noutput: wine.csv\n")

    assert main(["--config", str(conf)]) == 0
    assert csv.read_csv(tmp_path / "wine.csv").num_rows == 178


def test_cli_input_overrides_config_source(sample_csv: Path, tmp_path: Path):
    conf = tmp_path / "c.yaml"
    conf.write_text("source: {type: sklearn, name: iris}\nto: csv\noutput: out.csv\n")

    assert main([str(sample_csv), "--config", str(conf)]) == 0
    assert csv.read_csv(tmp_path / "out.csv").num_rows == 3


def test_source_requires_output(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--source", "sklearn:iris", "--to", "csv"])
    assert exc.value.code != 0
    assert "output path is required" in capsys.readouterr().err


def test_help_lists_sources(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "sklearn" in capsys.readouterr().out
