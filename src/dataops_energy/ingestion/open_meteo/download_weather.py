
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import pandas as pd
import requests

from config import (
    ARCHIVE_API_URL,
    HOURLY_VARIABLES,
    METROPOLES,
    OUTPUT_DIR,
    OUTPUT_FILE,
    TEMPORARY_FILE,
    START_DATE,
    TIMEZONE,
    TEMPERATURE_UNIT,
    WIND_SPEED_UNIT,
    PRECIPITATION_UNIT,
)


# ============================================================
# CONFIGURATION
# ============================================================

MODEL = "era5"

REQUEST_TIMEOUT = (30, 240)

MAX_RETRIES = 6
INITIAL_RETRY_DELAY = 60
MAX_RETRY_DELAY = 300

DELAY_BETWEEN_REQUESTS = 5

# Nombre maximum de jours à remonter pour trouver
# la dernière journée disponible dans Open-Meteo.
MAX_LOOKBACK_DAYS = 15

METADATA_COLUMNS = [
    "code_insee_epci",
    "libelle_metropole",
    "latitude",
    "longitude",
    "date_heure",
]

OUTPUT_COLUMNS = METADATA_COLUMNS + HOURLY_VARIABLES


# ============================================================
# GESTION DES ERREURS HTTP
# ============================================================

def get_retry_delay(response, attempt):
    """Détermine le délai avant une nouvelle tentative."""

    retry_after = response.headers.get("Retry-After")

    if retry_after:
        try:
            return min(
                max(float(retry_after), 1),
                MAX_RETRY_DELAY,
            )
        except ValueError:
            try:
                retry_date = parsedate_to_datetime(retry_after)

                if retry_date.tzinfo is None:
                    retry_date = retry_date.replace(
                        tzinfo=timezone.utc
                    )

                delay = (
                    retry_date - datetime.now(timezone.utc)
                ).total_seconds()

                return min(
                    max(delay, 1),
                    MAX_RETRY_DELAY,
                )

            except (TypeError, ValueError, OverflowError):
                pass

    return min(
        INITIAL_RETRY_DELAY * (2 ** attempt),
        MAX_RETRY_DELAY,
    )


