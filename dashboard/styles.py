import streamlit as st


def apply_custom_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --ap-blue: #0b63f6;
                --ap-blue-dark: #084bd8;
                --ap-blue-soft: #eef5ff;
                --ap-ink: #17213a;
                --ap-muted: #667085;
                --ap-line: #dfe5ef;
                --ap-bg: #ffffff;
                --ap-sidebar-bg: #f6f8fc;
            }

            .stApp {
                background: var(--ap-bg);
                color: var(--ap-ink);
                font-family: "Inter", "Pretendard", "Apple SD Gothic Neo", sans-serif;
            }

            div[data-testid="stAppViewContainer"],
            section.main {
                background: var(--ap-bg);
            }

            header[data-testid="stHeader"] {
                background: transparent;
            }

            #MainMenu, footer {
                visibility: hidden;
            }

            [data-testid="stSidebarNav"] {
                display: none;
            }

            section[data-testid="stSidebar"] {
                width: 330px !important;
                background: var(--ap-sidebar-bg);
                border-right: 1px solid #e7ecf4;
                box-shadow: 8px 0 24px rgba(15, 23, 42, 0.04);
            }

            section[data-testid="stSidebar"] > div {
                padding: 30px 18px 22px;
                background: var(--ap-sidebar-bg);
            }

            div[data-testid="stSidebarUserContent"] {
                height: calc(100vh - 48px);
                display: flex;
                flex-direction: column;
            }

            .alpha-brand {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 2px 8px 28px;
            }

            .alpha-mark {
                width: 26px;
                height: 26px;
                position: relative;
                border-radius: 8px;
                background: linear-gradient(135deg, #0b63f6 0%, #74a9ff 100%);
                box-shadow: 0 8px 18px rgba(11, 99, 246, 0.25);
            }

            .alpha-mark::after {
                content: "";
                position: absolute;
                top: 6px;
                left: 6px;
                width: 11px;
                height: 11px;
                border-top: 3px solid #ffffff;
                border-right: 3px solid #ffffff;
                transform: rotate(45deg);
            }

            .alpha-brand-name {
                color: var(--ap-ink);
                font-size: 26px;
                font-weight: 800;
                letter-spacing: 0;
            }

            .sidebar-label {
                margin: 28px 0 10px;
                color: var(--ap-ink);
                font-size: 15px;
                font-weight: 800;
            }

            .sidebar-label .hint {
                color: #98a2b3;
                font-size: 13px;
                font-weight: 700;
            }

            .sidebar-empty {
                margin: 4px 0 2px;
                padding: 18px 14px;
                border: 1px dashed #d7deea;
                border-radius: 12px;
                background: #fbfcff;
                color: #667085;
                font-size: 13px;
                line-height: 1.55;
            }

            .sidebar-bottom {
                margin-top: auto;
                padding-top: 20px;
                border-top: 1px solid #edf1f7;
            }

            .mypage-row {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 10px 12px;
                color: #667085;
                font-size: 14px;
                font-weight: 700;
            }

            .mypage-icon {
                width: 24px;
                height: 24px;
                border: 1px solid #cfd8e6;
                border-radius: 50%;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                color: #7b8798;
                font-size: 12px;
                font-weight: 800;
            }

            div[data-testid="stSidebar"] .stButton,
            section[data-testid="stSidebar"] .stButton {
                margin-bottom: 10px;
            }

            section[data-testid="stSidebar"] .stButton > button {
                width: 100%;
                min-height: 48px;
                justify-content: flex-start;
                border-radius: 11px;
                border: 1px solid var(--ap-line);
                background: #ffffff;
                color: #344054;
                padding: 0 16px;
                font-size: 15px;
                font-weight: 800;
                box-shadow: 0 8px 20px rgba(15, 23, 42, 0.035);
                transition: all 120ms ease;
            }

            section[data-testid="stSidebar"] .stButton > button:hover {
                border-color: #a9c7ff;
                background: #f8fbff;
                color: var(--ap-blue-dark);
                box-shadow: 0 10px 22px rgba(11, 99, 246, 0.10);
            }

            section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
                border-color: var(--ap-blue);
                background: linear-gradient(180deg, #1167ff 0%, #0557ea 100%);
                color: #ffffff;
                box-shadow: 0 12px 24px rgba(11, 99, 246, 0.24);
            }

            section[data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
                border-color: var(--ap-blue-dark);
                background: linear-gradient(180deg, #0f61f0 0%, #034fdb 100%);
                color: #ffffff;
            }

            section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
                gap: 8px;
            }

            section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] > div {
                flex: 1 1 0;
                min-width: 0;
            }

            section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton > button {
                min-height: 34px;
                justify-content: center;
                padding: 0 10px;
                border-radius: 10px;
                font-size: 13px;
                box-shadow: none;
            }

            section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
                border: 0;
                border-radius: 12px;
                background: transparent;
                box-shadow: none;
            }

            section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] > div {
                padding: 0 5px 0 0;
            }

            section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar,
            section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]::-webkit-scrollbar {
                width: 8px;
            }

            section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"]::-webkit-scrollbar-thumb,
            section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]::-webkit-scrollbar-thumb {
                background: #c9d2df;
                border-radius: 999px;
            }

            .main-shell,
            .st-key-investor_shell {
                max-width: 1280px;
                margin: 22px auto 0;
                padding: 34px 38px;
                border: 0;
                border-radius: 0;
                background: transparent;
                box-shadow: none;
            }
            .st-key-investor_shell {
                max-width: 1400px;
            }

            .selection-row {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                margin-bottom: 24px;
            }

            .selection-pill {
                display: inline-flex;
                align-items: center;
                min-height: 34px;
                padding: 0 14px;
                border-radius: 10px;
                background: #eef5ff;
                color: var(--ap-blue-dark);
                font-size: 14px;
                font-weight: 800;
            }

            .page-title {
                margin: 0 0 8px;
                color: var(--ap-ink);
                font-size: 32px;
                line-height: 1.25;
                font-weight: 850;
                letter-spacing: 0;
            }

            .page-copy {
                color: #475467;
                font-size: 17px;
                font-weight: 600;
            }
            .chair-report-header {
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 18px;
                margin-bottom: 18px;
            }
            .chair-report-pills {
                justify-content: flex-end;
                margin: 0;
            }
            .chair-report-body {
                margin-top: 18px;
                padding-top: 24px;
                border-top: 1px solid #e2e8f0;
                color: #344054;
                font-size: 15px;
                line-height: 1.78;
            }
            .chair-report-empty {
                margin-top: 18px;
                padding: 18px 16px;
                border: 1px dashed #d7deea;
                border-radius: 12px;
                background: #fbfcff;
                color: #667085;
                font-size: 14px;
                font-weight: 700;
            }
            .chair-report-body h2,
            .chair-report-body h3,
            .chair-report-body h4,
            .chair-report-body h5,
            .chair-report-body h6 {
                color: var(--ap-ink);
                letter-spacing: 0;
            }
            .chair-report-body h2 {
                margin: 4px 0 18px;
                font-size: 26px;
                line-height: 1.35;
                font-weight: 850;
            }
            .chair-report-body h3 {
                margin: 30px 0 12px;
                padding-top: 18px;
                border-top: 1px solid #edf1f7;
                font-size: 21px;
                line-height: 1.4;
                font-weight: 830;
            }
            .chair-report-body h4 {
                margin: 24px 0 10px;
                font-size: 17px;
                line-height: 1.45;
                font-weight: 800;
            }
            .chair-report-body p {
                margin: 0 0 14px;
            }
            .chair-report-body strong {
                color: #17213a;
                font-weight: 850;
            }
            .chair-report-body code {
                padding: 2px 6px;
                border-radius: 6px;
                background: #eef5ff;
                color: #084bd8;
                font-size: 0.92em;
            }
            .chair-report-body pre {
                overflow: auto;
                padding: 14px 16px;
                border: 1px solid #dfe5ef;
                border-radius: 10px;
                background: #f8fbff;
            }
            .chair-report-list {
                margin: 0 0 16px 0;
                padding-left: 22px;
            }
            .chair-report-list li {
                margin: 7px 0;
                padding-left: 3px;
            }
            .chair-report-body hr {
                border: 0;
                border-top: 1px solid #edf1f7;
                margin: 24px 0;
            }
            .metric-card {
                flex: 1 1 160px;
                padding: 16px 20px;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                background: #ffffff;
            }
            .metric-label {
                color: #667085;
                font-size: 13px;
                font-weight: 600;
                margin-bottom: 6px;
            }
            .metric-value {
                color: #17213a;
                font-size: 22px;
                font-weight: 800;
            }
            .metric-sub {
                color: #98a2b3;
                font-size: 12px;
                margin-top: 4px;
            }
            .investor-shell {
                max-width: 1400px;
                padding: 34px 34px 28px;
                background: #ffffff;
            }
            .investor-header {
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 18px;
                margin-bottom: 28px;
            }
            .investor-title-row {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 12px;
            }
            .investor-title-row .page-title {
                margin: 0;
                font-size: 34px;
            }
            .selection-pill.neutral {
                background: #f2f4f7;
                color: #344054;
            }
            .opinion-pill {
                min-height: 36px;
                padding: 0 16px;
            }
            .investor-subtitle {
                margin: 12px 0 0;
                color: #17213a;
                font-size: 16px;
                font-weight: 600;
            }
            .investor-update {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                min-height: 34px;
                color: #667085;
                font-size: 13px;
                font-weight: 700;
                white-space: nowrap;
            }
            .calendar-icon {
                width: 22px;
                height: 22px;
                border: 1px solid #cfd8e6;
                border-radius: 6px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                color: transparent;
                position: relative;
            }
            .calendar-icon::before,
            .calendar-icon::after {
                content: "";
                position: absolute;
                left: 5px;
                right: 5px;
                border-top: 2px solid #667085;
            }
            .calendar-icon::before {
                top: 7px;
            }
            .calendar-icon::after {
                top: 12px;
                border-top-width: 1px;
            }
            .investor-kpi-strip {
                width: min(860px, 100%);
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                margin: 0 0 22px;
                border: 1px solid #dfe5ef;
                border-radius: 13px;
                background: #ffffff;
                box-shadow: 0 8px 18px rgba(15, 23, 42, 0.025);
                overflow: hidden;
            }
            .investor-kpi {
                min-height: 112px;
                padding: 20px 18px;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                text-align: center;
                position: relative;
            }
            .investor-kpi + .investor-kpi {
                border-left: 1px solid #dfe5ef;
            }
            .investor-kpi-label {
                color: #17213a;
                font-size: 13px;
                font-weight: 700;
                margin-bottom: 7px;
            }
            .investor-kpi-value {
                color: #101828;
                font-size: 23px;
                line-height: 1.15;
                font-weight: 850;
            }
            .investor-kpi-sub {
                margin-top: 8px;
                color: #667085;
                font-size: 13px;
                font-weight: 700;
            }
            .investor-kpi-empty {
                display: block;
                padding: 0;
            }
            .investor-kpi-empty .investor-empty {
                margin: 0;
                border: 0;
                background: transparent;
            }
            .investor-grid-row {
                display: grid;
                gap: 14px;
                align-items: start;
                margin-top: 14px;
            }
            .investor-chart-section {
                margin-top: 18px;
            }
            .investor-row-main {
                grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.18fr);
            }
            .investor-row-wide {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 18px;
            }
            .investor-grid-row > .investor-card {
                height: auto;
            }
            .investor-card {
                min-height: 250px;
                margin-bottom: 0;
                padding: 20px 18px;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                background: #ffffff;
                box-shadow: 0 10px 24px rgba(15, 23, 42, 0.025);
            }
            .investor-card-title {
                display: flex;
                align-items: center;
                gap: 9px;
                color: #17213a;
                font-size: 17px;
                font-weight: 850;
                line-height: 1.3;
            }
            .title-icon {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 22px;
                height: 22px;
                border-radius: 7px;
                font-size: 13px;
                font-weight: 900;
            }
            .title-icon.blue {
                background: #eef5ff;
                color: #1263ff;
            }
            .investor-bullet-list {
                margin: 14px 0 0;
                padding: 0;
                list-style: none;
                color: #344054;
                font-size: 13px;
                font-weight: 650;
                line-height: 1.66;
            }
            .investor-bullet-list li {
                display: grid;
                grid-template-columns: 12px 1fr;
                gap: 8px;
                margin: 7px 0;
            }
            .investor-bullet-list li::before {
                content: "";
                width: 0;
                height: 0;
                margin-top: 8px;
                border-top: 4px solid transparent;
                border-bottom: 4px solid transparent;
                border-left: 6px solid #1263ff;
            }
            .investor-chart-card,
            .st-key-investor_chart_card {
                width: 100%;
                min-height: 320px;
                padding-bottom: 12px;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                background: #ffffff;
                box-shadow: 0 10px 24px rgba(15, 23, 42, 0.025);
            }
            .st-key-investor_chart_card {
                margin-top: 18px;
                padding: 20px 18px 12px;
            }
            .investor-chart-head {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                margin-bottom: 4px;
            }
            .chart-period-tabs {
                display: inline-flex;
                align-items: center;
                gap: 4px;
                flex-wrap: nowrap;
            }
            .chart-period-tab {
                min-width: 34px;
                min-height: 26px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 0 8px;
                border-radius: 8px;
                color: #667085;
                text-decoration: none;
                font-size: 12px;
                font-weight: 850;
                cursor: pointer;
                user-select: none;
            }
            .chart-period-tab:hover {
                background: #f2f6ff;
                color: #1263ff;
            }
            .chart-period-tab.active {
                background: #eaf2ff;
                color: #1263ff;
            }
            .investor-chart-card .chart-panel {
                display: none;
            }
            .chart-unit {
                margin-top: 8px;
                color: #667085;
                font-size: 12px;
                font-weight: 700;
            }
            .investor-chart-card .stButton > button,
            .st-key-investor_chart_card .stButton > button {
                min-height: 28px;
                padding: 0 8px;
                border: 0;
                border-radius: 8px;
                box-shadow: none;
                color: #667085;
                background: transparent;
                font-size: 12px;
                font-weight: 800;
            }
            .investor-chart-card .stButton > button[kind="primary"],
            .st-key-investor_chart_card .stButton > button[kind="primary"] {
                color: #1263ff;
                background: #eaf2ff;
            }
            .st-key-investor_chart_card [data-testid="stPlotlyChart"] {
                margin-top: 4px;
            }
            .investor-chart-svg {
                width: 100%;
                height: auto;
                min-height: 250px;
                max-height: 330px;
                margin-top: 6px;
                display: block;
            }
            .investor-chart-card .chart-hit {
                fill: transparent;
                pointer-events: all;
                cursor: crosshair;
                stroke: transparent;
                stroke-width: 6;
            }
            .investor-chart-card .chart-dot {
                fill: #1263ff;
                stroke: #ffffff;
                stroke-width: 1.5;
                opacity: 0;
                pointer-events: none;
            }
            .investor-chart-card .chart-tooltip {
                opacity: 0;
                pointer-events: none;
                transition: opacity 100ms ease;
            }
            .investor-chart-card .chart-tooltip rect {
                fill: #101828;
                opacity: 0.94;
            }
            .investor-chart-card .chart-tooltip-date {
                fill: #ffffff;
                font-size: 11px;
                font-weight: 750;
            }
            .investor-chart-card .chart-tooltip-price {
                fill: #dbeafe;
                font-size: 12px;
                font-weight: 850;
            }
            .investor-chart-card .chart-hover-point:hover .chart-dot,
            .investor-chart-card .chart-hover-point:hover .chart-tooltip {
                opacity: 1;
            }
            .finance-metric-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 10px;
                margin-top: 15px;
            }
            .finance-metric-tile {
                min-height: 92px;
                padding: 12px 8px 10px;
                border: 1px solid #e5ebf3;
                border-radius: 9px;
                background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
                text-align: center;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .finance-metric-label {
                min-height: 36px;
                color: #17213a;
                font-size: 13px;
                font-weight: 800;
                line-height: 1.25;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                word-break: keep-all;
            }
            .finance-metric-label span {
                display: block;
                margin-top: 2px;
                color: #475467;
                font-size: 12px;
                font-weight: 700;
            }
            .finance-metric-value {
                margin-top: 8px;
                color: #1263ff;
                font-size: 18px;
                line-height: 1.15;
                font-weight: 850;
                font-variant-numeric: tabular-nums;
                white-space: nowrap;
                min-height: 23px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .finance-metric-sub {
                margin-top: 6px;
                color: #475467;
                font-size: 12px;
                font-weight: 650;
            }
            .theme-list {
                display: grid;
                gap: 10px;
                margin-top: 15px;
            }
            .theme-row {
                display: grid;
                grid-template-columns: 34px 74px 1fr;
                align-items: center;
                gap: 11px;
                min-height: 48px;
                padding: 8px 10px;
                border-radius: 10px;
                background: #fbfcff;
            }
            .theme-icon {
                width: 32px;
                height: 32px;
                border-radius: 10px;
                display: inline-block;
                position: relative;
            }
            .theme-icon::after {
                content: "";
                position: absolute;
                inset: 9px;
                border: 2px solid currentColor;
                border-radius: 50%;
            }
            .theme-icon.blue {
                background: #eef5ff;
                color: #1263ff;
            }
            .theme-icon.green {
                background: #e8fbef;
                color: #13a35f;
            }
            .theme-icon.orange {
                background: #fff4e5;
                color: #f97316;
            }
            .theme-icon.purple {
                background: #f4e8ff;
                color: #8b5cf6;
            }
            .theme-label {
                color: #1263ff;
                font-size: 13px;
                font-weight: 850;
            }
            .theme-copy {
                min-width: 0;
                color: #344054;
                font-size: 12px;
                font-weight: 650;
                line-height: 1.45;
            }
            .theme-copy strong {
                color: #17213a;
                font-weight: 850;
                margin-right: 7px;
            }
            .agent-opinion-list {
                display: grid;
                gap: 10px;
                margin-top: 15px;
            }
            .agent-opinion-row {
                display: grid;
                grid-template-columns: 32px 76px 1fr;
                align-items: center;
                gap: 10px;
                min-height: 54px;
                padding: 9px 10px;
                border-radius: 10px;
                background: #fbfcff;
            }
            .agent-icon {
                width: 30px;
                height: 30px;
                border-radius: 10px;
                display: inline-block;
                position: relative;
            }
            .agent-icon::after {
                content: "";
                position: absolute;
                inset: 9px;
                border: 2px solid currentColor;
                border-radius: 50%;
            }
            .agent-icon.blue,
            .agent-icon.indigo {
                background: #eef5ff;
                color: #1263ff;
            }
            .agent-icon.green {
                background: #e8fbef;
                color: #13a35f;
            }
            .agent-icon.orange {
                background: #fff4e5;
                color: #f97316;
            }
            .agent-icon.purple {
                background: #f4e8ff;
                color: #8b5cf6;
            }
            .agent-icon.teal {
                background: #e6fffb;
                color: #0891b2;
            }
            .agent-label {
                color: #1263ff;
                font-size: 13px;
                font-weight: 850;
            }
            .agent-copy {
                min-width: 0;
                color: #344054;
                font-size: 12px;
                font-weight: 650;
                line-height: 1.48;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            .risk-list {
                margin: 15px 0 0;
                padding: 0;
                list-style: none;
                display: grid;
                gap: 10px;
            }
            .risk-row {
                display: grid;
                grid-template-columns: 25px 64px 1fr;
                gap: 10px;
                align-items: start;
                padding: 9px 10px;
                border-radius: 10px;
                background: #fbfcff;
                color: #344054;
                font-size: 12px;
                font-weight: 650;
                line-height: 1.5;
            }
            .risk-agent {
                color: #1263ff;
                font-size: 12px;
                font-weight: 850;
            }
            .risk-copy {
                min-width: 0;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            .risk-list li {
                display: grid;
                grid-template-columns: 25px 1fr;
                gap: 10px;
                align-items: start;
                padding: 9px 10px;
                border-radius: 10px;
                background: #fbfcff;
                color: #344054;
                font-size: 12px;
                font-weight: 650;
                line-height: 1.5;
            }
            .risk-dot {
                width: 22px;
                height: 22px;
                border-radius: 50%;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                background: #fff1f0;
                color: #f04438;
                font-size: 12px;
                font-weight: 900;
            }
            .investor-signal-card {
                min-height: 306px;
            }
            .info-dot {
                width: 18px;
                height: 18px;
                border: 1px solid #98a2b3;
                border-radius: 50%;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                color: #98a2b3;
                font-size: 12px;
                font-weight: 850;
            }
            .signal-layout {
                display: grid;
                grid-template-columns: 196px minmax(0, 1fr);
                gap: 16px;
                align-items: center;
                margin-top: 18px;
            }
            .gauge-panel {
                text-align: center;
            }
            .gauge {
                width: 196px;
                height: 98px;
                margin: 0 auto 8px;
                border-radius: 196px 196px 0 0;
                background: conic-gradient(from 270deg at 50% 100%, #ef3b2d 0deg, #f97316 36deg, #facc15 76deg, #22c55e 126deg, #0891b2 180deg, transparent 180deg);
                position: relative;
                overflow: hidden;
            }
            .gauge::after {
                content: "";
                position: absolute;
                left: 24px;
                right: 24px;
                bottom: 0;
                height: 74px;
                border-radius: 148px 148px 0 0;
                background: #ffffff;
            }
            .gauge-needle {
                position: absolute;
                left: 50%;
                bottom: 0;
                width: 4px;
                height: 78px;
                margin-left: -2px;
                border-radius: 999px;
                background: #17213a;
                transform-origin: 50% 100%;
                z-index: 2;
                box-shadow: 0 4px 10px rgba(23, 33, 58, 0.22);
            }
            .gauge-scale {
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                gap: 3px;
                color: #475467;
                font-size: 12px;
                font-weight: 750;
            }
            .signal-opinion {
                width: 82px;
                min-height: 34px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                margin-top: 8px;
                border-radius: 999px;
                font-size: 19px;
                font-weight: 900;
            }
            .signal-score {
                margin-top: 8px;
                color: #17213a;
                font-size: 14px;
                font-weight: 700;
                white-space: nowrap;
            }
            .signal-score strong {
                color: #059669;
                font-weight: 900;
            }
            .signal-caption {
                margin-top: 6px;
                color: #475467;
                font-size: 13px;
                font-weight: 650;
            }
            .signal-factors {
                padding: 18px 14px;
                border-radius: 12px;
                background: #fbfcff;
                box-sizing: border-box;
                width: 100%;
                min-width: 0;
            }
            .signal-factor-title {
                margin-bottom: 12px;
                color: #17213a;
                font-size: 13px;
                font-weight: 850;
            }
            .signal-factor {
                display: grid;
                grid-template-columns: 58px minmax(0, 1fr) 38px;
                align-items: center;
                gap: 7px;
                margin: 10px 0;
                color: #475467;
                font-size: 12px;
                font-weight: 750;
            }
            .signal-factor > span {
                min-width: 0;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .signal-track {
                min-width: 0;
                height: 10px;
                border-radius: 999px;
                background: #eef2f7;
                position: relative;
                overflow: hidden;
            }
            .signal-track::after {
                content: "";
                position: absolute;
                left: 50%;
                top: 0;
                bottom: 0;
                width: 1px;
                background: #d0d5dd;
            }
            .signal-fill {
                position: absolute;
                top: 0;
                bottom: 0;
                border-radius: 999px;
            }
            .signal-fill.positive {
                background: #16a34a;
            }
            .signal-fill.negative {
                background: #f97316;
            }
            .signal-factor em {
                color: #344054;
                font-style: normal;
                text-align: right;
            }
            .signal-range {
                margin-top: 12px;
                color: #667085;
                font-size: 12px;
                text-align: center;
            }
            .investor-empty {
                margin-top: 16px;
                padding: 18px 14px;
                border: 1px dashed #d7deea;
                border-radius: 10px;
                background: #fbfcff;
                color: #667085;
                font-size: 13px;
                font-weight: 700;
            }
            .investor-empty.compact {
                margin: 8px 0;
                padding: 12px;
                font-size: 12px;
            }

            @media (max-width: 760px) {
                section[data-testid="stSidebar"] {
                    width: 300px !important;
                }

                .main-shell {
                    margin-top: 10px;
                    padding: 26px 22px;
                    border-radius: 14px;
                }

                .page-title {
                    font-size: 26px;
                }

                .chair-report-header {
                    display: block;
                }

                .chair-report-pills {
                    justify-content: flex-start;
                    margin-top: 12px;
                }

                .investor-header {
                    display: block;
                }

                .investor-update {
                    margin-top: 12px;
                }

                .investor-kpi-strip,
                .investor-grid-row,
                .finance-metric-grid,
                .signal-layout {
                    grid-template-columns: 1fr;
                }

                .investor-kpi + .investor-kpi {
                    border-left: 0;
                    border-top: 1px solid #dfe5ef;
                }

                .theme-row {
                    grid-template-columns: 34px 62px 1fr;
                }

                .investor-chart-head {
                    align-items: flex-start;
                    flex-direction: column;
                }

                .chart-period-tabs {
                    width: 100%;
                    justify-content: space-between;
                }

                .agent-opinion-row,
                .risk-row {
                    grid-template-columns: 30px 68px 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
