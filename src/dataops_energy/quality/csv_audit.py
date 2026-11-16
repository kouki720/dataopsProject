
from pathlib import Path
from collections import Counter
from datetime import datetime
import csv
import json
import hashlib
import time

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

REPORT_DIR = PROJECT_ROOT / "reports" / "data_quality"

CHUNK_SIZE = 50_000

SOURCES = {
    "eco2mix": {
        "path": (
            PROJECT_ROOT
            / "data"
            / "raw"
            / "eco2mix"
            / "eco2mix-metropoles-tr.csv"
        ),
        "date_columns": ["date", "date_heure"],
        "city_column": "libelle_metropole",
        "identifier_column": "code_insee_epci",
        "numeric_columns": [
            "consommation",
            "production",
            "echanges_physiques",
        ],
        "candidate_keys": [
            ["code_insee_epci", "date_heure"],
        ],
    },

    "weather": {
        "path": (
            PROJECT_ROOT
            / "data"
            / "raw"
            / "open_meteo"
            / "weather_france.csv"
        ),
        "date_columns": ["date_heure"],
        "city_column": "libelle_metropole",
        "identifier_column": "code_insee_epci",
        "numeric_columns": [
            "latitude",
            "longitude",
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
        "candidate_keys": [
            ["code_insee_epci", "date_heure"],
        ],
    },
}


# ============================================================
# UTILITAIRES
# ============================================================

def detect_encoding(path):
    """Détecte les encodages courants."""

    encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]

    for encoding in encodings:
        try:
            with path.open(
                "r",
                encoding=encoding,
                newline="",
            ) as file:
                file.read(100_000)

            return encoding

        except UnicodeDecodeError:
            continue

    raise ValueError(f"Encodage non reconnu : {path}")


def detect_delimiter(path, encoding):
    """Détecte le séparateur CSV."""

    with path.open(
        "r",
        encoding=encoding,
        newline="",
    ) as file:

        sample = file.read(20_000)

    try:
        dialect = csv.Sniffer().sniff(
            sample,
            delimiters=";,|\t",
        )

        return dialect.delimiter

    except csv.Error:
        return ";"


def calculate_sha256(path):
    """Calcule l'empreinte SHA256 du fichier."""

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def normalize_value(value):
    """Normalise les valeurs pour détecter les champs vides."""

    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    return value


# ============================================================
# AUDIT D'UNE SOURCE
# ============================================================

