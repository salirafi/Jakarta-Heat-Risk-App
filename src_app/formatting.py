import pandas as pd
from html import escape

def format_timestamp(ts) -> str:
    if ts is None or pd.isna(ts):
        return ""
    return pd.Timestamp(ts).strftime("%Y-%m-%d %H:%M")

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

def short_city_name(name: str) -> str:
    if pd.isna(name):
        return ""
    name = str(name).strip()
    return name.replace("Kota Adm. ", "").replace("Kab. Adm. ", "")