
from pathlib import Path
import csv

PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATASET_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "eco2mix"
    / "eco2mix-metropoles-tr.csv"
)


def get_local_latest_date():
    if not DATASET_FILE.exists():
        raise FileNotFoundError(
            f"Dataset introuvable : {DATASET_FILE}"
        )

    latest_date = None
    row_count = 0

    with DATASET_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file, delimiter=";")

        if "date_heure" not in (reader.fieldnames or []):
            raise ValueError(
                "La colonne date_heure est absente du dataset."
            )

        for row in reader:
            date_value = row.get("date_heure")

            if date_value:
                row_count += 1

                if latest_date is None or date_value > latest_date:
                    latest_date = date_value

    return latest_date, row_count


if __name__ == "__main__":
    latest_date, row_count = get_local_latest_date()

    print("\n===== DATASET LOCAL =====")
    print(f"Nombre de lignes : {row_count:,}")
    print(f"Dernière date : {latest_date}")
