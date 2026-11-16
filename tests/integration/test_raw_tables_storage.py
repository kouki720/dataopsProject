
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "warehouse" / "dev" / "dev.duckdb"


EXPECTED_COLUMNS = {
    "eco2mix": [
        "code_insee_epci",
        "libelle_metropole",
        "nature",
        "date",
        "heures",
        "date_heure",
        "consommation",
        "production",
        "echanges_physiques",
    ],
    "weather": [
        "code_insee_epci",
        "libelle_metropole",
        "latitude",
        "longitude",
        "date_heure",
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "apparent_temperature",
        "precipitation",
        "rain",
        "snowfall",
        "weather_code",
        "pressure_msl",
        "cloud_cover",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "shortwave_radiation",
    ],
}


DLT_COLUMNS = [
    "_dlt_load_id",
    "_dlt_id",
]


def test_raw_tables_storage():
    """Vérifie le stockage et la structure des tables RAW dans DuckDB."""

    assert DB_PATH.exists(), (
        f"Base DuckDB introuvable : {DB_PATH}"
    )

    connection = duckdb.connect(
        str(DB_PATH),
        read_only=True,
    )

    try:
        print("\n" + "=" * 65)
        print("VERIFICATION DU STOCKAGE DUCKDB")
        print("=" * 65)

        for table_name, expected_columns in EXPECTED_COLUMNS.items():

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

            actual_columns = [
                row[0]
                for row in connection.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'raw'
                      AND table_name = ?
                    ORDER BY ordinal_position
                    """,
                    [table_name],
                ).fetchall()
            ]

            print(f"\nTable : raw.{table_name}")
            print(f"Colonnes attendues : {len(expected_columns)}")
            print(f"Colonnes trouvées  : {len(actual_columns)}")

            # Vérification des colonnes métier.
            business_columns = [
                column
                for column in actual_columns
                if column not in DLT_COLUMNS
            ]

            assert business_columns == expected_columns, (
                f"Structure métier incorrecte pour raw.{table_name}.\n"
                f"Attendu : {expected_columns}\n"
                f"Trouvé  : {business_columns}"
            )

            # Vérification des colonnes techniques DLT.
            missing_dlt_columns = [
                column
                for column in DLT_COLUMNS
                if column not in actual_columns
            ]

            assert not missing_dlt_columns, (
                f"Colonnes techniques DLT manquantes "
                f"dans raw.{table_name} : {missing_dlt_columns}"
            )

            print("Colonnes métier       : OK")
            print("Colonnes techniques DLT : OK")

        print("\n" + "=" * 65)
        print("VERIFICATION DU STOCKAGE TERMINEE")
        print("=" * 65)

    finally:
        connection.close()
