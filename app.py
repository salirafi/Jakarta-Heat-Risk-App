'''
Source code to create the web app.
Note that the pipeline of the code, in default, does not allow outputs of past weather data.
This can be changed by changing current_time variable, but note that the definition of 'current time' will not mean the present time anymore.
'''

from dash import Dash, html, dcc, Input, Output, State, ctx
import pandas as pd
import sqlite3

from src.constant import (
    DB_PATH,
    RISK_COLOR_MAP,
    HEAT_RISK_GUIDE,
    WEATHER_ICON_MAP,
    RISK_ABBR,
    WEATHER_TABLE,
)
from src.helpers import *
from src.plotting import *

boundary_json = load_boundary_data() # pd.DataFrame and JSON dict
current_time = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None) # definition of current_time

app = Dash(__name__, suppress_callback_exceptions=True)

# helper to make the header section
def make_header(pathname="/location"):

    # divide the app into two pages
    location_active = "nav-btn active" if pathname in ["/", "/location"] else "nav-btn"
    map_active = "nav-btn active" if pathname == "/map" else "nav-btn"

    return html.Div(
        className="top-header",
        children=[

            html.Div(
                className="header-left",
                children=[
                    html.Div("Jakarta Heat Risk Information", className="app-title"),
                ],
            ),

            html.Div(
                className="header-nav",
                children=[
                    dcc.Link("Ward Info", href="/location", className=location_active),
                    dcc.Link("Regional Info", href="/map", className=map_active),
                ],
            ),

            html.Div(
                [
                    html.Div("Database last updated", className="header-update-label"),
                    html.Div(get_last_db_update(), className="header-update-time"),
                ],
                className="header-right",
            )
        ],
    )

# get the nearest available time in the database from the current time
def get_nearest_current_time_from_store(times_data):
    times = deserialize_timestamps(times_data)
    if not times:
        return None

    times_series = pd.Series(times)
    nearest_idx = (times_series - current_time).abs().idxmin()
    return pd.Timestamp(times_series.loc[nearest_idx])

# default queried database has time coverage of 1 day
def get_default_query_window():
    return {
        "start_time": current_time,
        "end_time": current_time + pd.Timedelta(days=1.0),
    }

# get the available timestamps from the queried window
def load_forecast_times():
    window = get_default_query_window()

    # 3 hours offset to start_time is ti include the timestamp corresponds to the exact current time
    # if no offset, the earliest timestamp queried will be AFTER the current time
    start_time = pd.to_datetime(window["start_time"]) - pd.Timedelta(hours=3.0)
    end_time = pd.to_datetime(window["end_time"]) + pd.Timedelta(hours=3.0)

    conn = get_conn()
    try:
        times = available_timestamps(start_time, end_time, conn)
    finally:
        conn.close()

    return times

# query weather data of current time and selected location
def load_current_snapshot_df(selected_ward, times_data):
    if not selected_ward:
        return pd.DataFrame()

    nearest_time = get_nearest_current_time_from_store(times_data)
    if nearest_time is None:
        return pd.DataFrame()

    conn = get_conn()
    try:
        # this ideally should output only a single row 
        # since combination of code and timestamp is unique
        df_region = pd.read_sql_query(
            f"""
            SELECT adm4
            FROM {WEATHER_TABLE}
            WHERE desa_kelurahan = ?
            LIMIT 1
            """,
            conn,
            params=[selected_ward],
        )

        if df_region.empty:
            return pd.DataFrame()

        region_code = df_region.iloc[0]["adm4"]

        snap = current_condition(
            region_code,
            nearest_time,
            conn,
        )
    finally:
        conn.close()

    return snap

# get data for evolution plot
def load_heat_index_evolution_values(selected_ward, times_data):
    df = load_future_forecast_df(selected_ward, times_data)
    if df.empty:
        return None

    return create_heat_index_arr(df) # create the suitable array structure for plotting

# load future forecast dataframe for a selected ward between nearest current forecast time and the query window end time
def load_future_forecast_df(selected_ward, times_data):
    if not selected_ward:
        return pd.DataFrame()

    # this df will correspond to the nearest future timestamp to current time
    current_time_df = get_nearest_current_time_from_store(times_data)
    if current_time_df is None:
        return pd.DataFrame()

    end_time = get_default_query_window()["end_time"] # plus 1-day (default) from start_time

    conn = get_conn()
    try:
        df_region = pd.read_sql_query(
            f"""
            SELECT adm4
            FROM {WEATHER_TABLE}
            WHERE desa_kelurahan = ?
            LIMIT 1
            """,
            conn,
            params=[selected_ward],
        )

        if df_region.empty:
            return pd.DataFrame()

        region_code = df_region.iloc[0]["adm4"]

        df = future_forecast( # do SQL query to retrieve time, HI, risk level, and ward
            region_code,
            current_time_df,
            end_time,
            conn,
        )
    finally:
        conn.close()

    return df

