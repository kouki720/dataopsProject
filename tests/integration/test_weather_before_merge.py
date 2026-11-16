
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "warehouse" / "dev" / "dev.duckdb"


def test_weather_before_merge():
    assert DB_PATH.exists(), f"Base DuckDB introuvable : {DB_PATH}"

    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        exists = connection.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'raw'
              AND table_name = 'weather'
        """).fetchone()[0]

        if not exists:
            print("\nLa table raw.weather n'existe pas encore.")
            return

        count = connection.execute("""
            SELECT COUNT(*) FROM raw.weather
        """).fetchone()[0]

        print(f"\nLignes actuelles dans raw.weather : {count:,}")

    finally:
        connection.close()
