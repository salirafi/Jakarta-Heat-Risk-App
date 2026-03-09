import sqlite3
import geopandas as gpd
import pandas as pd
from shapely import wkt

from config import DB_PATH, BOUNDARY_TABLE, FORECAST_TABLE

def run_query(query: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()

def get_table_names() -> list[str]:
    tables = run_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return tables["name"].tolist()

def load_boundary_data() -> gpd.GeoDataFrame:
    query = f"SELECT * FROM {BOUNDARY_TABLE}"
    boundary_df = run_query(query)

    if boundary_df.empty:
        return gpd.GeoDataFrame(boundary_df, geometry=[], crs="EPSG:4326")

    boundary_df["adm4"] = boundary_df["adm4"].astype(str).str.strip()
    boundary_df["geometry"] = boundary_df["geometry_wkt"].apply(wkt.loads)

    gdf = gpd.GeoDataFrame(boundary_df, geometry="geometry", crs="EPSG:4326")

    # Drop missing geometries
    gdf = gdf[gdf.geometry.notna()].copy()

    # Try repairing invalid geometries
    invalid_mask = ~gdf.geometry.is_valid
    if invalid_mask.any():
        gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].buffer(0)

    # Drop anything still invalid or empty after repair
    gdf = gdf[gdf.geometry.notna()].copy()
    gdf = gdf[~gdf.geometry.is_empty].copy()
    gdf = gdf[gdf.geometry.is_valid].copy()

    # Keep one row per polygon id
    gdf = gdf.drop_duplicates(subset=["adm4"]).reset_index(drop=True)

    return gdf

def load_forecast_data(start_time=None, end_time=None) -> pd.DataFrame:
    where_clause = ""
    if start_time is not None and end_time is not None:
        start_str = pd.Timestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")
        end_str = pd.Timestamp(end_time).strftime("%Y-%m-%d %H:%M:%S")
        where_clause = f"""
        WHERE local_datetime >= '{start_str}'
          AND local_datetime <= '{end_str}'
        """

    query = f"""
    SELECT
        adm4,
        desa_kelurahan,
        kecamatan,
        kotkab,
        local_datetime,
        temperature_c,
        humidity_pct,
        heat_index_c,
        risk_level,
        weather_desc_en
    FROM {FORECAST_TABLE}
    {where_clause}
    ORDER BY local_datetime
    """
    df = run_query(query)

    if df.empty:
        return df

    df["local_datetime"] = pd.to_datetime(df["local_datetime"], errors="coerce")

    for col in [
        "adm4",
        "desa_kelurahan",
        "kecamatan",
        "kotkab",
        "risk_level",
        "weather_desc_en",
    ]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["local_datetime"]).reset_index(drop=True)
    return df

def get_forecast_time_bounds() -> dict:
    query = f"""
    SELECT
        MIN(local_datetime) AS min_time,
        MAX(local_datetime) AS max_time
    FROM {FORECAST_TABLE}
    """
    df = run_query(query)

    if df.empty:
        return {"min_time": None, "max_time": None}

    min_time = pd.to_datetime(df.loc[0, "min_time"], errors="coerce")
    max_time = pd.to_datetime(df.loc[0, "max_time"], errors="coerce")

    return {"min_time": min_time, "max_time": max_time}


def get_available_dates() -> list[pd.Timestamp]:
    query = f"""
    SELECT DISTINCT DATE(local_datetime) AS available_date
    FROM {FORECAST_TABLE}
    WHERE local_datetime IS NOT NULL
    ORDER BY available_date
    """
    df = run_query(query)

    if df.empty:
        return []

    dates = pd.to_datetime(df["available_date"], errors="coerce").dropna()
    return sorted(dates.dt.normalize().unique().tolist())


def floor_to_time_step(ts, step_hours: int = 3):
    if ts is None or pd.isna(ts):
        return None

    ts = pd.Timestamp(ts)
    floored_hour = (ts.hour // step_hours) * step_hours
    return ts.replace(hour=floored_hour, minute=0, second=0, microsecond=0)


def get_nearest_available_start_time(rounded_time):
    """
    Return the nearest available timestamp in DB such that:
        local_datetime <= rounded_time
    If none exists, return None.
    """
    if rounded_time is None or pd.isna(rounded_time):
        return None

    rounded_str = pd.Timestamp(rounded_time).strftime("%Y-%m-%d %H:%M:%S")

    query = f"""
    SELECT MAX(local_datetime) AS start_time
    FROM {FORECAST_TABLE}
    WHERE local_datetime <= '{rounded_str}'
    """
    df = run_query(query)

    if df.empty:
        return None

    start_time = pd.to_datetime(df.loc[0, "start_time"], errors="coerce")
    if pd.isna(start_time):
        return None

    return start_time

def compute_query_window(start_time, max_time, window_days: int = 1):
    if start_time is None or pd.isna(start_time):
        return {"start_time": None, "end_time": None}

    end_time = pd.Timestamp(start_time) + pd.Timedelta(days=window_days)

    if max_time is not None and pd.notna(max_time):
        end_time = min(end_time, pd.Timestamp(max_time))

    return {
        "start_time": pd.Timestamp(start_time),
        "end_time": pd.Timestamp(end_time),
    }

def get_first_available_time_on_or_after(start_time):
    """
    Return the first available timestamp in DB such that:
        local_datetime >= start_time
    If none exists, return None.
    """
    if start_time is None or pd.isna(start_time):
        return None

    start_str = pd.Timestamp(start_time).strftime("%Y-%m-%d %H:%M:%S")

    query = f"""
    SELECT MIN(local_datetime) AS start_time
    FROM {FORECAST_TABLE}
    WHERE local_datetime >= '{start_str}'
    """
    df = run_query(query)

    if df.empty:
        return None

    out = pd.to_datetime(df.loc[0, "start_time"], errors="coerce")
    if pd.isna(out):
        return None

    return out