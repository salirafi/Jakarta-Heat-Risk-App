from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DB_PATH = BASE_DIR / "tables" / "heat_risk.db"
BOUNDARY_TABLE = "jakarta_kelurahan_boundary"
FORECAST_TABLE = "heat_forecast_jakarta"

RISK_ORDER = [
    "No Data",
    "Lower Risk",
    "Caution",
    "Extreme Caution",
    "Danger",
    "Extreme Danger",
]

RISK_COLOR_MAP = {
    "No Data": "#dcdcdc",
    "Lower Risk": "#66bb6a",
    "Caution": "#ffee58",
    "Extreme Caution": "#ffa726",
    "Danger": "#ef5350",
    "Extreme Danger": "#9c27b0",
}

RISK_CODE_MAP = {name: i for i, name in enumerate(RISK_ORDER)}
CODE_TO_RISK = {i: name for name, i in RISK_CODE_MAP.items()}
