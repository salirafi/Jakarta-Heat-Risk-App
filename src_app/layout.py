from shiny import ui
from shinywidgets import output_widget

from .styles import APP_CSS

app_ui = ui.page_fluid(
    ui.tags.style(APP_CSS),

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

    ui.output_ui("manual_date_picker_ui"),

    ui.layout_columns(
        ui.div(
            ui.div(
                ui.output_ui("heat_map_title"),
                ui.output_ui("time_slider_ui"),
                output_widget("boundary_map"),
                ui.output_ui("map_legend"),
                ui.hr(style="margin: 0.8rem 0 0.8rem 0;"),
                ui.div(
                    ui.output_ui("avg_conditions_title"),
                    ui.output_ui("avg_conditions_note"),
                    output_widget("city_summary_plot"),
                    class_="city-summary-section"
                ),
                class_="panel-box left-panel-box",
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
                ui.div(
                    ui.output_ui("heat_index_over_time_title"),
                    ui.output_ui("heat_index_evolution_ui"),
                    class_="heat-index-section",
                ),
                class_="panel-box right-panel-box",
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