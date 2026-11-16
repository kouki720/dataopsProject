
from pathlib import Path
import csv
from datetime import datetime


PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATASET_ID = "eco2mix-metropoles-tr"

CSV_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "eco2mix"
    / f"{DATASET_ID}.csv"
)

REQUIRED_COLUMNS = {
    "code_insee_epci",
    "libelle_metropole",
    "nature",
    "date",
    "heures",
    "date_heure",
    "consommation",
    "production",
    "echanges_physiques",
}

MAX_DATE = datetime.fromisoformat(
    "2026-11-14T22:59:59+00:00"
)


def validate_dataset():

    print("=" * 60)
    print("VALIDATION DU DATASET HISTORIQUE ÉCO2MIX")
    print("=" * 60)

    if not CSV_FILE.exists():
        raise FileNotFoundError(CSV_FILE)

    print(f"\nFichier : {CSV_FILE}")
    print(f"Taille : {CSV_FILE.stat().st_size / (1024 ** 2):.2f} MB")

    total_rows = 0
    invalid_rows = 0
    invalid_dates = 0

    null_measurements = 0
    nd_measurements = 0
    usable_measurements = 0

    min_date = None
    max_date = None

    with CSV_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file, delimiter=";")

        columns = set(reader.fieldnames or [])

        missing_columns = REQUIRED_COLUMNS - columns

        if missing_columns:
            raise ValueError(
                f"Colonnes manquantes : {sorted(missing_columns)}"
            )

        for row in reader:

            total_rows += 1

            if None in row or any(
                value is None for value in row.values()
            ):
                invalid_rows += 1
                continue

            date_string = row["date_heure"]

            try:
                current_date = datetime.fromisoformat(date_string)
            except (ValueError, TypeError):
                invalid_dates += 1
                continue

            if current_date.tzinfo is None:
                invalid_dates += 1
                continue

            if min_date is None or current_date < min_date:
                min_date = current_date

            if max_date is None or current_date > max_date:
                max_date = current_date

            measurements = [
                row["consommation"],
                row["production"],
                row["echanges_physiques"],
            ]

            if all(value.strip() == "" for value in measurements):
                null_measurements += 1

            elif all(value.strip().upper() == "ND" for value in measurements):
                nd_measurements += 1

            else:
                usable_measurements += 1

    print("\n" + "-" * 60)
    print("RÉSULTATS")
    print("-" * 60)

    print(f"Nombre total de lignes : {total_rows:,}")
    print(f"Nombre de colonnes     : {len(columns)}")

    print(f"\nPremière date          : {min_date}")
    print(f"Dernière date          : {max_date}")
    print(f"Limite maximale        : {MAX_DATE}")

    print(f"\nLignes mal formées     : {invalid_rows:,}")
    print(f"Dates invalides        : {invalid_dates:,}")

    print(f"\nMesures toutes vides   : {null_measurements:,}")
    print(f"Mesures toutes ND      : {nd_measurements:,}")
    print(f"Au moins une mesure exploitable : {usable_measurements:,}")

    print("\n" + "-" * 60)

    if total_rows == 0:
        print("ÉCHEC : dataset vide.")

    elif invalid_rows > 0 or invalid_dates > 0:
        print("ATTENTION : certaines lignes sont invalides.")

    elif max_date > MAX_DATE:
        print("ATTENTION : certaines données dépassent la limite.")

    else:
        print("VALIDATION STRUCTURELLE RÉUSSIE.")

    print("=" * 60)


if __name__ == "__main__":
    validate_dataset()
