
import duckdb
import pytest

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DUCKDB_PATH = (
    PROJECT_ROOT
    / "warehouse"
    / "dev"
    / "dev.duckdb"
)

TABLES = [
    "eco2mix",
    "weather",
]

PRIMARY_KEY = [
    "code_insee_epci",
    "date_heure",
]


@pytest.fixture(scope="module")
def connection():
    """Ouvre la base DuckDB en lecture seule."""

    if not DUCKDB_PATH.exists():
        pytest.fail(
            f"Base DuckDB introuvable : {DUCKDB_PATH}"
        )

    conn = duckdb.connect(
        str(DUCKDB_PATH),
        read_only=True,
    )

    yield conn

    conn.close()


@pytest.mark.parametrize("table_name", TABLES)
def test_no_duplicate_primary_keys(connection, table_name):
    """Vérifie l'absence de doublons sur la clé primaire."""

    table_exists = connection.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'raw'
          AND table_name = ?
        """,
        [table_name],
    ).fetchone()[0]

    assert table_exists == 1, (
        f"La table raw.{table_name} n'existe pas."
    )

    duplicate_count = connection.execute(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT {", ".join(PRIMARY_KEY)}
            FROM raw.{table_name}
            GROUP BY {", ".join(PRIMARY_KEY)}
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    assert duplicate_count == 0, (
        f"{duplicate_count} groupes de doublons détectés "
        f"dans raw.{table_name}."
    )
