
import csv
from pathlib import Path
from typing import Iterator

import dlt
from dlt.destinations import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DUCKDB_PATH = PROJECT_ROOT / "warehouse" / "dev" / "dev.duckdb"

DATASET_NAME = "raw"

BATCH_SIZE = 10_000

PRIMARY_KEY = ["code_insee_epci", "date_heure"]


def get_duckdb_path() -> Path:
    """Retourne le chemin de la base DuckDB DEV."""
    DUCKDB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DUCKDB_PATH


def get_csv_columns(csv_path: Path) -> list[str]:
    """Lit et valide les noms des colonnes du CSV."""

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {csv_path}"
        )

    with csv_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.reader(file, delimiter=";")
        columns = next(reader, None)

    if not columns:
        raise ValueError(
            f"Le fichier CSV est vide : {csv_path}"
        )

    columns = [column.strip() for column in columns]

    if len(columns) != len(set(columns)):
        raise ValueError(
            "Le CSV contient des noms de colonnes dupliqués."
        )

    return columns


def validate_primary_key(columns: list[str]) -> None:
    """Vérifie la présence des colonnes de la clé primaire."""

    missing_columns = [
        column
        for column in PRIMARY_KEY
        if column not in columns
    ]

    if missing_columns:
        raise ValueError(
            "Colonnes de clé primaire absentes du CSV : "
            f"{missing_columns}"
        )


def iter_csv_batches(
    csv_path: Path,
    batch_size: int = BATCH_SIZE,
) -> Iterator[list[dict[str, str]]]:
    """
    Lit le CSV progressivement et transmet des lots de lignes.

    L'en-tête est consommé correctement.
    Affiche la progression toutes les 10 000 lignes extraites.
    """

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {csv_path}"
        )

    if batch_size <= 0:
        raise ValueError(
            "batch_size doit être supérieur à zéro."
        )

    columns = get_csv_columns(csv_path)

    validate_primary_key(columns)

    total_rows = 0
    batch = []

    with csv_path.open(
        mode="r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(
            file,
            delimiter=";",
        )

        # Consomme l'en-tête original du CSV.
        original_headers = reader.fieldnames

        if original_headers is None:
            raise ValueError(
                f"En-tête CSV introuvable : {csv_path}"
            )

        # Utilise les noms de colonnes nettoyés.
        reader.fieldnames = columns

        for row in reader:

            clean_row = {
                column: (row.get(column) or "").strip()
                for column in columns
            }

            batch.append(clean_row)
            total_rows += 1

            if len(batch) >= batch_size:

                print(
                    f"[EXTRACTION] {total_rows:,} lignes lues",
                    flush=True,
                )

                yield batch
                batch = []

        if batch:

            print(
                f"[EXTRACTION] {total_rows:,} lignes lues",
                flush=True,
            )

            yield batch

    print(
        f"[EXTRACTION TERMINÉE] Total : {total_rows:,} lignes",
        flush=True,
    )


def create_csv_resource(
    csv_path: Path,
    table_name: str,
    write_disposition: str = "merge",
    batch_size: int = BATCH_SIZE,
):
    """Crée une ressource DLT configurée pour les lots et le merge."""

    columns = get_csv_columns(csv_path)

    validate_primary_key(columns)

    dlt_columns = {
        column: {"data_type": "text"}
        for column in columns
    }

    return dlt.resource(
        iter_csv_batches(
            csv_path=csv_path,
            batch_size=batch_size,
        ),
        name=table_name,
        write_disposition=write_disposition,
        primary_key=PRIMARY_KEY,
        columns=dlt_columns,
    )


def create_duckdb_pipeline(pipeline_name: str):
    """Crée une pipeline DLT vers DuckDB DEV."""

    database_path = get_duckdb_path()

    return dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=duckdb(
            credentials=str(database_path),
        ),
        dataset_name=DATASET_NAME,
    )


def run_csv_pipeline(
    pipeline_name: str,
    csv_path: Path,
    table_name: str,
    write_disposition: str = "merge",
    batch_size: int = BATCH_SIZE,
):
    """Exécute une pipeline CSV vers DuckDB."""

    print("\n" + "=" * 70)
    print(f"PIPELINE : {pipeline_name}")
    print("=" * 70)

    print(f"Source      : {csv_path}")
    print(f"Destination : {DUCKDB_PATH}")
    print(f"Dataset     : {DATASET_NAME}")
    print(f"Table       : {table_name}")
    print(f"Mode        : {write_disposition}")
    print(f"Taille lot  : {batch_size:,}")
    print(
        f"Clé primaire: {' + '.join(PRIMARY_KEY)}"
    )

    print("=" * 70)

    resource = create_csv_resource(
        csv_path=csv_path,
        table_name=table_name,
        write_disposition=write_disposition,
        batch_size=batch_size,
    )

    pipeline = create_duckdb_pipeline(pipeline_name)

    print(
        "\nDémarrage du chargement DLT...\n",
        flush=True,
    )

    load_info = pipeline.run(resource)

    print("\n" + "=" * 70)
    print("CHARGEMENT DLT TERMINÉ")
    print("=" * 70)
    print(load_info)
    print("=" * 70)

    return load_info
