
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

SOURCE_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "eco2mix"
    / "eco2mix-metropoles-tr.csv"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "eco2mix"
    / "eco2mix-metropoles-tr-deduplicated.csv"
)

KEY_COLUMNS = ["code_insee_epci", "date_heure"]


def deduplicate_csv():
    if not SOURCE_FILE.exists():
        raise FileNotFoundError(SOURCE_FILE)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    seen_keys = set()
    total_rows = 0
    kept_rows = 0
    removed_rows = 0

    print("=" * 65)
    print("DEDUPLICATION ECO2MIX")
    print("=" * 65)

    with (
        SOURCE_FILE.open("r", encoding="utf-8-sig", newline="") as source,
        OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as output,
    ):
        reader = csv.DictReader(source, delimiter=";")

        if not reader.fieldnames:
            raise ValueError("CSV vide ou sans en-têtes.")

        for column in KEY_COLUMNS:
            if column not in reader.fieldnames:
                raise ValueError(f"Colonne absente : {column}")

        writer = csv.DictWriter(
            output,
            fieldnames=reader.fieldnames,
            delimiter=";",
        )
        writer.writeheader()

        for row in reader:
            total_rows += 1

            key = tuple(row[column].strip() for column in KEY_COLUMNS)

            if key in seen_keys:
                removed_rows += 1
            else:
                seen_keys.add(key)
                writer.writerow(row)
                kept_rows += 1

            if total_rows % 10000 == 0:
                print(
                    f"Lignes traitées : {total_rows:,} | "
                    f"Conservées : {kept_rows:,} | "
                    f"Supprimées : {removed_rows:,}"
                )

    print("\n" + "=" * 65)
    print("RÉSULTAT")
    print("=" * 65)
    print(f"Lignes initiales  : {total_rows:,}")
    print(f"Lignes conservées : {kept_rows:,}")
    print(f"Lignes supprimées : {removed_rows:,}")
    print(f"Fichier créé      : {OUTPUT_FILE}")


if __name__ == "__main__":
    deduplicate_csv()
