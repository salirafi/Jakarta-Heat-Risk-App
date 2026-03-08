import json
import sqlite3
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from shapely import wkt
from shiny import App, reactive, ui, render
from shinywidgets import output_widget, render_widget

from html import escape

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

LANG = {
    "id": {
        "page_title": "Peta dan Prakiraan Risiko Panas Jakarta",
        "page_subtitle": "Informasi indeks dan risiko panas di seluruh wilayah Jakarta berdasarkan data BMKG.",

        "heat_risk_map": "Peta risiko panas",
        "avg_conditions": "Nilai rata-rata parameter setiap kota di Jakarta",
        "avg_note": "Nilai rata-rata untuk temperatur, kelembapan, dan indeks panas yang dihitung dari seluruh kelurahan di kota terkait.",

        "current_conditions": "Kondisi saat ini dan prakiraan terdekat",
        "future_forecast": "Prakiraan di waktu mendatang pada lokasi yang dipilih",
        "heat_index_over_time": "Evolusi indeks panas terhadap waktu pada  lokasi yang dipilih",

        "city_regency": "Kota / Kabupaten",
        "kecamatan": "Kecamatan",
        "kelurahan": "Kelurahan / Desa",

        "temperature": "Temperatur",
        "humidity": "Kelembapan",
        "heat_index": "Indeks Panas",
        "risk": "Risiko",
        "weather": "Cuaca",

        "heat_risk_guide": "Panduan risiko panas",
        "guide_intro": "Klik salah satu tingkat risiko panas untuk melihat definisi, populasi yang rentan, dan tindakan yang disarankan untuk tingkat terkait. Panduan ini berdasarkan ",

        "footer_credit": "© Sayyed Ali Rafi",

        "reference_title": "Catatan dan Referensi",
        "reference_content": """
        1. Indeks panas dihitung menggunakan formulasi regresi dari US National Weather Service ([lihat di sini](https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml) dan [di sini](https://www.weather.gov/ama/heatindex#:~:text=Table_title:%20What%20is%20the%20heat%20index?%20Table_content:,the%20body:%20Heat%20stroke%20highly%20likely%20%7C)), dengan konversi suhu dari Celsius ke Fahrenheit dan sebaliknya. Formulasi ini pada dasarnya ditujukan untuk wilayah di sekitar Amerika Serikat, sehingga mungkin tidak sepenuhnya akurat untuk kondisi tropis di Jakarta, tetapi tetap memberikan perkiraan risiko panas yang berguna.
        
        2. Tabel batas wilayah administratif diambil dari basis data RBI10K_ADMINISTRASI_DESA_20230928 oleh Badan Informasi Geospasial (BIG).

        3. Kode wilayah administratif diambil dari [wilayah.id](https://wilayah.id/) berdasarkan Kepmendagri No 300.2.2-2138 Tahun 2025.

        4. Tabel prakiraan cuaca diambil dari Badan Meteorologi, Klimatologi, dan Geofisika (BMKG) yang dapat diakses melalui [Data Prakiraan Cuaca Terbuka](https://data.bmkg.go.id/prakiraan-cuaca/).
        
        5. Penggunaan *generative AI* meliputi: Visual Studio Code Copilot untuk membantu merapikan kode dan menulis komentar dan *docstring*, serta OpenAI ChatGPT untuk identifikasi *runtime error*. Selebihnya, termasuk perumusan masalah dan *brainstorming* kerangka berpikir, perunutan logika dan penulisan kode utama dari *database management* di SQLite hingga visualisasi oleh Streamlit, dikerjakan oleh *author* sepenuhnya tanpa campur tangan *generative AI*.
        """,
    },

    "en": {
        "page_title": "Jakarta's Heat Risk Map and Forecast",
        "page_subtitle": "Heat index and risk information throughout Jakarta region based on BMKG data. ",

        "heat_risk_map": "Heat risk map",
        "avg_conditions": "Average conditions across Jakarta cities",
        "avg_note": "Averaged across all wards within each city at the selected map time.",

        "current_conditions": "Current conditions and near-term forecast",
        "future_forecast": "Future forecasts at selected location",
        "heat_index_over_time": "Heat index over time at selected location",

        "city_regency": "City / Regency",
        "kecamatan": "Subdistrict",
        "kelurahan": "Ward",

        "temperature": "Temperature",
        "humidity": "Humidity",
        "heat_index": "Heat Index",
        "risk": "Risk",
        "weather": "Weather",

        "heat_risk_guide": "Heat risk guide",
        "guide_intro": "Click a heat risk level below to see what it means, who is most affected, and what actions to take. This guide is based on the ",

        "footer_credit": "© Sayyed Ali Rafi (salirafi8@gmail.com)",

        "reference_title": "Notes and References",
        "reference_content": """
        1. Heat index is computed using the regression formula from the US National Weather Service ([see here](https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml) and [here](https://www.weather.gov/ama/heatindex#:~:text=Table_title:%20What%20is%20the%20heat%20index?%20Table_content:,the%20body:%20Heat%20stroke%20highly%20likely%20%7C)), with Celcius to Fahrenheit conversion and vice versa. The formulation is expected to be valid for US sub-tropical region, but its use for tropical region like Indonesia does not guarantee very accurate results. However, as first-order approximation, this is already sufficient.

        2. Administrative regional border data is retrieved from RBI10K_ADMINISTRASI_DESA_20230928 database provided by Badan Informasi Geospasial (BIG).

        3. Administrative regional code is taken from [wilayah.id](https://wilayah.id/) based on Kepmendagri No 300.2.2-2138 Tahun 2025.

        4. Weather forecast data is taken from the public API of Badan Meteorologi, Klimatologi, dan Geofisika (BMKG) accessed via [Data Prakiraan Cuaca Terbuka](https://data.bmkg.go.id/prakiraan-cuaca/).

        5. The use of generative AI includes: Visual Studio Code's Copilot to help tidying up code and writing comments and docstring, as well as OpenAI's Chat GPT to identify runtime error. Outside of those, including problem formulation and framework of thinking, code logical reasoning and writing, from database management using SQLite to web development using Shiny, all is done solely by the author without the help of generative AI. 
        """,
    }
}

