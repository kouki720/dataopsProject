
import sys
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[2]

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


from dataops_energy.pipelines.dlt_csv_utils import (
    PROJECT_ROOT,
    BATCH_SIZE,
    run_csv_pipeline,
)


CSV_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "weather"
    / "weather_france-deduplicated.csv"
)

PIPELINE_NAME = "weather_pipeline"

TABLE_NAME = "weather"

WRITE_DISPOSITION = "replace"


def run():
    """Lance le chargement des données météo dans DuckDB."""

    return run_csv_pipeline(
        pipeline_name=PIPELINE_NAME,
        csv_path=CSV_PATH,
        table_name=TABLE_NAME,
        write_disposition=WRITE_DISPOSITION,
        batch_size=BATCH_SIZE,
    )


if __name__ == "__main__":
    run()
