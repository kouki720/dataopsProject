
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import csv
import io

import requests


# ============================================================
# CONFIGURATION COMMUNE
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATASET_ID = "eco2mix-metropoles-tr"

API_URL = (
    "https://odre.opendatasoft.com/api/explore/v2.1/"
    f"catalog/datasets/{DATASET_ID}/records"
)

TIME_API_URL = "https://timeapi.io/api/Time/current/zone"

PARIS_TZ = ZoneInfo("Europe/Paris")
UTC_TZ = ZoneInfo("UTC")

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "eco2mix"
    / f"{DATASET_ID}.csv"
)

TEMPORARY_FILE = OUTPUT_FILE.with_suffix(".csv.part")

COLUMNS = [
    "code_insee_epci",
    "libelle_metropole",
    "nature",
    "date",
    "heures",
    "date_heure",
    "consommation",
    "production",
    "echanges_physiques",
]

MEASURE_COLUMNS = [
    "consommation",
    "production",
    "echanges_physiques",
]

API_PAGE_SIZE = 100


# ============================================================
# 1. HEURE DE RÉFÉRENCE PARIS
# ============================================================

def get_reference_time():

    response = requests.get(
        TIME_API_URL,
        params={"timeZone": "Europe/Paris"},
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    reference_time = datetime.fromisoformat(data["dateTime"])

    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(
            tzinfo=PARIS_TZ
        )
    else:
        reference_time = reference_time.astimezone(
            PARIS_TZ
        )

    return reference_time


# ============================================================
# 2. DERNIÈRE DATE DU DATASET
# ============================================================

def get_latest_dataset_date():

    if not OUTPUT_FILE.exists():
        raise FileNotFoundError(
            f"Dataset introuvable : {OUTPUT_FILE}"
        )

    latest_date = None

    with OUTPUT_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        reader = csv.DictReader(file, delimiter=";")

        if not reader.fieldnames:
            raise ValueError("En-tête CSV absent.")

        missing = set(COLUMNS) - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"Colonnes manquantes : {sorted(missing)}"
            )

        for row in reader:

            date_string = row.get("date_heure", "")

            if not date_string:
                raise ValueError(
                    "Une ligne possède une date_heure vide."
                )

            current_date = datetime.fromisoformat(date_string)

            if current_date.tzinfo is None:
                raise ValueError(
                    f"Date sans fuseau horaire : {date_string}"
                )

            current_date = current_date.astimezone(UTC_TZ)

            if latest_date is None or current_date > latest_date:
                latest_date = current_date

    if latest_date is None:
        raise ValueError("Aucune date trouvée dans le dataset.")

    return latest_date


# ============================================================
# 3. RÉCUPÉRATION DES DONNÉES VIA L'EXPORT CSV
# ============================================================

def get_api_records(start_date, end_date):
    """Récupère toutes les lignes de la période via l'export CSV.

    L'endpoint /records est limité à 10 000 résultats cumulés.
    L'endpoint /exports/csv permet de récupérer un export complet.
    """

    start_string = (
        start_date.astimezone(UTC_TZ)
        .replace(tzinfo=None)
        .isoformat(timespec="seconds")
    )

    end_string = (
        end_date.astimezone(UTC_TZ)
        .replace(tzinfo=None)
        .isoformat(timespec="seconds")
    )

    where_clause = (
        f"date_heure >= date'{start_string}' "
        f"AND date_heure <= date'{end_string}'"
    )

    export_url = API_URL.replace("/records", "/exports/csv")

    params = {
        "select": ",".join(COLUMNS),
        "where": where_clause,
        "order_by": "date_heure ASC",
        "delimiter": ";",
        "with_bom": "false",
    }

    print("\nFiltre API :")
    print(where_clause)
    print("\nTéléchargement de l'export CSV...")

    response = requests.get(
        export_url,
        params=params,
        timeout=(20, 180),
    )
    response.raise_for_status()

    try:
        csv_content = response.content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Impossible de décoder l'export CSV reçu en UTF-8."
        ) from error

    reader = csv.DictReader(
        io.StringIO(csv_content, newline=""),
        delimiter=";",
    )

    if reader.fieldnames is None:
        raise ValueError("L'export CSV ne contient pas d'en-tête.")

    missing_columns = set(COLUMNS) - set(reader.fieldnames)
    if missing_columns:
        raise ValueError(
            f"Colonnes absentes de l'export CSV : {sorted(missing_columns)}"
        )

    records = []

    for row_number, row in enumerate(reader, start=2):
        if None in row:
            raise ValueError(
                f"Ligne CSV {row_number} : nombre de champs inattendu."
            )

        normalized_record = {
            column: (row.get(column) or "")
            for column in COLUMNS
        }

        date_string = normalized_record["date_heure"]
        if not date_string:
            raise ValueError(
                f"Ligne CSV {row_number} : date_heure vide."
            )

        try:
            record_date = datetime.fromisoformat(date_string)
        except ValueError as error:
            raise ValueError(
                f"Ligne CSV {row_number} : date_heure invalide : {date_string}"
            ) from error

        if record_date.tzinfo is None:
            raise ValueError(
                f"Ligne CSV {row_number} : date sans fuseau horaire : {date_string}"
            )

        record_date = record_date.astimezone(UTC_TZ)
        if not (start_date <= record_date <= end_date):
            raise ValueError(
                f"Ligne CSV {row_number} hors de la période demandée : {date_string}"
            )

        records.append(normalized_record)

    print(f"Lignes récupérées : {len(records):,}")
    return records


