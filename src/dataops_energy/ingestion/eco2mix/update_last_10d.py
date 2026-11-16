
from datetime import timedelta, datetime, time

from eco2mix_update_common import (
    PARIS_TZ,
    UTC_TZ,
    get_reference_time,
    get_latest_dataset_date,
    get_api_records,
    update_csv,
    display_result,
)


def update_last_48h():

    print("=" * 60)
    print("RÉCONCILIATION DES 10 days")
    print("=" * 60)

    # 1. Heure de référence
    reference_time = get_reference_time()

    # 2. Fin de la veille à Paris
    previous_day = reference_time.date() - timedelta(days=1)

    end_paris = datetime.combine(
        previous_day,
        time(23, 59, 59),
        tzinfo=PARIS_TZ,
    )

    end_utc = end_paris.astimezone(UTC_TZ)

    # 3. Dernière date du dataset
    latest_date = get_latest_dataset_date()

    # 4. Début de la fenêtre : 48 heures avant
    start_utc = latest_date - timedelta(days=10)

    historical_start = datetime(
        2024, 1, 1, tzinfo=UTC_TZ
    )

    start_utc = max(start_utc, historical_start)

    print(f"\nHeure Paris          : {reference_time}")
    print(f"Dernière date CSV    : {latest_date}")
    print(f"Début fenêtre UTC    : {start_utc}")
    print(f"Fin fenêtre Paris    : {end_paris}")
    print(f"Fin fenêtre UTC      : {end_utc}")

    if start_utc >= end_utc:
        print("\nAucune période historique à actualiser.")
        return

    # 5. API
    print("\nRécupération des données historiques...")

    api_records = get_api_records(
        start_utc,
        end_utc,
    )

    print(f"\nNombre de lignes API : {len(api_records):,}")

    # 6. Fusion
    print("\nFusion avec le dataset existant...")

    result = update_csv(
        api_records,
        start_utc,
        end_utc,
    )

    display_result(result)


if __name__ == "__main__":
    update_last_48h()
