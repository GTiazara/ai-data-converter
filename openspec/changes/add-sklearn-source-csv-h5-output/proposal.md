# Proposal

## Why

`ia-convert` ne sait lire que des fichiers CSV et n'écrit que du Feather. Pour préparer des jeux de données d'entraînement, on veut partir de données tabulaires de référence (les « toy datasets » de scikit-learn), puis plus tard d'autres sources, et les exporter dans les formats utilisés en aval (CSV, Feather, HDF5) en profitant de tout le pipeline existant (sélection de colonnes, mappings, `add_id`, rapport, écriture atomique).

## What Changes

- Introduire la notion de **source de données** : un registre de sources nommées, distinct de la lecture de fichier CSV, permettant d'ajouter de nouvelles origines de données sans modifier le pipeline.
- Ajouter une première source `sklearn` chargeant les toy datasets tabulaires embarqués de scikit-learn (`iris`, `wine`, `breast_cancer`, `diabetes`, `digits`, `linnerud`), sans accès réseau.
- Les tables issues d'une source passent par le même pipeline que le CSV : `columns`, `value_mappings`, `auto_mappings`, `add_id`, `mapping_report`, protection d'écrasement et écriture atomique.
- Ajouter les formats de sortie `csv` et `h5` (HDF5) au registre des writers, à côté de `feather`.
- Configuration : nouvelle clé `source` (`type` + options) dans le YAML, exclusive avec `input`. CLI : nouvelle option `--source TYPE:NOM` (ex. `sklearn:iris`), exclusive avec l'argument d'entrée.
- Fournir `conf/sklearn.yaml` et une cible `make run-sklearn` dédiée.
- scikit-learn devient une dépendance optionnelle (extra `sklearn`) ; `h5py` devient une dépendance d'exécution.

## Capabilities

### New Capabilities
- `dataset-sources`: chargement de tables depuis des sources de données nommées (non fichiers), à commencer par les toy datasets scikit-learn, et intégration au pipeline de conversion.

### Modified Capabilities
- `tabular-conversion`: les formats de sortie disponibles passent de `feather` seul à `csv`, `feather` et `h5`, avec leurs options et règles de représentation.
- `converter-cli`: la commande accepte une source de données (`--source` / clé `source`) à la place d'un fichier CSV d'entrée ; la sortie est alors obligatoire.

## Impact

- Code : nouveau sous-paquet `sources/`, nouveaux writers `writers/csv.py` et `writers/h5.py`, adaptations de `converter.py`, `config.py`, `cli.py`.
- Dépendances : `h5py` (runtime), `scikit-learn` (extra optionnel `sklearn` + groupe dev pour les tests).
- Configuration et outillage : `conf/sklearn.yaml`, `conf/README.md`, cible `run-sklearn` dans le `Makefile`, `README.md`.
- Prérequis : le changement `add-csv-to-feather-converter` (terminé) doit être archivé avant celui-ci, pour que les specs `tabular-conversion` et `converter-cli` existent dans `openspec/specs/`.