def audit_source(source_name, config):

    path = config["path"]

    print("\n" + "=" * 70)
    print(f"AUDIT : {source_name.upper()}")
    print("=" * 70)

    if not path.exists():
        raise FileNotFoundError(
            f"Fichier introuvable : {path}"
        )

    start_time = time.time()

    encoding = detect_encoding(path)
    delimiter = detect_delimiter(path, encoding)

    file_size = path.stat().st_size
    sha256 = calculate_sha256(path)

    print(f"Fichier       : {path}")
    print(f"Taille        : {file_size / 1024 / 1024:.2f} MB")
    print(f"Encodage      : {encoding}")
    print(f"Séparateur    : {repr(delimiter)}")
    print(f"SHA256        : {sha256}")

    # --------------------------------------------------------
    # INITIALISATION
    # --------------------------------------------------------

    total_rows = 0
    empty_counts = Counter()
    nd_counts = Counter()
    invalid_numeric = Counter()
    invalid_dates = Counter()

    value_counts = {
        column: Counter()
        for column in [
            config["city_column"],
            config["identifier_column"],
        ]
    }

    date_min = {
        column: None
        for column in config["date_columns"]
    }

    date_max = {
        column: None
        for column in config["date_columns"]
    }

    duplicate_keys = Counter()
    key_seen = {
        tuple(columns): set()
        for columns in config["candidate_keys"]
    }

    exact_rows_seen = set()
    exact_duplicates = 0

    detected_types = {}
    columns = None

    # --------------------------------------------------------
    # LECTURE PAR CHUNKS
    # --------------------------------------------------------

    reader = pd.read_csv(
        path,
        sep=delimiter,
        encoding=encoding,
        dtype=str,
        chunksize=CHUNK_SIZE,
        keep_default_na=False,
        on_bad_lines="error",
    )

    for chunk_number, chunk in enumerate(reader, start=1):

        if columns is None:
            columns = list(chunk.columns)

            detected_types = {
                column: {
                    "integer": 0,
                    "float": 0,
                    "datetime": 0,
                    "text": 0,
                }
                for column in columns
            }

            print("\nColonnes détectées :")
            for column in columns:
                print(f"  - {column}")

        total_rows += len(chunk)

        # Vérification des valeurs vides et ND
        for column in columns:

            values = chunk[column].astype(str).str.strip()

            empty_counts[column] += int(
                values.eq("").sum()
            )

            nd_counts[column] += int(
                values.str.upper().eq("ND").sum()
            )

        # Répartition des métropoles
        for column in value_counts:

            value_counts[column].update(
                value
                for value in chunk[column].astype(str).str.strip()
                if value
            )

        # Analyse des types numériques
        for column in config["numeric_columns"]:

            if column not in chunk.columns:
                continue

            values = chunk[column].astype(str).str.strip()

            present = values[
                values.ne("") &
                values.str.upper().ne("ND")
            ]

            numeric_values = pd.to_numeric(
                present,
                errors="coerce",
            )

            invalid_numeric[column] += int(
                numeric_values.isna().sum()
            )

            valid = numeric_values.dropna()

            if len(valid):
                integer_count = int(
                    (valid % 1 == 0).sum()
                )

                detected_types[column]["integer"] += integer_count
                detected_types[column]["float"] += (
                    len(valid) - integer_count
                )

        # Analyse des dates
        for column in config["date_columns"]:

            if column not in chunk.columns:
                continue

            values = chunk[column].astype(str).str.strip()

            present = values[values.ne("")]

            parsed = pd.to_datetime(
                present,
                errors="coerce",
                utc=True,
                format="mixed",
            )

            invalid_dates[column] += int(
                parsed.isna().sum()
            )

            valid_dates = parsed.dropna()

            if len(valid_dates):

                minimum = valid_dates.min()
                maximum = valid_dates.max()

                if (
                    date_min[column] is None
                    or minimum < date_min[column]
                ):
                    date_min[column] = minimum

                if (
                    date_max[column] is None
                    or maximum > date_max[column]
                ):
                    date_max[column] = maximum

        # Détection des doublons exacts
        for row in chunk.itertuples(
            index=False,
            name=None,
        ):

            normalized_row = tuple(
                str(value).strip()
                for value in row
            )

            row_hash = hashlib.sha256(
                "\x1f".join(normalized_row).encode("utf-8")
            ).hexdigest()

            if row_hash in exact_rows_seen:
                exact_duplicates += 1
            else:
                exact_rows_seen.add(row_hash)

        # Détection des doublons sur les clés candidates
        for key_columns in key_seen:

            if not all(
                column in chunk.columns
                for column in key_columns
            ):
                continue

            keys = chunk[list(key_columns)].astype(str)

            for values in keys.itertuples(
                index=False,
                name=None,
            ):

                key = tuple(
                    str(value).strip()
                    for value in values
                )

                if any(value == "" for value in key):
                    continue

                if key in key_seen[key_columns]:
                    duplicate_keys[
                        ",".join(key_columns)
                    ] += 1

                else:
                    key_seen[key_columns].add(key)

        print(
            f"\rChunks analysés : {chunk_number} | "
            f"Lignes : {total_rows:,}",
            end="",
            flush=True,
        )

    # --------------------------------------------------------
    # RÉSULTATS
    # --------------------------------------------------------

    print("\n\nRÉSULTATS")
    print("-" * 70)

    print(f"Nombre total de lignes : {total_rows:,}")
    print(f"Nombre de colonnes     : {len(columns)}")

    print("\nTypes détectés :")

    for column, counts in detected_types.items():

        if column not in config["numeric_columns"]:
            continue

        integer_count = counts["integer"]
        float_count = counts["float"]

        if integer_count + float_count == 0:
            detected = "Aucune valeur numérique valide"

        elif float_count == 0:
            detected = "Entier probable"

        elif integer_count == 0:
            detected = "Décimal probable"

        else:
            detected = "Mixte entier/décimal"

        print(f"  {column}: {detected}")

    print("\nValeurs manquantes :")

    for column, count in empty_counts.items():

        if count:
            percentage = count / total_rows * 100

            print(
                f"  {column}: {count:,} "
                f"({percentage:.2f}%)"
            )

    print("\nValeurs ND :")

    for column, count in nd_counts.items():

        if count:
            print(f"  {column}: {count:,}")

    print("\nValeurs numériques invalides :")

    for column, count in invalid_numeric.items():

        if count:
            print(f"  {column}: {count:,}")

    print("\nDates invalides :")

    for column, count in invalid_dates.items():

        if count:
            print(f"  {column}: {count:,}")

    print("\nPériodes temporelles :")

    for column in config["date_columns"]:

        print(
            f"  {column}: "
            f"{date_min[column]} -> {date_max[column]}"
        )

    print("\nDoublons :")

    print(
        f"  Lignes exactement dupliquées : "
        f"{exact_duplicates:,}"
    )

    for key, count in duplicate_keys.items():
        print(
            f"  Clé ({key}) : {count:,} doublons"
        )

    print("\nMétropoles :")

    for column, counter in value_counts.items():

        print(
            f"  {column}: {len(counter)} valeurs distinctes"
        )

        for value, count in counter.most_common(10):
            print(f"    {value}: {count:,}")

    elapsed = time.time() - start_time

    print(f"\nDurée de l'audit : {elapsed:.2f} secondes")

    # --------------------------------------------------------
    # RAPPORT STRUCTURÉ
    # --------------------------------------------------------

    report = {
        "source": source_name,
        "file": str(path),
        "file_size_bytes": file_size,
        "sha256": sha256,
        "encoding": encoding,
        "delimiter": delimiter,
        "total_rows": total_rows,
        "total_columns": len(columns),
        "columns": columns,
        "empty_values": dict(empty_counts),
        "nd_values": dict(nd_counts),
        "invalid_numeric_values": dict(invalid_numeric),
        "invalid_dates": dict(invalid_dates),
        "date_ranges": {
            column: {
                "min": (
                    str(date_min[column])
                    if date_min[column] is not None
                    else None
                ),
                "max": (
                    str(date_max[column])
                    if date_max[column] is not None
                    else None
                ),
            }
            for column in config["date_columns"]
        },
        "exact_duplicates": exact_duplicates,
        "duplicate_candidate_keys": dict(duplicate_keys),
        "distinct_values": {
            column: len(counter)
            for column, counter in value_counts.items()
        },
        "detected_numeric_types": detected_types,
        "duration_seconds": round(elapsed, 2),
    }

    return report


# ============================================================
# AUDIT GLOBAL
# ============================================================

def main():

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 70)
    print("AUDIT GLOBAL DES SOURCES DATAOPS ENERGY")
    print("=" * 70)

    reports = {}

    for source_name, config in SOURCES.items():

        reports[source_name] = audit_source(
            source_name,
            config,
        )

    report_path = (
        REPORT_DIR
        / f"csv_audit_{datetime.now():%Y%m%d_%H%M%S}.json"
    )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            reports,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print("\n" + "=" * 70)
    print("AUDIT GLOBAL TERMINÉ")
    print("=" * 70)

    for source_name, report in reports.items():

        print(
            f"{source_name}: "
            f"{report['total_rows']:,} lignes"
        )

    total_rows = sum(
        report["total_rows"]
        for report in reports.values()
    )

    print(f"\nTotal des deux sources : {total_rows:,} lignes")
    print(f"Rapport JSON : {report_path}")


if __name__ == "__main__":
    main()
