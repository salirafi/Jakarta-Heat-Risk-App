import json
import sqlite3
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pydeck as pdk
import streamlit as st
from shapely import wkt

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DB_PATH = Path("heat_risk.db")
FORECAST_TABLE = "heat_forecast_jakarta"
BOUNDARY_TABLE = "jakarta_kelurahan_boundary"

RISK_ORDER = [
    "Lower Risk",
    "Caution",
    "Extreme Caution",
    "Danger",
    "Extreme Danger",
]

RISK_COLOR_MAP = {
    "Lower Risk": [102, 187, 106, 160],
    "Caution": [255, 238, 88, 170],
    "Extreme Caution": [255, 167, 38, 180],
    "Danger": [239, 83, 80, 190],
    "Extreme Danger": [156, 39, 176, 200],
}

DEFAULT_FILL_COLOR = [220, 220, 220, 80]
DEFAULT_LINE_COLOR = [90, 90, 90, 120]
MAP_STYLE = "mapbox://styles/mapbox/light-v9"

@st.cache_data(ttl=900, show_spinner=False)
def run_query(query: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()

@st.cache_data(ttl=900, show_spinner=False)
def load_forecast_data() -> pd.DataFrame:
    query = f"""
    SELECT
        adm4,
        desa_kelurahan,
        kecamatan,
        kotkab,
        provinsi,
        latitude,
        longitude,
        timezone,
        local_datetime,
        temperature_c,
        humidity_pct,
        heat_index_c,
        risk_level,
        weather_desc_en,
        analysis_date
    FROM {FORECAST_TABLE}
    ORDER BY local_datetime
    """
    df = run_query(query)

    if not df.empty:
        df["local_datetime"] = pd.to_datetime(df["local_datetime"], errors="coerce") # convert to datetime, coercing errors to NaT
        df["analysis_date"] = pd.to_datetime(df["analysis_date"], errors="coerce") # same for analysis_date
        for col in ["adm4", "desa_kelurahan", "kecamatan", "kotkab", "provinsi", "risk_level"]:
            df[col] = df[col].astype(str).str.strip() # ensure string columns are stripped of whitespace and treated as strings

    return df

@st.cache_data(ttl=900, show_spinner=False)
def load_boundary_data() -> gpd.GeoDataFrame:
    query = f"SELECT * FROM {BOUNDARY_TABLE}"
    boundary_df = run_query(query)

    if boundary_df.empty:
        return gpd.GeoDataFrame(boundary_df, geometry=[], crs="EPSG:4326") # return empty GeoDataFrame with correct columns and CRS if no data is available

    boundary_df["adm4"] = boundary_df["adm4"].astype(str).str.strip() # ensure string columns are stripped of whitespace and treated as strings
    boundary_df["geometry"] = boundary_df["geometry_wkt"].apply(wkt.loads) # convert WKT geometry back to shapely geometry objects for use in GeoDataFrame; this assumes that the 'geometry_wkt' column contains valid WKT strings representing the geometries
    return gpd.GeoDataFrame(boundary_df, geometry="geometry", crs="EPSG:4326")

# @st.cache_data(show_spinner=False)
def get_table_names() -> list[str]:
    tables = run_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return tables["name"].tolist()

# this function is for generating the list of choices for the dropdown filters
# dynamically returns valid region names based on the currently filtered data
def region_filter_options(df: pd.DataFrame, column: str, prior_mask: pd.Series | None = None) -> list[str]:
    subset = df if prior_mask is None else df[prior_mask]
    values = sorted(subset[column].dropna().astype(str).str.strip().unique().tolist()) # drop NaN, ensure strings are stripped of whitespace, get unique values, convert to list and sort
    return values

# this function determines which timestamps can be used for the map visualization
def available_map_times(df: pd.DataFrame) -> list[pd.Timestamp]:

    # handle empty dataframe
    if df.empty:
        return []
    
    return sorted(df["local_datetime"].dropna().unique().tolist()) # drop NaN, get unique timestamps, convert to list and sort

    # valid = df.dropna(subset=["adm4", "local_datetime"]).copy()
    # if valid.empty:
    #     return [] # handle empty valid dataframe after dropping rows with missing adm4 or local_datetime

    # n_adm4 = valid["adm4"].nunique() # count how many unique adm4 codes (how many regions)

    # # count regions for each timestamp
    # counts = (
    #     valid.groupby("local_datetime")["adm4"]
    #     .nunique()
    #     .sort_index()
    # )

    # # ensure that only timestamps where the count of unique adm4 matches the total number of adm4 are included; 
    # # this means we only get times where we have data for every region, which allows the map to show all polygons without missing data
    # complete_times = counts[counts == n_adm4].index.tolist() 
    
    # it returns only the times where every region (adm4) has data, so the map will not have missing polygons
    # return [pd.Timestamp(t) for t in complete_times] # convert to pandas timestamps

# the function extracts only the forecast rows that correspond to the time selected by the user on the map slider
def forecast_at_selected_time(df: pd.DataFrame, selected_time) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    selected_time = pd.Timestamp(selected_time)
    out = df[df["local_datetime"] == selected_time].copy() # filter rows for the selected timestamp
    return out.sort_values(["kotkab", "kecamatan", "desa_kelurahan"]).reset_index(drop=True)

# keeping only the boundary polygons whose adm4 code exists in the forecast dataframe
def filtered_boundary(boundary_gdf: gpd.GeoDataFrame, df: pd.DataFrame) -> gpd.GeoDataFrame:
    
    # handle empty input
    if boundary_gdf.empty or df.empty:
        return boundary_gdf.iloc[0:0].copy()
    
    selected_adm4 = set(df["adm4"].dropna().astype(str).str.strip().unique()) # collect all region codes present in the forecast data
    return boundary_gdf[boundary_gdf["adm4"].isin(selected_adm4)].copy() # filters the boundary table to only polygons whose adm4 appears in the forecast data

# function builds the final GeoDataFrame used by pydeck
def build_map_geodata(boundary_gdf: gpd.GeoDataFrame, forecast_df: pd.DataFrame, selected_time) -> gpd.GeoDataFrame:
    time_df = forecast_at_selected_time(forecast_df, selected_time) # extract one-time forecast snapshot

    # if there are no polygons, just return empty output
    if boundary_gdf.empty:
        return boundary_gdf.copy()

    # merge forecast values into polygons
    map_gdf = boundary_gdf.merge(
        time_df[[
            "adm4",
            "local_datetime",
            "temperature_c",
            "humidity_pct",
            "heat_index_c",
            "risk_level",
            "weather_desc_en",
        ]],
        on="adm4", # using adm4 as key
        
        # how=left keeps polygons in boundary_gdf and attach forecast data where available
        # if no forecast data for a polygon, the new columns will have NaN values, which we can handle later when assigning colors and labels
        how="left",
    )

    map_gdf["fill_color"] = map_gdf["risk_level"].map(RISK_COLOR_MAP) # convert risk levels to RGBA colors
    map_gdf["fill_color"] = map_gdf["fill_color"].apply(lambda x: x if isinstance(x, list) else DEFAULT_FILL_COLOR) # if risk_level is NaN, assign default fill color
    
    # create formatted display fields
    map_gdf["local_datetime_str"] = map_gdf["local_datetime"].astype(str)
    map_gdf["heat_index_label"] = map_gdf["heat_index_c"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "No data") # format heat index with 1 decimal place, handle NaN by showing "No data"
    map_gdf["temperature_label"] = map_gdf["temperature_c"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "No data") # same for temperature
    map_gdf["humidity_label"] = map_gdf["humidity_pct"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "No data") # same for humidity, but no decimal places
    map_gdf["risk_label"] = map_gdf["risk_level"].fillna("No data") # if risk level is NaN, show "No data"
    map_gdf["weather_label"] = map_gdf["weather_desc_en"].fillna("No data") # if weather description is NaN, show "No data"
    return map_gdf

# converts the GeoDataFrame used for the map into a GeoJSON dictionary that pydeck can render
# see https://deckgl.readthedocs.io/en/latest/layer.html
# the flow for map generation in this dashboard is: boundary polygons -> forecast values -> GeoDataFrame (map_gdf) => GeoJSON dict -> pydeck map
def geodata_to_geojson_dict(map_gdf: gpd.GeoDataFrame) -> dict:
    export_gdf = map_gdf.copy()
    export_gdf["fill_color"] = export_gdf["fill_color"].apply(list) # ensure color values are list

    # GeoJSON cannot store pandas datetime objects, so we need to convert any datetime columns to strings
    for col in export_gdf.columns:
        if col == "geometry":
            continue
        if pd.api.types.is_datetime64_any_dtype(export_gdf[col]):
            export_gdf[col] = export_gdf[col].dt.strftime("%Y-%m-%d %H:%M:%S")

    # catching any remaining datetime objects that may not have been converted, for sanity check
    export_gdf = export_gdf.apply(
        lambda s: s.map(
            lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if isinstance(x, pd.Timestamp) else x
        ) if s.name != "geometry" else s
    )
    return json.loads(export_gdf.to_json()) # convert to string JSON first then to Python dict because pydeck expects a dict

# this function computes the initial camera view (the center latitude, longitude, and zoom level) based on the geographic extent of the polygons in the map
# see https://deckgl.readthedocs.io/en/latest/view_state.html
def make_view_state(map_gdf: gpd.GeoDataFrame) -> pdk.ViewState:
    if map_gdf.empty:
        return pdk.ViewState(latitude=-6.2, longitude=106.83, zoom=10, pitch=0) # default to Jakarta coordinate; pitch sets angle relative to map's plane

    minx, miny, maxx, maxy = map_gdf.total_bounds # total_bounds returns the bounding box of all geometries
    center_lat = (miny + maxy) / 2 # computing center latitude
    center_lon = (minx + maxx) / 2 # computing center longitude

    lon_span = max(maxx - minx, 0.01) # computing longitude span, with a minimum threshold to avoid zero span which can cause issues with zooming
    lat_span = max(maxy - miny, 0.01) # computing latitude span, with the same minimum threshold
    max_span = max(lon_span, lat_span)

    # the zoom  level will depend on how large the geographic extent is
    if max_span > 1.0:
        zoom = 8
    elif max_span > 0.6:
        zoom = 9
    elif max_span > 0.3:
        zoom = 10
    elif max_span > 0.15:
        zoom = 11
    else:
        zoom = 12

    return pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom, pitch=0)

