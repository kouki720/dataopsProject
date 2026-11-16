
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
    PROJECT_ROOT
    / "warehouse"
    / "dev"
    / "dev.duckdb"
)

EXPECTED_ROWS = {
    "eco2mix": 1_315_148,
    "weather": 529_704,
}


def test_raw_tables_row_count():
    connection = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        print("\n" + "=" * 65)
        print("VERIFICATION DU NOMBRE DE LIGNES DANS DUCKDB")
        print("=" * 65)

        for table_name, expected_count in EXPECTED_ROWS.items():

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

            actual_count = connection.execute(
                f'SELECT COUNT(*) FROM raw."{table_name}"'
            ).fetchone()[0]

            difference = actual_count - expected_count

            print(f"\nTable          : raw.{table_name}")
            print(f"Lignes attendues : {expected_count:,}")
            print(f"Lignes trouvées  : {actual_count:,}")
            print(f"Différence       : {difference:,}")

            assert actual_count == expected_count, (
                f"Nombre de lignes incorrect dans raw.{table_name} : "
                f"{actual_count:,} au lieu de {expected_count:,}"
            )

        print("\n" + "=" * 65)
        print("VOLUME TOTAL")
        print("=" * 65)

        total_rows = sum(
            connection.execute(
                f'SELECT COUNT(*) FROM raw."{table_name}"'
            ).fetchone()[0]
            for table_name in EXPECTED_ROWS
        )

        print(f"Total : {total_rows:,} lignes")

        assert total_rows == 1_844_852
        assert total_rows >= 1_000_000

    finally:
        connection.close()
