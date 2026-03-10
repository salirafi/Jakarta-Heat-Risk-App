APP_CSS = """
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
            margin-bottom: 0.1rem;
        }
                  
        .filter-block {
            margin-bottom: 0.001rem;
            color: rgba(255,255,255,0.2);
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
            overflow-wrap: anywhere;
        }
        .metric-card-weather .metric-value {
            font-size: 1.1rem;
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
        .main-panels > div {
            display: flex;
        }

        .main-panel {
            display: flex;
            width: 100%;
            height: 100%;
            min-height: 100%;
        }
        .main-panel > .panel-box {
            display: flex;
            flex-direction: column;
            width: 100%;
            flex: 1 1 auto;
            min-height: 100%;
        }

        .left-panel-box,
        .right-panel-box {
            flex: 1 1 auto;
            min-height: 100%;
        }

        .heat-index-section {
            flex: 1 1 280px;
            min-height: 280px;
            display: flex;
            flex-direction: column;
        }
        .heat-index-section .panel-subtitle {
            flex: 0 0 auto;
            margin-bottom: 0.5rem;
        }
        .heat-index-section > .shiny-plotly-output,
        .heat-index-section > .html-widget,
        .heat-index-section > .plotly html-widget,
        .heat-index-section .js-plotly-plot,
        .heat-index-section .plotly,
        .heat-index-section .js-plotly-plot,
        .heat-index-section .plot-container,
        .heat-index-section .svg-container {
            flex: 1 1 auto;
            min-height: 0;
            height: 100% !important;
        }

        .city-summary-section {
            flex: 1 1 280px;
            min-height: 280px;
            display: flex;
            flex-direction: column;
        }

        .city-summary-section .panel-subtitle {
            flex: 0 0 auto;
            margin-bottom: 0.35rem;
        }

        .city-summary-section .caption,
        .city-summary-section .text-muted,
        .city-summary-section p {
            flex: 0 0 auto;
            margin-bottom: 0.5rem;
        }

        .city-summary-section > .shiny-plotly-output,
        .city-summary-section > .html-widget,
        .city-summary-section .js-plotly-plot,
        .city-summary-section .plotly,
        .city-summary-section .plot-container,
        .city-summary-section .svg-container {
            flex: 1 1 auto;
            min-height: 0;
            height: 100% !important;
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
    """