# creating the future forecast cards
def build_forecast_cards(df):
    if df.empty:
        return html.Div("No available data.", className="city-summary-note")

    cards = []

    wards = df["desa_kelurahan"]
    times = df["local_datetime"]
    heat_index = df["heat_index_c"]
    risks = df["risk_level"]

    for ward, ts_, hi_, risk_ in zip(wards, times, heat_index, risks):

        #  color the cards' background to the risk level
        bg_color = hex_to_rgba_css(
            RISK_COLOR_MAP.get(risk_, "#dcdcdc"),
            alpha=0.18,
        )

        card = html.Div(
            className="forecast-card",
            style={"background": bg_color},
            children=[
                html.Div(str(ward), className="forecast-card-title"),
                html.Div(
                    pd.Timestamp(ts_).strftime("%b %d, %H:%M"),
                    className="forecast-card-time",
                ),
                html.Div(f"HI: {hi_:.1f} °C", className="forecast-card-hi"),
                html.Div(risk_badge(risk_), className="forecast-card-risk"),
            ],
        )

        cards.append(card)

    return html.Div(cards, className="forecast-scroll")

def build_map_legend():
    return html.Div(
        className="legend-container",
        children=[
            html.Div(
                className="legend-item",
                children=[
                    html.Div(
                        className="legend-color",
                        style={"backgroundColor": color},
                    ),
                    html.Span(label, className="legend-label"),
                ],
            )
            for label, color in RISK_COLOR_MAP.items()
        ],
    )

# options to be displayed to the search bar
# all available wards will be listed
options = make_ward_search_options(get_conn())

def build_metric_card(label, value, extra_class=""):
    class_name = "metric-card"
    if extra_class:
        class_name += f" {extra_class}"

    return html.Div(
        className=class_name,
        children=[
            html.Div(label, className="metric-label"),
            html.Div(value, className="metric-value"),
        ],
    )

# function to construct the heat risk guide section
def build_heat_risk_guide_component():
    levels = ["Lower Risk", "Caution", "Extreme Caution", "Danger", "Extreme Danger"]

    return html.Div(
        children=[
            html.H3("Heat Risk Guide", className="left-title"),
            html.P(
                [
                    "Guide to what it means and what actions to take. Based on ",
                    html.A(
                        "U.S. National Weather Service",
                        href="https://www.wpc.ncep.noaa.gov/heatrisk/",
                        target="_blank",
                    ),
                    ".",
                ],
                className="left-paragraph risk-guide-intro",
            ),
            html.Div(
                className="guide-button-list",
                children=[
                    html.Button(
                        [
                            html.Span(
                                className="risk-guide-item-left",
                                children=[
                                    html.Span(
                                        "",
                                        className="risk-guide-dot",
                                        style={"background": RISK_COLOR_MAP[level]},
                                    ),
                                    html.Span(level, className="risk-guide-item-title"),
                                ],
                            ),
                            html.Span("View", className="risk-guide-item-right"),
                        ],
                        id=f"guide-btn-{idx}",
                        className="guide-btn risk-guide-item",
                    )
                    for idx, level in enumerate(levels, start=1)
                ],
            ),
        ]
    )

# ====================
# LAYOUT-RELATED
# ====================

def location_layout():
    return html.Div(
        className="right-column",
        children=[
            html.Div(
                className="location-panel",
                children=[
                    html.Div(
                        className="location-panel-body",
                        children=[
                            html.Div(
                                className="search-row",
                                children=[
                                    html.Div(
                                        id="current_snapshot_time_text",
                                        className="search-time-meta-slot",
                                    ),
                                    html.Div(
                                        className="search-dropdown-wrap",
                                        children=[
                                            dcc.Dropdown(
                                                id="selected_ward_search",
                                                options=options,
                                                placeholder="Search ward...",
                                                searchable=True,
                                                clearable=True,
                                                className="search-dropdown",
                                            ),
                                            # html.Div(
                                            #     id="current_snapshot_time_text",
                                            #     className="search-time-meta-slot",
                                            # ),
                                        ],
                                    ),
                                    html.Div(className="search-row-spacer"),
                                ],
                            ),

                            html.Div(id="location_content_ui", className="location-panel-body"),
                        ],
                    ),
                ],
            ),
        ],
    )

