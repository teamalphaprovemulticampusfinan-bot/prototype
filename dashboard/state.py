from pathlib import Path

import streamlit as st

from dashboard.companies import companies_by_sector


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MENU_VALUES = {"investor_report", "chair_report", "quant_dashboard"}
CHART_PERIODS = {"3M", "6M", "1Y", "2Y", "3Y"}


def _query_value(key: str) -> str | None:
    try:
        value = st.query_params.get(key)
    except AttributeError:
        return None
    if isinstance(value, list):
        value = value[0] if value else None
    return str(value) if value else None


def initialize_state() -> None:
    query_menu = _query_value("menu")
    query_sector = _query_value("sector")
    query_company = _query_value("company")
    query_period = _query_value("period")

    defaults = {
        "selected_menu": query_menu if query_menu in MENU_VALUES else "investor_report",
        "selected_sector": query_sector if query_sector in companies_by_sector else None,
        "company_name": None,
        "chart_period": query_period.upper() if query_period and query_period.upper() in CHART_PERIODS else "3M",
    }
    if defaults["selected_sector"] and query_company in companies_by_sector.get(defaults["selected_sector"], []):
        defaults["company_name"] = query_company

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def get_company_name(companies: list[str]) -> str | None:
    company_name = st.session_state.get("company_name")
    return company_name if company_name in companies else None


def reset_company_if_needed(companies: list[str]) -> None:
    if get_company_name(companies) is None:
        st.session_state.company_name = None


def select_sector(sector: str) -> None:
    st.session_state.selected_sector = sector
    reset_company_if_needed(companies_by_sector.get(sector, []))


def select_company(company_name: str) -> None:
    st.session_state.company_name = company_name


def get_chair_report_dir() -> Path | None:
    selected_sector = st.session_state.get("selected_sector")
    company_name = st.session_state.get("company_name")
    if not selected_sector or not company_name:
        return None
    return DATA_DIR / selected_sector / company_name / "chair"
