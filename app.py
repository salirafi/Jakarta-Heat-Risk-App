'''
Source code to create the web app.
Note that the pipeline of the code, in default, does not allow outputs of past weather data.
This can be changed by changing default_start_time variable, but note that the definition of 'current time' will not mean the present time anymore. See current_time_for_metrics().
'''

from src.constant import RISK_COLOR_MAP
from src.helpers import region_filter_options
from src.plotting import create_dynamic_colormap
from shiny import ui, App, reactive, render
from shinywidgets import output_widget, render_widget
import pandas as pd
from html import escape

from src.constant import DB_PATH, BOUNDARY_TABLE, WEATHER_TABLE, CITY_ORDER, HEAT_RISK_GUIDE
from src.helpers import *
from src.plotting import *

app_ui = ui.page_fluid(

    # ui.tags.link(href="styles.css", rel="stylesheet"),
    ui.head_content(ui.include_css("styles.css")),

    ui.div(
        ui.div("Jakarta's Heat Risk Map and Forecast", class_="page-title"),
        ui.div("Heat index and risk information throughout Jakarta region based on BMKG data.", class_="page-subtitle"),
        class_="title-block"
    ),

    ui.layout_columns(
        ui.div(
            ui.div(
                ui.h2("Current Weather and Forecast", class_="panel-title"),
                ui.layout_columns(
                    ui.output_ui("city_ui"),
                    ui.output_ui("subdistrict_ui"),
                    ui.output_ui("ward_ui"),
                    col_widths=[4, 4, 4],
                ),
                ui.output_ui("current_time_caption"),
                ui.output_ui("current_metrics_ui"),
                # ui.output_ui("test"),
                ui.hr(style="margin: 1rem 0 0.8rem 0;"),
                ui.h3("Future forecast", class_="panel-subtitle"),
                ui.output_ui("future_forecast_cards_ui"),
                ui.hr(style="margin: 1rem 0 0.8rem 0;"),
                ui.div(
                    ui.output_ui("heat_evolution_caption"),
                    output_widget("heat_index_evolution_plot"),
                    class_="heat-index-section",
                ),
                class_="panel-box right-panel-box",
            ),
            class_="main-panel",
        ),
        ui.div(
            ui.div(
                ui.h2("Heat Risk Map", class_="panel-title"),
                ui.output_ui("time_slider_ui"),
                output_widget("heat_risk_map"),
                ui.output_ui("map_legend"),
                ui.hr(style="margin: 0.8rem 0 0.8rem 0;"),
                ui.div(
                    ui.h3("Average conditions across Jakarta cities", class_="panel-subtitle"),
                    ui.p("Averaged across all wards within each city at the selected map time.", class_="city-summary-note"),
                    output_widget("city_summary_plot"),
                    class_="city-summary-section"
                ),
                class_="panel-box left-panel-box",
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

    ui.div(
            ui.hr(style="margin: 0.2rem 0 0.7rem 0;"),
            ui.div("© Sayyed Ali Rafi", class_="footer-text"),
            ui.div("e-mail: salirafi8@gmail.com | GitHub: ",
                    ui.a("salirafi",href="https://github.com/salirafi",target="_blank", class_='footer-text'),
                class_="footer-text"),
            
            class_="footer-section",
        )
)

def server(input, output, _):

    # setting default query time window from current system's time to a day after; UTC+7
    default_start_time = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None)
    query_window = reactive.Value({"start_time": default_start_time, # reactive value used; when it changes, all process downstreams invalidated
                                    "end_time": default_start_time + pd.Timedelta(days=1.0)
                                    })
    
    @reactive.calc
    def load_data():

        # if no table at the specified path
        if not DB_PATH.exists():
            return {"error": "Database file 'heat_risk.db' was not found."}

        # check if required tables exist
        existing_tables = set(get_table_names())
        if BOUNDARY_TABLE not in existing_tables:
            return {"error": f"Table {BOUNDARY_TABLE} was not found."}
        if WEATHER_TABLE not in existing_tables:
            return {"error": f"Table {WEATHER_TABLE} was not found."}

        # assign query window
        window = query_window.get()
        start_time = window.get("start_time")
        end_time = window.get("end_time")

        # load data
        weather_data = load_weather_data(start_time, end_time) # pd.DataFrame
        boundary_data, boundary_json = load_boundary_data() # gpd.GeoDataFrame and JSON dict

        # telling error if any of the table is empty
        if boundary_data.empty:
            return {"error": "Boundary table is empty"}
        if weather_data.empty:
            return {"error": "Weather table is empty for the selected time window"}

        # indexing region code for choropleth plotting
        boundary_index = boundary_data[["adm4"]].copy().sort_values("adm4").reset_index(drop=True) # pd.DataFrame

        return {
            "boundary_gdf": boundary_data,
            "boundary_json": boundary_json,
            "boundary_index": boundary_index,
            "weather_df": weather_data,
            "query_start_time": start_time,
            "query_end_time": end_time,
        }

    @reactive.calc
    def weather_data_lookup():
        data = load_data()
        if "error" in data:
            return {}
        return build_weather_data_lookup(data["weather_df"])

    @reactive.calc
    def forecast_times():
        data = load_data()
        if "error" in data:
            return []
        return available_times_in_data(data["weather_df"])

    # create map figure
    @render_widget
    def heat_risk_map():

        data = load_data()
        if "error" in data:
            return ui.div("No available data", class_='city-summary-note')

        times = forecast_times() # list of unique timestamps in data["weather_df"]
        if not times:
            return ui.div("No available data", class_='city-summary-note')
        selected_time = times[0] # initial timestamp to show (first timestamp in data)

        # slicing created grouped dictionary at selected_time
        colormap = create_dynamic_colormap(
            boundary_index=data["boundary_index"],
            weather_lookup=weather_data_lookup(),
            selected_time=selected_time,
        )

        return build_map_figure(
                boundary_geojson=data["boundary_json"],
                locations=data["boundary_index"]["adm4"].tolist(),
                colormap=colormap,
            )

    # create city summary plot
    @render_widget
    def city_summary_plot():

        times = forecast_times() # list of unique timestamps in data["weather_df"]
        if not times:
            return ui.div("No available data", class_='city-summary-note')

        initial_summary = city_summary_at_time(
                            selected_time=times[0], # initial average value for first timestamp
                            weather_lookup=weather_data_lookup(),
                            )

        return build_city_summary_plot(
                summary_value=initial_summary,
            )

    @output
    @render.ui
    def map_legend():
        return ui.div(
            ui.HTML(legend_html()), # creating map legend
            class_="legend-row"
        )

    @output
    @render.ui
    def time_slider_ui(): # UI for time slider

        times = forecast_times() # list of unique timestamps in data["weather_df"]
        if not times:
            return ui.div("No available data", class_='city-summary-note')
        step = pd.Timedelta(hours=3) # since the data is in 3-hourly basis

        return  ui.div(
            ui.input_slider(
                "selected_time",
                None,
                min=times[0],
                max=times[-1],
                value=times[int(len(times)/2)],
                step=step,
                ticks=False,
                width="100%",
                time_format="%b %d %Y, %H:%M",
                timezone="+0000",
            ),
            ui.output_ui("selected_map_time_text"), # showing the selected time from the slider
        )

    @output
    @render.ui
    def selected_map_time_text():

        selected = input.selected_time()
        if selected is None:
            return ui.div("No available data", class_='city-summary-note')

        selected_time = pd.Timestamp(selected).strftime("%b %d %Y, %H:%M")
        return ui.div(
            f"Map time: {selected_time} WIB",
            class_="map-time-caption"
        )

    @output
    @render.ui
    def city_ui():

        data = load_data()
        if "error" in data:
            return ui.div("No available data", class_='city-summary-note')

        choices = region_filter_options(data["weather_df"], "kota_kabupaten") # for city-level, no prior_mask
        
        return ui.div(
            ui.input_select(
                "selected_city",
                "City",
                choices=choices,
                selected=choices[0] if choices else None, # if user does not select, default is the top option
            ),
            class_="filter-block"
        )

    @output
    @render.ui
    def subdistrict_ui():

        data = load_data()
        if "error" in data:
            return ui.div("No available data", class_='city-summary-note')
        df = data["weather_df"]

        selected_city = input.selected_city()
        if not selected_city:
            choices = []
        else:
            mask_city = df["kota_kabupaten"] == selected_city # mask district based on selected city
            choices = region_filter_options(df, "kecamatan", prior_mask=mask_city)

        return ui.div(
            ui.input_select(
                "selected_subdistrict",
                "Subdistrict",
                choices=choices,
                selected=choices[0] if choices else None, # if user does not select, default is the top option
            ),
            class_="filter-block"
        )

    @output
    @render.ui
    def ward_ui():

        data = load_data()
        if "error" in data:
            return ui.div("No available data", class_='city-summary-note')
        df = data["weather_df"]

        selected_city = input.selected_city()
        selected_subdistrict = input.selected_subdistrict()

        if selected_city and selected_subdistrict:
            mask = pd.Series(True, index=df.index)
            mask &= df["kota_kabupaten"] ==  selected_city # mask subdistrict based on selected city
            mask &= df["kecamatan"] == selected_subdistrict # mask ward based on selected subdistrict
            choices = region_filter_options(df, "desa_kelurahan", prior_mask=mask)
        else:
            choices = []

        return ui.div(
            ui.input_select(
                "selected_ward",
                "Ward",
                choices=choices,
                selected=choices[0] if choices else None, # if user does not select, default is the top option
            ),
            class_="filter-block"
        )

    @reactive.calc
    def selected_region_df(): # filter dataframe to only the selected region

        data = load_data()
        if "error" in data:
            return ui.div("No available data", class_='city-summary-note')
        df = data["weather_df"]

        selected_city = input.selected_city()
        selected_subdistrict = input.selected_subdistrict()
        selected_ward = input.selected_ward()

        if selected_city:
            df = df[df["kota_kabupaten"] == selected_city]
        if selected_subdistrict:
            df = df[df["kecamatan"] == selected_subdistrict]
        if selected_ward:
            df = df[df["desa_kelurahan"] == selected_ward]

        return df

    @ reactive.calc
    def current_time_for_metrics():
        window = query_window.get()
        #!!!!!!!!!!!!!!!! IMPORTANT !!!!!!!!!!!!!!!
        # this pipeline assumes that the 'current time' is the start_time (which defaults to the user's current system time)
        current_time = window.get("start_time")
        df = selected_region_df()
        if df.empty:
            return None
        return nearest_available_time_in_df(df, current_time) # output pd.Timestamp

    @reactive.calc
    def current_snapshot(): # get the weather data for selected region and time
        df = selected_region_df() # pd.DataFrame
        ts = current_time_for_metrics() # pd.Timestamp; nearest timestamp in the region-filtered df to the current time
        if df.empty or ts is None:
            return df.iloc[0:0].copy()
        return weather_at_selected_time(df, ts) # this ideally should output a database with only one row since timestamp and region code are the unique parameters

    @output
    @render.ui
    def current_time_caption():
        # now_local = pd.Timestamp('2026-03-20 13:42:15.382917')
        # now_local = pd.Timestamp.now(tz="Asia/Jakarta").strftime("%B %d %Y, %H:%M")
        window = query_window.get()
        current_time = window.get("start_time").strftime("%B %d %Y, %H:%M")
        current_time_df = current_time_for_metrics()
        current_time = current_time_df.strftime("%B %d %Y, %H:%M") if current_time_df is not None else "No matching data"
        return ui.div(
            ui.div(f"Current Jakarta time: {current_time} WIB", class_="current-time-caption"),
            ui.div(f"Actual data shown is at time: {current_time_df} WIB", class_="city-summary-note")
            )

    @output
    @render.ui
    def current_metrics_ui():

        snap = current_snapshot()
        if snap.empty:
            return ui.div("No data for the selected region and time.", class_="city-summary-note")

        html = "".join([
            metric_card_html("Temperature", f"{snap['temperature_c'].iloc[0]:.1f} °C"),
            metric_card_html("Humidity", f"{snap['humidity_ptg'].iloc[0]:.1f} %"),
            metric_card_html("Heat Index", f"{snap['heat_index_c'].iloc[0]:.1f} °C"),
            metric_card_html("Risk Level", f"{snap['risk_level'].iloc[0]}", extra_class="metric-card-weather"),
            metric_card_html("Weather", f"{snap['weather_desc'].iloc[0]}", extra_class="metric-card-weather"),
        ])

        return ui.div(ui.HTML(html), class_="metric-grid metric-grid-5")

    @reactive.calc
    def future_forecast_df(): # getting weather data after current time at selected region
        df = selected_region_df()
        ts = current_time_for_metrics()
        if df.empty or ts is None:
            return df.iloc[0:0].copy()
        return (
            df[df["local_datetime"] > ts]
            .sort_values("local_datetime") # to make sure the cards are sorted correctly
            .copy()
        )

    @output
    @render.ui
    def future_forecast_cards_ui():
        df = future_forecast_df()
        if df.empty:
            return ui.div("No data available.", class_="city-summary-note")

        cards = []
        for ward_, hi_, risk_, ts_ in zip( # note: not using iterrows() due to slow performance
            df["desa_kelurahan"],
            df["heat_index_c"],
            df["risk_level"],
            df["local_datetime"],
        ):

            bg_color = hex_to_rgba_css(RISK_COLOR_MAP.get(risk_, "#dcdcdc"), alpha=0.18)
            cards.append(
                f"""
                <div class="forecast-card" style="background:{bg_color};">
                    <div class="forecast-card-title">{escape(str(ward_))}</div>
                    <div class="forecast-card-hi">{"HI"}: {hi_:.1f} °C</div>
                    <div class="forecast-card-risk">{escape(risk_badge(risk_))}</div>
                    <div class="forecast-card-time">
                        {pd.Timestamp(ts_)}
                    </div>
                </div>
                """
            )

        return ui.div(ui.HTML("".join(cards)), class_="forecast-scroll")

    @output
    @render.ui
    def heat_evolution_caption():
        return ui.h3(f"Heat index evolution at {input.selected_ward()}", class_="panel-subtitle"),

    @render_widget
    def heat_index_evolution_plot():
        data = load_data()
        if "error" in data:
            return ui.div("No available data", class_='city-summary-note')
        df = data["weather_df"]

        df = df[df["kota_kabupaten"] == "Kota Adm. Jakarta Barat"]
        df = df[df["kecamatan"] == "Cengkareng"]
        df = df[df["desa_kelurahan"] == "Cengkareng Barat"]

        df = df[["local_datetime", "temperature_c", "heat_index_c"]] # pd.DataFrame

        evolution_values = create_heat_index_arr(df)

        return build_heat_index_plot(
            evolution_values=evolution_values,
        )

    # @render.ui
    # def test():
    #     snap = current_snapshot()
    #     return ui.div(
    #         ui.p(f"{snap['temperature_c']}"),
    #         ui.p(f"{snap['humidity_ptg']}"),
    #         ui.p(f"{snap['heat_index_c']}"),
    #         )

    # update the map based on selected slider time
    @reactive.effect
    def _update_map_in_place():

        data = load_data()
        if "error" in data:
            return ui.div("No available data", class_='city-summary-note')
        selected_time =  pd.Timestamp(input.selected_time())
        if selected_time is None:
            return

        # slicing created grouped dictionary at selected_time
        colormap = create_dynamic_colormap(
            boundary_index=data["boundary_index"],
            weather_lookup=weather_data_lookup(),
            selected_time=selected_time,
        )

        widget = heat_risk_map.widget
        widget = getattr(heat_risk_map, "widget", None)
        if widget is None or not widget.data:
            return

        # update the color map but the boundary polygon stays
        widget.data[0].z = colormap["z"]
        widget.data[0].customdata = colormap["customdata"]

    # update the city summary plot on selected slider time
    @reactive.effect
    def _update_city_summary_in_place():

        selected_time =  pd.Timestamp(input.selected_time())

        # slicing created grouped dictionary at selected_time
        timestamp_summary = city_summary_at_time(
                            selected_time=selected_time, # initial average value for first timestamp
                            weather_lookup=weather_data_lookup(),
                            )

        widget = getattr(city_summary_plot, "widget", None)
        if widget is None or not widget.data:
            return

        # update the color map but the boundary polygon stays
        trace_idx = 0
        metric_cols = ["avg_temperature_c", "avg_humidity_ptg", "avg_heat_index_c"]
        timestamp_customdata = [[timestamp_summary["local_datetime"]] for _ in CITY_ORDER]
        for metric_col in metric_cols:
            widget.data[trace_idx].customdata = timestamp_customdata
            widget.data[trace_idx].y = timestamp_summary[metric_col]
            trace_idx += 1

    # update the plot based on selected region
    @reactive.effect
    def _update_heat_index_plot_in_place():

        df = selected_region_df()
        if df.empty:
            return None
        evolution_values = create_heat_index_arr(df)

        widget = heat_index_evolution_plot.widget

        # update the color map but the boundary polygon stays
        widget.data[0].x = evolution_values["x"]
        widget.data[0].y = evolution_values["y_hi"]

        widget.data[1].x = evolution_values["x"]
        widget.data[1].y = evolution_values["y_temp"]

        # update range as well
        widget.layout.yaxis.range = evolution_values["y_range"]

    @output
    @render.ui
    def heat_risk_guide_ui(): # for heat risk guide section

        levels = ["Lower Risk", "Caution", "Extreme Caution", "Danger", "Extreme Danger"]

        return ui.div(
            ui.h4("Heat Risk Guide", class_="panel-title"),
            ui.p("Click a heat risk level below to see what it means and what actions to take. This guide is based on the ",
                ui.a(
                    "U.S. National Weather Service HeatRisk Guide",
                    href="https://www.wpc.ncep.noaa.gov/heatrisk/",
                    target="_blank"
                ),
                ".",
                class_="caption risk-guide-intro"
            ),
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
                                ui.tags.span(level, class_="risk-guide-item-title"),
                                class_="risk-guide-item-left",
                            ),
                            ui.tags.span("View", class_="risk-guide-item-right"),
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

    def show_heat_risk_modal(level: str):
        guide = HEAT_RISK_GUIDE[level]

        modal = ui.modal(
            ui.div(
                ui.div(
                    ui.tags.span(
                        "",
                        class_="risk-guide-dot",
                        style=f"background:{RISK_COLOR_MAP[level]}; width:16px; height:16px;"
                    ),
                    ui.div(
                        ui.tags.div(level, class_="risk-guide-modal-title"),
                        ui.tags.div(guide["level"], class_="caption"),
                    ),
                    class_="risk-guide-modal-header",
                ),
                ui.div(
                    ui.tags.div("What to expect", class_="risk-guide-modal-label"),
                    ui.tags.div(guide["expect"], class_="risk-guide-modal-text"),
                    class_="risk-guide-modal-section",
                ),
                ui.div(
                    ui.tags.div("Recommended actions", class_="risk-guide-modal-label"),
                    ui.tags.div(guide["do"], class_="risk-guide-modal-text"),
                    class_="risk-guide-modal-section",
                ),
            ),
            title=None,
            easy_close=True,
            footer=None,
        )
        ui.modal_show(modal)

    @output
    @render.ui
    def reference_ui():
        return ui.div(
            ui.h5("Notes and References", class_="panel-subtitle"),
            ui.div(
                ui.markdown("""
                    1. Heat index is computed using the regression formula from the US National Weather Service ([see here](https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml) and [here](https://www.weather.gov/ama/heatindex#:~:text=Table_title:%20What%20is%20the%20heat%20index?%20Table_content:,the%20body:%20Heat%20stroke%20highly%20likely%20%7C)), with Celcius to Fahrenheit conversion and vice versa. The formulation is expected to be valid for US sub-tropical region, but its use for tropical region like Indonesia does not guarantee very accurate results. However, as first-order approximation, this is already sufficient.

                    2. Administrative regional border data is retrieved from RBI10K_ADMINISTRASI_DESA_20230928 database provided by Badan Informasi Geospasial (BIG).

                    3. Administrative regional code is taken from [wilayah.id](https://wilayah.id/) based on Kepmendagri No 300.2.2-2138 Tahun 2025.

                    4. Weather forecast data is taken from the public API of Badan Meteorologi, Klimatologi, dan Geofisika (BMKG) accessed via [Data Prakiraan Cuaca Terbuka](https://data.bmkg.go.id/prakiraan-cuaca/).

                    5. The use of generative AI includes: Visual Studio Code's Copilot to help tidying up code and writing comments and docstring, as well as OpenAI's Chat GPT to give code syntax ideas and identify runtime error. Outside of those, including problem formulation and framework of thinking, code logical reasoning and writing, from database management using SQLite to web development using Shiny, all is done solely by the author. 
                """
                ),
                class_="notes-references",
            ),
            style="margin-top: 1.5rem; margin-bottom: 0.5rem"
        )


app = App(app_ui, server)