HEAT_RISK_GUIDE = {
    "id": {
        "Lower Risk": {
            "level": "Level 0 · Sedikit hingga Tidak Ada",
            "expect": (
                "Tingkat panas ini menimbulkan sedikit hingga tidak ada peningkatan risiko "
                "bagi kebanyakan orang. Tingkat panas ini sangat umum dan "
                "biasanya tidak memerlukan tindakan pencegahan khusus."
            ),
            "who": (
                "Tidak ada risiko yang berarti bagi sebagian besar populasi."
            ),
            "do": (
                "Biasanya tidak diperlukan tindakan pencegahan khusus. "
                "Cukup menjaga hidrasi dasar dan tetap sadar terhadap kondisi panas."
            ),
        },
        "Caution": {
            "level": "Level 1 · Ringan",
            "expect": (
                "Sebagian besar orang masih dapat mentoleransi panas ini, tetapi ada risiko "
                "ringan terhadap dampak dari panas bagi orang yang sangat sensitif terhadap panas."
            ),
            "who": (
                "Terutama orang yang sangat sensitif terhadap panas, khususnya saat berada di luar "
                "ruangan tanpa pendinginan yang memadai atau tanpa hidrasi yang cukup."
            ),
            "do": (
                "Perbanyak minum, kurangi waktu di luar ruangan di saat matahari yang paling terik, "
                "berteduh, dan manfaatkan udara malam yang lebih sejuk bila memungkinkan."
            ),
        },
        "Extreme Caution": {
            "level": "Level 2 · Sedang",
            "expect": (
                "Banyak orang masih dapat mentoleransi panas ini, tetapi risikonya menjadi lebih "
                "tinggi bagi kelompok rentan akan panas, pendatang atau orang luar yang belum terbiasa dengan "
                "kondisi panas, dan orang yang menghabiskan waktu lama di luar ruangan. "
                "Gangguan kesehatan akibat panas mulai dapat terjadi."
            ),
            "who": (
                "Kelompok rentan terhadap panas, orang tanpa pendinginan atau hidrasi yang memadai, "
                "pendatang atau orang luar yang belum terbiasa dengan panas, serta orang sehat yang terpapar "
                "dalam durasi lama."
            ),
            "do": (
                "Kurangi waktu di bawah sinar matahari di saat-saat yang paling terik, "
                "tetap terhidrasi, tetap berada di tempat yang sejuk, dan tunda atau pindahkan aktivitas luar "
                "ruangan ke jam-jam yang lebih sejuk."
            ),
        },
        "Danger": {
            "level": "Level 3 · Tinggi",
            "expect": (
                "Ini adalah tingkat risiko panas yang tinggi. Kondisi berbahaya dapat memengaruhi "
                "bagian populasi yang jauh lebih besar, terutama siapa pun yang aktif di bawah "
                "matahari atau tanpa pendinginan dan hidrasi yang memadai."
            ),
            "who": (
                "Sebagian besar populasi berisiko, terutama orang tanpa pendinginan yang efektif, "
                "hidrasi yang cukup, atau yang terpapar sinar matahari langsung dalam "
                "waktu lama."
            ),
            "do": (
                "Pertimbangkan untuk membatalkan aktivitas luar ruangan pada waktu terpanas, "
                "tetap terhidrasi, tetap berada di dalam ruangan yang lebih sejuk, dan gunakan AC "
                "jika tersedia. Kipas angin saja mungkin tidak cukup."
            ),
        },
        "Extreme Danger": {
            "level": "Level 4 · Ekstrem",
            "expect": (
                "Ini adalah tingkat risiko panas yang langka dan sangat ekstrem. Kondisi ini "
                "sering mencerminkan kejadian panas berkepanjangan selama beberapa hari dan dapat "
                "berbahaya bagi seluruh populasi, terutama mereka yang tanpa pendinginan memadai."
            ),
            "who": (
                "Semua orang yang terpapar panas berisiko, terutama kelompok rentan terhadap panas "
                "dan orang tanpa pendinginan yang efektif. Pada tingkat ini, kondisi dapat mematikan."
            ),
            "do": (
                "Benar-benar pertimbangkan untuk membatalkan aktivitas luar ruangan, tetap terhidrasi, "
                "tetap berada di tempat yang sejuk termasuk pada malam hari, gunakan AC jika "
                "tersedia, dan periksa tetangga, kerabat, atau orang lain yang rentan."
            ),
        },
    },

    "en": {
        "Lower Risk": {
            "level": "Level 0 · Little to None",
            "expect": (
                "This level of heat poses little to no elevated risk for most people. "
                "It is a very common level of heat and usually does not require special precautions."
            ),
            "who": (
                "No elevated risk for the general population."
            ),
            "do": (
                "No special preventive action is usually needed. "
                "Basic hydration and normal heat awareness are enough."
            ),
        },
        "Caution": {
            "level": "Level 1 · Minor",
            "expect": (
                "Most people can tolerate this heat, but there is a minor risk of heat-related effects "
                "for people who are extremely heat-sensitive."
            ),
            "who": (
                "Primarily people who are extremely sensitive to heat, especially outdoors without "
                "effective cooling or enough hydration."
            ),
            "do": (
                "Increase hydration, reduce time outdoors during the strongest sun, stay in the shade, "
                "and use cooler nighttime air when possible."
            ),
        },
        "Extreme Caution": {
            "level": "Level 2 · Moderate",
            "expect": (
                "Many people can still tolerate this heat, but the risk becomes more noticeable for "
                "heat-sensitive groups, visitors not acclimated to the heat, and people spending long "
                "periods outside. Heat illness can begin to occur."
            ),
            "who": (
                "Heat-sensitive groups, people without effective cooling or hydration, visitors not used "
                "to the heat, and otherwise healthy people exposed for long durations."
            ),
            "do": (
                "Reduce time in the sun during the warmest part of the day, stay hydrated, stay in a cool "
                "place, and move outdoor activities to cooler hours."
            ),
        },
        "Danger": {
            "level": "Level 3 · Major",
            "expect": (
                "This is a major heat risk. Dangerous conditions can affect a much larger part of the "
                "population, especially anyone active in the sun or without proper cooling and hydration."
            ),
            "who": (
                "Much of the population is at risk, especially people without effective cooling, hydration, "
                "or those exposed to direct sun for long periods."
            ),
            "do": (
                "Consider canceling outdoor activity during the hottest part of the day, stay hydrated, "
                "remain in cooler indoor places, and use air conditioning if available. Fans alone may not be enough."
            ),
        },
        "Extreme Danger": {
            "level": "Level 4 · Extreme",
            "expect": (
                "This is a rare and extreme level of heat risk. It often reflects a prolonged multi-day "
                "heat event and can be dangerous for the entire population, especially without cooling."
            ),
            "who": (
                "Everyone exposed to the heat is at risk, especially heat-sensitive groups and people "
                "without effective cooling. This level can become deadly."
            ),
            "do": (
                "Strongly consider canceling outdoor activities, stay hydrated, stay in a cool place "
                "including overnight, use air conditioning if available, and check on neighbors or other vulnerable people."
            ),
        },
    },
}

# ============================================================
# Helpers
# ============================================================

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


