import sqlite3
import pandas as pd
import geopandas as gpd
from shapely import wkb
import json
from html import escape

from .constant import DB_PATH, BOUNDARY_TABLE, WEATHER_TABLE

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
def load_boundary_data() -> gpd.GeoDataFrame:

    # returns region code and geometry column
    query = f"""
            SELECT adm4, geometry_wkb
            FROM {BOUNDARY_TABLE};
            """
    boundary_df = run_query(query)

    if boundary_df.empty:
        return gpd.GeoDataFrame(boundary_df, geometry=[], crs="EPSG:4326") # if table is empty, return empty geopandas dataframe

    boundary_df["adm4"] = boundary_df["adm4"].astype(str).str.strip() # remove trailing and leading whitespace
    boundary_df["geometry_wkb"] = boundary_df["geometry_wkb"].apply(wkb.loads) # convert WKB to polygon geometry

    # note that, even though the column name is geometry_wkb, at this stage, it is already in polygon geometry
    # rewriting the column avoids additional large column
    gdf = gpd.GeoDataFrame(boundary_df, geometry="geometry_wkb", crs="EPSG:4326")
    
    gdf["geometry_wkb"] = gdf.make_valid() # repair invalid geometries to be valid

    # look https://geopandas.org/en/stable/docs/user_guide/missing_empty.html for differences between empty and missing
    gdf = gdf[gdf.geometry.notna()] # drop missing geometries
    gdf = gdf[~gdf.geometry.is_empty] # drop empty geometries

    gdf = gdf.drop_duplicates(subset=["adm4"]).reset_index(drop=True) # keep only distinct adm4 values

    geojson = json.loads(gdf.to_json()) # converting geodataframe to geojson dict for choropleth plotting

    return gdf, geojson # note that the cleaned-up gdf may or may not drop some regions

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

    for col in [
        "adm4",
        "desa_kelurahan",
        "kecamatan",
        "kota_kabupaten",
        "risk_level",
        "weather_desc",
    ]:
        df[col] = df[col].astype(str).str.strip() # remove trailing and leading whitespace for string columns

    # drop NaN values for datetime columns
    df = df.dropna(subset=["local_datetime"]).reset_index(drop=True)

    return df # comparing to the boundary table, the shared column is adm4

# get unique timestamp values in weather data
def available_times_in_data(df: pd.DataFrame) -> list[pd.Timestamp]:
    if df.empty or "local_datetime" not in df.columns:
        return []
    return sorted(df["local_datetime"].dropna().unique().tolist()) # list of pd.Timestamp sorted

# get the nearest time in region filtered df to the current time
def nearest_available_time_in_df(df: pd.DataFrame, current_time: pd.Timestamp):
    times = available_times_in_data(df)
    if not times:
        return None

    times = pd.to_datetime(pd.Series(times))
    if times.empty:
        return None

    nearest_idx = (times - current_time).abs().idxmin()
    return pd.Timestamp(times.loc[nearest_idx])

# filtering region-filtered df to the selected time
def weather_at_selected_time(df: pd.DataFrame, selected_time:pd.Timestamp) -> pd.DataFrame:
    if df.empty or selected_time is None:
        return df.iloc[0:0].copy()
    out = df[df["local_datetime"] == selected_time]
    return out
    # return (
    #     out.sort_values(["kota_kabupaten", "kecamatan", "desa_kelurahan"])
    #     .reset_index(drop=True)
    # )

# function to give available options for region filtering
# for city-level, prior_mask must be None
def region_filter_options(
    df: pd.DataFrame,
    column: str,
    prior_mask: pd.Series | None = None,
) -> list[str]:

    if df.empty or column not in df.columns:
        return []

    subset = df if prior_mask is None else df[prior_mask]
    if subset.empty:
        return []
    # subset = subset[column].apply(short_city_name)
    return sorted(
        subset[column].astype(str).str.strip().unique().tolist() # get only distinct values
    )

