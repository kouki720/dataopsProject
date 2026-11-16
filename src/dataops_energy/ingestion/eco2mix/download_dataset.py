
from pathlib import Path
import argparse
import csv
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

import requests


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

DATASET_ID = "eco2mix-metropoles-tr"

DOWNLOAD_URL = (
    "https://odre.opendatasoft.com/api/explore/v2.1/"
    f"catalog/datasets/{DATASET_ID}/exports/csv"
)

TIME_API_URL = "https://timeapi.io/api/Time/current/zone"

PARIS_TZ = ZoneInfo("Europe/Paris")
UTC_TZ = ZoneInfo("UTC")

START_DATE = "2025-01-01T00:00:00"

OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "eco2mix"
OUTPUT_FILE = OUTPUT_DIR / f"{DATASET_ID}.csv"

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


# ============================================================
# 1. RÉCUPÉRER L'HEURE DE RÉFÉRENCE
# ============================================================

def get_reference_time():
    """
    Récupère l'heure actuelle depuis TimeAPI
    dans le fuseau Europe/Paris.
    """

    response = requests.get(
        TIME_API_URL,
        params={"timeZone": "Europe/Paris"},
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    reference_time = datetime.fromisoformat(data["dateTime"])

    # TimeAPI retourne normalement une date sans offset,
    # accompagnée du fuseau horaire demandé.
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=PARIS_TZ)
    else:
        reference_time = reference_time.astimezone(PARIS_TZ)

    return reference_time


# ============================================================
# 2. CALCULER LA FIN DE LA VEILLE
# ============================================================

def calculate_historical_end(reference_time):
    """
    Calcule la fin de la journée précédente à Paris,
    puis convertit cette date en UTC.
    """

    previous_day = reference_time.date() - timedelta(days=1)

    end_paris = datetime.combine(
        previous_day,
        time(23, 59, 59),
        tzinfo=PARIS_TZ,
    )

    end_utc = end_paris.astimezone(UTC_TZ)

    return end_paris, end_utc


# ============================================================
# 3. CONSTRUIRE LE FILTRE API
# ============================================================

def build_where_clause(end_utc):

    end_string = end_utc.replace(
        tzinfo=None
    ).isoformat(timespec="seconds")

    return (
        f"date_heure >= date'{START_DATE}' "
        f"AND date_heure <= date'{end_string}'"
    )


# ============================================================
# 4. TÉLÉCHARGER LE DATASET
# ============================================================

def download_dataset(force=False):

    # Vérifier si le fichier existe déjà
    if OUTPUT_FILE.exists() and not force:

        file_size = OUTPUT_FILE.stat().st_size

        if file_size > 0:
            print("Le dataset existe déjà.")
            print(f"Emplacement : {OUTPUT_FILE}")
            print(f"Taille : {file_size / (1024 * 1024):.2f} MB")
            print("Téléchargement ignoré.")
            print("Utilisez --force pour télécharger une nouvelle version.")
            return

    # Récupérer l'heure de référence
    print("Récupération de l'heure de référence Paris...")

    reference_time = get_reference_time()

    # Calculer la fin de la veille
    end_paris, end_utc = calculate_historical_end(reference_time)

    # Construire le filtre
    where_clause = build_where_clause(end_utc)

    # Préparer les dossiers
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    temporary_file = OUTPUT_FILE.with_suffix(".csv.part")

    params = {
        "where": where_clause,
        "delimiter": ";",
    }

    print("\n" + "=" * 60)
    print("TÉLÉCHARGEMENT HISTORIQUE ÉCO2MIX")
    print("=" * 60)

    print(f"Heure de référence Paris : {reference_time}")
    print(f"Début historique         : {START_DATE}")
    print(f"Fin historique Paris     : {end_paris}")
    print(f"Fin historique UTC       : {end_utc}")

    print("\nFiltre API :")
    print(where_clause)

    print("\nTéléchargement du dataset...")
    print(f"Dataset : {DATASET_ID}")
    print(f"URL : {DOWNLOAD_URL}")

    try:

        with requests.get(
            DOWNLOAD_URL,
            params=params,
            timeout=(30, 600),
            stream=True,
        ) as response:

            print("Statut HTTP :", response.status_code)

            response.raise_for_status()

            with temporary_file.open("wb") as file:

                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):

                    if chunk:
                        file.write(chunk)

        # Vérifier que le fichier n'est pas vide
        if (
            not temporary_file.exists()
            or temporary_file.stat().st_size == 0
        ):
            raise ValueError("Le fichier téléchargé est vide.")

        # Vérifier la structure du CSV
        with temporary_file.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:

            reader = csv.reader(file, delimiter=";")

            columns = next(reader, None)

        if not columns:
            raise ValueError("Le CSV ne contient aucun en-tête.")

        actual_columns = set(columns)

        missing_columns = REQUIRED_COLUMNS - actual_columns

        if missing_columns:
            raise ValueError(
                f"Colonnes indispensables absentes : "
                f"{sorted(missing_columns)}"
            )

        # Remplacer le fichier uniquement après validation
        temporary_file.replace(OUTPUT_FILE)

        file_size = OUTPUT_FILE.stat().st_size

        print("\n" + "=" * 60)
        print("TÉLÉCHARGEMENT TERMINÉ")
        print("=" * 60)

        print(f"Fichier : {OUTPUT_FILE}")
        print(f"Taille : {file_size / (1024 * 1024):.2f} MB")
        print(f"Nombre de colonnes : {len(columns)}")
        print("Structure CSV : valide.")

    except Exception as error:

        temporary_file.unlink(missing_ok=True)

        print(f"\nErreur pendant le téléchargement : {error}")

        raise


# ============================================================
# 5. POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Téléchargement historique éCO2mix Métropoles"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Télécharger à nouveau même si le fichier existe",
    )

    args = parser.parse_args()

    download_dataset(force=args.force)
