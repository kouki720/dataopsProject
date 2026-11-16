
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
# SESSION HTTP
# ============================================================

def create_session():

    session = requests.Session()

    session.headers.update({
        "User-Agent": "DataOps-Energy/1.0"
    })

    return session


# ============================================================
# GESTION DES ERREURS HTTP
# ============================================================

def get_retry_delay(response, attempt):

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

            print(f"\n[ATTENTION] Connexion impossible pour {name}.")
            print(f"Nouvelle tentative dans {delay} secondes...")

            time.sleep(delay)

    raise RuntimeError(
        f"Échec définitif de la requête pour {name}."
    )


# ============================================================
# DÉTECTION DE LA DERNIÈRE DATE DISPONIBLE
# ============================================================

def probe_available_date(session, metropole, target_date):

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

        return bool(
            hourly and hourly.get("time")
        )

    except requests.exceptions.HTTPError as error:

        status_code = error.response.status_code

        if status_code in (400, 404, 422):
            return False

        raise


def get_latest_available_date(session):

    today = datetime.now(timezone.utc).date()

    reference_metropole = METROPOLES[0]

    print("\nRecherche de la dernière journée disponible...")
    print(
        f"Métropole de référence : "
        f"{reference_metropole['libelle_metropole']}"
    )
    print(f"Date actuelle UTC : {today}")

    for days_back in range(MAX_LOOKBACK_DAYS + 1):

        candidate_date = today - timedelta(days=days_back)

        print(
            f"Vérification de {candidate_date}...",
            end=" ",
            flush=True,
        )

        available = probe_available_date(
            session,
            reference_metropole,
            candidate_date,
        )

        if available:

            print("Disponible.")

            print(
                f"Dernière date disponible : {candidate_date}"
            )

            return candidate_date

        print("Non disponible.")

    raise RuntimeError(
        "Aucune journée disponible trouvée dans la période "
        f"des {MAX_LOOKBACK_DAYS + 1} derniers jours."
    )


# ============================================================
# LECTURE DU DATASET EXISTANT
# ============================================================

def load_existing_dataset():

    if not OUTPUT_FILE.exists():

        raise FileNotFoundError(
            f"Dataset météo introuvable : {OUTPUT_FILE}\n"
            "Lance d'abord download_weather.py pour créer "
            "le dataset initial."
        )

    print("\nLecture du dataset météo existant...")

    df = pd.read_csv(
        OUTPUT_FILE,
        sep=";",
        encoding="utf-8-sig",
        dtype={
            "code_insee_epci": str
        },
    )

    missing_columns = set(OUTPUT_COLUMNS) - set(df.columns)

    if missing_columns:

        raise ValueError(
            f"Colonnes manquantes dans le dataset : "
            f"{missing_columns}"
        )

    df = df[OUTPUT_COLUMNS].copy()

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
            "Le dataset existant contient des dates invalides."
        )

    if df.empty:
        raise ValueError(
            "Le dataset météo existant est vide."
        )

    return df


# ============================================================
# DERNIÈRE DATE PAR MÉTROPOLE
# ============================================================

def get_last_dates_by_metropole(df):

    print("\nDernières dates présentes dans le fichier :")

    last_dates = {}

    for metropole in METROPOLES:

        code = str(metropole["code_insee_epci"])

        metro_df = df[
            df["code_insee_epci"] == code
        ]

        if metro_df.empty:

            raise ValueError(
                f"Aucune donnée existante pour "
                f"{metropole['libelle_metropole']} ({code})."
            )

        last_timestamp = metro_df["date_heure"].max()

        last_date = last_timestamp.date()

        last_dates[code] = last_date

        print(
            f"  {metropole['libelle_metropole']} : "
            f"{last_timestamp}"
        )

    return last_dates


# ============================================================
# TÉLÉCHARGEMENT DES NOUVELLES DONNÉES
# ============================================================

def download_metropole_weather(
    session,
    metropole,
    start_date,
    end_date,
):

    if start_date > end_date:
        return []

    params = {
        "latitude": metropole["latitude"],
        "longitude": metropole["longitude"],
        "start_date": start_date.isoformat(),
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
            f"Erreur Open-Meteo pour "
            f"{metropole['libelle_metropole']} : "
            f"{data.get('reason')}"
        )

    hourly = data.get("hourly")

    if not hourly or not hourly.get("time"):
        return []

    timestamps = hourly["time"]

    records = []

    for index, timestamp in enumerate(timestamps):

        record = {
            "code_insee_epci": str(
                metropole["code_insee_epci"]
            ),
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

    print("\nValidation du dataset fusionné...")

    if df.empty:
        raise ValueError("Le dataset fusionné est vide.")

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
        subset=[
            "code_insee_epci",
            "date_heure",
        ]
    ).sum()

    if duplicates:

        raise ValueError(
            f"{duplicates} doublons détectés."
        )

    expected_codes = {
        str(m["code_insee_epci"])
        for m in METROPOLES
    }

    received_codes = set(df["code_insee_epci"])

    if received_codes != expected_codes:

        raise ValueError(
            "Les codes des métropoles ne correspondent "
            "pas à la configuration."
        )

    if df["date_heure"].max().date() > end_date:

        raise ValueError(
            "Le dataset contient des dates postérieures "
            "à la date de fin demandée."
        )

    print("Colonnes : OK")
    print("Dates : OK")
    print("Doublons : 0")
    print(f"Métropoles : {len(received_codes)}")
    print(f"Nombre de lignes : {len(df):,}")

    for metropole in METROPOLES:

        code = str(metropole["code_insee_epci"])

        metro_df = df[
            df["code_insee_epci"] == code
        ]

        if metro_df.empty:

            raise ValueError(
                f"Aucune donnée pour "
                f"{metropole['libelle_metropole']}."
            )

        print(
            f"  {metropole['libelle_metropole']} : "
            f"{len(metro_df):,} lignes | "
            f"Dernière date : "
            f"{metro_df['date_heure'].max()}"
        )


