"""scikit-learn toy datasets (bundled with the library, no network access)."""

import pyarrow as pa

from ia_data_format_converter.errors import SourceError

DATASETS = ("iris", "wine", "breast_cancer", "diabetes", "digits", "linnerud")


class SklearnSource:
    name = "sklearn"

    def load(self, name: str) -> pa.Table:
        if name not in DATASETS:
            raise SourceError(
                f"Unknown sklearn dataset {name!r}. Accepted datasets: {', '.join(DATASETS)}"
            )
        try:
            from sklearn import datasets
        except ImportError as exc:
            raise SourceError(
                "scikit-learn is required for the sklearn source: install it with "
                "'poetry install --extras sklearn' (or 'pip install scikit-learn')"
            ) from exc

        bunch = getattr(datasets, f"load_{name}")()
        columns = {
            feature: pa.array(bunch.data[:, index])
            for index, feature in enumerate(bunch.feature_names)
        }
        if bunch.target.ndim == 1:
            columns["target"] = pa.array(bunch.target)
        else:
            for index, target in enumerate(bunch.target_names):
                columns[f"target_{target}"] = pa.array(bunch.target[:, index])
        return pa.table(columns)