# function to convert risk level to a badge with emoji for better visual display in the tooltip and forecast cards
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

# finds the most recent forecast entry for each region (adm4)
# currently not used in the main dashboard but kept for potential use in future
def latest_snapshot_per_adm4(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy() # handle empty dataframe
    valid = df.dropna(subset=["adm4", "local_datetime"]).copy() # remove invalid rows
    if valid.empty:
        return valid
    idx = valid.groupby("adm4")["local_datetime"].idxmax() # find the newest timestamp for each region
    return valid.loc[idx].sort_values(["heat_index_c", "desa_kelurahan"], ascending=[False, True]).reset_index(drop=True) # sort by descending heat index first

# helper to find the forecast timestamp closest to the current system time
def nearest_available_time(df: pd.DataFrame, now=None):

    # get valid timestamps
    # this can be used as reference timestamps because all regions should have the same set of timestamps
    times = available_map_times(df)
    if not times:
        return None

    if now is None:
        now = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None) # get local Jakarta time without timezone info for comparison

    times = pd.to_datetime(pd.Series(times))
    nearest_idx = (times - now).abs().idxmin() # computing absolute time differences and find the smallest difference
    return pd.Timestamp(times.loc[nearest_idx])


st.set_page_config(page_title="Peta dan Informasi Heat Risk Jakarta", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: #e7e7e7;
    }
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1rem;
        max-width: 1400px;
    }
    .page-title {
        font-size: 2.8rem;
        font-weight: 800;
        color: #111111;
        margin-bottom: 0.1rem;
    }
    .page-subtitle {
        font-size: 0.8rem;
        font-weight: 300;
        color: #111111;
        margin-bottom: 1rem;
    }
    .panel {
        background: white;
        border: 1px solid #d0d7de;
        color: #111111;
        padding: 14px 16px;
        min-height: 100px;
        border-radius: 10px;
    }
    .panel-title {
        font-size: 1.05rem;
        font-weight: 700;
        margin-bottom: 0.65rem;
    }
    .subtle {
        opacity: 0.95;
        font-size: 0.95rem;
        line-height: 1.45;
    }
    .legend-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-right: 14px;
        margin-bottom: 6px;
        font-size: 0.88rem;
    }
    .metric-big {
        font-size: 1.55rem;
        font-weight: 700;
    }
    .metric-label {
        font-size: 0.88rem;
        opacity: 0.95;
    }
    .forecast-card {
        border: 1px solid rgba(0,0,0,0.1);
        padding: 10px 12px;
        min-width: 160px;
        border-radius: 10px;
        background: rgba(0,0,0,0.01);
        backdrop-filter: blur(3px);
        display: inline-block;
        margin-right: 12px;
    }
    .forecast-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 14px rgba(0,0,0,0.15);
    }
    .note-list {
        margin: 0;
        padding-left: 1rem;
        line-height: 1.5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="page-title">Peta dan Informasi Heat Risk Jakarta</div>', unsafe_allow_html=True)
st.markdown('''
            <div class="page-subtitle">Sayyed A. Rafi.
            e-mail: salirafi8@gmail.com</div>
            ''', unsafe_allow_html=True)

if not DB_PATH.exists():
    st.error("Database file 'heat_risk.db' was not found. Run the ingestion pipeline first.")
    st.stop()

existing_tables = set(get_table_names())
missing_tables = [t for t in [FORECAST_TABLE, BOUNDARY_TABLE] if t not in existing_tables]
if missing_tables:
    st.error("Required table(s) are missing from the database: " + ", ".join(missing_tables))
    st.stop()

try:
    df = load_forecast_data()
    boundary_gdf = load_boundary_data()
except Exception as exc:
    st.exception(exc)
    st.stop()

if df.empty:
    st.warning("The forecast table exists, but no rows were found.")
    st.stop()

if boundary_gdf.empty:
    st.warning("The boundary table exists, but no rows were found.")
    st.stop()

map_time_options = available_map_times(df)
if not map_time_options:
    st.warning("No valid forecast timestamps are available for the current selection.")
    st.stop()

now_time = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None)

