"""Loading and validation of YAML configuration files."""

from pathlib import Path
from typing import Any

import yaml

# Expected type for each allowed configuration key.
_SCHEMA: dict[str, type] = {
    "input": str,
    "output": str,
    "to": str,
    "sep": str,
    "encoding": str,
    "compression": str,
    "overwrite": bool,
    "columns": list,
    "trim_whitespace": bool,
    "value_mappings": dict,
    "add_id": bool,
    "auto_mappings": list,
    "mapping_report": str,
    "source": dict,
}
_PATH_KEYS = ("input", "output", "mapping_report")


class ConfigError(Exception):
    """The configuration file is missing or invalid."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Load and validate a YAML configuration file.

    Relative ``input`` and ``output`` paths are resolved against the directory of the file.
    """
    path = Path(path)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"Cannot read configuration file {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in configuration file {path}: {exc}") from exc

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(
            f"Configuration file {path} must contain a mapping of settings"
        )

    config: dict[str, Any] = {}
    for key, value in data.items():
        expected = _SCHEMA.get(key)
        if expected is None:
            raise ConfigError(
                f"Unknown configuration setting {key!r}. Allowed: {', '.join(_SCHEMA)}"
            )
        if not isinstance(value, expected):
            raise ConfigError(
                f"Invalid value for setting {key!r}: expected {expected.__name__}, "
                f"got {type(value).__name__}"
            )
        if key == "columns" and (
            not value
            or any(not isinstance(column, str) or not column for column in value)
        ):
            raise ConfigError(
                "Invalid value for setting 'columns': expected non-empty names"
            )
        if key == "value_mappings":
            if not value:
                raise ConfigError(
                    "Invalid value for setting 'value_mappings': must not be empty"
                )
            for column, mapping in value.items():
                if (
                    not isinstance(column, str)
                    or not column
                    or not isinstance(mapping, dict)
                    or not mapping
                ):
                    raise ConfigError(
                        "Invalid value for setting 'value_mappings': expected column names "
                        "mapped to non-empty mappings"
                    )
                for source, target in mapping.items():
                    if isinstance(source, dict | list) or isinstance(
                        target, dict | list
                    ):
                        raise ConfigError(
                            f"Invalid mapping for column {column!r}: values must be scalars"
                        )
        if key == "auto_mappings" and (
            not value or any(not isinstance(spec, dict) for spec in value)
        ):
            raise ConfigError(
                "Invalid value for setting 'auto_mappings': expected a non-empty list of "
                "mappings with 'strategy' and optional 'name' and 'columns'"
            )
        if key == "source" and (
            set(value) != {"type", "name"}
            or not all(isinstance(item, str) and item for item in value.values())
        ):
            raise ConfigError(
                "Invalid value for setting 'source': expected a mapping with non-empty "
                "'type' and 'name' strings only"
            )
        if key in _PATH_KEYS:
            value = str((path.parent / value).resolve())
        config[key] = value
    if "input" in config and "source" in config:
        raise ConfigError(
            "Settings 'input' and 'source' are exclusive: provide only one of them"
        )
    return config