def request_with_retry(session, params, metropole):
    """Effectue une requête avec gestion des erreurs temporaires."""

    name = metropole["libelle_metropole"]

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = session.get(
                ARCHIVE_API_URL,
                params=params,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 200:
                return response

            if (
                response.status_code == 429
                or response.status_code >= 500
            ):
                if attempt >= MAX_RETRIES:
                    response.raise_for_status()

                delay = get_retry_delay(response, attempt)

                print(
                    f"\n[ATTENTION] HTTP {response.status_code} "
                    f"pour {name}."
                )

                print(
                    f"Nouvelle tentative dans {delay:.0f} secondes "
                    f"({attempt + 1}/{MAX_RETRIES})..."
                )

                response.close()
                time.sleep(delay)
                continue

            response.raise_for_status()

        except requests.exceptions.Timeout:
            if attempt >= MAX_RETRIES:
                raise

            delay = min(
                INITIAL_RETRY_DELAY * (2 ** attempt),
                MAX_RETRY_DELAY,
            )

            print(f"\n[ATTENTION] Timeout pour {name}.")
            print(f"Nouvelle tentative dans {delay} secondes...")

            time.sleep(delay)

        except requests.exceptions.ConnectionError:
            if attempt >= MAX_RETRIES:
                raise

            delay = min(
                INITIAL_RETRY_DELAY * (2 ** attempt),
                MAX_RETRY_DELAY,
            )

            print(f"\n[ATTENTION] Problème de connexion pour {name}.")
            print(f"Nouvelle tentative dans {delay} secondes...")

            time.sleep(delay)

    raise RuntimeError(
        f"Échec définitif du téléchargement pour {name}."
    )


# ============================================================
# DÉTECTION DE LA DERNIÈRE DATE DISPONIBLE
# ============================================================

def probe_available_date(session, metropole, target_date):
    """
    Vérifie si Open-Meteo possède des données pour une journée.

    Retourne True si des données horaires sont disponibles.
    """

    params = {
        "latitude": metropole["latitude"],
        "longitude": metropole["longitude"],
        "start_date": target_date.isoformat(),
        "end_date": target_date.isoformat(),
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": TIMEZONE,
        "temperature_unit": TEMPERATURE_UNIT,
        "wind_speed_unit": WIND_SPEED_UNIT,
        "precipitation_unit": PRECIPITATION_UNIT,
        "models": MODEL,
    }

    try:
        response = request_with_retry(
            session,
            params,
            metropole,
        )

        try:
            data = response.json()
        finally:
            response.close()

        if data.get("error"):
            return False

        hourly = data.get("hourly", {})

        return bool(hourly and hourly.get("time"))

    except requests.exceptions.HTTPError as error:
        status_code = error.response.status_code

        # Une date non disponible peut produire une erreur client.
        if status_code in (400, 404, 422):
            return False

        raise


def get_latest_available_date(session):
    """
    Recherche la dernière journée disponible dans Open-Meteo.

    On commence aujourd'hui et on remonte progressivement
    jusqu'à trouver une journée avec des données.
    """

    today = datetime.now(timezone.utc).date()

    reference_metropole = METROPOLES[0]

    print("\nRecherche de la dernière date météo disponible...")
    print(f"Métropole de référence : "
          f"{reference_metropole['libelle_metropole']}")
    print(f"Date actuelle UTC      : {today}")

    for days_back in range(MAX_LOOKBACK_DAYS + 1):

        candidate_date = today - timedelta(days=days_back)

        print(
            f"Vérification : {candidate_date}...",
            end=" ",
            flush=True,
        )

        available = probe_available_date(
            session,
            reference_metropole,
            candidate_date,
        )

        if available:
            print("Données disponibles.")

            print(
                f"\nDernière date disponible détectée : "
                f"{candidate_date}"
            )

            return candidate_date

        print("Pas encore disponible.")

    raise RuntimeError(
        "Impossible de trouver une date météo disponible "
        f"dans les {MAX_LOOKBACK_DAYS + 1} derniers jours."
    )


# ============================================================
# APPEL OPEN-METEO
# ============================================================

def get_weather_data(session, metropole, end_date):
    """Télécharge les données horaires d'une métropole."""

    params = {
        "latitude": metropole["latitude"],
        "longitude": metropole["longitude"],
        "start_date": START_DATE,
        "end_date": end_date.isoformat(),
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": TIMEZONE,
        "temperature_unit": TEMPERATURE_UNIT,
        "wind_speed_unit": WIND_SPEED_UNIT,
        "precipitation_unit": PRECIPITATION_UNIT,
        "models": MODEL,
    }

    response = request_with_retry(
        session,
        params,
        metropole,
    )

    try:
        data = response.json()
    finally:
        response.close()

    if data.get("error"):
        raise RuntimeError(
            f"Erreur Open-Meteo : {data.get('reason')}"
        )

    hourly = data.get("hourly")

    if not hourly or not hourly.get("time"):
        raise ValueError(
            f"Aucune donnée horaire reçue pour "
            f"{metropole['libelle_metropole']}"
        )

    timestamps = hourly["time"]

    records = []

    for index, timestamp in enumerate(timestamps):

        record = {
            "code_insee_epci": metropole["code_insee_epci"],
            "libelle_metropole": metropole["libelle_metropole"],
            "latitude": metropole["latitude"],
            "longitude": metropole["longitude"],
            "date_heure": timestamp,
        }

        for variable in HOURLY_VARIABLES:

            values = hourly.get(variable, [])

            record[variable] = (
                values[index]
                if index < len(values)
                else None
            )

        records.append(record)

    return records


# ============================================================
# VALIDATION
# ============================================================

def validate_dataset(df, end_date):

    print("\nValidation du dataset...")

    if df.empty:
        raise ValueError("Le dataset météo est vide.")

    missing_columns = set(OUTPUT_COLUMNS) - set(df.columns)

    if missing_columns:
        raise ValueError(
            f"Colonnes manquantes : {missing_columns}"
        )

    df["code_insee_epci"] = (
        df["code_insee_epci"].astype(str)
    )

    df["date_heure"] = pd.to_datetime(
        df["date_heure"],
        errors="coerce",
        utc=True,
    )

    if df["date_heure"].isna().any():
        raise ValueError(
            "Des dates invalides ont été détectées."
        )

    duplicates = df.duplicated(
        subset=["code_insee_epci", "date_heure"]
    ).sum()

    if duplicates:
        raise ValueError(
            f"{duplicates} doublons détectés."
        )

    received_codes = set(df["code_insee_epci"])

    expected_codes = {
        str(m["code_insee_epci"])
        for m in METROPOLES
    }

    if received_codes != expected_codes:
        raise ValueError(
            "La liste des métropoles reçues ne correspond "
            "pas à la configuration."
        )

    counts = df.groupby("code_insee_epci").size()

    if len(counts) != len(METROPOLES):
        raise ValueError(
            "Certaines métropoles ne possèdent aucune donnée."
        )

    if df["date_heure"].max().date() > end_date:
        raise ValueError(
            "Le dataset contient des dates postérieures "
            "à la date demandée."
        )

    print("Colonnes             : OK")
    print("Dates                : OK")
    print("Doublons             : 0")
    print(f"Métropoles           : {len(counts)}")
    print("Lignes par métropole :")

    for metropole in METROPOLES:

        code = str(metropole["code_insee_epci"])

        metro_df = df[df["code_insee_epci"] == code]

        print(
            f"  {metropole['libelle_metropole']}: "
            f"{counts[code]:,} lignes | "
            f"Dernière date : {metro_df['date_heure'].max()}"
        )


# ============================================================
# TÉLÉCHARGEMENT HISTORIQUE
# ============================================================

def download_weather():

    print("=" * 65)
    print("TÉLÉCHARGEMENT HISTORIQUE OPEN-METEO")
    print("=" * 65)

    # --------------------------------------------------------
    # PROTECTION DU FICHIER EXISTANT
    # --------------------------------------------------------

    if OUTPUT_FILE.exists():

        print("\n[ARRÊT] Le fichier météo existe déjà :")
        print(OUTPUT_FILE)

        print(
            "\nAucune donnée n'a été téléchargée et "
            "le fichier existant n'a pas été modifié."
        )

        print(
            "\nSi tu souhaites refaire un téléchargement historique "
            "complet, déplace ou supprime d'abord ce fichier."
        )

        return

    # --------------------------------------------------------
    # PRÉPARATION
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    session = requests.Session()

    session.headers.update({
        "User-Agent": "DataOps-Energy/1.0"
    })

    try:

        # ----------------------------------------------------
        # DÉTECTION DE LA DATE DISPONIBLE
        # ----------------------------------------------------

        end_date = get_latest_available_date(session)

        if end_date < datetime.fromisoformat(START_DATE).date():
            raise ValueError(
                "La date disponible précède la date de début."
            )

        # ----------------------------------------------------
        # TÉLÉCHARGEMENT DES 21 MÉTROPOLES
        # ----------------------------------------------------

        all_records = []

        for index, metropole in enumerate(
            METROPOLES,
            start=1,
        ):

            name = metropole["libelle_metropole"]

            print("\n" + "-" * 60)
            print(f"[{index}/{len(METROPOLES)}] {name}")

            records = get_weather_data(
                session,
                metropole,
                end_date,
            )

            print(f"Lignes reçues : {len(records):,}")

            all_records.extend(records)

            if index < len(METROPOLES):

                print(
                    f"Pause de {DELAY_BETWEEN_REQUESTS} secondes..."
                )

                time.sleep(DELAY_BETWEEN_REQUESTS)

    finally:
        session.close()

    # --------------------------------------------------------
    # ASSEMBLAGE
    # --------------------------------------------------------

    print("\nAssemblage des données...")

    df = pd.DataFrame(
        all_records,
        columns=OUTPUT_COLUMNS,
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    validate_dataset(df, end_date)

    df = df.sort_values(
        ["code_insee_epci", "date_heure"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # ÉCRITURE TEMPORAIRE
    # --------------------------------------------------------

    print("\nÉcriture du fichier temporaire...")

    try:

        df.to_csv(
            TEMPORARY_FILE,
            sep=";",
            index=False,
            encoding="utf-8-sig",
        )

        check_df = pd.read_csv(
            TEMPORARY_FILE,
            sep=";",
            usecols=OUTPUT_COLUMNS,
            encoding="utf-8-sig",
            dtype={
                "code_insee_epci": str
            },
        )

        if len(check_df) != len(df):
            raise ValueError(
                "Le nombre de lignes après écriture est incorrect."
            )

        check_codes = set(check_df["code_insee_epci"])

        expected_codes = {
            str(m["code_insee_epci"])
            for m in METROPOLES
        }

        if check_codes != expected_codes:
            raise ValueError(
                "La validation des codes après écriture a échoué."
            )

        if OUTPUT_FILE.exists():
            raise FileExistsError(
                "Le fichier final existe déjà. "
                "Il ne sera pas écrasé."
            )

        TEMPORARY_FILE.replace(OUTPUT_FILE)

    except Exception:

        if TEMPORARY_FILE.exists():
            TEMPORARY_FILE.unlink()

        raise

    # --------------------------------------------------------
    # RÉSULTAT FINAL
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print("TÉLÉCHARGEMENT TERMINÉ")
    print("=" * 65)

    print(
        f"Métropoles       : "
        f"{df['code_insee_epci'].nunique()}"
    )

    print(
        f"Nombre de lignes : {len(df):,}"
    )

    print(
        f"Nombre de colonnes : {len(df.columns)}"
    )

    print(
        f"Première date    : {df['date_heure'].min()}"
    )

    print(
        f"Dernière date    : {df['date_heure'].max()}"
    )

    print(
        f"Fichier          : {OUTPUT_FILE}"
    )

    print(
        f"Taille           : "
        f"{OUTPUT_FILE.stat().st_size / (1024 ** 2):.2f} MB"
    )


# ============================================================
# EXÉCUTION
# ============================================================

if __name__ == "__main__":
    download_weather()
