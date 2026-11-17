import sys

import pyarrow as pa
import pytest

from ia_data_format_converter.errors import SourceError, UnknownSourceError
from ia_data_format_converter.sources import available_sources, get_source

IRIS_FEATURES = [
    "sepal length (cm)",
    "sepal width (cm)",
    "petal length (cm)",
    "petal width (cm)",
]


def test_available_sources():
    assert available_sources() == ["sklearn"]


def test_unknown_source_lists_available():
    with pytest.raises(UnknownSourceError, match="openml.*sklearn"):
        get_source("openml")


def test_load_iris():
    table = get_source("sklearn").load("iris")

    assert table.num_rows == 150
    assert table.column_names == [*IRIS_FEATURES, "target"]
    assert pa.types.is_integer(table["target"].type)


def test_single_target_is_last_column():
    table = get_source("sklearn").load("diabetes")
    assert table.column_names[-1] == "target"
    assert "target" not in table.column_names[:-1]


def test_multiple_targets():
    table = get_source("sklearn").load("linnerud")
    assert table.column_names == [
        "Chins",
        "Situps",
        "Jumps",
        "target_Weight",
        "target_Waist",
        "target_Pulse",
    ]


def test_unknown_dataset_lists_accepted():
    with pytest.raises(SourceError, match="titanic.*iris, wine"):
        get_source("sklearn").load("titanic")


def test_missing_sklearn(monkeypatch):
    monkeypatch.setitem(sys.modules, "sklearn", None)
    with pytest.raises(SourceError, match="scikit-learn is required.*--extras sklearn"):
        get_source("sklearn").load("iris")
