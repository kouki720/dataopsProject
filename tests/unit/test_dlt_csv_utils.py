
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dataops_energy.pipelines.dlt_csv_utils import (
    PROJECT_ROOT as PIPELINE_ROOT,
    get_csv_columns,
    get_duckdb_path,
)

from dataops_energy.pipelines.eco2mix_pipeline import (
    CSV_PATH as ECO2MIX_CSV,
)

from dataops_energy.pipelines.weather_pipeline import (
    CSV_PATH as WEATHER_CSV,
)


def test_project_root():
    assert PIPELINE_ROOT == PROJECT_ROOT


def test_duckdb_path():
    path = get_duckdb_path()

    assert path == PROJECT_ROOT / "warehouse" / "dev" / "dev.duckdb"
    assert path.parent.exists()


@pytest.mark.parametrize(
    "csv_path, expected_columns",
    [
        (ECO2MIX_CSV, 9),
        (WEATHER_CSV, 19),
    ],
)
def test_csv_exists_and_columns(csv_path, expected_columns):
    assert csv_path.exists()

    columns = get_csv_columns(csv_path)

    assert len(columns) == expected_columns
    assert len(columns) == len(set(columns))
