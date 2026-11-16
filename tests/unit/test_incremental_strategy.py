
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TIME_API_URL = "https://timeapi.io/api/Time/current/zone"

API_URL = (
    "https://odre.opendatasoft.com/api/explore/v2.1/"
    "catalog/datasets/eco2mix-metropoles-tr/records"
)

PARIS_TZ = ZoneInfo("Europe/Paris")
UTC_TZ = ZoneInfo("UTC")

START_DATE = "2024-01-01T00:00:00"


def get_paris_reference_time():
    """Récupère l'heure de référence depuis TimeAPI."""

    response = requests.get(
        TIME_API_URL,
        params={"timeZone": "Europe/Paris"},
        timeout=15,
    )
    response.raise_for_status()

    data = response.json()

    paris_time = datetime.fromisoformat(
        data["dateTime"]
    ).replace(tzinfo=PARIS_TZ)

    return paris_time


def get_previous_day_end_utc(paris_time):
    """Calcule la fin de la veille en heure UTC."""

    previous_day = paris_time.date() - timedelta(days=1)

    paris_end = datetime(
        previous_day.year,
        previous_day.month,
        previous_day.day,
        23,
        59,
        59,
        tzinfo=PARIS_TZ,
    )

    return paris_end.astimezone(UTC_TZ)


def test_date_range(start_date, end_date_utc):
    """Teste le filtre entre deux dates."""

    end_string = end_date_utc.replace(
        tzinfo=None
    ).isoformat(timespec="seconds")

    where_clause = (
        f"date_heure >= date'{start_date}' "
        f"AND date_heure <= date'{end_string}'"
    )

    params = {
        "select": (
            "code_insee_epci,libelle_metropole,nature,"
            "date_heure,consommation,production,echanges_physiques"
        ),
        "where": where_clause,
        "order_by": "date_heure DESC",
        "limit": 5,
    }

    print("\nFiltre utilisé :")
    print(where_clause)

    response = requests.get(
        API_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()

    print("\nNombre total de lignes correspondant au filtre :")
    print(data.get("total_count"))

    print("\nÉchantillon des 5 dernières lignes :")

    for record in data.get("results", []):
        print(record)


def test_non_null_filter(start_date, end_date_utc):
    """Vérifie si l'API accepte le filtre sur les mesures non nulles."""

    end_string = end_date_utc.replace(
        tzinfo=None
    ).isoformat(timespec="seconds")

    where_clause = (
        f"date_heure >= date'{start_date}' "
        f"AND date_heure <= date'{end_string}' "
        "AND (consommation IS NOT NULL "
        "OR production IS NOT NULL "
        "OR echanges_physiques IS NOT NULL)"
    )

    params = {
        "select": (
            "code_insee_epci,libelle_metropole,nature,"
            "date_heure,consommation,production,echanges_physiques"
        ),
        "where": where_clause,
        "order_by": "date_heure DESC",
        "limit": 5,
    }

    print("\n\nTest du filtre des mesures non nulles :")
    print(where_clause)

    response = requests.get(
        API_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()

    print("\nNombre total de lignes avec au moins une mesure non nulle :")
    print(data.get("total_count"))

    print("\nÉchantillon :")

    for record in data.get("results", []):
        print(record)


def main():
    print("=" * 60)
    print("TEST DE LA STRATÉGIE D'INGESTION ÉCO2MIX")
    print("=" * 60)

    paris_time = get_paris_reference_time()
    end_date_utc = get_previous_day_end_utc(paris_time)

    print("\nHeure de référence Paris :", paris_time)
    print("Début historique         :", START_DATE)
    print("Fin historique UTC       :", end_date_utc)
    print(
        "Fin historique Paris     :",
        end_date_utc.astimezone(PARIS_TZ),
    )

    test_date_range(START_DATE, end_date_utc)
    test_non_null_filter(START_DATE, end_date_utc)


if __name__ == "__main__":
    main()
