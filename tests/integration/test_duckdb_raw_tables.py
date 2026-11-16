
from pathlib import Path

import duckdb
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DUCKDB_PATH = (
    PROJECT_ROOT
    / "warehouse"
    / "dev"
    / "dev.duckdb"
)


@pytest.fixture
def db():
    if not DUCKDB_PATH.exists():
        pytest.fail(f"Base DuckDB introuvable : {DUCKDB_PATH}")

    connection = duckdb.connect(
        str(DUCKDB_PATH),
        read_only=True,
    )

    yield connection

    connection.close()


def test_raw_schema_exists(db):
    schemas = db.execute(
        """
        SELECT schema_name
        FROM information_schema.schemata
        """
    ).fetchall()

    schema_names = [row[0] for row in schemas]

    assert "raw" in schema_names


def test_existing_raw_tables(db):
    tables = db.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'raw'
        ORDER BY table_name
        """
    ).fetchall()

    print("\nTables présentes dans raw :")

    if not tables:
        print("Aucune table")

    for (table_name,) in tables:
        count = db.execute(
            f'SELECT COUNT(*) FROM raw."{table_name}"'
        ).fetchone()[0]

        print(f"{table_name}: {count:,} lignes")

    assert isinstance(tables, list)
