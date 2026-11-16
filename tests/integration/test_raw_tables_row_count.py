
import duckdb
import pytest

DB_PATH = "warehouse/dev/dev.duckdb"

TABLES = ["eco2mix", "weather"]


@pytest.fixture
def connection():
    conn = duckdb.connect(DB_PATH, read_only=True)
    yield conn
    conn.close()


@pytest.mark.parametrize("table", TABLES)
def test_raw_table_row_count(connection, table):
    result = connection.execute(
        f'SELECT COUNT(*) FROM raw."{table}"'
    ).fetchone()

    row_count = result[0]

    print(f"\nraw.{table}: {row_count:,} lignes")

    assert row_count >= 0, f"Impossible de lire le nombre de lignes de raw.{table}"