# ============================================================
# 4. CLÉ UNIQUE
# ============================================================

def get_record_key(row):

    return (
        row["code_insee_epci"],
        row["nature"],
        row["date_heure"],
    )


# ============================================================
# 5. FUSION DE DEUX VERSIONS D'UNE MESURE
# ============================================================

def merge_records(old_record, new_record):

    merged = old_record.copy()

    for column in COLUMNS:

        old_value = old_record.get(column, "")
        new_value = new_record.get(column, "")

        if column in MEASURE_COLUMNS:

            old_is_usable = (
                old_value.strip() != ""
                and old_value.strip().upper() != "ND"
            )

            new_is_usable = (
                new_value.strip() != ""
                and new_value.strip().upper() != "ND"
            )

            if new_is_usable:
                merged[column] = new_value

            elif not old_is_usable:
                merged[column] = new_value

        elif new_value != "":
            merged[column] = new_value

    return merged


# ============================================================
# 6. FUSION ET ÉCRITURE SÉCURISÉE DU CSV
# ============================================================

def update_csv(api_records, start_date, end_date):

    # Indexer les nouvelles données reçues de l'API
    merged_records = {}

    for record in api_records:

        key = get_record_key(record)

        if key in merged_records:
            merged_records[key] = merge_records(
                merged_records[key],
                record,
            )
        else:
            merged_records[key] = record

    old_window_count = 0

    try:

        with OUTPUT_FILE.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as source:

            reader = csv.DictReader(source, delimiter=";")

            with TEMPORARY_FILE.open(
                "w",
                encoding="utf-8-sig",
                newline="",
            ) as destination:

                writer = csv.DictWriter(
                    destination,
                    fieldnames=COLUMNS,
                    delimiter=";",
                    extrasaction="ignore",
                )

                writer.writeheader()

                final_count = 0

                # Conserver les lignes hors de la période actualisée
                for row in reader:

                    current_date = datetime.fromisoformat(
                        row["date_heure"]
                    ).astimezone(UTC_TZ)

                    if current_date < start_date or current_date > end_date:

                        writer.writerow(row)
                        final_count += 1

                    else:

                        old_window_count += 1

                        key = get_record_key(row)

                        if key in merged_records:

                            merged_records[key] = merge_records(
                                row,
                                merged_records[key],
                            )

                        else:
                            # Garder les anciennes lignes si l'API
                            # ne retourne pas de nouvelle version.
                            merged_records[key] = row

                # Écrire les données fusionnées dans l'ordre chronologique
                sorted_records = sorted(
                    merged_records.values(),
                    key=lambda row: (
                        row["date_heure"],
                        row["code_insee_epci"],
                        row["nature"],
                    ),
                )

                for record in sorted_records:

                    writer.writerow(record)
                    final_count += 1

        # Validation du fichier temporaire
        checked_count = 0

        with TEMPORARY_FILE.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            reader = csv.DictReader(file, delimiter=";")

            if reader.fieldnames != COLUMNS:
                raise ValueError(
                    "Les colonnes du fichier temporaire sont incorrectes."
                )

            for row in reader:

                if not all(column in row for column in COLUMNS):
                    raise ValueError("Ligne CSV invalide.")

                if not row["date_heure"]:
                    raise ValueError("Date vide dans le fichier temporaire.")

                datetime.fromisoformat(row["date_heure"])

                checked_count += 1

        if checked_count != final_count:
            raise ValueError(
                "Le nombre de lignes après écriture est incorrect."
            )

        # Remplacement après validation seulement
        TEMPORARY_FILE.replace(OUTPUT_FILE)

        return {
            "old_window": old_window_count,
            "api_records": len(api_records),
            "merged_window": len(merged_records),
            "final_total": final_count,
        }

    except Exception:

        TEMPORARY_FILE.unlink(missing_ok=True)

        raise


# ============================================================
# 7. AFFICHER LE RÉSULTAT
# ============================================================

def display_result(result):

    print("\n" + "=" * 60)
    print("RÉSULTAT DE LA MISE À JOUR")
    print("=" * 60)

    print(
        f"Anciennes lignes dans la période : "
        f"{result['old_window']:,}"
    )

    print(
        f"Lignes reçues de l'API           : "
        f"{result['api_records']:,}"
    )

    print(
        f"Lignes fusionnées dans la période: "
        f"{result['merged_window']:,}"
    )

    print(
        f"Nombre total de lignes           : "
        f"{result['final_total']:,}"
    )

    print(f"\nFichier : {OUTPUT_FILE}")
