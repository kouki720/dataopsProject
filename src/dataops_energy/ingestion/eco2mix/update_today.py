
from datetime import datetime, time

from eco2mix_update_common import (
    PARIS_TZ,
    UTC_TZ,
    get_reference_time,
    get_latest_dataset_date,
    get_api_records,
    update_csv,
    display_result,
)


def update_today():

    print("=" * 60)
    print("INGESTION DES DONNÉES DU JOUR")
    print("=" * 60)

    # 1. Heure actuelle de Paris
    reference_time = get_reference_time()

    # 2. Heure actuelle en UTC
    end_utc = reference_time.astimezone(
        UTC_TZ
    ).replace(microsecond=0)

    # 3. Minuit aujourd'hui à Paris
    today_start_paris = datetime.combine(
        reference_time.date(),
        time(0, 0, 0),
        tzinfo=PARIS_TZ,
    )

    today_start_utc = today_start_paris.astimezone(
        UTC_TZ
    )

    # 4. Dernière date présente dans le dataset
    latest_date = get_latest_dataset_date()

    # 5. Comparer la dernière date avec minuit
    # On reprend la dernière date si elle est déjà dans la journée.
    start_utc = max(
        latest_date,
        today_start_utc,
    )

    print(f"\nHeure actuelle Paris : {reference_time}")
    print(f"Heure actuelle UTC   : {end_utc}")
    print(f"Minuit Paris         : {today_start_paris}")
    print(f"Minuit UTC           : {today_start_utc}")
    print(f"Dernière date CSV    : {latest_date}")
    print(f"Début récupération   : {start_utc}")
    print(f"Fin récupération     : {end_utc}")

    if start_utc >= end_utc:
        print("\nAucune nouvelle période à récupérer.")
        return

    # 6. Récupérer les données du jour
    print("\nRécupération des données du jour depuis l'API...")

    api_records = get_api_records(
        start_utc,
        end_utc,
    )

    print(f"\nNombre de lignes API : {len(api_records):,}")

    # 7. Fusionner avec le dataset
    print("\nFusion avec le dataset existant...")

    result = update_csv(
        api_records,
        start_utc,
        end_utc,
    )

    display_result(result)


if __name__ == "__main__":
    update_today()
