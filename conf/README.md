# Configuration

YAML files passed to `ia-convert --config FILE` provide default values for the conversion options.
Explicit command-line arguments always take precedence over the file.

| Key           | Type   | Default                         | Description                                   |
|---------------|--------|---------------------------------|-----------------------------------------------|
| `input`       | string | —                               | Input CSV file (header row required)          |
| `output`      | string | input path + format extension   | Output file                                   |
| `to`          | string | —                               | Output format (`feather`)                     |
| `sep`         | string | `,`                             | CSV field separator (single character)        |
| `encoding`    | string | `utf-8`                         | CSV file encoding (e.g. `latin-1`)            |
| `columns`     | list of strings | all columns            | Column names to include, in the specified order |
| `trim_whitespace` | bool | `false` | Trim whitespace around fields and column names |
| `value_mappings` | mapping | — | Replace values in columns with mapped values |
| `add_id` | bool | `false` | Add a sequential integer `id` column (0-based) at the beginning |
| `compression` | string | `lz4`                           | Feather compression: `lz4`, `zstd`, `uncompressed` |
| `overwrite`   | bool   | `false`                         | Replace an existing output file               |

Unknown keys or values of the wrong type are rejected with an error naming the setting.
For example, `columns: [id, label]` includes only those two columns. Omit the key to include
all columns. Unknown or duplicate names are rejected.
Enable `trim_whitespace: true` for CSV files with padded values or spaces before quoted fields.

Use `value_mappings` to map every non-null value in a column. Values not listed in the mapping
cause an error; null cells remain null. Quote string keys such as `"no"` and `"yes"` in YAML.

```yaml
value_mappings:
  y:
    "no": 0
    "yes": 1
add_id: true
```

When enabled, `add_id` creates an `int64` column named `id` with values starting at 0. If an
`id` column is already selected for output, conversion fails instead of replacing it.

## Path resolution

Relative `input` and `output` paths are resolved against the directory containing the
configuration file, not the current working directory. With `conf/example.yaml`,
`../data/train.csv` points to `data/train.csv` at the repository root.

Do not commit secrets or machine-specific absolute paths in these files.
