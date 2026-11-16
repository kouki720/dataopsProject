
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = (
    PROJECT_ROOT
    / "warehouse"
    / "dev"
    / "dev.duckdb"
)


def test_inspect_eco2mix_extra_row():
    connection = duckdb.connect(
        str(DB_PATH),
        read_only=True,
    )

    try:
        print("\n" + "=" * 65)
        print("DIAGNOSTIC DE LA TABLE ECO2MIX")
        print("=" * 65)

        suspicious_rows = connection.execute("""
            SELECT
                code_insee_epci,
                libelle_metropole,
                nature,
                date,
                heures,
                date_heure,
                consommation,
                production,
                echanges_physiques
            FROM raw.eco2mix
            WHERE code_insee_epci = 'code_insee_epci'
               OR date_heure = 'date_heure'
        """).fetchall()

        print("\nLignes ressemblant à un en-tête CSV :")
        print(f"Nombre : {len(suspicious_rows)}")

        for row in suspicious_rows:
            print(row)

        duplicate_keys = connection.execute("""
            SELECT
                COUNT(*)
            FROM (
                SELECT
                    code_insee_epci,
                    date_heure
                FROM raw.eco2mix
                GROUP BY
                    code_insee_epci,
                    date_heure
                HAVING COUNT(*) > 1
            ) AS duplicates
        """).fetchone()[0]

        print("\nGroupes de clés primaires en doublon :")
        print(f"Nombre : {duplicate_keys}")

    finally:
        connection.close()
