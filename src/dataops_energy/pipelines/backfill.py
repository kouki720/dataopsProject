
import argparse
import csv
import sys

from collections import OrderedDict
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from dataops_energy.pipelines.dlt_csv_utils import (
    PROJECT_ROOT,
    BATCH_SIZE,
    get_csv_columns,
    validate_primary_key,
    run_csv_pipeline,
)


SOURCES = {
    "eco2mix": {
        "csv_path": (
            PROJECT_ROOT
            / "data"
            / "processed"
            / "eco2mix"
            / "eco2mix-metropoles-tr-deduplicated.csv"
        ),
        "pipeline_name": "eco2mix_pipeline",
        "table_name": "eco2mix",
    },
    "weather": {
        "csv_path": (
            PROJECT_ROOT
            / "data"
            / "processed"
            / "weather"
            / "weather_france-deduplicated.csv"
        ),
        "pipeline_name": "weather_pipeline",
        "table_name": "weather",
    },
}

MAX_OPEN_FILES = 64


def parse_date(value: str) -> date:
    """Convertit une date ISO en objet date."""

    try:
        return date.fromisoformat(value)

    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"Date invalide : {value}. Format attendu : YYYY-MM-DD"
        ) from error


def create_daily_partitions(
    csv_path: Path,
    start_date: date,
    end_date: date,
    temp_dir: Path,
) -> dict[date, int]:
    """
    Lit le CSV source une seule fois et répartit les lignes
    dans des fichiers temporaires journaliers.

    Utilise un nombre limité de fichiers ouverts simultanément.
    """

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {csv_path}"
        )

    columns = get_csv_columns(csv_path)
    validate_primary_key(columns)

    partitions = {}
    open_files = OrderedDict()

    total_rows = 0
    selected_rows = 0

    def get_writer(target_date: date):
        """Retourne le writer de la journée, en gérant les fichiers ouverts."""

        if target_date in open_files:
            open_files.move_to_end(target_date)
            return open_files[target_date][1]

        if len(open_files) >= MAX_OPEN_FILES:
            _, (old_file, _) = open_files.popitem(last=False)
            old_file.close()

        partition_path = (
            temp_dir / f"{target_date.isoformat()}.csv"
        )

        file_exists = partition_path.exists()

        file = partition_path.open(
            mode="a" if file_exists else "w",
            encoding="utf-8",
            newline="",
        )

        writer = csv.DictWriter(
            file,
            fieldnames=columns,
            delimiter=";",
        )

        if not file_exists:
            writer.writeheader()

        open_files[target_date] = (file, writer)

        return writer

    try:
        with csv_path.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as source_file:

            reader = csv.DictReader(
                source_file,
                delimiter=";",
            )

            if reader.fieldnames is None:
                raise ValueError(
                    f"En-tête CSV introuvable : {csv_path}"
                )

            reader.fieldnames = columns

            for row in reader:

                total_rows += 1

                clean_row = {
                    column: (row.get(column) or "").strip()
                    for column in columns
                }

                date_value = clean_row["date_heure"][:10]

                try:
                    row_date = date.fromisoformat(date_value)

                except ValueError as error:
                    raise ValueError(
                        f"Date invalide à la ligne {total_rows + 1} : "
                        f"{date_value}"
                    ) from error

                if not start_date <= row_date <= end_date:
                    continue

                writer = get_writer(row_date)

                writer.writerow(clean_row)

                partitions[row_date] = (
                    partitions.get(row_date, 0) + 1
                )

                selected_rows += 1

                if total_rows % BATCH_SIZE == 0:
                    print(
                        f"[BACKFILL EXTRACTION] "
                        f"{total_rows:,} lignes analysées",
                        flush=True,
                    )

    finally:
        for file, _ in open_files.values():
            file.close()

    print("\n[BACKFILL EXTRACTION TERMINÉE]")
    print(f"Lignes analysées : {total_rows:,}")
    print(f"Lignes sélectionnées : {selected_rows:,}")
    print(f"Journées trouvées : {len(partitions)}")

    return partitions


def run_backfill(
    source_name: str,
    start_date: date,
    end_date: date,
):
    """Exécute le backfill jour par jour."""

    if start_date > end_date:
        raise ValueError(
            "La date de début doit être antérieure ou égale à la date de fin."
        )

    if source_name not in SOURCES:
        raise ValueError(
            f"Source inconnue : {source_name}"
        )

    source = SOURCES[source_name]

    print("\n" + "=" * 70)
    print(f"BACKFILL : {source_name.upper()}")
    print("=" * 70)
    print(f"Début : {start_date}")
    print(f"Fin   : {end_date}")
    print(f"Table : raw.{source['table_name']}")
    print("Mode  : merge")
    print("=" * 70)

    with TemporaryDirectory(
        prefix=f"backfill_{source_name}_"
    ) as temporary_directory:

        temp_dir = Path(temporary_directory)

        partitions = create_daily_partitions(
            csv_path=source["csv_path"],
            start_date=start_date,
            end_date=end_date,
            temp_dir=temp_dir,
        )

        current_date = start_date
        loaded_days = 0
        skipped_days = 0

        while current_date <= end_date:

            daily_csv = (
                temp_dir / f"{current_date.isoformat()}.csv"
            )

            print("\n" + "-" * 70)
            print(f"DATE : {current_date}")
            print("-" * 70)

            if current_date not in partitions:
                print(
                    f"[SKIP] Aucune donnée pour {current_date}"
                )

                skipped_days += 1

            else:
                print(
                    f"[CHARGEMENT] "
                    f"{partitions[current_date]:,} lignes"
                )

                run_csv_pipeline(
                    pipeline_name=source["pipeline_name"],
                    csv_path=daily_csv,
                    table_name=source["table_name"],
                    write_disposition="merge",
                    batch_size=BATCH_SIZE,
                )

                loaded_days += 1

            current_date += timedelta(days=1)

        print("\n" + "=" * 70)
        print("BACKFILL TERMINÉ")
        print("=" * 70)
        print(f"Source : {source_name}")
        print(f"Journées chargées : {loaded_days}")
        print(f"Journées sans données : {skipped_days}")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Backfill journalier des données vers DuckDB."
    )

    parser.add_argument(
        "--source",
        choices=["eco2mix", "weather", "all"],
        required=True,
        help="Source à recharger.",
    )

    parser.add_argument(
        "--start-date",
        type=parse_date,
        required=True,
        help="Date de début (YYYY-MM-DD).",
    )

    parser.add_argument(
        "--end-date",
        type=parse_date,
        required=True,
        help="Date de fin (YYYY-MM-DD).",
    )

    args = parser.parse_args()

    sources_to_run = (
        list(SOURCES.keys())
        if args.source == "all"
        else [args.source]
    )

    for source_name in sources_to_run:
        run_backfill(
            source_name=source_name,
            start_date=args.start_date,
            end_date=args.end_date,
        )


if __name__ == "__main__":
    main()
