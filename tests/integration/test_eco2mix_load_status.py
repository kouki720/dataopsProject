
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
    PROJECT_ROOT
    / "warehouse"
    / "dev"
    / "dev.duckdb"
)


def test_eco2mix_load_status():
    assert DB_PATH.exists(), "Base DuckDB introuvable"

    db = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        result = db.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'raw'
              AND table_name = 'eco2mix'
            """
        ).fetchone()

        if result is None:
            print("\nTable raw.eco2mix : ABSENTE")
            return

        count = db.execute(
            "SELECT COUNT(*) FROM raw.eco2mix"
        ).fetchone()[0]

        print(f"\nTable raw.eco2mix : PRESENTE")
        print(f"Nombre de lignes : {count:,}")

    finally:
        db.close()
