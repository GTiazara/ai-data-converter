# Spec Delta

## MODIFIED Requirements

### Requirement: Formats de sortie enregistrés
Le système SHALL exposer la liste des formats de sortie disponibles, identifiés par un nom, et SHALL refuser un format inconnu. Dans cette version, les formats `csv`, `feather` et `h5` sont disponibles.

#### Scenario: Liste des formats
- **WHEN** la liste des formats disponibles est demandée
- **THEN** elle contient `csv`, `feather` et `h5`

#### Scenario: Format inconnu
- **WHEN** une conversion est demandée vers `parquet` alors qu'il n'est pas encore disponible
- **THEN** la conversion échoue avec une erreur indiquant le format inconnu et les formats disponibles, sans créer de fichier

## ADDED Requirements

### Requirement: Sortie CSV
Le format `csv` SHALL produire un fichier texte UTF-8 avec une ligne d'en-tête, le séparateur `,`, les mêmes colonnes dans le même ordre et le même nombre de lignes que la table convertie. Les valeurs nulles SHALL être écrites comme des cellules vides. L'extension par défaut SHALL être `.csv`.

#### Scenario: Export CSV relu
- **WHEN** iris est converti vers `csv` puis relu comme CSV
- **THEN** le fichier relu a les mêmes colonnes, dans le même ordre, et les mêmes 150 lignes de valeurs

#### Scenario: Valeur nulle en CSV
- **WHEN** une table contenant une valeur nulle est convertie vers `csv`
- **THEN** la cellule correspondante est vide dans le fichier produit

#### Scenario: Compression refusée pour CSV
- **WHEN** une conversion vers `csv` est demandée avec une compression
- **THEN** la conversion échoue avec une erreur indiquant que l'option n'est pas supportée par `csv`, sans créer de fichier

### Requirement: Sortie HDF5
Le format `h5` SHALL produire un fichier HDF5 contenant, à la racine, un dataset unidimensionnel par colonne, nommé comme la colonne, ainsi qu'un attribut racine `columns` donnant l'ordre des colonnes. L'extension par défaut SHALL être `.h5`.

#### Scenario: Export HDF5 relu
- **WHEN** iris est converti vers `h5` puis relu avec une bibliothèque HDF5 standard
- **THEN** le fichier contient un dataset de 150 valeurs par colonne et l'attribut `columns` liste les 5 colonnes dans l'ordre d'origine

#### Scenario: Types conservés
- **WHEN** une table avec des colonnes entière, flottante, booléenne et chaîne est convertie vers `h5`
- **THEN** les datasets sont respectivement entier, flottant, booléen et chaîne UTF-8, avec les mêmes valeurs

#### Scenario: Nom de colonne invalide pour HDF5
- **WHEN** une colonne dont le nom contient `/` est convertie vers `h5`
- **THEN** la conversion échoue avec une erreur nommant la colonne, sans créer de fichier

### Requirement: Valeurs nulles et dates en HDF5
Pour le format `h5`, les colonnes numériques contenant des valeurs nulles SHALL être écrites en flottants avec `NaN` pour les nulls. Les colonnes de dates/heures SHALL être écrites en chaînes ISO 8601. Une valeur nulle dans une colonne booléenne ou chaîne SHALL faire échouer la conversion avec une erreur nommant la colonne.

#### Scenario: Entiers avec nulls
- **WHEN** une colonne entière contenant une valeur nulle est convertie vers `h5`
- **THEN** le dataset correspondant est flottant et contient `NaN` à la place de la valeur nulle

#### Scenario: Chaîne nulle refusée
- **WHEN** une colonne de chaînes contenant une valeur nulle est convertie vers `h5`
- **THEN** la conversion échoue avec une erreur nommant la colonne, sans créer de fichier

### Requirement: Compression HDF5
Le format `h5` SHALL permettre de choisir la compression des datasets parmi `gzip` (par défaut), `lzf` et `uncompressed`, et SHALL refuser toute autre valeur.

#### Scenario: Compression HDF5 choisie
- **WHEN** une conversion vers `h5` est demandée avec la compression `lzf`
- **THEN** les datasets du fichier produit utilisent le filtre `lzf` et restent lisibles

#### Scenario: Compression HDF5 invalide
- **WHEN** une conversion vers `h5` est demandée avec la compression `lz4`
- **THEN** la conversion échoue avec une erreur nommant la valeur invalide et les valeurs acceptées, sans créer de fichier
