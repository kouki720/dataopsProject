
# DataOps Energy

## 1. Présentation du projet

DataOps Energy est une plateforme DataOps dédiée à la collecte, au traitement, à la transformation et à l'analyse des données énergétiques françaises.

Le projet vise à construire un pipeline de données automatisé permettant de combiner les données de production et de consommation électrique avec les données météorologiques.

## 2. Objectifs métier

Le projet cherche à répondre aux questions suivantes :

1. Quelle est la part des énergies renouvelables dans la production électrique française ?
2. Quelle est la relation entre la température et la consommation électrique ?
3. Quelles sources de production contribuent le plus aux émissions de CO2 ?

## 3. Sources de données

### Source 1 : éCO2mix

- Fournisseur : ODRE / Open Data Réseaux Énergies.
- Dataset : `eco2mix-national-cons-def`
- Type : données historiques et API REST.
- Contenu :
  - Consommation électrique.
  - Production par filière énergétique.
  - Émissions de CO2.
  - Échanges électriques avec les pays voisins.

### Source 2 : Open-Meteo

- Fournisseur : Open-Meteo.
- API : Historical Weather API.
- Type : API REST.
- Contenu :
  - Température.
  - Humidité.
  - Précipitations.
  - Vitesse du vent.

## 4. Architecture technique

| Technologie | Responsabilité |
|---|---|
| Python | Développement des pipelines |
| dlt | Ingestion des données |
| DuckDB | Data Warehouse |
| dbt | Transformations SQL |
| Prefect | Orchestration |
| Docker | Conteneurisation |
| Git / GitHub | Versionnement du code |
| GitHub Actions | CI/CD |
| Prometheus | Collecte des métriques |
| Grafana | Monitoring |

## 5. Architecture du pipeline

1. Extraction des données depuis les sources.
2. Chargement des données brutes.
3. Stockage dans DuckDB.
4. Transformation avec dbt.
5. Tests et validation de la qualité.
6. Orchestration quotidienne avec Prefect.
7. Monitoring du pipeline.
8. Mise à disposition des données analytiques pour le dashboard.

## 6. Structure du projet

- `config/` : configurations des environnements.
- `data/` : données brutes et intermédiaires.
- `src/` : code Python.
- `dbt/` : modèles de transformation SQL.
- `orchestration/` : workflows Prefect.
- `warehouse/` : bases DuckDB.
- `tests/` : tests automatisés.
- `monitoring/` : configuration du monitoring.
- `docs/` : documentation technique.
- `scripts/` : scripts utilitaires.

## 7. Environnements

Le projet prévoit deux environnements :

- Development : `warehouse/dev/dev.duckdb`
- Production : `warehouse/prod/prod.duckdb`

Les configurations sont séparées pour éviter de mélanger les données de développement et de production.

## 8. Installation

### Prérequis

- Python 3.11 ou version compatible avec les dépendances du projet.
- Git.
- Visual Studio Code.

### Cloner le projet

```bash
git clone <URL_DU_DEPOT>
cd dataops-energy
```

### Créer l'environnement virtuel

```bash
py -3 -m venv .venv
```

### Activer l'environnement sous Windows

```powershell
.\.venv\Scripts\Activate.ps1
```

### Installer les dépendances

```bash
pip install -r requirements.txt
```

## 9. Configuration

Créer un fichier `.env` à partir de `.env.example`.

```powershell
Copy-Item .env.example .env
```

Les variables d'environnement permettent de configurer les sources de données et les chemins de stockage.

## 10. Sécurité

- Ne jamais publier le fichier `.env`.
- Ne jamais versionner de clés API ou de mots de passe.
- Les données volumineuses sont exclues du dépôt Git.
- Le fichier `.env.example` contient uniquement des valeurs non sensibles.

## 11. État du projet

Projet en cours de développement.

Les différentes composantes seront intégrées progressivement selon le plan DataOps.