def map_layout():
    return html.Div(
        className="right-column right-column-map",
        children=[
            html.Div(
                className="map-panel",
                children=[
                    html.Div(
                        className="map-slider-row",
                        children=[
                            html.Div(id="selected_map_time_text", className="map-time-caption"),
                            html.Div(
                                className="map-slider-control",
                                children=[
                                    dcc.Slider(
                                        id="selected_time_idx",
                                        min=0,
                                        max=0,
                                        step=1,
                                        value=0,
                                        marks={},
                                        allow_direct_input=False,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    html.Div(
                        className="map-content-row",
                        children=[
                            html.Div(
                                className="map-section",
                                children=[
                                    dcc.Graph(
                                        id="heat_risk_map",
                                        figure={},
                                        config={"displayModeBar": False},
                                        style={"height": "100%", "width": "100%"},
                                    ),
                                    html.Div(id="map_legend", className="legend-row"),
                                ],
                            ),
                            html.Div(
                                className="map-section",
                                children=[
                                    # html.Div(
                                    #     "Regional Summary",
                                    #     className="city-summary-header"
                                    # ),

                                    html.Div(
                                        className="city-summary-center",
                                        children=[
                                            dcc.Graph(
                                                id="city_summary_plot",
                                                figure={},
                                                config={"displayModeBar": False},
                                            ),
                                        ],
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
            ),
        ],
    )

def build_empty_location_state():
    return html.Div(
        "Please select location to display.",
        className="location-empty-state",
    )

def build_location_content_layout():
    return [
        html.Div(id="current_metrics_ui", className="card-row"),

        html.Div(
            className="location-section",
            children=[
                # html.Div(id="future_forecast_caption", className="section-title"),
                html.Div(
                    id="future_forecast_cards_ui",
                    className="section-content",
                ),
            ],
        ),

        html.Div(
            className="location-section",
            children=[
                html.Div(
                    className="section-content heat-index-section",
                    children=[
                        dcc.Graph(
                            id="heat_index_evolution_plot",
                            figure={},
                            config={"displayModeBar": False},
                            style={"height": "100%", "width": "100%"},
                        ),
                        html.Div(
                            "*Gap between heat index and temperature shows how humid it is.",
                            className="heat-index-note",
                        ),
                    ],
                ),
            ],
        ),
    ]

app.layout = html.Div(
    className="app-shell",
    children=[
        dcc.Location(id="url"),
        dcc.Store(id="forecast-times-store"),
        html.Div(id="header-container"),

        html.Div(
            className="page-body",
            children=[

                # LEFT PANEL
                html.Div(
                    className="left-column",
                    children=[
                        html.Div(
                            className="left-panel",
                            children=[
                                build_heat_risk_guide_component(),

                                html.Hr(className="left-divider"),

                                html.H4("About", className="left-subtitle"),

                                dcc.Markdown("""                                                        
                                                Heat index is computed using the regression formula from the US National Weather Service (see [here](https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml) and [here](https://www.weather.gov/ama/heatindex#:~:text=Table_title:%20What%20is%20the%20heat%20index?%20Table_content:,the%20body:%20Heat%20stroke%20highly%20likely%20%7C)). The formulation is expected to be valid for US sub-tropical region, but its use for tropical region like Indonesia does not guarantee very accurate results. However, as first-order approximation, this is already sufficient.
                                            """,
                                    className="left-about",
                                ),
                                dcc.Markdown(""" 
                                                Weather data is taken from BMKG's [Data Prakiraan Cuaca Terbuka](https://data.bmkg.go.id/prakiraan-cuaca/) through its free public API.
                                            """,
                                    className="left-about",
                                ),

                                html.Div([
                                        html.Img(
                                            src=f"/assets/github.svg",
                                            className="left-footer",
                                        ),
                                        "     ",
                                        html.A(
                                            "salirafi", 
                                            href="https://github.com/salirafi",
                                            target="_blank",
                                            className="left-footer"
                                            ),
                                ],
                                className="left-footer",),
                            ],
                        )
                    ],
                ),

                # RIGHT CONTENT
                html.Div(id="page-container", className="right-column"),
            ],
        ),

        dcc.Store(id="guide-modal-store", data=False),
        html.Div(
            id="guide-modal",
            className="modal-overlay",
            children=[
                html.Div(
                    className="modal-box",
                    children=[
                        html.Button("×", id="modal-close", className="modal-close-btn"),
                        html.Div(id="modal-content", className="modal-content"),
                    ],
                )
            ],
        ),

    ],
)

# ====================
# CALLBACK FUNCTIONS
# ====================

@app.callback(
    Output("location_content_ui", "children"),
    Input("selected_ward_search", "value"),
)
def location_content_ui(selected_ward):
    if not selected_ward: # if no selected ward, display text
        return build_empty_location_state()

    return build_location_content_layout() # else display data

@app.callback(
    Output("header-container", "children"),
    Output("page-container", "children"),
    Input("url", "pathname"),
)
def render_page(pathname):
    pathname = pathname or "/location"

    header = make_header(pathname)

    if pathname == "/map":
        return header, map_layout()

    return header, location_layout()

@app.callback(
    Output("selected_time_idx", "min"),
    Output("selected_time_idx", "max"),
    Output("selected_time_idx", "value"),
    Output("selected_time_idx", "marks"),
    Input("forecast-times-store", "data"),
)
def time_slider(store_data):
    timestamps = deserialize_timestamps(store_data)
    if not timestamps:
        return 0, 0, 0, {}

    marks = build_slider_marks(timestamps)
    current_idx = 0

    return 0, len(timestamps) - 1, current_idx, marks

@app.callback(
    Output("forecast-times-store", "data"),
    Input("url", "pathname"),
)
def forecast_times_store(_pathname):
    times = load_forecast_times()
    return serialize_timestamps(times)

@app.callback(
    Output("selected_map_time_text", "children"),
    Input("selected_time_idx", "value"),
    Input("forecast-times-store", "data"),
)
def selected_map_time_text(selected_idx, store_data):
    selected_time = get_selected_time_from_store(selected_idx, store_data)

    if selected_time is None:
        return "Map time: -"

    return f"Map time: {selected_time.strftime('%b %d %H:%M')}"

@app.callback(
    Output("heat_risk_map", "figure"),
    Input("selected_time_idx", "value"),
    State("forecast-times-store", "data"),
)
def heat_risk_map(selected_idx, times_data):
    selected_time = get_selected_time_from_store(selected_idx, times_data)

    if selected_time is None:
        return {}

    conn = get_conn()
    try:
        colormap = create_dynamic_colormap(
            selected_time=selected_time,
            conn=conn,
        )
    finally:
        conn.close()

    fig = build_map_figure(
        boundary_geojson=boundary_json,
        locations=colormap["customdata"][:, -1].tolist(),
        colormap=colormap,
    )
    fig.update_layout(uirevision="heat-risk-map") # this does not changing the UI, so it should be faster to load
    return fig

@app.callback(
    Output("map_legend", "children"),
    Input("selected_time_idx", "value"),
)
def map_legend(_):
    return build_map_legend()

@app.callback(
    Output("city_summary_plot", "figure"),
    Input("selected_time_idx", "value"),
    State("forecast-times-store", "data"),
)
def city_summary_plot(selected_idx, times_data):
    selected_time = get_selected_time_from_store(selected_idx, times_data)

    if selected_time is None:
        return {}

    conn = get_conn()
    try:
        summary = city_summary_at_time(
            selected_time=selected_time,
            conn=conn,
        )
    finally:
        conn.close()

    fig = build_city_summary_plot(summary_value=summary)
    fig.update_layout(uirevision="city-summary") # this does not changing the UI, so it should be faster to load
    return fig

@app.callback(
    Output("current_metrics_ui", "children"),
    Input("selected_ward_search", "value"),
    Input("forecast-times-store", "data"),
)
def current_metrics_ui(selected_ward, times_data):
    if not selected_ward:
        return []
    snap = load_current_snapshot_df(selected_ward, times_data)

    if snap.empty:
        return html.Div(
            "No data for the selected region and time.",
            className="city-summary-note",
        )

    row = snap.iloc[0]

    return [
        html.Div(
            className="info-card",
            children=[
                html.Div("Temperature", className="card-label"),
                html.Div(f"{row['temperature_c']:.1f}°C", className="card-value"),
            ],
        ),
        html.Div(
            className="info-card",
            children=[
                html.Div("Humidity", className="card-label"),
                html.Div(f"{row['humidity_ptg']:.1f}%", className="card-value"),
            ],
        ),
        html.Div(
            className="info-card",
            children=[
                html.Div("Heat Index", className="card-label"),
                html.Div(f"{row['heat_index_c']:.1f}°C", className="card-value"),
            ],
        ),
        html.Div(
            className="info-card",
            children=[
                html.Div("Risk Level", className="card-label"),
                html.Div(
                    RISK_ABBR.get(row["risk_level"], row["risk_level"]),
                    className="card-value",
                ),
            ],
        ),
        html.Div(
            className="info-card",
            children=[
                html.Div("Weather", className="card-label"),
                html.Img(
                    src=f"/assets/{WEATHER_ICON_MAP.get(row['weather_desc'], 'cloudy.svg')}",
                    className="weather-icon",
                ),
            ],
        ),
    ]

@app.callback(
    Output("future_forecast_caption", "children"),
    Input("selected_ward_search", "value"),
)
def future_forecast_caption(selected_ward):
    if not selected_ward:
        return ""

    return f"Future Forecast at {selected_ward}"

@app.callback(
    Output("future_forecast_cards_ui", "children"),
    Input("selected_ward_search", "value"),
    Input("forecast-times-store", "data"),
)
def future_forecast_cards_ui(selected_ward, times_data):
    if not selected_ward:
        return []
    df = load_future_forecast_df(selected_ward, times_data)
    return build_forecast_cards(df)

@app.callback(
    Output("heat_index_evolution_plot", "figure"),
    Input("selected_ward_search", "value"),
    Input("forecast-times-store", "data"),
)
def heat_index_evolution_plot(selected_ward, times_data):
    if not selected_ward:
        return {}

    evolution_values = load_heat_index_evolution_values(selected_ward, times_data)
    if evolution_values is None:
        return {}

    fig = build_heat_index_plot(evolution_values=evolution_values)
    fig.update_layout(uirevision="heat-index-evolution") # this does not changing the UI, so it should be faster to load
    return fig

# callback for displaying the current time and database's timestamp
@app.callback(
    Output("current_snapshot_time_text", "children"),
    Input("selected_ward_search", "value"),
    Input("forecast-times-store", "data"),
)
def current_snapshot_time_text(selected_ward, times_data):

    actual_now = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None)

    # if no ward selected → show placeholder
    if not selected_ward:
        return f"Current time: {actual_now.strftime('%b %d, %H:%M')} Data shown: —"

    data_time = get_nearest_current_time_from_store(times_data)

    if data_time is None:
        return f"Current time: {actual_now.strftime('%b %d, %H:%M')} Data shown: —"

    return (
        f"Current time: {actual_now.strftime('%b %d, %H:%M')} "
        f"Data shown: {data_time.strftime('%b %d, %H:%M')}"
    )

@app.callback(
    Output("guide-modal", "className"),
    Output("modal-content", "children"),
    Input("guide-btn-1", "n_clicks"),
    Input("guide-btn-2", "n_clicks"),
    Input("guide-btn-3", "n_clicks"),
    Input("guide-btn-4", "n_clicks"),
    Input("guide-btn-5", "n_clicks"),
    Input("modal-close", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_modal(b1, b2, b3, b4, b5, close_clicks):
    trigger = ctx.triggered_id

    if trigger == "modal-close":
        return "modal-overlay", ""

    level_map = {
        "guide-btn-1": "Lower Risk",
        "guide-btn-2": "Caution",
        "guide-btn-3": "Extreme Caution",
        "guide-btn-4": "Danger",
        "guide-btn-5": "Extreme Danger",
    }

    level = level_map.get(trigger)
    if level is None:
        return "modal-overlay", ""

    guide = HEAT_RISK_GUIDE[level]

    modal_body = html.Div(
        children=[
            html.Div(
                className="risk-guide-modal-header",
                children=[
                    html.Span(
                        "",
                        className="risk-guide-dot",
                        style={
                            "background": RISK_COLOR_MAP[level],
                            "width": "16px",
                            "height": "16px",
                        },
                    ),
                    html.Div(
                        children=[
                            html.Div(level, className="risk-guide-modal-title"),
                            html.Div(guide["level"], className="guide-modal-caption"),
                        ]
                    ),
                ],
            ),
            html.Div(
                className="risk-guide-modal-section",
                children=[
                    html.Div("What to expect", className="risk-guide-modal-label"),
                    html.Div(guide["expect"], className="risk-guide-modal-text"),
                ],
            ),
            html.Div(
                className="risk-guide-modal-section",
                children=[
                    html.Div("Recommended actions", className="risk-guide-modal-label"),
                    html.Div(guide["do"], className="risk-guide-modal-text"),
                ],
            ),
        ]
    )

    return "modal-overlay modal-overlay-show", modal_body

if __name__ == "__main__":
    app.run(debug=True)