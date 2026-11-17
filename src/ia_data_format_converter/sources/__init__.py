"""Registry of data sources producing Arrow tables from named datasets."""

from typing import Protocol

import pyarrow as pa

from ia_data_format_converter.errors import UnknownSourceError
from ia_data_format_converter.sources.sklearn import SklearnSource


class Source(Protocol):
    name: str

    def load(self, name: str) -> pa.Table:
        """Return the dataset ``name`` as a table or raise SourceError."""
        ...


_REGISTRY: dict[str, Source] = {source.name: source for source in (SklearnSource(),)}


def available_sources() -> list[str]:
    """Return the names of the registered data source types."""
    return sorted(_REGISTRY)


def get_source(name: str) -> Source:
    """Return the data source registered under ``name``."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise UnknownSourceError(
            f"Unknown source type {name!r}. Available sources: {', '.join(available_sources())}"
        ) from None
