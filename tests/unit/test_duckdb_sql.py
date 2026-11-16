
import sys
from pathlib import Path

# Ajouter le dossier src au chemin de recherche Python
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_PATH))

from dataops_energy.storage.duckdb_manager import get_connection


def test_sql_operations():
    connection = get_connection("dev")

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS raw.test_sql_operations (
                id INTEGER,
                source VARCHAR,
                value DOUBLE
            )
        """)

        connection.execute("DELETE FROM raw.test_sql_operations")

        connection.execute("""
            INSERT INTO raw.test_sql_operations
            VALUES
                (1, 'eco2mix', 125.5),
                (2, 'open_meteo', 18.7)
        """)

        rows = connection.execute("""
            SELECT *
            FROM raw.test_sql_operations
            ORDER BY id
        """).fetchall()

        assert len(rows) == 2
        assert rows[0] == (1, "eco2mix", 125.5)
        assert rows[1] == (2, "open_meteo", 18.7)

    finally:
        connection.execute(
            "DROP TABLE IF EXISTS raw.test_sql_operations"
        )
        connection.close()
