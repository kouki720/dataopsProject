
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_PATH))

from dataops_energy.storage.duckdb_manager import get_connection


def test_dev_and_prod_are_isolated():
    dev = get_connection("dev")
    prod = get_connection("prod")

    try:
        dev.execute("""
            CREATE TABLE IF NOT EXISTS raw.test_isolation (
                id INTEGER,
                environment VARCHAR
            )
        """)

        dev.execute("DELETE FROM raw.test_isolation")

        dev.execute("""
            INSERT INTO raw.test_isolation
            VALUES (1, 'DEV')
        """)

        dev_tables = dev.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'raw'
              AND table_name = 'test_isolation'
        """).fetchall()

        prod_tables = prod.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'raw'
              AND table_name = 'test_isolation'
        """).fetchall()

        assert dev_tables == [('test_isolation',)]
        assert prod_tables == []

    finally:
        dev.execute("DROP TABLE IF EXISTS raw.test_isolation")
        dev.close()
        prod.close()
