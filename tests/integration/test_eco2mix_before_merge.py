
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "warehouse" / "dev" / "dev.duckdb"


def test_eco2mix_before_merge():
    assert DB_PATH.exists(), f"Base DuckDB introuvable : {DB_PATH}"

    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        result = connection.execute("""
            SELECT COUNT(*)
            FROM raw.eco2mix
        """).fetchone()

        print(f"\nLignes actuelles dans raw.eco2mix : {result[0]:,}")

        columns = connection.execute("""
            DESCRIBE raw.eco2mix
        """).fetchall()

        print("\nColonnes de la table :")
        for column in columns:
            print(f"- {column[0]}")

    finally:
        connection.close()
