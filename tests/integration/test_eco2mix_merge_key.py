
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[2]

CSV_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "eco2mix"
    / "eco2mix-metropoles-tr.csv"
)


def test_eco2mix_merge_key_candidates():
    assert CSV_PATH.exists(), f"CSV introuvable : {CSV_PATH}"

    db = duckdb.connect(":memory:")

    try:
        csv_path = str(CSV_PATH).replace("\\", "/").replace("'", "''")

        source = f"""
            read_csv(
                '{csv_path}',
                delim = ';',
                header = true,
                all_varchar = true
            )
        """

        candidates = {
            "code_insee_epci + date_heure": [
                "code_insee_epci",
                "date_heure",
            ],
            "code_insee_epci + date_heure + nature": [
                "code_insee_epci",
                "date_heure",
                "nature",
            ],
        }

        print("\nANALYSE DES CLÉS CANDIDATES")

        for label, columns in candidates.items():
            group_columns = ", ".join(columns)

            result = db.execute(
                f"""
                SELECT
                    COUNT(*) AS duplicate_groups,
                    COALESCE(SUM(occurrences - 1), 0) AS extra_rows
                FROM (
                    SELECT COUNT(*) AS occurrences
                    FROM {source}
                    GROUP BY {group_columns}
                    HAVING COUNT(*) > 1
                ) duplicates
                """
            ).fetchone()

            print(f"\nClé : {label}")
            print(f"Groupes dupliqués : {result[0]:,}")
            print(f"Lignes supplémentaires : {result[1]:,}")

        print("\nEXEMPLES DES DOUBLONS DE LA PREMIÈRE CLÉ")

        examples = db.execute(
            f"""
            SELECT
                code_insee_epci,
                date_heure,
                nature,
                consommation,
                production,
                echanges_physiques,
                COUNT(*) AS occurrences
            FROM {source}
            GROUP BY
                code_insee_epci,
                date_heure,
                nature,
                consommation,
                production,
                echanges_physiques
            HAVING COUNT(*) > 1
            LIMIT 10
            """
        ).fetchall()

        for row in examples:
            print(row)

    finally:
        db.close()
