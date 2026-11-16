
from pathlib import Path


# ============================================================
# CHEMINS DU PROJET
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

ENERGY_DATASET = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "eco2mix"
    / "eco2mix-metropoles-tr.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "open_meteo"
)

OUTPUT_FILE = OUTPUT_DIR / "weather_france.csv"
TEMPORARY_FILE = OUTPUT_DIR / "weather_france.csv.part"


# ============================================================
# CONFIGURATION OPEN-METEO
# ============================================================

ARCHIVE_API_URL = "https://archive-api.open-meteo.com/v1/archive"

START_DATE = "2024-01-01"

TIMEZONE = "UTC"

TEMPERATURE_UNIT = "celsius"
WIND_SPEED_UNIT = "kmh"
PRECIPITATION_UNIT = "mm"


# ============================================================
# VARIABLES MÉTÉO HORAIRES
# ============================================================

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "snowfall",
    "weather_code",
    "pressure_msl",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
]


# ============================================================
# LES 21 MÉTROPOLES FRANÇAISES
# ============================================================

METROPOLES = [
    {
        "code_insee_epci": "243300316",
        "libelle_metropole": "Bordeaux Métropole",
        "latitude": 44.8378,
        "longitude": -0.5792,
    },
    {
        "code_insee_epci": "242900314",
        "libelle_metropole": "Brest Métropole",
        "latitude": 48.3904,
        "longitude": -4.4861,
    },
    {
        "code_insee_epci": "246300701",
        "libelle_metropole": "Clermont Auvergne Métropole",
        "latitude": 45.7772,
        "longitude": 3.0870,
    },
    {
        "code_insee_epci": "242100410",
        "libelle_metropole": "Dijon Métropole",
        "latitude": 47.3220,
        "longitude": 5.0415,
    },
    {
        "code_insee_epci": "246700488",
        "libelle_metropole": "Eurométropole de Strasbourg",
        "latitude": 48.5734,
        "longitude": 7.7521,
    },
    {
        "code_insee_epci": "243400017",
        "libelle_metropole": "Montpellier Méditerranée Métropole",
        "latitude": 43.6108,
        "longitude": 3.8767,
    },
    {
        "code_insee_epci": "245900410",
        "libelle_metropole": "Métropole Européenne de Lille",
        "latitude": 50.6292,
        "longitude": 3.0573,
    },
    {
        "code_insee_epci": "200040715",
        "libelle_metropole": "Métropole Grenoble-Alpes-Métropole",
        "latitude": 45.1885,
        "longitude": 5.7245,
    },
    {
        "code_insee_epci": "200030195",
        "libelle_metropole": "Métropole Nice Côte d'Azur",
        "latitude": 43.7102,
        "longitude": 7.2620,
    },
    {
        "code_insee_epci": "243500139",
        "libelle_metropole": "Métropole Rennes Métropole",
        "latitude": 48.1173,
        "longitude": -1.6778,
    },
    {
        "code_insee_epci": "200023414",
        "libelle_metropole": "Métropole Rouen Normandie",
        "latitude": 49.4432,
        "longitude": 1.0993,
    },
    {
        "code_insee_epci": "248300543",
        "libelle_metropole": "Métropole Toulon-Provence-Méditerranée",
        "latitude": 43.1242,
        "longitude": 5.9280,
    },
    {
        "code_insee_epci": "200054807",
        "libelle_metropole": "Métropole d'Aix-Marseille-Provence",
        "latitude": 43.5297,
        "longitude": 5.4474,
    },
    {
        "code_insee_epci": "200046977",
        "libelle_metropole": "Métropole de Lyon",
        "latitude": 45.7640,
        "longitude": 4.8357,
    },
    {
        "code_insee_epci": "245400676",
        "libelle_metropole": "Métropole du Grand Nancy",
        "latitude": 48.6921,
        "longitude": 6.1844,
    },
    {
        "code_insee_epci": "200054781",
        "libelle_metropole": "Métropole du Grand Paris",
        "latitude": 48.8566,
        "longitude": 2.3522,
    },
    {
        "code_insee_epci": "244400404",
        "libelle_metropole": "Nantes Métropole",
        "latitude": 47.2184,
        "longitude": -1.5536,
    },
    {
        "code_insee_epci": "244500468",
        "libelle_metropole": "Orléans Métropole",
        "latitude": 47.9029,
        "longitude": 1.9093,
    },
    {
        "code_insee_epci": "244200770",
        "libelle_metropole": "Saint-Etienne Métropole",
        "latitude": 45.4397,
        "longitude": 4.3872,
    },
    {
        "code_insee_epci": "243100518",
        "libelle_metropole": "Toulouse Métropole",
        "latitude": 43.6045,
        "longitude": 1.4440,
    },
    {
        "code_insee_epci": "243700754",
        "libelle_metropole": "Tours Métropole Val de Loire",
        "latitude": 47.3941,
        "longitude": 0.6848,
    },
]


# ============================================================
# VALIDATION DE LA CONFIGURATION
# ============================================================

EXPECTED_METROPOLES_COUNT = 21

if len(METROPOLES) != EXPECTED_METROPOLES_COUNT:
    raise ValueError(
        f"Nombre incorrect de métropoles : {len(METROPOLES)}"
    )

codes = [m["code_insee_epci"] for m in METROPOLES]

if len(codes) != len(set(codes)):
    raise ValueError("Des codes INSEE EPCI sont dupliqués.")

if not ENERGY_DATASET.exists():
    raise FileNotFoundError(
        f"Dataset éCO₂mix introuvable : {ENERGY_DATASET}"
    )
