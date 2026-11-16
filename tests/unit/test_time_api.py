
import requests
from datetime import datetime
from zoneinfo import ZoneInfo


TIME_API_URL = (
    "https://timeapi.io/api/Time/current/zone"
)

ECO2MIX_API_URL = (
    "https://odre.opendatasoft.com/api/explore/v2.1/"
    "catalog/datasets/eco2mix-metropoles-tr/records"
)


def get_reference_time():
    response = requests.get(
        TIME_API_URL,
        params={"timeZone": "Europe/Paris"},
        timeout=15,
    )
    response.raise_for_status()

    data = response.json()

    paris_time = datetime.fromisoformat(
        data["dateTime"]
    ).replace(tzinfo=ZoneInfo("Europe/Paris"))

    return paris_time.astimezone(ZoneInfo("UTC"))


def get_latest_records(reference_time_utc):
    reference_string = (
        reference_time_utc
        .replace(tzinfo=None)
        .isoformat(timespec="seconds")
    )

    params = {
        "select": (
            "code_insee_epci,libelle_metropole,nature,"
            "date_heure,consommation,production,"
            "echanges_physiques"
        ),
        "where": (
            f"date_heure <= date'{reference_string}'"
        ),
        "order_by": "date_heure DESC",
        "limit": 10,
    }

    response = requests.get(
        ECO2MIX_API_URL,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    return response.json()


if __name__ == "__main__":

    # 1. Heure de référence externe
    reference_time = get_reference_time()

    print("\n===== HEURE DE REFERENCE =====")
    print("UTC :", reference_time)
    print(
        "Paris :",
        reference_time.astimezone(
            ZoneInfo("Europe/Paris")
        )
    )

    # 2. Interrogation de l'API éCO2mix
    data = get_latest_records(reference_time)

    print("\n===== RESULTAT ECO2MIX =====")
    print("Nombre total de résultats :", data["total_count"])
    print("Nombre de lignes affichées :", len(data["results"]))

    # 3. Affichage des dernières données
    for index, record in enumerate(data["results"], start=1):
        print(f"\n--- Enregistrement {index} ---")

        for key, value in record.items():
            print(f"{key}: {value}")
