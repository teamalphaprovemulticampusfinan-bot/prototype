import streamlit as st

from dashboard.companies import SECTOR_OPTIONS, companies_by_sector
from dashboard.state import reset_company_if_needed, select_company, select_sector


MENU_OPTIONS = [
    {"name": "보고서 요약", "value": "investor_report"},
    {"name": "투자자 보고서", "value": "chair_report"},
    {"name": "정량 대시보드", "value": "quant_dashboard"},
]


def render_brand() -> None:
    st.sidebar.markdown(
        """
        <div class="alpha-brand">
            <div class="alpha-mark"></div>
            <div class="alpha-brand-name">AlphaProve</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_menu() -> None:
    for option in MENU_OPTIONS:
        selected = st.session_state.selected_menu == option["value"]
        if st.sidebar.button(
            option["name"],
            key=f"menu_{option['value']}",
            type="primary" if selected else "secondary",
        ):
            st.session_state.selected_menu = option["value"]
            st.rerun()


def render_sector_selector() -> None:
    st.sidebar.markdown(
        '<div class="sidebar-label">분야 선택 <span class="hint">ⓘ</span></div>',
        unsafe_allow_html=True,
    )

    columns = st.sidebar.columns(3, gap="small")
    for column, sector in zip(columns, SECTOR_OPTIONS):
        selected = st.session_state.get("selected_sector") == sector
        with column:
            if st.button(
                sector,
                key=f"sector_{sector}",
                type="primary" if selected else "secondary",
                use_container_width=True,
            ):
                select_sector(sector)
                st.rerun()


def render_company_selector() -> None:
    selected_sector = st.session_state.get("selected_sector")
    if not selected_sector:
        st.sidebar.markdown(
            """
            <div class="sidebar-empty">
                분야를 선택하면 기업 목록이 표시됩니다.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    companies = companies_by_sector.get(selected_sector, [])
    reset_company_if_needed(companies)

    st.sidebar.markdown(
        '<div class="sidebar-label">기업 선택 <span class="hint">ⓘ</span></div>',
        unsafe_allow_html=True,
    )

    if not companies:
        st.sidebar.markdown(
            """
            <div class="sidebar-empty">
                아직 등록된 기업이 없습니다.<br>
                companies.py의 companies_by_sector에 기업명을 문자열로 추가해 주세요.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    with st.sidebar.container(height=348, border=False):
        for company_name in companies:
            if not company_name:
                continue

            selected = st.session_state.get("company_name") == company_name
            label = f"✓  {company_name}" if selected else company_name
            if st.button(
                label,
                key=f"company_{selected_sector}_{company_name}",
                type="primary" if selected else "secondary",
            ):
                select_company(company_name)
                st.rerun()


def render_mypage() -> None:
    st.sidebar.markdown(
        """
        <div class="sidebar-bottom">
            <div class="mypage-row">
                <span class="mypage-icon">M</span>
                <span>마이페이지</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    render_brand()
    render_menu()
    render_sector_selector()
    render_company_selector()
    render_mypage()
