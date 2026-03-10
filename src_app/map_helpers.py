import json
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .config import RISK_CODE_MAP, RISK_COLOR_MAP, RISK_ORDER
from .formatting import format_timestamp

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