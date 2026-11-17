# Spec Delta

## Purpose

Charger des données tabulaires depuis des sources de données nommées, autres qu'un fichier CSV, et les faire passer par le même pipeline de conversion que les fichiers. Les toy datasets de scikit-learn sont la première source prise en charge.

## ADDED Requirements

### Requirement: Sources de données enregistrées
Le système SHALL exposer la liste des types de source de données disponibles, chacun identifié par un nom, et SHALL refuser un type de source inconnu. Dans cette version, seul `sklearn` est disponible.

#### Scenario: Liste des sources
- **WHEN** la liste des types de source disponibles est demandée
- **THEN** elle contient `sklearn`

#### Scenario: Type de source inconnu
- **WHEN** une conversion est demandée depuis la source `openml`
- **THEN** la conversion échoue avec une erreur indiquant le type inconnu et les types disponibles, sans créer de fichier

### Requirement: Chargement des toy datasets scikit-learn
La source `sklearn` SHALL charger, sans accès réseau, un toy dataset tabulaire désigné par son nom parmi `iris`, `wine`, `breast_cancer`, `diabetes`, `digits` et `linnerud`. La table produite SHALL contenir une colonne par variable, nommée comme dans le jeu de données et dans le même ordre, puis la ou les colonnes cibles.

#### Scenario: Chargement d'iris
- **WHEN** la source `sklearn` est utilisée avec le nom `iris`
- **THEN** la table contient 150 lignes, les 4 colonnes de variables d'iris dans leur ordre d'origine, puis une colonne `target` entière

#### Scenario: Cible unique
- **WHEN** un jeu de données à une seule cible est chargé (par exemple `diabetes`)
- **THEN** la cible est placée dans une colonne nommée `target`, en dernière position

#### Scenario: Cibles multiples
- **WHEN** le jeu de données `linnerud`, qui a plusieurs cibles, est chargé
- **THEN** chaque cible est placée dans une colonne nommée `target_<nom de la cible>`, après les colonnes de variables

#### Scenario: Nom de jeu de données inconnu
- **WHEN** la source `sklearn` est utilisée avec le nom `titanic`
- **THEN** la conversion échoue avec une erreur nommant `titanic` et listant les jeux de données acceptés, sans créer de fichier

### Requirement: Dépendance optionnelle scikit-learn
La source `sklearn` SHALL fonctionner seulement lorsque scikit-learn est installé. S'il est absent, l'utilisation de cette source SHALL échouer avec une erreur expliquant comment l'installer, et les conversions depuis un fichier CSV SHALL continuer de fonctionner.

#### Scenario: scikit-learn absent
- **WHEN** scikit-learn n'est pas installé et qu'une conversion depuis la source `sklearn` est demandée
- **THEN** la conversion échoue avec une erreur indiquant que scikit-learn est requis et comment l'installer, sans créer de fichier

#### Scenario: CSV sans scikit-learn
- **WHEN** scikit-learn n'est pas installé et qu'un fichier CSV est converti
- **THEN** la conversion réussit

### Requirement: Pipeline commun aux sources
Une table chargée depuis une source SHALL subir les mêmes traitements qu'une table lue depuis un CSV : sélection de colonnes, mappings de valeurs, encodage automatique, ajout d'identifiant, rapport de mappings, protection de la sortie existante et écriture sans fichier partiel. Les options propres à la lecture CSV (séparateur, encodage, suppression des espaces) SHALL être sans effet sur une source.

#### Scenario: Sélection de colonnes sur une source
- **WHEN** iris est converti avec la sélection de colonnes `petal length (cm)` et `target`
- **THEN** la sortie contient uniquement ces deux colonnes, dans cet ordre

#### Scenario: Mapping de la cible
- **WHEN** iris est converti avec un mapping de valeurs `target` : `0 -> setosa`, `1 -> versicolor`, `2 -> virginica`
- **THEN** la colonne `target` de la sortie contient les noms d'espèces et le rapport de mappings décrit ce mapping

#### Scenario: Identifiant ajouté
- **WHEN** iris est converti avec l'ajout d'identifiant activé
- **THEN** la sortie commence par une colonne `id` allant de 0 à 149

### Requirement: Exclusivité entre source et fichier d'entrée
Une conversion SHALL avoir exactement une origine : soit un fichier CSV d'entrée, soit une source de données. Fournir les deux, ou aucun, SHALL être refusé.

#### Scenario: Source et fichier fournis
- **WHEN** une conversion est demandée avec à la fois un fichier d'entrée et une source
- **THEN** la conversion échoue avec une erreur indiquant que les deux sont exclusifs, sans créer de fichier
