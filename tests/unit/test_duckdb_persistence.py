
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_PATH))

from dataops_energy.storage.duckdb_manager import get_connection


def test_data_persistence_after_reconnection():
    # Première connexion : création et insertion
    connection = get_connection("dev")

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS raw.test_persistence (
                id INTEGER,
                source VARCHAR,
                value DOUBLE
            )
        """)

        connection.execute("DELETE FROM raw.test_persistence")

        connection.execute("""
            INSERT INTO raw.test_persistence
            VALUES (1, 'eco2mix', 125.5)
        """)

    finally:
        connection.close()

    # Deuxième connexion : vérification de la persistance
    connection = get_connection("dev")

    try:
        rows = connection.execute("""
            SELECT *
            FROM raw.test_persistence
        """).fetchall()

        assert rows == [(1, "eco2mix", 125.5)]

    finally:
        connection.execute(
            "DROP TABLE IF EXISTS raw.test_persistence"
        )
        connection.close()
