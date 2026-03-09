import numpy as np
import pandas as pd
import plotly.graph_objects as go
from shiny import reactive, render, ui
from shinywidgets import render_widget

from text_context import *
from config import *
from helpers.formatting import *
from helpers.db import *
from helpers.map_helpers import *
from helpers.region_helpers import *
from helpers.plot_helpers import *
from ui.components import *

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

    language = reactive.Value("en")
    manual_start_date = reactive.Value(None)
    needs_manual_date = reactive.Value(False)
    current_query_window = reactive.Value({"start_time": None, "end_time": None})

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
    def forecast_db_info():
        if not DB_PATH.exists():
            return {
                "min_time": None,
                "max_time": None,
                "available_dates": [],
            }

        existing_tables = set(get_table_names())
        if FORECAST_TABLE not in existing_tables:
            return {
                "min_time": None,
                "max_time": None,
                "available_dates": [],
            }

        bounds = get_forecast_time_bounds()
        dates = get_available_dates()

        return {
            "min_time": bounds["min_time"],
            "max_time": bounds["max_time"],
            "available_dates": dates,
        }
    
    @reactive.effect
    def _resolve_query_window():
        info = forecast_db_info()
        min_time = info["min_time"]
        max_time = info["max_time"]

        # if min_time is None or max_time is None or pd.isna(min_time) or pd.isna(max_time):
        #     needs_manual_date.set(False)
        #     current_query_window.set({"start_time": None, "end_time": None})
        #     return

        now_time = pd.Timestamp.now(tz="Asia/Jakarta").tz_localize(None)
        # now_time = pd.Timestamp('2026-03-20 13:42:15.382917')

        # if current time is outside table coverage, require manual selection
        if now_time < min_time or now_time > max_time:

            needs_manual_date.set(True)
            chosen_date = manual_start_date.get()
            if chosen_date is None:
                # needs_manual_date.set(False)
                current_query_window.set({"start_time": None, "end_time": None})
                return

            chosen_start = pd.Timestamp(chosen_date).normalize()
            first_available_from_date = get_first_available_time_on_or_after(chosen_start)

            if first_available_from_date is None:
                # needs_manual_date.set(True)
                current_query_window.set({"start_time": None, "end_time": None})
                return

            window = compute_query_window(first_available_from_date, max_time)
            current_query_window.set(window)
            return

        # current time is inside table coverage -> auto mode
        rounded_now = floor_to_time_step(now_time, step_hours=3)
        auto_start = get_nearest_available_start_time(rounded_now)

        # if auto_start is None:
        #     needs_manual_date.set(True)
        #     current_query_window.set({"start_time": None, "end_time": None})
        #     return

        # needs_manual_date.set(False)
        # manual_start_date.set(None)

        window = compute_query_window(auto_start, max_time)
        current_query_window.set(window)

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

        window = current_query_window.get()
        start_time = window.get("start_time")
        end_time = window.get("end_time")

        if start_time is None or end_time is None:
            return {
                "error": lang_text(
                    "Data prakiraan untuk waktu saat ini tidak tersedia. Silakan pilih tanggal.",
                    "Forecast data for the current time is not available. Please choose a date."
                )
            }

        forecast_df = load_forecast_data(start_time=start_time, end_time=end_time)

        if boundary_gdf.empty:
            return {"error": lang_text("Tabel batas wilayah kosong", "Boundary table is empty")}

        if forecast_df.empty:
            return {"error": lang_text("Tabel prakiraan kosong pada rentang waktu yang dipilih", "Forecast table is empty for the selected time window")}

        boundary_index_df = boundary_gdf[["adm4"]].copy().sort_values("adm4").reset_index(drop=True)

        return {
            "error": None,
            "boundary_gdf": boundary_gdf,
            "boundary_index_df": boundary_index_df,
            "forecast_df": forecast_df,
            "query_start_time": start_time,
            "query_end_time": end_time,
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

        window = current_query_window.get()
        query_start = window.get("start_time")

        if query_start is not None:
            default_time = pd.Timestamp(query_start).to_pydatetime()
        else:
            default_time = pd.Timestamp(times[0]).to_pydatetime()

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

        # update only dynamic trace data
        widget.data[0].z = payload["z"]
        widget.data[0].customdata = payload["customdata"]

    @reactive.effect
    def _update_heat_index_plot_in_place():
        data = app_data()
        if data["error"] is not None:
            return

        df = selected_region_df()
        chart_df = build_heat_index_series_df(df)
        payload = build_heat_index_payload(chart_df)

        widget = heat_index_evolution_plot.widget
        if widget is None or len(widget.data) == 0:
            return

        widget.data[0].x = payload["x"]
        widget.data[0].y = payload["y_hi"]

        widget.data[1].x = payload["x"]
        widget.data[1].y = payload["y_temp"]

        widget.layout.yaxis.range = payload["y_range"]

        widget.layout.xaxis.visible = not payload["is_empty"]
        widget.layout.yaxis.visible = not payload["is_empty"]

        if payload["is_empty"]:
            widget.layout.annotations = [
                dict(
                    text=lang_text("Data indeks panas tidak tersedia", "No heat index data available"),
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=14, color="#666"),
                )
            ]
        else:
            widget.layout.annotations = []

    @reactive.effect
    def _update_city_summary_in_place():
        data = app_data()
        if data["error"] is not None:
            return

        times = forecast_times()
        if not times:
            return

        selected_time = nearest_available_time(input.selected_time(), times)
        if selected_time is None:
            return

        cities = city_order()
        if not cities:
            return

        summary = city_summary_at_time(data["forecast_df"], selected_time)
        payload = build_city_summary_payload(summary, cities)

        widget = city_summary_plot.widget
        if widget is None or len(widget.data) == 0:
            return

        metric_cols = ["temperature_c", "humidity_pct", "heat_index_c"]

        trace_idx = 0
        for metric_col in metric_cols:
            for city_idx, _city in enumerate(cities):
                widget.data[trace_idx].y = [payload[metric_col][city_idx]]
                trace_idx += 1

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
        return build_heat_index_series_df(selected_region_df())
    
    @reactive.calc
    def city_order():
        data = app_data()
        if data["error"] is not None:
            return []
        return get_fixed_city_order(data["forecast_df"])
    
    @output
    @render.ui
    def current_time_caption():
        # now_local = pd.Timestamp('2026-03-20 13:42:15.382917')
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
            metric_card_html(tr("risk"), escape(risk_label(dominant_risk)), extra_class="metric-card-weather"),
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
        data = app_data()
        if data["error"] is not None:
            fig = go.Figure()
            fig.update_layout(
                title=data["error"],
                margin=dict(l=0, r=0, t=0, b=0),
                height=420,
            )
            return fig

        initial_df = build_heat_index_series_df(data["forecast_df"])
        initial_payload = build_heat_index_payload(initial_df)

        return build_heat_index_plot(
            initial_payload=initial_payload,
            heat_index_label=tr("heat_index"),
            empty_label=lang_text("Data indeks panas tidak tersedia", "No heat index data available"),
            time_label=lang_text("Waktu", "Time"),
        )

    @render_widget
    def city_summary_plot():
        data = app_data()
        if data["error"] is not None:
            fig = go.Figure()
            fig.update_layout(
                title=data["error"],
                margin=dict(l=0, r=0, t=0, b=0),
                height=320,
            )
            return fig

        times = forecast_times()
        if not times:
            return build_city_summary_plot(
                city_order=[],
                initial_payload={
                    "temperature_c": [],
                    "humidity_pct": [],
                    "heat_index_c": [],
                },
                temperature_label=tr("temperature"),
                humidity_label=tr("humidity"),
                heat_index_label=tr("heat_index"),
                empty_label=lang_text("Data ringkasan kota tidak tersedia", "No city summary data available"),
            )

        initial_time = pd.Timestamp(times[0])
        cities = city_order()
        initial_summary = city_summary_at_time(data["forecast_df"], initial_time)
        initial_payload = build_city_summary_payload(initial_summary, cities)

        return build_city_summary_plot(
            city_order=cities,
            initial_payload=initial_payload,
            temperature_label=tr("temperature"),
            humidity_label=tr("humidity"),
            heat_index_label=tr("heat_index"),
            empty_label=lang_text("Data ringkasan kota tidak tersedia", "No city summary data available"),
        )
    
    @output
    @render.ui
    def manual_date_picker_ui():
        if not needs_manual_date.get():
            return # ui.div(str(needs_manual_date.get()))

        info = forecast_db_info()
        available_dates = info["available_dates"]

        if not available_dates:
            return ui.div(
                ui.p(
                    lang_text(
                        "Data prakiraan tidak tersedia.",
                        "Forecast data is not available."
                    ),
                    class_="caption",
                ),
                class_="panel-box",
                style="margin-bottom: 1rem;",
            )

        min_date = pd.Timestamp(min(available_dates)).date()
        max_date = pd.Timestamp(max(available_dates)).date()

        return ui.div(
            ui.h5(
                lang_text("Pilih tanggal awal", "Choose a start date"),
                class_="panel-subtitle",
            ),
            ui.p(
                lang_text(
                    "Data untuk waktu saat ini tidak tersedia. Silakan pilih tanggal awal dari kalender untuk data historis.",
                    "Forecast data for the current time is not available. Please choose a start date from the calendar for historical data."
                ),
                class_="caption",
            ),
            ui.input_date(
                "manual_date_input",
                None,
                value=min_date,
                min=min_date,
                max=max_date,
                format="yyyy-mm-dd",
                startview="month",
                weekstart=1,
            ),
            ui.p(
                lang_text(
                    ui.span(
                        "Lihat ",
                        ui.a("repositori Github", href="https://github.com/salirafi/Jakarta-Heat-Risk-App/blob/main/README.md", target="_blank"),
                        " untuk melihat cara mendapatkan data terbaru."
                    ),
                    ui.span(
                        "See the ",
                        ui.a("Github repository", href="https://github.com/salirafi/Jakarta-Heat-Risk-App/blob/main/README.md", target="_blank"),
                        " to know how to get the latest data."
                    ),
                ),
                class_="caption",
            ),
            class_="panel-box",
            style="margin-bottom: 1rem;",
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
    def _store_manual_date():
        selected = input.manual_date_input()

        if selected is None:
            return

        manual_start_date.set(pd.Timestamp(selected))

    @reactive.effect
    def _show_manual_date_notification():
        if not needs_manual_date.get():
            return

        ui.notification_show(
            lang_text(
                "Data untuk waktu saat ini tidak tersedia. Silakan pilih tanggal awal dari kalender untuk data historis.",
                "Forecast data for the current time is not available. Please choose a start date from the calendar for historical data."
            ),
            type="warning",
            duration=6,
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

