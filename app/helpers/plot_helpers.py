import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from helpers.formatting import short_city_name

def build_heat_index_plot(
    initial_payload: dict,
    heat_index_label: str,
    empty_label: str,
    time_label: str,
) -> go.Figure:

    fig = go.Figure()

    # Heat index trace
    fig.add_trace(
        go.Scatter(
            x=initial_payload["x"],
            y=initial_payload["y_hi"],
            mode="lines+markers",
            name=heat_index_label,
            line=dict(color="#d62728", width=2),
            marker=dict(size=5),
            hovertemplate=(
                f"{time_label}: %{{x|%b %d %H:%M}}<br>"
                f"{heat_index_label}: %{{y:.1f}} °C<extra></extra>"
            ),
            yaxis="y",
        )
    )

    # Temperature trace
    fig.add_trace(
        go.Scatter(
            x=initial_payload["x"],
            y=initial_payload["y_temp"],
            mode="lines+markers",
            name="Temperature",
            line=dict(color="#1f77b4", width=2, dash="dot"),
            marker=dict(size=5),
            hovertemplate=(
                f"{time_label}: %{{x|%b %d %H:%M}}<br>"
                f"Temperature: %{{y:.1f}} °C<extra></extra>"
            ),
            yaxis="y2",
        )
    )

    annotations = []
    if initial_payload["is_empty"]:
        annotations = [
            dict(
                text=empty_label,
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=14, color="#666"),
            )
        ]

    fig.update_layout(
        height=None,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        annotations=annotations,
        xaxis=dict(
            title=None,
            tickformat="%b %d %H:%M",
            tickangle=0,
            showgrid=True,
            gridcolor="rgba(0,0,0,0.08)",
            zeroline=False,
            visible=not initial_payload["is_empty"],
        ),
        yaxis=dict(
            title=f"{heat_index_label} (°C)",
            range=initial_payload["y_range"],
            gridcolor="rgba(0,0,0,0.08)",
            zeroline=False,
            visible=not initial_payload["is_empty"],
        ),

        yaxis2=dict(
            title="Temperature (°C)",
            overlaying="y",
            side="right",
            showgrid=False,
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
        legend=dict(
            x=0.02,
            y=0.98,
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(255,255,255,0)",
            bordercolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(size=12),
        )
    )

    return fig

def build_heat_index_series_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["local_datetime", "heat_index_c", "temperature_c"])

    chart_df = (
        df.groupby("local_datetime", as_index=False)
        .agg(
            heat_index_c=("heat_index_c", "mean"),
            temperature_c=("temperature_c", "mean"),
        )
        .sort_values("local_datetime")
        .reset_index(drop=True)
    )

    return chart_df

def build_heat_index_payload(chart_df: pd.DataFrame):
    chart_df = chart_df.copy()
    chart_df["local_datetime"] = pd.to_datetime(chart_df["local_datetime"], errors="coerce")
    chart_df = chart_df.dropna(subset=["local_datetime"]).reset_index(drop=True)

    x_ = np.array(chart_df["local_datetime"].dt.to_pydatetime()) # .to_pydatetime() returns datetime objects instead ndarray
    x_values = x_.tolist()
    y_hi = chart_df["heat_index_c"].tolist()
    y_temp = chart_df["temperature_c"].tolist()

    y_min = chart_df["heat_index_c"].min() if not chart_df.empty else np.nan
    y_max = chart_df["heat_index_c"].max() if not chart_df.empty else np.nan

    if pd.notna(y_min) and pd.notna(y_max):
        if y_min == y_max:
            y_min -= 1
            y_max += 1
        else:
            pad = 0.05 * (y_max - y_min)
            y_min -= pad
            y_max += pad
        y_range = [y_min, y_max]
    else:
        y_range = None

    return {
        "x": x_values,
        "y_hi": y_hi,
        "y_temp": y_temp,
        "y_range": y_range,
        "is_empty": chart_df.empty,
    }


def build_city_color_map(city_names: list[str]) -> dict[str, str]:
    city_colors = {
        "Jakarta Barat": "#1f77b4",
        "Jakarta Pusat": "#17becf",
        "Jakarta Selatan": "#8c564b",
        "Jakarta Timur": "#7f7f7f",
        "Jakarta Utara": "#393b79",
    }

    fallback_colors = [
        "#4C6EF5", "#F59F00", "#12B886", "#E8590C", "#C2255C",
        "#7B61FF", "#2F9E44", "#D6336C", "#1098AD", "#6741D9"
    ]

    color_map = {}
    for i, city in enumerate(city_names):
        color_map[city] = city_colors.get(city, fallback_colors[i % len(fallback_colors)])
    return color_map

def build_city_summary_plot(
    city_order: list[str],
    initial_payload: dict,
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

    if not city_order:
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

    color_map = build_city_color_map(city_order)

    metrics = [
        ("temperature_c", temperature_label, "°C"),
        ("humidity_pct", humidity_label, "%"),
        ("heat_index_c", heat_index_label, "°C"),
    ]

    for col_idx, (metric_col, metric_label, unit) in enumerate(metrics, start=1):
        for city_idx, city in enumerate(city_order):
            value = initial_payload[metric_col][city_idx]

            fig.add_trace(
                go.Bar(
                    x=[city],
                    y=[value],
                    name=city,
                    legendgroup=city,
                    showlegend=(col_idx == 1),
                    marker_color=color_map[city],
                    hovertemplate=f"{city}<br>{metric_label}: %{{y:.1f}} {unit}<extra></extra>",
                ),
                row=1,
                col=col_idx,
            )

    fig.update_layout(
        height=None,
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

    fig.update_yaxes(row=1, col=1, title_standoff=5, gridcolor="rgba(0,0,0,0.08)", zeroline=False)
    fig.update_yaxes(row=1, col=2, title_standoff=5, gridcolor="rgba(0,0,0,0.08)", zeroline=False)
    fig.update_yaxes(row=1, col=3, title_standoff=5, gridcolor="rgba(0,0,0,0.08)", zeroline=False)

    return fig

def build_city_summary_payload(
    summary_df: pd.DataFrame,
    city_order: list[str],
):
    metric_cols = ["temperature_c", "humidity_pct", "heat_index_c"]

    if summary_df.empty:
        summary_map = {}
    else:
        df = summary_df.copy()
        df["city_short"] = df["kotkab"].apply(short_city_name)
        summary_map = df.set_index("city_short")[metric_cols].to_dict(orient="index")

    payload = {}
    for metric_col in metric_cols:
        payload[metric_col] = [
            summary_map.get(city, {}).get(metric_col, np.nan)
            for city in city_order
        ]

    return payload