from pathlib import Path

import pytest

from ia_data_format_converter.config import ConfigError, load_config

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_valid_config_resolves_paths(tmp_path: Path):
    conf_dir = tmp_path / "conf"
    conf_dir.mkdir()
    path = conf_dir / "c.yaml"
    path.write_text(
        "input: data.csv\noutput: ../out/data.feather\nto: feather\noverwrite: true\n"
    )

    config = load_config(path)

    assert config["input"] == str((conf_dir / "data.csv").resolve())
    assert config["output"] == str((tmp_path / "out" / "data.feather").resolve())
    assert config["to"] == "feather"
    assert config["overwrite"] is True


def test_empty_config(tmp_path: Path):
    path = tmp_path / "c.yaml"
    path.write_text("")
    assert load_config(path) == {}


def test_unknown_key(tmp_path: Path):
    path = tmp_path / "c.yaml"
    path.write_text("delimiter: ';'\n")
    with pytest.raises(ConfigError, match="delimiter"):
        load_config(path)


def test_invalid_type(tmp_path: Path):
    path = tmp_path / "c.yaml"
    path.write_text("overwrite: 'yes please'\n")
    with pytest.raises(ConfigError, match="overwrite"):
        load_config(path)


def test_not_a_mapping(tmp_path: Path):
    path = tmp_path / "c.yaml"
    path.write_text("- a\n- b\n")
    with pytest.raises(ConfigError):
        load_config(path)


def test_missing_file(tmp_path: Path):
    with pytest.raises(ConfigError, match="nope.yaml"):
        load_config(tmp_path / "nope.yaml")


def test_example_config_is_valid():
    config = load_config(REPO_ROOT / "conf" / "example.yaml")
    assert config["to"] == "feather"
    assert config["input"] == str(REPO_ROOT / "data" / "train.csv")


@pytest.mark.parametrize("value", ["id", "[]", "[id, 123]", "['']"])
def test_invalid_columns_config(tmp_path: Path, value: str):
    path = tmp_path / "c.yaml"
    path.write_text(f"columns: {value}\n")
    with pytest.raises(ConfigError, match="columns"):
        load_config(path)


def test_value_mappings_config(tmp_path: Path):
    path = tmp_path / "c.yaml"
    path.write_text('value_mappings:\n  y:\n    "no": 0\n    "yes": 1\n')

    assert load_config(path)["value_mappings"] == {"y": {"no": 0, "yes": 1}}


def test_invalid_value_mappings_config(tmp_path: Path):
    path = tmp_path / "c.yaml"
    path.write_text("value_mappings:\n  y: []\n")
    with pytest.raises(ConfigError, match="value_mappings"):
        load_config(path)


def test_add_id_config(tmp_path: Path):
    path = tmp_path / "c.yaml"
    path.write_text("add_id: true\n")

    assert load_config(path)["add_id"] is True


def test_invalid_add_id_config(tmp_path: Path):
    path = tmp_path / "c.yaml"
    path.write_text("add_id: yes please\n")

    with pytest.raises(ConfigError, match="add_id"):
        load_config(path)


def test_sklearn_config_is_valid():
    config = load_config(REPO_ROOT / "conf" / "sklearn.yaml")
    assert config["source"] == {"type": "sklearn", "name": "iris"}
    assert config["output"] == str(REPO_ROOT / "data" / "output" / "iris.h5")


def test_source_config(tmp_path: Path):
    path = tmp_path / "c.yaml"
    path.write_text("source: {type: sklearn, name: wine}\n")

    assert load_config(path)["source"] == {"type": "sklearn", "name": "wine"}


@pytest.mark.parametrize(
    "value",
    [
        "{type: sklearn}",
        "{type: sklearn, name: iris, extra: 1}",
        "{type: '', name: iris}",
        "iris",
    ],
)
def test_invalid_source_config(tmp_path: Path, value: str):
    path = tmp_path / "c.yaml"
    path.write_text(f"source: {value}\n")
    with pytest.raises(ConfigError, match="source"):
        load_config(path)


def test_source_and_input_config_exclusive(tmp_path: Path):
    path = tmp_path / "c.yaml"
    path.write_text("input: data.csv\nsource: {type: sklearn, name: iris}\n")
    with pytest.raises(ConfigError, match="exclusive"):
        load_config(path)
