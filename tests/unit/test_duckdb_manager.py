
import sys
from pathlib import Path

# Ajouter le dossier src au chemin de recherche Python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_PATH))

from dataops_energy.storage.duckdb_manager import (
    get_connection,
    get_database_path,
)


def test_dev_database_connection():
    connection = get_connection("dev")
    try:
        result = connection.execute("SELECT 1").fetchone()
        assert result == (1,)
    finally:
        connection.close()


def test_prod_database_connection():
    connection = get_connection("prod")
    try:
        result = connection.execute("SELECT 1").fetchone()
        assert result == (1,)
    finally:
        connection.close()


def test_database_paths():
    assert get_database_path("dev").name == "dev.duckdb"
    assert get_database_path("prod").name == "prod.duckdb"
