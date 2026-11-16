
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
    PROJECT_ROOT
    / "warehouse"
    / "dev"
    / "dev.duckdb"
)


def test_inspect_weather_extra_row():
    connection = duckdb.connect(
        str(DB_PATH),
        read_only=True,
    )

    try:
        rows = connection.execute("""
            SELECT *
            FROM raw.weather
            WHERE code_insee_epci = 'code_insee_epci'
               OR date_heure = 'date_heure'
        """).fetchall()

        print("\nLignes ressemblant à un header :")
        print(f"Nombre : {len(rows)}")

        for row in rows:
            print(row)

        assert len(rows) == 1

    finally:
        connection.close()