map_time_series = pd.Series(map_time_options)
nearest_idx = (map_time_series - now_time).abs().idxmin()
default_slider_time = map_time_series.loc[nearest_idx]

# ----------------------------
# Layout
# ----------------------------
left_col, right_col = st.columns([1.05, 1.3], gap="small")

with left_col:
    st.markdown('<div class="panel-title" style="visibility:hidden;">Map</div>', unsafe_allow_html=True)

    selected_map_time = st.select_slider(
            "Waktu peta (YYYY-MM-DD HH:MM)",
            options=map_time_options,
            value=default_slider_time,
            format_func=lambda x: pd.Timestamp(x).strftime("%Y-%m-%d %H:%M"),
        )

    boundary_filtered = filtered_boundary(boundary_gdf, df)
    map_gdf = build_map_geodata(boundary_filtered, df, selected_map_time)

    geojson_data = geodata_to_geojson_dict(map_gdf)
    view_state = make_view_state(map_gdf)

    if map_gdf.empty:
        st.markdown('<div class="panel"><div class="subtle">No polygon data is available for the current filters.</div></div>', unsafe_allow_html=True)
    else:
        tooltip = {
            "html": """
            <b>Kelurahan:</b> {desa_kelurahan}<br/>
            <b>Kecamatan:</b> {kecamatan}<br/>
            <b>Kota / kabupaten:</b> {kotkab}<br/>
            <b>Heat Index (°C):</b> {heat_index_label}<br/>
            <b>Temperatur (°C):</b> {temperature_label}<br/>
            <b>Kelembapan (%):</b> {humidity_label}<br/>
            <b>Tingkat Risiko:</b> {risk_label}<br/>
            <b>Cuaca:</b> {weather_label}<br/>
            <b>Waktu Prakiraan:</b> {local_datetime_str}
            """,
            "style": {"backgroundColor": "#1f2937", "color": "white"},
        }

        layer = pdk.Layer(
            "GeoJsonLayer",
            data=geojson_data,
            pickable=True,
            stroked=True,
            filled=True,
            extruded=False,
            wireframe=False,
            opacity=1.0,
            get_fill_color="properties.fill_color",
            get_line_color=DEFAULT_LINE_COLOR,
            line_width_min_pixels=1,
        )

        st.pydeck_chart(
            pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                tooltip=tooltip,
                map_style=MAP_STYLE,
            ),
            use_container_width=True,
            height=560,
        )

    legend_html = []
    legend_items = [("No Data", DEFAULT_FILL_COLOR)] + [(k, RISK_COLOR_MAP[k]) for k in RISK_ORDER]
    for label, color in legend_items:
        rgba = f"rgba({color[0]}, {color[1]}, {color[2]}, {color[3] / 255:.2f})"
        legend_html.append(
            f"<span class='legend-chip'><span style='width:14px;height:14px;background:{rgba};border:1px solid #777;display:inline-block;'></span>{label}</span>"
        )
    st.markdown("<div>" + "".join(legend_html) + "</div>", unsafe_allow_html=True)

