
import requests
import json


API_URL = (
    "https://odre.opendatasoft.com/api/explore/v2.1/"
    "catalog/datasets/eco2mix-metropoles-tr/records"
)


def inspect_api():

    params = {
        "limit": 3,
        "order_by": "date_heure DESC",
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    print("Nombre total :", data["total_count"])

    for index, record in enumerate(data["results"], start=1):

        print(f"\n{'=' * 50}")
        print(f"ENREGISTREMENT {index}")
        print("=" * 50)

        for column, value in record.items():
            print(f"{column}: {value}")

    print("\nInspection terminée.")


if __name__ == "__main__":
    inspect_api()
