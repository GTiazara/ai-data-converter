# Tasks

## 1. Dépendances

- [x] 1.1 Ajouter `h5py>=3.10` aux dépendances d'exécution, l'extra `[project.optional-dependencies] sklearn = ["scikit-learn>=1.3"]` et `scikit-learn` au groupe dev dans `pyproject.toml`, mettre à jour `poetry.lock`, et vérifier avec `poetry check` puis `poetry install` et `poetry run python -c "import h5py, sklearn"`

## 2. Writers CSV et HDF5

- [x] 2.1 Implémenter `writers/csv.py` (`CsvWriter`, extension `.csv`, `pyarrow.csv.write_csv`, toute option refusée par `InvalidOptionError`) et l'enregistrer ; vérifier dans `tests/test_writers.py` la relecture (colonnes, ordre, valeurs), une valeur nulle écrite vide et le refus de `compression`
- [x] 2.2 Implémenter `writers/h5.py` (`H5Writer`, extension `.h5`, un dataset par colonne + attribut racine `columns`, entiers/flottants/booléens/chaînes UTF-8, nulls numériques -> `float64` + `NaN`, dates -> ISO 8601, nulls booléens/chaînes et noms invalides refusés en nommant la colonne, compression `gzip`/`lzf`/`uncompressed`) et l'enregistrer ; vérifier dans `tests/test_writers.py` les types relus via `h5py`, l'ordre des colonnes, les nulls, les dates, le filtre `lzf`, le refus de `lz4` et d'un nom contenant `/`
- [x] 2.3 Mettre à jour le test de la liste des formats (`csv`, `feather`, `h5`) et le texte d'aide de `--compression` dans `cli.py` ; vérifier avec `poetry run pytest tests/test_writers.py tests/test_cli.py`

## 3. Sources de données

- [x] 3.1 Ajouter `UnknownSourceError` et `SourceError` (sous-classes de `ConversionError`) dans `errors.py`, créer `sources/__init__.py` (protocole `Source`, registre, `available_sources()`, `get_source()`) et vérifier dans `tests/test_sources.py` que la liste contient `sklearn` et que `openml` lève `UnknownSourceError` avec les types disponibles
- [x] 3.2 Implémenter `sources/sklearn.py` (import paresseux, liste blanche `iris`, `wine`, `breast_cancer`, `diabetes`, `digits`, `linnerud`, colonnes depuis `feature_names`, `target` ou `target_<nom>` pour les cibles multiples, `SourceError` explicite si scikit-learn est absent) ; vérifier dans `tests/test_sources.py` : iris 150 x 5 avec colonnes dans l'ordre et `target` entière, `diabetes` cible en dernière colonne, `linnerud` en `target_<nom>`, nom `titanic` refusé avec la liste, scikit-learn absent simulé via `monkeypatch` de `sys.modules`

## 4. Intégration dans le pipeline

- [x] 4.1 Adapter `converter.convert()` : `input_path` optionnel, paramètre `source`, exactement une origine, `output_path` obligatoire avec une source, chargement via `get_source(...).load(name)` sinon `read_csv`, reste du pipeline inchangé ; exporter `available_sources` dans `__init__.py`
- [x] 4.2 Vérifier dans `tests/test_converter.py` : iris vers `csv`, `feather` et `h5` ; sélection `columns` ; `value_mappings` sur `target` avec rapport de mappings ; `add_id` (0 à 149) ; source + entrée refusés et aucun des deux refusé ; source sans sortie refusée ; conversion CSV inchangée sans scikit-learn (simulé)

## 5. Configuration et CLI

- [x] 5.1 Ajouter la clé `source` dans `config.py` (mapping avec `type` et `name` chaînes non vides, aucune autre clé, `input` + `source` refusés) et vérifier dans `tests/test_config.py` les cas valide, `name` manquant, clé en trop et exclusivité avec `input`
- [x] 5.2 Ajouter `--source TYPE:NOM` dans `cli.py` (parsing, exclusivité avec l'argument positionnel, précédence CLI sur l'origine de la configuration, sortie obligatoire, types de source dans l'`epilog`) et vérifier dans `tests/test_cli.py` : `--source sklearn:iris --to h5 -o ...` code 0, `--source iris` refusé, fichier + source refusés, source de config utilisée, entrée CLI prioritaire sur la source de config, source sans sortie refusée, `--help` mentionne `sklearn`
- [x] 5.3 Créer `conf/sklearn.yaml` (source iris, `to: h5`, sortie `../data/output/iris.h5`, `add_id`, `overwrite`) et documenter `source` dans `conf/README.md` ; vérifier qu'un test charge `conf/sklearn.yaml` avec `load_config` sans erreur

## 6. Makefile et documentation

- [x] 6.1 Ajouter la cible `run-sklearn` (`poetry run ia-convert --config $(SKLEARN_CONF)`, `SKLEARN_CONF ?= conf/sklearn.yaml`), l'inclure dans `.PHONY` et `help`, et vérifier que `make run-sklearn` produit `data/output/iris.h5`
- [x] 6.2 Mettre à jour `README.md` : formats `csv`/`feather`/`h5` et leurs options, structure du fichier HDF5, sources de données et `--source`, extra `sklearn`, exemple `make run-sklearn` ; vérifier que les commandes documentées s'exécutent telles quelles

## 7. Vérification d'ensemble

- [ ] 7.1 Exécuter `make check` (lint + tests) et `make format-check` et vérifier qu'ils passent sans erreur

## Workflow follow-up

- Archiver `add-csv-to-feather-converter` avant d'archiver ce changement, pour que les deltas MODIFIED de `tabular-conversion` et `converter-cli` s'appliquent sur des specs existantes.
- Archiver ce changement après revue.