with right_col:

    st.markdown("### Kondisi saat ini dan prakiraan terdekat")

    # ----------------------------
    # Filters
    # ----------------------------

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        kotkab_options = region_filter_options(df, "kotkab")
        selected_kotkab = st.selectbox("City / Regency", kotkab_options, index=0)

    mask_kotkab = pd.Series(True, index=df.index)
    mask_kotkab = df["kotkab"] == selected_kotkab

    kecamatan_options = region_filter_options(df, "kecamatan", prior_mask=mask_kotkab)

    with filter_col2:
        selected_kecamatan = st.selectbox("Kecamatan", kecamatan_options, index=0)

    mask_kecamatan = mask_kotkab.copy()
    mask_kecamatan = mask_kecamatan & (df["kecamatan"] == selected_kecamatan)

    kelurahan_options = region_filter_options(df, "desa_kelurahan", prior_mask=mask_kecamatan)

    with filter_col3:
        selected_kelurahan = st.selectbox("Kelurahan / Desa", kelurahan_options, index=0)

    filtered_df = df[
        (df["kotkab"] == selected_kotkab) &
        (df["kecamatan"] == selected_kecamatan) &
        (df["desa_kelurahan"] == selected_kelurahan)
    ].copy()

    if filtered_df.empty:
        st.warning("Tidak ada data yang tersedia untuk wilayah yang dipilih. Pastikan pilihan sudah benar dan data untuk wilayah tersebut memang ada.")
        # st.stop()

    current_time_for_metrics = nearest_available_time(filtered_df)
    if current_time_for_metrics is None:
        current_snapshot = filtered_df.iloc[0:0].copy()
    else:
        current_snapshot = forecast_at_selected_time(filtered_df, current_time_for_metrics)

    if current_time_for_metrics is not None:
        st.caption(
            "Prakiraan terdekat dari waktu lokal saat ini yang tersedia: "
            + pd.Timestamp(current_time_for_metrics).strftime("%Y-%m-%d %H:%M")
        )

    if current_time_for_metrics is None:
        future_forecast_df = filtered_df.iloc[0:0].copy()
    else:
        future_forecast_df = (
            filtered_df[filtered_df["local_datetime"] > current_time_for_metrics]
            .sort_values("local_datetime")
            .copy()
        )

    current_cols = st.columns([1,1,1,2.5], gap="small")

    avg_temp = current_snapshot["temperature_c"].mean() if not current_snapshot.empty else None
    avg_hum = current_snapshot["humidity_pct"].mean() if not current_snapshot.empty else None
    avg_hi = current_snapshot["heat_index_c"].mean() if not current_snapshot.empty else None
    dominant_risk = (
        current_snapshot["risk_level"].mode().iloc[0]
        if not current_snapshot.empty and not current_snapshot["risk_level"].mode().empty
        else "NaN"
    )

    with current_cols[0]:
        st.metric("Temperatur", f"{avg_temp:.1f} °C" if pd.notna(avg_temp) else "No data")
    with current_cols[1]:
        st.metric("Kelembapan", f"{avg_hum:.1f} %" if pd.notna(avg_hum) else "No data")
    with current_cols[2]:
        st.metric("Indeks Panas", f"{avg_hi:.1f} °C" if pd.notna(avg_hi) else "No data")
    with current_cols[3]:
        st.metric("Risiko", risk_badge(dominant_risk))

    # st.write("")

    # forecast_html = "".join(
    #     [
    #         f"""
    #         <div class="forecast-card">
    #             <div style="font-weight:700; margin-bottom:4px;">{card['kelurahan']}</div>
    #             <div style="font-size:0.82rem; opacity:0.9; margin-bottom:8px;">{card['kecamatan']}</div>
    #             <div style="font-size:0.92rem;">HI: {card['heat_index']:.1f} °C</div>
    #             <div style="font-size:0.9rem; margin:4px 0;">{risk_badge(card['risk'])}</div>
    #             <div style="font-size:0.78rem; opacity:0.85;">{pd.Timestamp(card['time']).strftime('%m-%d %H:%M')}</div>
    #         </div>
    #         """
    #         for card in forecast_cards if pd.notna(card["heat_index"])
    #     ]
    # )
    # if not forecast_html:
    #     forecast_html = '<div class="subtle">Tidak ada prakiraan yang tersedia.</div>'
    
    st.markdown("#### Prakiraan untuk waktu yang akan datang")

    if not future_forecast_df.empty:
        card_html = []
        for _, row in future_forecast_df.iterrows():
            if pd.notna(row["heat_index_c"]):
                    color = RISK_COLOR_MAP.get(row["risk_level"], [200,200,200,150])
                    r,g,b,_ = color

                    card_color = f"rgba({r},{g},{b},0.18)"
                    card_html.append(
                            f"""<div class="forecast-card" style="background:{card_color};">
                        <div style="font-weight:700; margin-bottom:4px;">
                            {row['desa_kelurahan']}
                        </div>
                        <div style="font-size:0.95rem; margin-bottom:8px;">
                            HI: {row['heat_index_c']:.1f} °C
                        </div>
                        <div style="margin-bottom:8px;">
                            {risk_badge(row['risk_level'])}
                        </div>
                        <div style="font-size:0.82rem; opacity:0.85;">
                            {pd.Timestamp(row['local_datetime']).strftime('%B %d, %I %p')}
                        </div>
                        </div>"""
                    )
        forecast_html = "".join(card_html)

        st.markdown(
            f"""<div style="overflow-x:auto; white-space:nowrap; padding-bottom:8px;">
        {forecast_html}
        </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.info("Tidak ada prakiraan masa depan yang tersedia.")

    st.write("")

    # st.markdown('<div class="panel-title" style="margin-bottom:6px;">Time evolution plot for heat index</div>', unsafe_allow_html=True)
    st.markdown("#### Indeks panas terhadap waktu")
    chart_df = (
        filtered_df.groupby("local_datetime", as_index=False)["heat_index_c"]
        .mean()
        .sort_values("local_datetime")
        .set_index("local_datetime")
    )

    fig, ax = plt.subplots(figsize=(5,1))

    ax.plot(
        chart_df.index,
        chart_df["heat_index_c"],
        color="black",
        linewidth=1
    )

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%B %d, %I %p'))
    fig.autofmt_xdate()

    ax.set_ylabel("Heat Index (°C)", fontsize=6)

    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.4)

    ax.set_ylim(
        chart_df["heat_index_c"].min() * 0.95,
        chart_df["heat_index_c"].max() * 1.05
    )

    fig.patch.set_alpha(0)      # transparent background
    ax.set_facecolor("none")    # transparent axis

    ax.tick_params(axis='x', labelrotation=45)
    ax.tick_params(axis='both', labelsize=5)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    st.pyplot(fig, use_container_width=True)

st.write("")

max_hi = filtered_df["heat_index_c"].max()
avg_hi = filtered_df["heat_index_c"].mean()
num_locations = filtered_df["adm4"].nunique()

with st.expander("Project notes"):
    st.markdown(
        """
        - Indeks panas dihitung menggunakan formulasi regresi dari US National Weather Service ([lihat di sini](https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml) dan [di sini](https://www.weather.gov/ama/heatindex#:~:text=Table_title:%20What%20is%20the%20heat%20index?%20Table_content:,the%20body:%20Heat%20stroke%20highly%20likely%20%7C)), dengan konversi suhu dari Celsius ke Fahrenheit dan sebaliknya. Formulasi ini pada dasarnya ditujukan untuk wilayah di sekitar Amerika Serikat, sehingga mungkin tidak sepenuhnya akurat untuk kondisi tropis di Jakarta, tetapi tetap memberikan perkiraan risiko panas yang berguna.
        - Tabel batas wilayah administratif diambil dari basis data RBI10K_ADMINISTRASI_DESA_20230928 oleh Badan Informasi Geospasial (BIG).
        - Kode wilayah administratif diambil dari [wilayah.id](https://wilayah.id/) berdasarkan Kepmendagri No 300.2.2-2138 Tahun 2025.
        - Tabel prakiraan cuaca diambil dari Badan Meteorologi, Klimatologi, dan Geofisika (BMKG) yang dapat diakses melalui [Data Prakiraan Cuaca Terbuka](https://data.bmkg.go.id/prakiraan-cuaca/).
        - Semua data diproses dan divisualisasikan menggunakan Python, dan disimpan dalam basis data SQLite.
        
        Penggunaan *generative AI* meliputi: Visual Studio Code Copilot untuk membantu merapikan kode dan menulis komentar dan *docstring*, serta OpenAI ChatGPT untuk identifikasi *runtime error*. Selebihnya, termasuk perumusan masalah dan *brainstorming* kerangka berpikir, perunutan logika dan penulisan kode utama dari *database management* di SQLite hingga visualisasi oleh Streamlit, dikerjakan oleh *author* sepenuhnya tanpa campur tangan *generative AI*.
        """
    )
