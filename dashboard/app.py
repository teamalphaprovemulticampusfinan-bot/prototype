import sys
from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

st.set_page_config(
    page_title="AlphaProve",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    from dashboard.chair_report import render_chair_report
    from dashboard.investor_report import render_investor_report
    from dashboard.quant_dashboard import render_quant_dashboard
    from dashboard.sidebar import render_sidebar
    from dashboard.state import initialize_state
    from dashboard.styles import apply_custom_css

    initialize_state()
    apply_custom_css()
    render_sidebar()

    if st.session_state.selected_menu == "quant_dashboard":
        render_quant_dashboard()
        return

    if st.session_state.selected_menu == "chair_report":
        render_chair_report()
        return

    render_investor_report()


if __name__ == "__main__":
    main()
