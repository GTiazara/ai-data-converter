# Design

## Context

Le pipeline actuel est linéaire : `convert()` appelle directement `read_csv()`, puis applique `columns`, `value_mappings`, `auto_mappings` et `add_id` sur une `pa.Table`, et délègue l'écriture à un registre de writers (`writers/__init__.py`, seul `FeatherWriter` est enregistré). La CLI fusionne valeurs par défaut, configuration YAML (`config.py`, schéma plat clé -> type) et arguments explicites. Voir proposal.md pour la motivation et les specs pour le comportement attendu.

```
  input (CSV) --> read_csv --+
                             +--> pa.Table --> columns/mappings/add_id --> writer (csv|feather|h5)
  source      --> Source  ---+
```

## Goals / Non-Goals

**Goals:**
- Un point d'extension `Source` symétrique au registre de writers, pour ajouter de futures sources sans toucher au pipeline.
- Réutiliser la totalité du traitement existant de `convert()` après le chargement de la table.
- Garder les tests hors-ligne et rapides.

**Non-Goals:**
- Datasets scikit-learn téléchargés (`fetch_*`), OpenML, Hugging Face, lecture de fichiers Feather/HDF5 en entrée.
- Plusieurs formats de sortie en une seule exécution (un format par exécution, comme aujourd'hui).
- Conversion automatique de la cible en noms de classes (`target_names`) : faisable par `value_mappings`.
- Options de sortie CSV (séparateur, guillemets, compression).
- Compatibilité de lecture via `pandas.read_hdf`.

## Decisions

### Registre de sources dans un sous-paquet `sources/`
`sources/__init__.py` définit un `Protocol` `Source` (`name: str`, `load(name: str) -> pa.Table`), un registre, `available_sources()` et `get_source(type)` levant `UnknownSourceError` (nouvelle sous-classe de `ConversionError`). `sources/sklearn.py` implémente `SklearnSource`.
- Le CSV reste lu par `read_csv` via `input` : il a des options propres (`sep`, `encoding`, `trim_whitespace`) et le passer dans le registre obligerait à généraliser les options de source maintenant, sans besoin concret.
- Alternative écartée : une commande séparée `ia-dataset` (dupliquerait le pipeline, voir l'exploration).

### Intégration dans `convert()`
`input_path` devient optionnel et un paramètre mot-clé `source: Mapping[str, str] | None` (`{"type": ..., "name": ...}`) est ajouté. `convert()` vérifie qu'il y a exactement une origine, exige `output_path` quand `source` est fourni, puis obtient la table via `get_source(type).load(name)` ou `read_csv(...)`. Tout le reste du corps est inchangé. La validation (sortie existante, rapport) reste faite avant le chargement pour échouer tôt.

### Chargement sklearn sans pandas
Import paresseux de `sklearn.datasets` dans `load()` ; `ImportError` -> `SourceError` (sous-classe de `ConversionError`) avec le message « scikit-learn est requis : `poetry install --extras sklearn` (ou `pip install scikit-learn`) ». Liste blanche `{iris, wine, breast_cancer, diabetes, digits, linnerud}` -> `load_<name>()`, ce qui empêche d'appeler une fonction arbitraire de `sklearn.datasets`. La table est construite depuis `bunch.data` (colonnes nommées par `feature_names`) et `bunch.target` : 1D -> `target`, 2D -> `target_<target_names[i]>`. `as_frame=True` est évité pour ne pas ajouter pandas.
- Noms de colonnes conservés tels quels (ex. `sepal length (cm)`) : c'est ce que connaissent les utilisateurs de sklearn.

### Writer CSV
`writers/csv.py`, `pyarrow.csv.write_csv` (en-tête, `,`, nulls vides, UTF-8). `validate_options` refuse toute option, comme Feather refuse les options inconnues.

### Writer HDF5 avec h5py
`writers/h5.py`, un dataset 1D par colonne à la racine + attribut `columns`. Conversion par type Arrow : entiers/flottants -> numpy (cast en `float64` avec `NaN` si nulls), booléens -> `bool`, chaînes -> `h5py.string_dtype("utf-8")`, timestamps/dates -> chaînes ISO 8601 ; nulls dans booléens/chaînes -> `InvalidOptionError` nommant la colonne ; nom contenant `/` (ou `.`/vide) -> erreur. Compression `gzip` (défaut), `lzf`, `uncompressed`.
- Alternative écartée : `pandas.to_hdf` (PyTables) : dépendances plus lourdes (pandas + tables) et format interne à pandas, moins lisible depuis d'autres outils.
- Le dictionnaire produit par l'encodage `auto_mappings` est déjà sous forme de valeurs simples ; aucun cas spécial n'est nécessaire.

### Options de writer par format
La CLI ne passe `compression` que si elle est définie ; chaque writer applique son propre défaut (`lz4` pour Feather, `gzip` pour HDF5) et refuse ce qu'il ne supporte pas. Le texte d'aide de `--compression` est mis à jour pour lister les valeurs par format.

### Configuration et CLI
- `config.py` : `source: dict` ajouté à `_SCHEMA`, validation dédiée (`type` et `name` chaînes non vides, aucune autre clé), et refus de `input` + `source` dans le même fichier.
- `cli.py` : `--source TYPE:NOM` parsé en `{"type", "name"}` ; mutuellement exclusif avec l'argument positionnel (erreur si les deux). Précédence : une origine passée en CLI (fichier ou source) efface l'autre origine venant de la configuration. Messages d'erreur et `epilog` listent les types de source.
- `conf/sklearn.yaml` (`source: {type: sklearn, name: iris}`, `to: h5`, `output: ../data/output/iris.h5`, `add_id: true`, `overwrite: true`) et cible `run-sklearn` : `poetry run ia-convert --config $(SKLEARN_CONF)` avec `SKLEARN_CONF ?= conf/sklearn.yaml`, pour changer de config sans éditer le Makefile.

### Dépendances
`h5py>=3.10` en dépendance d'exécution. `scikit-learn>=1.3` en extra `[project.optional-dependencies] sklearn` et dans le groupe dev pour que `make install` + `make test` couvrent la source. Les tests de « scikit-learn absent » simulent l'absence via `monkeypatch` sur `sys.modules`.

## Risks / Trade-offs

- [h5py tire numpy et des binaires HDF5] -> roues précompilées disponibles pour Linux/macOS/Windows ; acceptable pour un outil ML.
- [Le format HDF5 maison n'est pas lisible par `pandas.read_hdf`] -> documenter la structure dans le README ; lecture triviale via h5py.
- [Les nulls d'entiers deviennent des flottants en HDF5] -> comportement spécifié et documenté ; les toy datasets n'ont pas de nulls.
- [Les options CSV sont silencieusement ignorées avec une source] -> documenté ; les valeurs par défaut rendent la détection d'un réglage explicite peu fiable.
- [Le changement `add-csv-to-feather-converter` n'est pas archivé] -> les deltas MODIFIED de ce changement ciblent des specs qui n'existent pas encore dans `openspec/specs/` ; archiver ce changement en premier.

## Migration Plan

Aucune migration : `input` et les conversions CSV -> Feather existantes restent inchangées. Les nouveaux formats et la clé `source` sont additifs.
