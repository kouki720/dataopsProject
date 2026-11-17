
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
    / "eco2mix"
    / "eco2mix-metropoles-tr-deduplicated.csv"
)

PIPELINE_NAME = "eco2mix_pipeline"

TABLE_NAME = "eco2mix"

WRITE_DISPOSITION = "replace"


def run():
    return run_csv_pipeline(
        pipeline_name=PIPELINE_NAME,
        csv_path=CSV_PATH,
        table_name=TABLE_NAME,
        write_disposition=WRITE_DISPOSITION,
        batch_size=BATCH_SIZE,
    )


if __name__ == "__main__":
    run()
