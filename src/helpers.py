import sqlite3
import pandas as pd
import json
from html import escape

from .constant import DB_PATH, BOUNDARY_GEOJSON_PATH, WEATHER_TABLE, CITY_SUMMARY_TABLE

def guide_button_id(level: str) -> str:
    return {
        "Lower Risk": "guide_lower_risk",
        "Caution": "guide_caution",
        "Extreme Caution": "guide_extreme_caution",
        "Danger": "guide_danger",
        "Extreme Danger": "guide_extreme_danger",
    }[level]

def risk_badge(level: str) -> str:
    if level == "Extreme Danger":
        return "🚨 Extreme Danger"
    if level == "Danger":
        return "🔴 Danger"
    if level == "Extreme Caution":
        return "🟠 Extreme Caution"
    if level == "Caution":
        return "🟡 Caution"
    if level == "Lower Risk":
        return "🟢 Lower Risk"
    return "⚪ No Data"

# formatting pandas Timestamp to cleaner format
def format_timestamp(ts) -> str:
    if ts is None or pd.isna(ts):
        return ""
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M")

def short_city_name(name: str) -> str:
    if pd.isna(name):
        return ""
    name = str(name).strip()
    return name.replace("Kota Adm. ", "")

# HTML for current-weather metric cards
def metric_card_html(label: str, value: str, extra_class: str = "") -> str:
    return f"""
    <div class="metric-card {extra_class}">
        <div class="metric-label">{escape(label)}</div>
        <div class="metric-value">{value}</div>
    </div>
    """
def hex_to_rgba_css(hex_color: str, alpha: float = 0.18) -> str:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return f"rgba(220,220,220,{alpha})"

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def run_query(query: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(query,conn)
    finally:
        conn.close()

# function to get name of all tables in sqlite database
def get_table_names() -> list[str]:
    tables = run_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return tables["name"].tolist()

# function to load boundary data from boundary table
def load_boundary_data() -> tuple[pd.DataFrame, dict]:

    with open(BOUNDARY_GEOJSON_PATH, "r", encoding="utf-8") as f:
        geojson = json.load(f) # becomes dict

    features = geojson.get("features", [])
    boundary_index = pd.DataFrame(
        {
            "adm4": [
                str(feature.get("properties", {}).get("adm4", "")).strip()
                for feature in features
            ]
        }
    )

    return boundary_index, geojson

# function to load weather data from weather table
def load_weather_data(start_time: pd.Timestamp, end_time: pd.Timestamp) -> pd.DataFrame:

    start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")

    # return only relevant columns
    query = f"""
            SELECT
                adm4,
                desa_kelurahan,
                kecamatan,
                kota_kabupaten,
                local_datetime,
                temperature_c,
                humidity_ptg,
                heat_index_c,
                risk_level,
                weather_desc
            FROM {WEATHER_TABLE}
            WHERE local_datetime BETWEEN '{start_time}' AND '{end_time}'
            """
    df = run_query(query)

    if df.empty: 
        return df # return empty df is df is empty

    # convert to panda's datetime since the SQL's date is initially string
    df["local_datetime"] = pd.to_datetime(df["local_datetime"], errors="coerce") # output -> Series of datetime.datetime

    return df # comparing to the boundary table, the shared column is adm4

# get unique timestamp values in weather data
def available_timestamps(start_time: pd.Timestamp, end_time: pd.Timestamp) -> list[pd.Timestamp]:
    query = f"""
        SELECT DISTINCT local_datetime
        FROM {WEATHER_TABLE}
        WHERE local_datetime >= '{start_time}'
          AND local_datetime <= '{end_time}'
        ORDER BY local_datetime
    """
    df = run_query(query)

    if df.empty:
        return []

    return pd.to_datetime(df["local_datetime"]).tolist() # list of pd.Timestamp sorted

# functions to get available options for region filtering
def city_options() -> list[str]: # fory city-level
    query = f"""
        SELECT DISTINCT kota_kabupaten
        FROM {WEATHER_TABLE}
        WHERE kota_kabupaten IS NOT NULL
          AND TRIM(kota_kabupaten) != ''
        ORDER BY kota_kabupaten
    """
    df = run_query(query)
    if df.empty:
        return []
    return df["kota_kabupaten"].astype(str).str.strip().tolist()
def subdistrict_options(selected_city: str) -> list[str]: # for subdistrict-level
    query = f"""
        SELECT DISTINCT kecamatan
        FROM {WEATHER_TABLE}
        WHERE kota_kabupaten = '{selected_city}'
          AND kecamatan IS NOT NULL
          AND TRIM(kecamatan) != ''
        ORDER BY kecamatan
    """
    df = run_query(query)
    if df.empty:
        return []
    return df["kecamatan"].astype(str).str.strip().tolist()
def ward_options(selected_city: str, selected_subdistrict: str) -> list[str]: # for ward-level
    query = f"""
        SELECT DISTINCT desa_kelurahan
        FROM {WEATHER_TABLE}
        WHERE kota_kabupaten = '{selected_city}'
          AND kecamatan = '{selected_subdistrict}'
          AND desa_kelurahan IS NOT NULL
          AND TRIM(kecamatan) != ''
        ORDER BY kecamatan
    """
    df = run_query(query)
    if df.empty:
        return []
    return df["desa_kelurahan"].astype(str).str.strip().tolist()

# function to get the region code for the selected region for filtering the database to the selected reigion
def ward_final_selection(selected_city: str, selected_subdistrict: str, selected_ward: str) -> str | None:
    query = f"""
        SELECT adm4
        FROM {WEATHER_TABLE}
        WHERE kota_kabupaten = '{selected_city}'
          AND kecamatan = '{selected_subdistrict}'
          AND desa_kelurahan = '{selected_ward}'
        ORDER BY local_datetime
        LIMIT 1
    """
    df = run_query(query)
    if df.empty:
        return None
    value = df.iloc[0]["adm4"] # get the code
    return str(value).strip()

# selecting rows with the filtered-region and (current) time
def current_condition(adm4: str, current_time: pd.Timestamp) -> pd.DataFrame:
    query = f"""
        SELECT *
        FROM {WEATHER_TABLE}
        WHERE adm4 = '{adm4}'
          AND local_datetime <= '{current_time.strftime("%Y-%m-%d %H:%M:%S")}'
        ORDER BY local_datetime DESC
        LIMIT 1
    """
    df = run_query(query)

    if df.empty:
        return df

    df["local_datetime"] = pd.to_datetime(df["local_datetime"], errors="coerce")
    return df

# function to query future weather data relative to current time
def future_forecast(adm4: str, current_time: pd.Timestamp, end_time: pd.Timestamp) -> pd.DataFrame:
    query = f"""
        SELECT *
        FROM {WEATHER_TABLE}
        WHERE adm4 = '{adm4}'
          AND local_datetime BETWEEN '{current_time.strftime("%Y-%m-%d %H:%M:%S")}'
                                AND '{end_time.strftime("%Y-%m-%d %H:%M:%S")}'
        ORDER BY local_datetime
    """
    df = run_query(query)

    if df.empty:
        return df

    df["local_datetime"] = pd.to_datetime(df["local_datetime"], errors="coerce")
    return df


