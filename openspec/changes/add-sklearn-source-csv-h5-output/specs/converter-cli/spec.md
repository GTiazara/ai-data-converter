# Spec Delta

## MODIFIED Requirements

### Requirement: Commande de conversion
Le système SHALL fournir la commande `ia-convert` prenant en entrée soit un chemin CSV, soit une source de données (`--source`), ainsi qu'un format cible (`--to`), et produisant le fichier converti.

#### Scenario: Conversion par la CLI
- **WHEN** l'utilisateur exécute `ia-convert data.csv --to feather -o data.feather`
- **THEN** le fichier `data.feather` est créé et la commande se termine avec le code 0

#### Scenario: Conversion d'une source par la CLI
- **WHEN** l'utilisateur exécute `ia-convert --source sklearn:iris --to h5 -o iris.h5`
- **THEN** le fichier `iris.h5` est créé et la commande se termine avec le code 0

#### Scenario: Aide
- **WHEN** l'utilisateur exécute `ia-convert --help`
- **THEN** l'aide décrit les arguments disponibles, les formats de sortie et les types de source, avec le code 0

## ADDED Requirements

### Requirement: Option de source en ligne de commande
La commande SHALL accepter `--source TYPE:NOM` désignant une source de données et le nom du jeu de données à charger. Une valeur sans `:` ou avec un type ou un nom vide SHALL être refusée.

#### Scenario: Valeur de source mal formée
- **WHEN** l'utilisateur exécute `ia-convert --source iris --to csv -o iris.csv`
- **THEN** la commande indique le format attendu `TYPE:NOM` sur la sortie d'erreur et se termine avec un code non nul

#### Scenario: Source et fichier en ligne de commande
- **WHEN** l'utilisateur exécute `ia-convert data.csv --source sklearn:iris --to csv -o out.csv`
- **THEN** la commande indique que le fichier d'entrée et la source sont exclusifs et se termine avec un code non nul

### Requirement: Source dans la configuration YAML
Le fichier de configuration SHALL accepter une clé `source` contenant un mapping avec `type` (type de source) et `name` (jeu de données). Une clé `source` mal formée SHALL être refusée avec une erreur nommant le paramètre. Une source passée en ligne de commande SHALL remplacer la source et le fichier d'entrée de la configuration, et inversement un fichier d'entrée passé en ligne de commande SHALL remplacer la source de la configuration.

#### Scenario: Source issue de la configuration
- **WHEN** la configuration contient `source: {type: sklearn, name: wine}`, `to: csv` et `output: wine.csv`, et que la CLI ne précise ni entrée ni source
- **THEN** le jeu de données wine est converti en CSV dans `wine.csv`, résolu par rapport au dossier de la configuration

#### Scenario: Source mal formée dans la configuration
- **WHEN** la configuration contient `source: {type: sklearn}` sans `name`
- **THEN** la commande affiche une erreur nommant le paramètre `source` et se termine avec un code non nul

#### Scenario: Source et entrée dans la configuration
- **WHEN** la configuration contient à la fois `input` et `source`
- **THEN** la commande affiche une erreur indiquant qu'ils sont exclusifs et se termine avec un code non nul

#### Scenario: Entrée CLI prioritaire sur la source de configuration
- **WHEN** la configuration contient `source` et que l'utilisateur passe un fichier CSV en argument
- **THEN** le fichier CSV est converti et la source de la configuration est ignorée

### Requirement: Sortie obligatoire avec une source
Lorsqu'une source de données est utilisée, la commande SHALL exiger un chemin de sortie (`-o/--output` ou `output` dans la configuration), faute de fichier d'entrée à partir duquel en déduire un.

#### Scenario: Source sans sortie
- **WHEN** l'utilisateur exécute `ia-convert --source sklearn:iris --to csv` sans `-o` ni `output` en configuration
- **THEN** la commande indique qu'un chemin de sortie est requis et se termine avec un code non nul