def load_forecast_data() -> pd.DataFrame:
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
    ORDER BY local_datetime
    """
    df = run_query(query)

    if df.empty:
        return df

    df["local_datetime"] = pd.to_datetime(df["local_datetime"], errors="coerce")

    for col in ["adm4", "desa_kelurahan", "kecamatan", "kotkab", "risk_level", "weather_desc_en"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    df = df.dropna(subset=["local_datetime"]).reset_index(drop=True)
    return df


def available_map_times(df: pd.DataFrame) -> list[pd.Timestamp]:
    if df.empty:
        return []
    return sorted(pd.to_datetime(df["local_datetime"]).dropna().unique().tolist())


def infer_time_step(times: list[pd.Timestamp]):
    if len(times) < 2:
        return pd.Timedelta(hours=3)

    diffs = pd.Series(times).sort_values().diff().dropna()
    if diffs.empty:
        return pd.Timedelta(hours=3)

    return diffs.mode().iloc[0]


def nearest_available_time(selected_time, map_times: list[pd.Timestamp]):
    if not map_times:
        return None

    if selected_time is None:
        return pd.Timestamp(map_times[0])

    selected_time = pd.Timestamp(selected_time)
    return min(map_times, key=lambda t: abs(pd.Timestamp(t) - selected_time))


def format_timestamp(ts) -> str:
    if ts is None or pd.isna(ts):
        return ""
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M")


def geodata_to_geojson_dict(gdf: gpd.GeoDataFrame) -> dict:
    export_gdf = gdf[["adm4", "geometry"]].copy()
    return json.loads(export_gdf.to_json())


def make_discrete_colorscale():
    """
    Build a stepwise colorscale for numeric z values:
      0 No Data
      1 Lower Risk
      2 Caution
      3 Extreme Caution
      4 Danger
      5 Extreme Danger
    """
    n = len(RISK_ORDER)
    if n == 1:
        return [[0.0, RISK_COLOR_MAP[RISK_ORDER[0]]], [1.0, RISK_COLOR_MAP[RISK_ORDER[0]]]]

    scale = []
    for i, label in enumerate(RISK_ORDER):
        start = i / (n - 1)
        end = i / (n - 1)
        color = RISK_COLOR_MAP[label]
        scale.append([start, color])
        scale.append([end, color])
    return scale


def compute_map_bounds(boundary_gdf: gpd.GeoDataFrame):
    """
    Compute a stable map center from bounding box only.
    This avoids union_all(), which can fail on invalid geometries.
    """
    if boundary_gdf.empty:
        return {"lon": 106.8456, "lat": -6.2088}

    gdf4326 = boundary_gdf.to_crs(4326)
    minx, miny, maxx, maxy = gdf4326.total_bounds

    return {
        "lon": float((minx + maxx) / 2.0),
        "lat": float((miny + maxy) / 2.0),
    }


def build_time_payload(
    boundary_index_df: pd.DataFrame,
    forecast_lookup: dict[pd.Timestamp, pd.DataFrame],
    selected_time,
    risk_label_fn,
):
    """
    Build only the dynamic arrays that change with time:
    - z values (risk codes)
    - customdata for hover
    The polygon geometry and locations stay fixed.
    """
    base_df = boundary_index_df.copy()

    time_df = forecast_lookup.get(pd.Timestamp(selected_time))
    if time_df is None or time_df.empty:
        merged = base_df.copy()
        merged["desa_kelurahan"] = ""
        merged["kecamatan"] = ""
        merged["kotkab"] = ""
        merged["local_datetime"] = ""
        merged["temperature_c"] = np.nan
        merged["humidity_pct"] = np.nan
        merged["heat_index_c"] = np.nan
        merged["risk_level"] = "No Data"
        merged["weather_desc_en"] = ""
    else:
        merged = base_df.merge(time_df, on="adm4", how="left")
        merged["risk_level"] = merged["risk_level"].fillna("No Data")
        merged["desa_kelurahan"] = merged["desa_kelurahan"].fillna("")
        merged["kecamatan"] = merged["kecamatan"].fillna("")
        merged["kotkab"] = merged["kotkab"].fillna("")
        merged["weather_desc_en"] = merged["weather_desc_en"].fillna("")
        merged["local_datetime"] = merged["local_datetime"].apply(format_timestamp)

    z = merged["risk_level"].map(RISK_CODE_MAP).fillna(RISK_CODE_MAP["No Data"]).astype(float).to_numpy()

    customdata = np.column_stack(
        [
            merged["adm4"].astype(str).to_numpy(),
            merged["desa_kelurahan"].astype(str).to_numpy(),
            merged["kecamatan"].astype(str).to_numpy(),
            merged["kotkab"].astype(str).to_numpy(),
            merged["local_datetime"].astype(str).to_numpy(),
            merged["temperature_c"].to_numpy(dtype=object),
            merged["humidity_pct"].to_numpy(dtype=object),
            merged["heat_index_c"].to_numpy(dtype=object),
            merged["risk_level"].apply(risk_label_fn).astype(str).to_numpy(),
            merged["weather_desc_en"].astype(str).to_numpy(),
        ]
    )

    return {
        "z": z,
        "customdata": customdata,
    }


def build_forecast_lookup(forecast_df: pd.DataFrame) -> dict[pd.Timestamp, pd.DataFrame]:
    if forecast_df.empty:
        return {}

    keep_cols = [
        "adm4",
        "desa_kelurahan",
        "kecamatan",
        "kotkab",
        "local_datetime",
        "temperature_c",
        "humidity_pct",
        "heat_index_c",
        "risk_level",
        "weather_desc_en",
    ]

    lookup = {}
    grouped = forecast_df[keep_cols].groupby("local_datetime", sort=True)

    for ts, group in grouped:
        group = (
            group.sort_values(["kotkab", "kecamatan", "desa_kelurahan"])
            .drop_duplicates(subset=["adm4"], keep="last")
            .reset_index(drop=True)
            .copy()
        )
        lookup[pd.Timestamp(ts)] = group

    return lookup


def build_base_figure(
    boundary_geojson: dict,
    locations: list[str],
    initial_payload: dict,
    map_center: dict,
    heat_index_label: str,
) -> go.Figure:
    colorscale = make_discrete_colorscale()

    fig = go.Figure()

    fig.add_trace(
        go.Choropleth(
            geojson=boundary_geojson,
            locations=locations,
            z=initial_payload["z"],
            customdata=initial_payload["customdata"],
            featureidkey="properties.adm4",
            zmin=0,
            zmax=len(RISK_ORDER) - 1,
            colorscale=colorscale,
            showscale=False,
            marker_line_color="rgba(70,70,70,0.8)",
            marker_line_width=0.8,
            hovertemplate=(
                "&nbsp;<b>%{customdata[1]}, %{customdata[2]}</b>&nbsp;<br>"
                # "&nbsp;────────────<br>&nbsp;"
                f"&nbsp;{heat_index_label} %{{customdata[7]:.1f}} °C - %{{customdata[8]}}&nbsp;<br>"
                "&nbsp;%{customdata[9]}&nbsp;"
                "<extra></extra>"
            )
            ),
        )

    fig.update_geos(
        visible=False,
        bgcolor="rgba(0,0,0,0)",
        center=map_center,
        projection_scale=500,
    )

    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hoverlabel=dict(
            bgcolor="rgba(203, 210, 200, 0.4)",
            font_size=13,
            font_family="Arial",
            font_color="#222",
            bordercolor="rgba(0,0,0,0.9)",
            align="left",
            namelength=-1
            )
        )


    return fig


def legend_html(label_fn) -> str:
    items = [
        ("No Data", RISK_COLOR_MAP["No Data"]),
        ("Lower Risk", RISK_COLOR_MAP["Lower Risk"]),
        ("Caution", RISK_COLOR_MAP["Caution"]),
        ("Extreme Caution", RISK_COLOR_MAP["Extreme Caution"]),
        ("Danger", RISK_COLOR_MAP["Danger"]),
        ("Extreme Danger", RISK_COLOR_MAP["Extreme Danger"]),
    ]

    parts = []
    for label, color in items:
        parts.append(
            f"""
            <span class="legend-chip">
                <span class="legend-box" style="background:{color};"></span>
                {label_fn(label)}
            </span>
            """
        )

    return "".join(parts)

def region_filter_options(
    df: pd.DataFrame,
    column: str,
    prior_mask: pd.Series | None = None,
) -> list[str]:
    subset = df if prior_mask is None else df[prior_mask]
    return sorted(
        subset[column]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )


def nearest_available_time_in_df(df: pd.DataFrame, now=None):
    times = available_map_times(df)
    if not times:
        return None

    if now is None:
        now = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None)

    times = pd.to_datetime(pd.Series(times))
    nearest_idx = (times - now).abs().idxmin()
    return pd.Timestamp(times.loc[nearest_idx])


def forecast_at_selected_time(df: pd.DataFrame, selected_time) -> pd.DataFrame:
    if df.empty or selected_time is None:
        return df.iloc[0:0].copy()

    selected_time = pd.Timestamp(selected_time)
    out = df[df["local_datetime"] == selected_time].copy()

    return (
        out.sort_values(["kotkab", "kecamatan", "desa_kelurahan"])
        .reset_index(drop=True)
    )


def hex_to_rgba_css(hex_color: str, alpha: float = 0.18) -> str:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return f"rgba(220,220,220,{alpha})"

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def metric_card_html(label: str, value: str, extra_class: str = "") -> str:
    return f"""
    <div class="metric-card {extra_class}">
        <div class="metric-label">{escape(label)}</div>
        <div class="metric-value">{value}</div>
    </div>
    """


def build_heat_index_plot(
    chart_df: pd.DataFrame,
    heat_index_label: str,
    empty_label: str,
    time_label: str,
) -> go.Figure:
    fig = go.Figure()
    chart_df = chart_df.copy()
    chart_df["local_datetime"] = pd.to_datetime(chart_df["local_datetime"], errors="coerce")
    chart_df = chart_df.dropna(subset=["local_datetime"]).reset_index(drop=True)

    x_values = chart_df["local_datetime"].dt.to_pydatetime()

    if chart_df.empty:
        fig.update_layout(
            height=220,
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[
                dict(
                    text=empty_label,
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=14, color="#666"),
                )
            ],
        )
        return fig

    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=chart_df["heat_index_c"],
            mode="lines+markers",
            line=dict(color="black", width=2),
            marker=dict(size=5),
            hovertemplate=(
                f"{time_label}: %{{x|%b %d %H:%M}}<br>"
                f"{heat_index_label} %{{y:.1f}} °C<extra></extra>"
            ),
        )
    )

    y_min = chart_df["heat_index_c"].min()
    y_max = chart_df["heat_index_c"].max()

    if pd.notna(y_min) and pd.notna(y_max):
        if y_min == y_max:
            y_min -= 1
            y_max += 1
        else:
            pad = 0.05 * (y_max - y_min)
            y_min -= pad
            y_max += pad
    else:
        y_min, y_max = None, None

    fig.update_layout(
        height=220,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(
            title=None,
            tickformat="%b %d %H:%M",
            tickangle=0,
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            title=f"{heat_index_label} (°C)",
            range=[y_min, y_max] if y_min is not None else None,
            gridcolor="rgba(0,0,0,0.08)",
            zeroline=False,
        ),
        hoverlabel=dict(
            bgcolor="rgba(203, 210, 200, 0.4)",
            font_size=13,
            font_family="Arial",
            font_color="#222",
            bordercolor="rgba(0,0,0,0.9)",
            align="left",
            namelength=-1
            )
    )

    return fig

def short_city_name(name: str) -> str:
    if pd.isna(name):
        return ""
    name = str(name).strip()
    return name.replace("Kota Adm. ", "").replace("Kab. Adm. ", "")

def build_city_summary_plot(
    summary_df: pd.DataFrame,
    temperature_label: str,
    humidity_label: str,
    heat_index_label: str,
    empty_label: str,
) -> go.Figure:
    fig = make_subplots(
        rows=1,
        cols=3,
        horizontal_spacing=0.05,
        subplot_titles=(
            f"{temperature_label} (°C)",
            f"{humidity_label} (%)",
            f"{heat_index_label} (°C)",
        ),
    )

    if summary_df.empty:
        fig.update_layout(
            height=320,
            margin=dict(l=0, r=0, t=30, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[
                dict(
                    text=empty_label,
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=14, color="#666"),
                )
            ],
        )
        return fig

    summary_df = summary_df.copy().sort_values("kotkab").reset_index(drop=True)
    summary_df["city_short"] = summary_df["kotkab"].apply(short_city_name)

    city_colors = {
        "Jakarta Barat": "#1f77b4",   # blue
        "Jakarta Pusat": "#17becf",   # cyan
        "Jakarta Selatan": "#8c564b", # brown
        "Jakarta Timur": "#7f7f7f",   # gray
        "Jakarta Utara": "#393b79",   # indigo
    }

    # fallback color if a city is outside the predefined list
    fallback_colors = [
        "#4C6EF5", "#F59F00", "#12B886", "#E8590C", "#C2255C",
        "#7B61FF", "#2F9E44", "#D6336C", "#1098AD", "#6741D9"
    ]

    color_map = {}
    for i, city in enumerate(summary_df["city_short"]):
        color_map[city] = city_colors.get(city, fallback_colors[i % len(fallback_colors)])

    metrics = [
        ("temperature_c", temperature_label),
        ("humidity_pct", humidity_label),
        ("heat_index_c", heat_index_label),
    ]

    # Add one trace per city per subplot
    # Show legend only in the first subplot so there is only one legend
    for col_idx, (metric_col, metric_label) in enumerate(metrics, start=1):
        for _, row in summary_df.iterrows():
            city = row["city_short"]
            value = row[metric_col]

            unit = "°C" if metric_col != "humidity_pct" else "%"

            fig.add_trace(
                go.Bar(
                    x=[city],
                    y=[value],
                    name=city,
                    legendgroup=city,
                    showlegend=(col_idx == 1),
                    marker_color=color_map[city],
                    hovertemplate=(
                        f"{city}<br>{metric_label}: %{{y:.1f}} {unit}<extra></extra>"
                    ),
                ),
                row=1,
                col=col_idx,
            )

    fig.update_layout(
        height=320,
        margin=dict(l=0, r=0, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.10,
            xanchor="left",
            x=0,
            title=None,
        ),
        hoverlabel=dict(
            bgcolor="rgba(203, 210, 200, 0.4)",
            font_size=13,
            font_family="Arial",
            font_color="#222",
            bordercolor="rgba(0,0,0,0.9)",
            align="left",
            namelength=-1,
        ),
    )

    fig.update_xaxes(
        title=None,
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        showline=True,
        linecolor="rgba(0,0,0,0.35)",
        linewidth=1,
    )

    fig.update_yaxes(
        # title="°C",
        row=1,
        col=1,
        title_standoff=5,
        gridcolor="rgba(0,0,0,0.08)",
        zeroline=False,
    )
    fig.update_yaxes(
        # title="%",
        row=1,
        col=2,
        title_standoff=5,
        gridcolor="rgba(0,0,0,0.08)",
        zeroline=False,
    )
    fig.update_yaxes(
        # title="°C",
        row=1,
        col=3,
        title_standoff=5,
        gridcolor="rgba(0,0,0,0.08)",
        zeroline=False,
    )

    return fig

def guide_button_id(level: str) -> str:
    return {
        "Lower Risk": "guide_lower_risk",
        "Caution": "guide_caution",
        "Extreme Caution": "guide_extreme_caution",
        "Danger": "guide_danger",
        "Extreme Danger": "guide_extreme_danger",
    }[level]

# ============================================================
# UI
# ============================================================
app_ui = ui.page_fluid(
    ui.tags.style("""
        body {
            background: rgba(232, 80, 80, 0.1);
        }
        .language-toggle-wrap {
            display: flex;
            justify-content: flex-end;
            align-items: flex-start;
            margin-top: 1.8rem;
            margin-right: 2rem;
        }

        .language-toggle-group {
            display: inline-flex;
            align-items: center;
            gap: 0.2rem;
            padding: 0.22rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.75);
            border: 1px solid rgba(0,0,0,0.08);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        .language-toggle-btn {
            border: none;
            background: transparent;
            border-radius: 999px;
            padding: 0.38rem 0.78rem;
            font-size: 0.95rem;
            font-weight: 600;
            color: #555555;
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .language-toggle-btn.active {
            background: white;
            color: #111111;
            box-shadow: 0 1px 4px rgba(0,0,0,0.10);
        }

        .language-toggle-btn:hover {
            color: #111111;
        }

        .language-toggle-flag {
            width: 18px;
            height: 12px;
            object-fit: cover;
            border-radius: 2px;
        }

        .language-toggle-label {
            line-height: 1;
        }
        .page-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.01em;
            margin-top: 1.5rem;
            margin-left: 0.1rem;
        }
        .title-block {
            margin-left: 0.1rem;
        }
        .page-subtitle {
            font-size: 1.2rem;
            font-weight: 400;
            margin-bottom: 1rem;
            margin-left: 0.1rem;
        }
        .panel-box {
            background: rgba(224, 182, 154, 0.2);
            border-radius: 14px;
            padding: 1rem 1rem 0.9rem 1rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.06);
        }
        .panel-title {
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 0.6rem;
            color: #111111;
        }
        .panel-subtitle {
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 0.6rem;
            color: #111111;
        }

        .legend-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.6rem 1rem;
            margin-top: 0.2rem;
            margin-bottom: 0.8rem;
        }

        .legend-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            font-size: 0.92rem;
            color: #333333;
            white-space: nowrap;
        }

        .legend-box {
            width: 14px;
            height: 14px;
            border: 1px solid rgba(0,0,0,0.35);
            display: inline-block;
            border-radius: 2px;
        }

        .caption {
            color: #666666;
            font-size: 0.95rem;
        }
                  
        .filter-block {
            margin-bottom: 0.001rem;
        }

        .shiny-input-container {
            margin-bottom: 0.1rem;
        }

        .current-time-caption {
            color: #222222;
            font-size: 1.15rem;
            font-weight: 700;
            margin-top: 0.001rem;
            margin-bottom: 0.95rem;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.7rem;
            margin-bottom: 0.3rem;
        }

        .metric-grid.metric-grid-5 {
            grid-template-columns: repeat(5, minmax(0, 1fr));
        }

        .metric-card {
            background: rgba(0,0,0,0.05);
            border: 1px solid rgba(0,0,0,0.2);
            border-radius: 12px;
            padding: 0.8rem 0.85rem;
            min-height: 86px;
        }
        .metric-card-weather .metric-value {
            # font-size: 1.05rem;
            line-height: 1.3;
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: break-word;
        }
        .metric-label {
            font-size: 0.82rem;
            color: #666666;
            margin-bottom: 0.35rem;
        }

        .metric-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: #111111;
            line-height: 1.25;
            width: 100%;
            overflow: hidden;
        }

        .forecast-scroll {
            overflow-x: auto;
            overflow-y: hidden;
            white-space: nowrap;
            padding-bottom: 0.25rem;
            background: transparent;
            scrollbar-color: rgba(120,120,120,0.85) transparent;
            scrollbar-width: auto;
        }

        .forecast-card {
            display: inline-block;
            vertical-align: top;
            min-width: 165px;
            margin-right: 12px;
            border: 1px solid rgba(0,0,0,0.08);
            border-radius: 12px;
            padding: 0.8rem 0.9rem;
            box-shadow: 0 1px 6px rgba(0,0,0,0.04);
        }

        .forecast-card:hover {
            transform: translateY(-2px);
            transition: 0.15s ease;
        }

        .forecast-card-title {
            font-weight: 700;
            margin-bottom: 0.3rem;
            color: #111111;
        }

        .forecast-card-hi {
            font-size: 0.95rem;
            margin-bottom: 0.45rem;
        }

        .forecast-card-risk {
            margin-bottom: 0.45rem;
        }

        .forecast-card-time {
            font-size: 0.82rem;
            color: #555555;
        }

        .empty-note {
            color: #666666;
            font-size: 0.95rem;
        }

        @media (max-width: 1100px) {
            .metric-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        .js-irs-0 {
            margin-bottom: 0.75rem;
        }
        # .irs {
        #     font-family: inherit;
        # }
        .irs--shiny .irs-line {
            height: 10px;
            border-radius: 999px;
            background: #e5e7eb;
            border: none;
        }
        .irs--shiny .irs-bar {
            height: 10px;
            border-radius: 999px;
            background: #f59e0b;
            border: none;
        }
        .irs--shiny .irs-handle {
            top: 22px;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: white;
            border: 2px solid #d97706;
            box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        }
        .irs--shiny .irs-single,
        .irs--shiny .irs-from,
        .irs--shiny .irs-to {
            background: #111827;
            color: white;
            border-radius: 8px;
            padding: 2px 8px;
            font-size: 0.82rem;
        }
        .irs--shiny .irs-grid-text {
            color: #666666;
            font-size: 0.75rem;
        }
        .shiny-input-container label {
            font-weight: 600;
            color: #222222;
            margin-bottom: 0.35rem;
        }
        .time-slider-wrap label {
            font-weight: 700;
            color: #111111;
            margin-bottom: 0.35rem;
        }
        .time-slider-wrap {
            margin-bottom: 0.8rem;
        }

        .time-slider-wrap .shiny-input-container {
            margin-bottom: 0.2rem;
        }

        .time-slider-wrap .irs {
            margin-top: 0.1rem;
        }

        .time-slider-wrap .irs--shiny .irs-line {
            top: 25px !important;
            height: 8px !important;
            border-radius: 999px;
            background: #d1d5db;
            border: none;
        }

        .time-slider-wrap .irs--shiny .irs-bar {
            top: 25px !important;
            height: 8px !important;
            border-radius: 999px;
            background: #f59e0b;
            border: none;
        }

        .time-slider-wrap .irs--shiny .irs-handle {
            top: 21px !important;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #ffffff;
            border: 2px solid #d97706;
            box-shadow: 0 1px 4px rgba(0,0,0,0.15);
        }

        .time-slider-wrap .irs--shiny .irs-single,
        .time-slider-wrap .irs--shiny .irs-from,
        .time-slider-wrap .irs--shiny .irs-to {
            background: #111827;
            color: white;
            border-radius: 8px;
            padding: 2px 8px;
            font-size: 0.82rem;
        }

        .time-slider-wrap .irs--shiny .irs-min,
        .time-slider-wrap .irs--shiny .irs-max {
            font-size: 0.68rem;
            color: #4b5563;
            background: rgba(255,255,255,0);
            border-radius: 4px;
            padding: 1px 4px;
            line-height: 1.1;
            top: 8px; # larger means closer to the slider
        }
        .map-time-caption {
            margin-top: 0.45rem;
            font-size: 0.95rem;
            font-weight: 600;
            color: #222222;
        }
        .js-plotly-plot {
            margin: 0 !important;
            padding: 0 !important;
        }
        .plotly {
            margin: 0 !important;
        }
        .risk-guide-intro {
            margin-top: -0.15rem;
            margin-bottom: 0.7rem;
        }

        .risk-guide-list {
            display: flex;
            flex-direction: column;
            gap: 0.55rem;
        }

        .risk-guide-list-hidden-inputs {
            display: none;
        }

        .risk-guide-item {
            width: 100%;
            border: 1px solid rgba(0,0,0,0.12);
            background: rgba(0,0,0,0.04);
            border-radius: 12px;
            padding: 0.75rem 0.9rem;
            text-align: left;
            cursor: pointer;
            transition: 0.15s ease;
        }

        .risk-guide-item:hover {
            background: rgba(0,0,0,0.06);
            transform: translateY(-1px);
        }

        .risk-guide-item-inner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
        }

        .risk-guide-item-left {
            display: inline-flex;
            align-items: center;
            gap: 0.6rem;
        }

        .risk-guide-dot {
            width: 14px;
            height: 14px;
            border-radius: 999px;
            border: 1px solid rgba(0,0,0,0.18);
            display: inline-block;
            flex: 0 0 14px;
        }

        .risk-guide-item-title {
            font-size: 1rem;
            font-weight: 700;
            color: #111111;
        }

        .risk-guide-item-right {
            font-size: 0.9rem;
            color: #666666;
            font-weight: 600;
        }

        .risk-guide-modal-header {
            display: flex;
            align-items: center;
            gap: 0.65rem;
            margin-bottom: 1rem;
        }

        .risk-guide-modal-title {
            font-size: 1.25rem;
            font-weight: 800;
            color: #111111;
        }

        .risk-guide-modal-section + .risk-guide-modal-section {
            margin-top: 1rem;
        }

        .risk-guide-modal-label {
            font-size: 0.88rem;
            font-weight: 700;
            color: #666666;
            margin-bottom: 0.25rem;
        }

        .risk-guide-modal-text {
            font-size: 1rem;
            line-height: 1.5;
            color: #222222;
        }
        .city-summary-note {
            color: #666666;
            font-size: 0.9rem;
            margin-top: -0.2rem;
            margin-bottom: 0.6rem;
        }
        .main-panels {
            align-items: stretch;
        }

        .main-panel {
            height: 100%;
            display: flex;
        }

        .main-panel .panel-box {
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
        }
        .notes-references {
            font-size: 0.9rem;
            line-height: 1.5;
        }

        .notes-references p {
            margin-bottom: 0.5rem;
        }
        .footer-section {
            margin-top: 2rem;
            margin-bottom: 1rem;
            padding-top: 0.8rem;
        }

        .footer-text {
            text-align: center;
            font-size: 0.9rem;
            color: #555555;
        }
        }
    """),

    ui.layout_columns(

        ui.div(
            ui.output_ui("page_title_ui"),
            ui.output_ui("page_subtitle_ui"),
            class_="title-block"
        ),

        ui.div(
            ui.output_ui("language_toggle_ui"),
            class_="language-toggle-wrap"
        ),

        col_widths=[10,2],
    ),

    ui.layout_columns(
        ui.div(
            ui.div(
                ui.output_ui("heat_map_title"),
                ui.output_ui("time_slider_ui"),
                output_widget("boundary_map"),
                ui.output_ui("map_legend"),
                ui.hr(style="margin: 0.8rem 0 0.8rem 0;"),
                ui.output_ui("avg_conditions_title"),
                ui.output_ui("avg_conditions_note"),
                output_widget("city_summary_plot"),
                class_="panel-box",
            ),
            class_="main-panel",
        ),
        ui.div(
            ui.div(
                ui.output_ui("current_conditions_title"),
                ui.layout_columns(
                    ui.output_ui("kotkab_ui"),
                    ui.output_ui("kecamatan_ui"),
                    ui.output_ui("kelurahan_ui"),
                    col_widths=[4, 4, 4],
                ),
                ui.output_ui("current_time_caption"),
                ui.output_ui("current_metrics_ui"),
                ui.hr(style="margin: 1rem 0 0.8rem 0;"),
                ui.output_ui("future_forecast_title"),
                ui.output_ui("future_forecast_cards_ui"),
                ui.hr(style="margin: 1rem 0 0.8rem 0;"),
                ui.output_ui("heat_index_over_time_title"),
                output_widget("heat_index_evolution_plot"),
                class_="panel-box",
            ),
            class_="main-panel",
        ),
        col_widths=[6, 6],
        class_="main-panels",
    ),

    ui.div(
        ui.output_ui("heat_risk_guide_ui"),
        style="margin-top: 1rem;",
    ),

    ui.output_ui("reference_ui"),

    ui.output_ui("footer_ui"),
)


# ============================================================
# SERVER
# ============================================================
def server(input, output, session):

    def lang_text(id_text: str, en_text: str) -> str:
        return id_text if language.get() == "id" else en_text

    def month_label(ts) -> str:
        if ts is None or pd.isna(ts):
            return ""
        ts = pd.Timestamp(ts)

        if language.get() == "en":
            return ts.strftime("%B %d %Y, %H:%M")

        bulan = {
            1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
            5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
            9: "September", 10: "Oktober", 11: "November", 12: "Desember",
        }
        return f"{ts.day:02d} {bulan[ts.month]} {ts.year}, {ts.hour:02d}:{ts.minute:02d}"

    def month_label_short(ts) -> str:
        if ts is None or pd.isna(ts):
            return ""
        ts = pd.Timestamp(ts)

        if language.get() == "en":
            return ts.strftime("%b %d %Y, %H:%M")

        bulan = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
            5: "Mei", 6: "Jun", 7: "Jul", 8: "Agu",
            9: "Sep", 10: "Okt", 11: "Nov", 12: "Des",
        }
        return f"{bulan[ts.month]} {ts.day:02d} {ts.year}, {ts.hour:02d}:{ts.minute:02d}"

    language = reactive.Value("id")

    def risk_label(level: str) -> str:
        labels = {
            "No Data": ("Tidak ada data", "No Data"),
            "Lower Risk": ("Risiko Rendah", "Lower Risk"),
            "Caution": ("Waspada", "Caution"),
            "Extreme Caution": ("Waspada Tinggi", "Extreme Caution"),
            "Danger": ("Bahaya", "Danger"),
            "Extreme Danger": ("Bahaya Ekstrem", "Extreme Danger"),
        }
        return labels.get(level, (level, level))[0 if language.get() == "id" else 1]

    def risk_badge(level: str) -> str:
        if level == "Extreme Danger":
            return f"🚨 {risk_label(level)}"
        if level == "Danger":
            return f"🔴 {risk_label(level)}"
        if level == "Extreme Caution":
            return f"🟠 {risk_label(level)}"
        if level == "Caution":
            return f"🟡 {risk_label(level)}"
        if level == "Lower Risk":
            return f"🟢 {risk_label(level)}"
        return f"⚪ {risk_label('No Data')}"

    def tr(key):
        lang = language.get()
        return LANG.get(lang, LANG["id"]).get(key, key)

    @reactive.effect
    def _sync_language_toggle():
        selected = input.language_toggle()
        if selected in ("id", "en"):
            language.set(selected)

    @output
    @render.ui
    def language_toggle_ui():
        current_lang = language.get()

        def toggle_button(value: str, flag_url: str, label: str):
            active_class = "language-toggle-btn active" if current_lang == value else "language-toggle-btn"

            return ui.tags.button(
                ui.tags.img(
                    src=flag_url,
                    class_="language-toggle-flag",
                ),
                ui.tags.span(label, class_="language-toggle-label"),
                type="button",
                class_=active_class,
                onclick=f"Shiny.setInputValue('language_toggle', '{value}', {{priority: 'event'}})",
            )

        return ui.div(
            toggle_button("id", "https://flagcdn.com/id.svg", "ID"),
            toggle_button("en", "https://flagcdn.com/us.svg", "EN"),
            class_="language-toggle-group",
        )

    @output
    @render.ui
    def page_title_ui():
        return ui.div(tr("page_title"), class_="page-title")

    @output
    @render.ui
    def page_subtitle_ui():
        return ui.div(tr("page_subtitle"),
                    class_="page-subtitle")

    @output
    @render.ui
    def heat_map_title():
        return ui.h4(tr("heat_risk_map"), class_="panel-title")

    @output
    @render.ui
    def avg_conditions_title():
        return ui.h5(tr("avg_conditions"), class_="panel-subtitle")

    @output
    @render.ui
    def avg_conditions_note():
        return ui.p(tr("avg_note"), class_="city-summary-note")

    @output
    @render.ui
    def current_conditions_title():
        return ui.h4(tr("current_conditions"), class_="panel-title")

    @output
    @render.ui
    def future_forecast_title():
        return ui.h5(tr("future_forecast"), class_="panel-subtitle")

    @output
    @render.ui
    def heat_index_over_time_title():
        return ui.h5(tr("heat_index_over_time"), class_="panel-subtitle")

    @output
    @render.ui
    def heat_risk_guide_title():
        return ui.h4(tr("heat_risk_guide"), class_="panel-title")

    @output
    @render.ui
    def guide_intro_tr():
        return ui.p(
                tr("guide_intro"),
                ui.a(
                    "U.S. National Weather Service HeatRisk Guide",
                    href="https://www.wpc.ncep.noaa.gov/heatrisk/",
                    target="_blank"
                ),
                ".",
                class_="caption risk-guide-intro",
            )

    def show_heat_risk_modal(level: str):
        guide = HEAT_RISK_GUIDE[language.get()][level]

        modal = ui.modal(
            ui.div(
                ui.div(
                    ui.tags.span(
                        "",
                        class_="risk-guide-dot",
                        style=f"background:{RISK_COLOR_MAP[level]}; width:16px; height:16px;"
                    ),
                    ui.div(
                        ui.tags.div(risk_label(level), class_="risk-guide-modal-title"),
                        ui.tags.div(guide["level"], class_="caption"),
                    ),
                    class_="risk-guide-modal-header",
                ),
                ui.div(
                    ui.tags.div(lang_text("Hal-hal yang perlu diantisipasi", "What to expect"), class_="risk-guide-modal-label"),
                    ui.tags.div(guide["expect"], class_="risk-guide-modal-text"),
                    class_="risk-guide-modal-section",
                ),
                ui.div(
                    ui.tags.div(lang_text("Populasi yang paling rentan", "Who is most at risk"), class_="risk-guide-modal-label"),
                    ui.tags.div(guide["who"], class_="risk-guide-modal-text"),
                    class_="risk-guide-modal-section",
                ),
                ui.div(
                    ui.tags.div(lang_text("Tindakan yang disarankan", "Recommended actions"), class_="risk-guide-modal-label"),
                    ui.tags.div(guide["do"], class_="risk-guide-modal-text"),
                    class_="risk-guide-modal-section",
                ),
            ),
            title=None,
            easy_close=True,
            footer=None,
        )
        ui.modal_show(modal)

    @reactive.calc
    def app_data():
        if not DB_PATH.exists():
            return {"error": lang_text("File database 'heat_risk.db' tidak ditemukan", "Database file 'heat_risk.db' was not found")}

        existing_tables = set(get_table_names())

        if BOUNDARY_TABLE not in existing_tables:
            return {"error": lang_text(f"Tabel '{BOUNDARY_TABLE}' tidak ditemukan", f"Table '{BOUNDARY_TABLE}' was not found")}

        if FORECAST_TABLE not in existing_tables:
            return {"error": lang_text(f"Tabel '{FORECAST_TABLE}' tidak ditemukan", f"Table '{FORECAST_TABLE}' was not found")}

        boundary_gdf = load_boundary_data()
        forecast_df = load_forecast_data()

        if boundary_gdf.empty:
            return {"error": lang_text("Tabel batas wilayah kosong", "Boundary table is empty")}

        if forecast_df.empty:
            return {"error": lang_text("Tabel prakiraan kosong", "Forecast table is empty")}

        boundary_index_df = boundary_gdf[["adm4"]].copy().sort_values("adm4").reset_index(drop=True)

        return {
            "error": None,
            "boundary_gdf": boundary_gdf,
            "boundary_index_df": boundary_index_df,
            "forecast_df": forecast_df,
        }

    @reactive.calc
    def forecast_times():
        data = app_data()
        if data["error"] is not None:
            return []
        return available_map_times(data["forecast_df"])

    @reactive.calc
    def boundary_geojson():
        data = app_data()
        if data["error"] is not None:
            return None
        return geodata_to_geojson_dict(data["boundary_gdf"])

    @reactive.calc
    def forecast_lookup():
        data = app_data()
        if data["error"] is not None:
            return {}
        return build_forecast_lookup(data["forecast_df"])

    @reactive.calc
    def map_center():
        data = app_data()
        if data["error"] is not None:
            return {"lon": 106.8456, "lat": -6.2088}
        return compute_map_bounds(data["boundary_gdf"])

    @reactive.calc
    def city_summary_df():
        data = app_data()
        if data["error"] is not None:
            return pd.DataFrame()

        df = data["forecast_df"].copy()
        times = forecast_times()
        if df.empty or not times:
            return pd.DataFrame()

        selected_time = nearest_available_time(input.selected_time(), times)
        if selected_time is None:
            return pd.DataFrame()

        snap = df[df["local_datetime"] == pd.Timestamp(selected_time)].copy()
        if snap.empty:
            return pd.DataFrame()

        summary = (
            snap.groupby("kotkab", as_index=False)
            .agg(
                temperature_c=("temperature_c", "mean"),
                humidity_pct=("humidity_pct", "mean"),
                heat_index_c=("heat_index_c", "mean"),
            )
            .sort_values("kotkab")
            .reset_index(drop=True)
        )

        return summary

    @output
    @render.ui
    def time_slider_ui():
        times = forecast_times()

        if not times:
            return ui.p(
                        lang_text("Tidak ada timestamp prakiraan yang valid.", "No valid forecast timestamps found."),
                        class_="caption",
                    )

        min_time = pd.Timestamp(times[0]).to_pydatetime()
        max_time = pd.Timestamp(times[-1]).to_pydatetime()
        step = infer_time_step(times).to_pytimedelta()

        now_time = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None)
        time_series = pd.Series(times)
        nearest_idx = (time_series - now_time).abs().idxmin()
        default_time = pd.Timestamp(time_series.loc[nearest_idx]).to_pydatetime()

        return ui.div(
            ui.input_slider(
                "selected_time",
                None,
                min=min_time,
                max=max_time,
                value=default_time,
                step=step,
                ticks=False,
                width="100%",
                time_format="%b %d %Y, %H:%M",
                timezone="+0700",
            ),
            ui.output_ui("selected_map_time_text"),
            class_="time-slider-wrap",
        )
    
    @output
    @render.ui
    def selected_map_time_text():
        times = forecast_times()
        if not times:
            return ui.div(
                lang_text("Waktu di peta: Tidak ada data", "Map time: No data"),
                class_="map-time-caption",
            )

        raw_value = input.selected_time()
        selected_time = nearest_available_time(raw_value, times)

        if selected_time is None:
            return ui.div(
                lang_text("Waktu di peta: Tidak ada data", "Map time: No data"),
                class_="map-time-caption",
            )

        label = pd.Timestamp(selected_time).strftime("%b %d %Y, %H:%M")
        return ui.div(
            lang_text(f"Waktu di peta: {label} WIB", f"Map time: {label} WIB"),
            class_="map-time-caption",
        )

    @render_widget
    def boundary_map():
        data = app_data()
        err = data["error"]

        if err is not None:
            fig = go.Figure()
            fig.update_layout(
                title=err,
                margin=dict(l=0, r=0, t=0, b=0),
                height=520,
                mapbox=dict(
                    domain=dict(x=[0,1], y=[0,1])
                )
            )
            return fig

        times = forecast_times()
        if not times:
            fig = go.Figure()
            fig.update_layout(
                title=lang_text("Tidak ada timestamp prakiraan yang valid", "No valid forecast timestamps found"),
                margin=dict(l=0, r=0, t=0, b=0),
                height=520,
                mapbox=dict(
                    domain=dict(x=[0,1], y=[0,1])
                )
            )
            return fig

        initial_time = pd.Timestamp(times[0])

        payload = build_time_payload(
            boundary_index_df=data["boundary_index_df"],
            forecast_lookup=forecast_lookup(),
            selected_time=initial_time,
            risk_label_fn=risk_label,
        )

        return build_base_figure(
            boundary_geojson=boundary_geojson(),
            locations=data["boundary_index_df"]["adm4"].tolist(),
            initial_payload=payload,
            map_center=map_center(),
            heat_index_label=tr("heat_index"),
        )

    @reactive.effect
    def _update_map_in_place():
        data = app_data()
        if data["error"] is not None:
            return

        times = forecast_times()
        if not times:
            return

        selected_time = nearest_available_time(input.selected_time(), times)
        if selected_time is None:
            return

        payload = build_time_payload(
            boundary_index_df=data["boundary_index_df"],
            forecast_lookup=forecast_lookup(),
            selected_time=selected_time,
            risk_label_fn=risk_label,
        )

        widget = boundary_map.widget
        if widget is None or len(widget.data) == 0:
            return

        # Update only dynamic trace data.
        widget.data[0].z = payload["z"]
        widget.data[0].customdata = payload["customdata"]

    @output
    @render.ui
    def map_legend():
        return ui.div(
            ui.HTML(legend_html(risk_label)),
            class_="legend-row",
        )
    
    @output
    @render.ui
    def kotkab_ui():
        data = app_data()
        if data["error"] is not None:
            return ui.p(lang_text("Tidak ada data wilayah.", "No region data."), class_="caption")

        choices = region_filter_options(data["forecast_df"], "kotkab")
        selected = choices[0] if choices else None

        return ui.div(
            ui.input_select(
                "selected_kotkab",
                tr("city_regency"),
                choices=choices,
                selected=selected,
            ),
            class_="filter-block",
        )

    @output
    @render.ui
    def kecamatan_ui():
        data = app_data()
        if data["error"] is not None:
            return ui.p(lang_text("Tidak ada data wilayah.", "No region data."), class_="caption")

        df = data["forecast_df"]
        selected_kotkab = input.selected_kotkab()
        mask_kotkab = df["kotkab"] == selected_kotkab if selected_kotkab else pd.Series(False, index=df.index)

        choices = region_filter_options(df, "kecamatan", prior_mask=mask_kotkab)
        selected = choices[0] if choices else None

        return ui.div(
            ui.input_select(
                "selected_kecamatan",
                tr("kecamatan"),
                choices=choices,
                selected=selected,
            ),
            class_="filter-block",
        )

    @output
    @render.ui
    def kelurahan_ui():
        data = app_data()
        if data["error"] is not None:
            return ui.p(lang_text("Tidak ada data wilayah.", "No region data."), class_="caption")

        df = data["forecast_df"]
        selected_kotkab = input.selected_kotkab()
        selected_kecamatan = input.selected_kecamatan()

        mask = pd.Series(True, index=df.index)
        if selected_kotkab:
            mask &= df["kotkab"] == selected_kotkab
        if selected_kecamatan:
            mask &= df["kecamatan"] == selected_kecamatan

        choices = region_filter_options(df, "desa_kelurahan", prior_mask=mask)
        selected = choices[0] if choices else None

        return ui.div(
            ui.input_select(
                "selected_kelurahan",
                tr("kelurahan"),
                choices=choices,
                selected=selected,
            ),
            class_="filter-block",
        )
    
    @reactive.calc
    def selected_region_df():
        data = app_data()
        if data["error"] is not None:
            return pd.DataFrame()

        df = data["forecast_df"].copy()

        selected_kotkab = input.selected_kotkab()
        selected_kecamatan = input.selected_kecamatan()
        selected_kelurahan = input.selected_kelurahan()

        if selected_kotkab:
            df = df[df["kotkab"] == selected_kotkab]
        if selected_kecamatan:
            df = df[df["kecamatan"] == selected_kecamatan]
        if selected_kelurahan:
            df = df[df["desa_kelurahan"] == selected_kelurahan]

        return df.copy()

    @reactive.calc
    def current_time_for_metrics():
        return nearest_available_time_in_df(selected_region_df())

    @reactive.calc
    def current_snapshot():
        df = selected_region_df()
        ts = current_time_for_metrics()
        return forecast_at_selected_time(df, ts)

    @reactive.calc
    def future_forecast_df():
        df = selected_region_df()
        ts = current_time_for_metrics()

        if df.empty or ts is None:
            return df.iloc[0:0].copy()

        return (
            df[df["local_datetime"] > ts]
            .sort_values("local_datetime")
            .copy()
        )

    @reactive.calc
    def heat_index_series_df():
        df = selected_region_df()
        if df.empty:
            return pd.DataFrame(columns=["local_datetime", "heat_index_c"])

        chart_df = (
            df.groupby("local_datetime", as_index=False)["heat_index_c"]
            .mean()
            .sort_values("local_datetime")
            .reset_index(drop=True)
        )
        return chart_df
    
    @output
    @render.ui
    def current_time_caption():
        now_local = pd.Timestamp.now(tz="Asia/Jakarta")
        label = month_label(now_local)
        return ui.div(f"{label} WIB", class_="current-time-caption")

    @output
    @render.ui
    def current_metrics_ui():
        snap = current_snapshot()

        avg_temp = snap["temperature_c"].mean() if not snap.empty else np.nan
        avg_hum = snap["humidity_pct"].mean() if not snap.empty else np.nan
        avg_hi = snap["heat_index_c"].mean() if not snap.empty else np.nan

        dominant_risk = (
            snap["risk_level"].mode().iloc[0]
            if not snap.empty and not snap["risk_level"].mode().empty
            else lang_text("Tidak ada data", "No data")
        )

        dominant_weather = (
            snap["weather_desc_en"].mode().iloc[0]
            if not snap.empty and not snap["weather_desc_en"].mode().empty
            else lang_text("Tidak ada data", "No data")
        )

        html = "".join([
            metric_card_html(tr("temperature"), f"{avg_temp:.1f} °C" if pd.notna(avg_temp) else "No data"),
            metric_card_html(tr("humidity"), f"{avg_hum:.1f} %" if pd.notna(avg_hum) else "No data"),
            metric_card_html(tr("heat_index"), f"{avg_hi:.1f} °C" if pd.notna(avg_hi) else "No data"),
            metric_card_html(tr("risk"), escape(risk_label(dominant_risk))),
            metric_card_html(tr("weather"), escape(dominant_weather), extra_class="metric-card-weather"),
        ])

        return ui.div(ui.HTML(html), class_="metric-grid metric-grid-5")
    
    @output
    @render.ui
    def future_forecast_cards_ui():
        df = future_forecast_df()

        if df.empty:
            return ui.div(
                lang_text("Tidak ada prakiraan mendatang yang tersedia.", "No future forecasts available."),
                class_="empty-note",
            )

        cards = []
        for _, row in df.iterrows():
            if pd.isna(row["heat_index_c"]):
                continue

            risk_level = row["risk_level"] if pd.notna(row["risk_level"]) else "No Data"
            bg_color = hex_to_rgba_css(RISK_COLOR_MAP.get(risk_level, "#dcdcdc"), alpha=0.18)

            cards.append(
                f"""
                <div class="forecast-card" style="background:{bg_color};">
                    <div class="forecast-card-title">{escape(str(row["desa_kelurahan"]))}</div>
                    <div class="forecast-card-hi">{tr("heat_index")}: {row["heat_index_c"]:.1f} °C</div>
                    <div class="forecast-card-risk">{escape(risk_badge(risk_level))}</div>
                    <div class="forecast-card-time">
                        {month_label(pd.Timestamp(row["local_datetime"]))}
                    </div>
                </div>
                """
            )

        if not cards:
            return ui.div(
                lang_text("Tidak ada prakiraan mendatang yang tersedia.", "No future forecasts available."),
                class_="empty-note",
            )
        return ui.div(ui.HTML("".join(cards)), class_="forecast-scroll")
    
    @render_widget
    def heat_index_evolution_plot():
        return build_heat_index_plot(
            heat_index_series_df(),
            heat_index_label=tr("heat_index"),
            empty_label=lang_text("Data indeks panas tidak tersedia", "No heat index data available"),
            time_label=lang_text("Waktu", "Time"),
        )

    @render_widget
    def city_summary_plot():
        return build_city_summary_plot(
            city_summary_df(),
            temperature_label=tr("temperature"),
            humidity_label=tr("humidity"),
            heat_index_label=tr("heat_index"),
            empty_label=lang_text("Data ringkasan kota tidak tersedia", "No city summary data available"),
        )

    @output
    @render.ui
    def heat_risk_guide_ui():
        levels = ["Lower Risk", "Caution", "Extreme Caution", "Danger", "Extreme Danger"]

        return ui.div(
            ui.output_ui("heat_risk_guide_title"),
            ui.output_ui("guide_intro_tr"),
            ui.div(
                *[
                    ui.input_action_button(
                        guide_button_id(level),
                        label="",
                        icon=None,
                        class_="risk-guide-item-btn",
                    )
                    for level in levels
                ],
                class_="risk-guide-list-hidden-inputs",
            ),
            ui.div(
                *[
                    ui.tags.button(
                        ui.tags.span(
                            ui.tags.span(
                                ui.tags.span(
                                    "",
                                    class_="risk-guide-dot",
                                    style=f"background:{RISK_COLOR_MAP[level]};"
                                ),
                                ui.tags.span(risk_label(level), class_="risk-guide-item-title"),
                                class_="risk-guide-item-left",
                            ),
                            ui.tags.span(lang_text("Lihat", "View"), class_="risk-guide-item-right"),
                            class_="risk-guide-item-inner",
                        ),
                        id=f"{guide_button_id(level)}_proxy",
                        class_="risk-guide-item",
                        type="button",
                        onclick=f"document.getElementById('{guide_button_id(level)}').click();",
                    )
                    for level in levels
                ],
                class_="risk-guide-list",
            ),
        )

    @reactive.effect
    @reactive.event(input.guide_lower_risk)
    def _show_lower_risk_modal():
        show_heat_risk_modal("Lower Risk")

    @reactive.effect
    @reactive.event(input.guide_caution)
    def _show_caution_modal():
        show_heat_risk_modal("Caution")

    @reactive.effect
    @reactive.event(input.guide_extreme_caution)
    def _show_extreme_caution_modal():
        show_heat_risk_modal("Extreme Caution")

    @reactive.effect
    @reactive.event(input.guide_danger)
    def _show_danger_modal():
        show_heat_risk_modal("Danger")

    @reactive.effect
    @reactive.event(input.guide_extreme_danger)
    def _show_extreme_danger_modal():
        show_heat_risk_modal("Extreme Danger")

    @output
    @render.ui
    def reference_ui():
        return ui.div(
            ui.h5(tr("reference_title"), class_="panel-subtitle"),
            ui.div(
                ui.markdown(tr("reference_content")),
                class_="notes-references",
            ),
            style="margin-top: 1.5rem;"
        )

    @output
    @render.ui
    def footer_ui():
        return ui.div(
            ui.hr(style="margin: 0.2rem 0 0.7rem 0;"),
            ui.div(
                tr("footer_credit"),
                class_="footer-text",
            ),
            ui.div("e-mail: salirafi8@gmail.com | GitHub: ",
                    ui.a("salirafi",href="https://github.com/salirafi",target="_blank", class_='footer-text'),
                class_="footer-text"),
            class_="footer-section",
        )


app = App(app_ui, server)