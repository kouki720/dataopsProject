
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATABASES = {
    "dev": PROJECT_ROOT / "warehouse" / "dev" / "dev.duckdb",
    "prod": PROJECT_ROOT / "warehouse" / "prod" / "prod.duckdb",
}


def get_connection(environment: str = "dev"):
    """
    Retourne une connexion à la base DuckDB demandée.
    Environnements autorisés : dev et prod.
    """
    if environment not in DATABASES:
        raise ValueError(
            f"Environnement invalide : {environment}. "
            f"Valeurs autorisées : {list(DATABASES)}"
        )

    database_path = DATABASES[environment]
    database_path.parent.mkdir(parents=True, exist_ok=True)

    return duckdb.connect(str(database_path))


def get_database_path(environment: str = "dev") -> Path:
    """Retourne le chemin de la base DuckDB."""
    if environment not in DATABASES:
        raise ValueError(f"Environnement invalide : {environment}")

    return DATABASES[environment]
