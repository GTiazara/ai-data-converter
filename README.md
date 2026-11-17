# IA_DATA_FORMAT_CONVERTER

Command-line tool and Python library that converts tabular data (CSV files or data sources such
as the scikit-learn toy datasets) used for machine learning or other AI tasks into formats that
load faster and keep column types.

Supported output formats:

| Format    | Extension  | Status    |
|-----------|------------|-----------|
| `csv`     | `.csv`     | available |
| `feather` | `.feather` | available |
| `h5`      | `.h5`      | available |
| Apache Parquet, Zarr, SQLite, ... | | planned |

Supported data sources (instead of a CSV file):

| Source    | Datasets                                                        |
|-----------|-----------------------------------------------------------------|
| `sklearn` | `iris`, `wine`, `breast_cancer`, `diabetes`, `digits`, `linnerud` |

## Requirements

- Python >= 3.11
- [Poetry](https://python-poetry.org/) >= 2.0

## Installation

```bash
make install        # or: poetry install (includes scikit-learn as a dev dependency)
```

The `sklearn` source needs scikit-learn, an optional extra for end users:
`poetry install --extras sklearn` or `pip install "ia-data-format-converter[sklearn]"`.

## Usage

```bash
poetry run ia-convert INPUT.csv --to FORMAT [-o OUTPUT] [options]
poetry run ia-convert --source TYPE:NAME --to FORMAT -o OUTPUT [options]
```

| Option              | Default                              | Description                                       |
|---------------------|--------------------------------------|---------------------------------------------------|
| `INPUT`             | —                                    | Input CSV file with a header row                  |
| `--source TYPE:NAME`| —                                    | Load a dataset from a source (e.g. `sklearn:iris`); exclusive with `INPUT`, requires `-o` |
| `--to FORMAT`       | —                                    | Output format (`csv`, `feather`, `h5`)            |
| `-o, --output PATH` | input path with the format extension | Output file                                       |
| `--sep CHAR`        | `,`                                  | CSV field separator                               |
| `--encoding NAME`   | `utf-8`                              | CSV file encoding (e.g. `latin-1`)                |
| `--columns NAME ...`| all columns                          | Include named columns in the specified order      |
| `--add-id`          | off                                  | Add a sequential 0-based integer `id` column      |
| `--no-add-id`       | —                                    | Disable ID generation from YAML config           |
| `--auto-map S`      | off                                  | Encode all unmapped string columns: `ordinal`, `onehot` |
| `--mapping-report P`| —                                    | Write mapping summary (`.md`, `.yaml`, `.yml`, `.json`) |
| `--compression C`   | `lz4` (feather), `gzip` (h5)         | Feather: `lz4`, `zstd`, `uncompressed`; h5: `gzip`, `lzf`, `uncompressed`; not for csv |
| `--overwrite`       | off                                  | Replace an existing output file                   |
| `--config FILE`     | —                                    | YAML file providing default values for the options|

Examples:

```bash
poetry run ia-convert data/train.csv --to feather                  # writes data/train.feather
poetry run ia-convert data/train.csv --to feather -o out/train.feather --compression zstd
poetry run ia-convert data/eu.csv --to feather --sep ";" --encoding latin-1
poetry run ia-convert data/train.csv --to feather --columns id label
poetry run ia-convert data/train.csv --to feather --add-id
poetry run ia-convert data/train.csv --to feather --auto-map onehot --mapping-report data/mapping.md
poetry run ia-convert --config conf/example.yaml
poetry run ia-convert --config conf/conf.yaml
poetry run ia-convert --source sklearn:iris --to h5 -o data/output/iris.h5 --overwrite
poetry run ia-convert --source sklearn:wine --to csv -o data/output/wine.csv --overwrite
make run ARGS="--config conf/example.yaml"
make run-sklearn                                   # uses conf/sklearn.yaml
make run-sklearn SKLEARN_CONF=conf/my-dataset.yaml
```

### Inputs and outputs

- **Input**: a CSV file with a header row. Column types (integer, float, boolean, string,
  date/time) are inferred; empty cells become null values. The whole file is loaded in memory.
- **Source**: a named dataset. `sklearn` loads a scikit-learn toy dataset (no network access):
  feature columns keep their scikit-learn names (e.g. `sepal length (cm)`), followed by a
  `target` column, or one `target_<name>` column per target for `linnerud`. All options
  (`--columns`, mappings, `--add-id`, report) apply; CSV options (`--sep`, `--encoding`,
  `--trim-whitespace`) are ignored.
- **Output**:
  - `csv`: UTF-8, header row, `,` separator, nulls written as empty cells.
  - `feather`: Arrow IPC v2, readable with `pyarrow.feather.read_table`,
    `pandas.read_feather` or `polars.read_ipc`.
  - `h5`: HDF5 file with one 1-D dataset per column at the root, named after the column, and
    a root attribute `columns` giving the column order. Strings are UTF-8, dates/times are ISO
    8601 strings, numeric columns with nulls become `float64` with `NaN`; nulls in boolean or
    string columns and column names containing `/` are rejected. Read it with `h5py`
    (it is not a `pandas.read_hdf` file):

    ```python
    import h5py
    with h5py.File("data/output/iris.h5") as h5:
        columns = {name: h5[name][()] for name in h5.attrs["columns"]}
    ```
- An existing output file is never replaced unless `--overwrite` is given. Output is written
  atomically: a failed conversion leaves no partial file.
- On error, a message is printed on stderr and the command exits with a non-zero status.

### Configuration

See [conf/README.md](conf/README.md), [conf/example.yaml](conf/example.yaml),
[conf/sklearn.yaml](conf/sklearn.yaml) and
[conf/conf.yaml](conf/conf.yaml). Run your own configuration with
`poetry run ia-convert --config conf/conf.yaml`; ensure its input and output paths match your
environment. Command-line arguments override values from the configuration file; relative paths
in the file are resolved against the file's directory.

To export a data source, replace `input` with `source` (the two are exclusive) and set `output`:

```yaml
source:
  type: sklearn
  name: iris
to: h5
output: ../data/output/iris.h5
```

To select columns in your YAML file, add:

```yaml
columns: [id, label]
```

The output contains only those columns, in the specified order. Omit `columns` to include all
columns; unknown names cause an error. `--columns` overrides the YAML selection.

To map string categories to numeric values, configure a mapping for that column:

```yaml
value_mappings:
  y:
    "no": 0
    "yes": 1
```

All non-null values in a mapped column must have an entry; otherwise conversion fails and no
partial output is written. Null values remain null. Quote string keys in YAML.

To encode categorical columns automatically, list one or more strategies (like scikit-learn
`ColumnTransformer` entries) and optionally write a report of every applied mapping:

```yaml
auto_mappings:
  - name: categorical
    strategy: onehot          # one int8 column per category: job_admin., job_blue-collar, ...
    columns: [job, marital]
  - strategy: ordinal         # no 'columns': every remaining string column -> int64 codes
mapping_report: ../data/output/mapping.yaml   # or .md / .json
```

Categories are sorted before encoding. Columns from `value_mappings` are reported as `manual`
and skipped by automatic specs. See [conf/README.md](conf/README.md) for details.

Set `add_id: true` in YAML or pass `--add-id` to prepend a sequential integer `id` column,
starting at 0. Conversion fails if an `id` column is already included in the output. Use
`--no-add-id` to disable ID generation from a config file.

### Python API

```python
from ia_data_format_converter import available_formats, convert

convert("data/train.csv", "data/train.feather", "feather", compression="zstd")
convert("data/train.csv", "data/selected.feather", "feather", columns=["id", "label"])
convert("data/train.csv", "data/with_id.feather", "feather", add_id=True)
convert(
  "data/train.csv",
  "data/mapped.feather",
  "feather",
  value_mappings={"y": {"no": 0, "yes": 1}},
)
convert(
  "data/train.csv",
  "data/encoded.feather",
  "feather",
  auto_mappings=[
    {"name": "categorical", "strategy": "onehot", "columns": ["job"]},
    {"strategy": "ordinal"},
  ],
  mapping_report="data/mapping.json",
)
convert(
  None,
  "data/iris.h5",
  "h5",
  source={"type": "sklearn", "name": "iris"},
  value_mappings={"target": {0: "setosa", 1: "versicolor", 2: "virginica"}},
)
```

## Adding a data source

Each source lives in `src/ia_data_format_converter/sources/`, exposing `name` and
`load(name)` returning a `pyarrow.Table` (raise `SourceError` for unknown datasets or missing
dependencies). Register an instance in `_REGISTRY` in `sources/__init__.py` and add tests in
`tests/test_sources.py`; `--source` and the `source` config key pick it up automatically.

## Adding an output format

Each output format is a *writer* in `src/ia_data_format_converter/writers/`, exposing `name`,
`extension`, `validate_options(**options)` and `write(table, path, **options)` where `table` is
a `pyarrow.Table`. To add a format (Parquet, Zarr, SQLite, ...):

1. Create `writers/<format>.py` implementing the writer.
2. Register an instance in `_REGISTRY` in `writers/__init__.py`.
3. Add tests in `tests/test_writers.py`.

The CLI picks up the new format automatically.

## Development

```bash
make test           # run tests
make lint           # ruff check
make format-check   # ruff format --check
make check          # lint + tests
```