# ============================================================
# ÉCRITURE SÉCURISÉE
# ============================================================

def save_dataset(df):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

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
            encoding="utf-8-sig",
            dtype={
                "code_insee_epci": str
            },
        )

        if len(check_df) != len(df):

            raise ValueError(
                "Le nombre de lignes après écriture "
                "ne correspond pas."
            )

        if list(check_df.columns) != OUTPUT_COLUMNS:

            raise ValueError(
                "Les colonnes après écriture "
                "ne correspondent pas."
            )

        # Le fichier original est remplacé seulement
        # après validation du fichier temporaire.
        TEMPORARY_FILE.replace(OUTPUT_FILE)

    except Exception:

        if TEMPORARY_FILE.exists():
            TEMPORARY_FILE.unlink()

        raise


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def update_weather():

    print("=" * 65)
    print("MISE À JOUR INCRÉMENTALE OPEN-METEO")
    print("=" * 65)

    session = create_session()

    try:

        # ----------------------------------------------------
        # 1. LECTURE DU FICHIER EXISTANT
        # ----------------------------------------------------

        existing_df = load_existing_dataset()

        print(
            f"\nLignes existantes : "
            f"{len(existing_df):,}"
        )

        # ----------------------------------------------------
        # 2. DERNIÈRE DATE PAR MÉTROPOLE
        # ----------------------------------------------------

        last_dates = get_last_dates_by_metropole(
            existing_df
        )

        # ----------------------------------------------------
        # 3. DERNIÈRE DATE DISPONIBLE DANS L'API
        # ----------------------------------------------------

        available_date = get_latest_available_date(
            session
        )

        # ----------------------------------------------------
        # 4. TÉLÉCHARGEMENT INCRÉMENTAL
        # ----------------------------------------------------

        new_records = []

        for index, metropole in enumerate(
            METROPOLES,
            start=1,
        ):

            code = str(metropole["code_insee_epci"])

            name = metropole["libelle_metropole"]

            # On repart de la dernière journée enregistrée
            # pour compléter une éventuelle journée partielle.
            start_date = last_dates[code]

            end_date = available_date

            print("\n" + "-" * 60)

            print(
                f"[{index}/{len(METROPOLES)}] {name}"
            )

            print(f"Dernière date enregistrée : {start_date}")
            print(f"Début de récupération      : {start_date}")
            print(f"Fin de récupération        : {end_date}")

            if start_date > end_date:

                print(
                    "Aucune nouvelle période disponible "
                    "pour cette métropole."
                )

                continue

            records = download_metropole_weather(
                session,
                metropole,
                start_date,
                end_date,
            )

            print(
                f"Nouvelles lignes reçues : {len(records):,}"
            )

            new_records.extend(records)

            if index < len(METROPOLES):

                time.sleep(DELAY_BETWEEN_REQUESTS)

    finally:
        session.close()

    # --------------------------------------------------------
    # 5. AUCUNE NOUVELLE DONNÉE
    # --------------------------------------------------------

    if not new_records:

        print("\nAucune nouvelle donnée météo disponible.")
        print("Le fichier existant reste inchangé.")

        return

    # --------------------------------------------------------
    # 6. FUSION
    # --------------------------------------------------------

    print("\nFusion des anciennes et nouvelles données...")

    new_df = pd.DataFrame(
        new_records,
        columns=OUTPUT_COLUMNS,
    )

    combined_df = pd.concat(
        [
            existing_df,
            new_df,
        ],
        ignore_index=True,
    )

    combined_df["code_insee_epci"] = (
        combined_df["code_insee_epci"].astype(str)
    )

    combined_df["date_heure"] = pd.to_datetime(
        combined_df["date_heure"],
        errors="coerce",
        utc=True,
    )

    # Les nouvelles données remplacent les anciennes
    # pour une même métropole et une même heure.
    combined_df = combined_df.drop_duplicates(
        subset=[
            "code_insee_epci",
            "date_heure",
        ],
        keep="last",
    )

    combined_df = combined_df.sort_values(
        [
            "code_insee_epci",
            "date_heure",
        ]
    ).reset_index(drop=True)

    combined_df = combined_df[OUTPUT_COLUMNS]

    # --------------------------------------------------------
    # 7. VALIDATION
    # --------------------------------------------------------

    validate_dataset(
        combined_df,
        available_date,
    )

    # --------------------------------------------------------
    # 8. SAUVEGARDE
    # --------------------------------------------------------

    save_dataset(combined_df)

    # --------------------------------------------------------
    # 9. RÉSULTAT
    # --------------------------------------------------------

    print("\n" + "=" * 65)
    print("MISE À JOUR TERMINÉE")
    print("=" * 65)

    print(
        f"Anciennes lignes : {len(existing_df):,}"
    )

    print(
        f"Nouvelles lignes reçues : {len(new_df):,}"
    )

    print(
        f"Lignes finales : {len(combined_df):,}"
    )

    print(
        f"Dernière date disponible API : {available_date}"
    )

    print(
        f"Dernière date du fichier : "
        f"{combined_df['date_heure'].max()}"
    )

    print(
        f"Fichier mis à jour : {OUTPUT_FILE}"
    )

    print(
        f"Taille finale : "
        f"{OUTPUT_FILE.stat().st_size / (1024 ** 2):.2f} MB"
    )


# ============================================================
# EXÉCUTION
# ============================================================

if __name__ == "__main__":
    update_weather()
