import json
import re
from html import escape
from pathlib import Path
from textwrap import dedent
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.state import get_chair_report_dir


PERIOD_DELTAS = {
    "3M": pd.DateOffset(months=3),
    "6M": pd.DateOffset(months=6),
    "1Y": pd.DateOffset(years=1),
    "2Y": pd.DateOffset(years=2),
    "3Y": pd.DateOffset(years=3),
}

AGENT_LABELS = {
    "finance": "재무",
    "market": "시장",
    "tech": "기술",
    "valuation": "밸류에이션",
    "issue": "이슈",
    "macro": "거시환경",
}

AGENT_TONES = {
    "finance": "blue",
    "market": "teal",
    "tech": "indigo",
    "valuation": "green",
    "issue": "orange",
    "macro": "purple",
}

CHART_QUERY_KEY = "period"


def _html(markup: str) -> str:
    text = dedent(markup).strip()
    return re.sub(r"\n[ \t]+(?=<)", "\n", text)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip().replace(",", "")
        if not value:
            return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if pd.isna(number):
        return None
    return number


def _sort_finance_frame(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values("year").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_data(company_dir: Path) -> tuple[dict[str, Any], pd.DataFrame | None, pd.DataFrame | None]:
    json_files = sorted(
        company_dir.glob("*_chair.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    data: dict[str, Any] = {}
    if json_files:
        with open(json_files[0], encoding="utf-8") as f:
            data = json.load(f)

    finance_dir = company_dir.parent / "finance"

    stock_files = sorted(
        finance_dir.glob("*_주식.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    df_stock = None
    if stock_files:
        df_stock = pd.read_csv(stock_files[0], parse_dates=["date"])
        df_stock = df_stock.sort_values("date").reset_index(drop=True)
        df_stock = df_stock[df_stock["volume"] > 0]

    finance_files = sorted(
        finance_dir.glob("*_재무.csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    df_finance = None
    if finance_files:
        df_finance = _sort_finance_frame(pd.read_csv(finance_files[0]))

    return data, df_stock, df_finance


def _quantitative_decision(data: dict[str, Any]) -> dict[str, Any]:
    return data.get("auditor_summary", {}).get("quantitative_decision", {}) or {}


def _agent_decisions(data: dict[str, Any]) -> dict[str, Any]:
    return _quantitative_decision(data).get("agent_decisions", {}) or {}


def _compact_packets(data: dict[str, Any]) -> list[dict[str, Any]]:
    packets = data.get("auditor_compact_packets") or []
    return [packet for packet in packets if isinstance(packet, dict)]


def _final_opinion(data: dict[str, Any]) -> str:
    decision = _quantitative_decision(data)
    return (
        decision.get("final_recommendation")
        or decision.get("base_recommendation")
        or data.get("opinion")
        or "보유"
    )


def _opinion_tone(opinion: str) -> tuple[str, str]:
    if "매수" in opinion:
        return "#dcfce7", "#05803d"
    if "매도" in opinion:
        return "#fee2e2", "#d92d20"
    return "#dff8ea", "#059669"


def _format_number(value: Any, digits: int = 1, suffix: str = "") -> str:
    number = _as_float(value)
    if number is None:
        return "N/A"
    return f"{number:,.{digits}f}{suffix}"


def _format_percent(value: Any, digits: int = 1, signed: bool = False) -> str:
    number = _as_float(value)
    if number is None:
        return "N/A"
    sign = "+" if signed and number > 0 else ""
    return f"{sign}{number:.{digits}f}%"


def _format_price(value: Any) -> str:
    number = _as_float(value)
    if number is None:
        return "N/A"
    return f"{int(round(number)):,} 원"


def _format_krw_amount(value: Any) -> str:
    number = _as_float(value)
    if number is None:
        return "N/A"
    absolute = abs(number)
    sign = "-" if number < 0 else ""
    if absolute >= 100_000_000:
        return f"{sign}{absolute / 100_000_000:,.0f} 억원"
    if absolute >= 10_000:
        return f"{sign}{absolute / 10_000:,.0f} 만원"
    return f"{sign}{absolute:,.0f} 원"


def _text_color(value: Any, positive_color: str = "#f04438") -> str:
    number = _as_float(value)
    if number is None:
        return "#17213a"
    if number > 0:
        return positive_color
    if number < 0:
        return "#0b63f6"
    return "#17213a"


def _agent_key(packet: dict[str, Any]) -> str:
    return str(
        packet.get("agent")
        or packet.get("agent_name")
        or packet.get("name")
        or ""
    ).strip()


def _agent_label(agent: str) -> str:
    key = agent.lower()
    return AGENT_LABELS.get(key, agent or "Agent")


def _agent_tone(agent: str) -> str:
    return AGENT_TONES.get(agent.lower(), "blue")


def _selected_chart_period() -> str:
    period = str(st.session_state.get("chart_period") or "").upper()
    if not period:
        query_value = None
        try:
            query_value = st.query_params.get(CHART_QUERY_KEY)
        except AttributeError:
            query_value = None

        if isinstance(query_value, list):
            query_value = query_value[0] if query_value else None
        period = str(query_value or "3M").upper()

    if period not in PERIOD_DELTAS:
        period = "3M"
    st.session_state.chart_period = period
    return period


def _set_chart_period(period: str) -> None:
    selected_period = str(period).upper()
    if selected_period not in PERIOD_DELTAS:
        selected_period = "3M"

    st.session_state.chart_period = selected_period
    try:
        st.query_params[CHART_QUERY_KEY] = selected_period
    except AttributeError:
        pass


def calc_metrics(df: pd.DataFrame) -> dict[str, Any]:
    latest = df.iloc[-1]
    current_price = latest["close"]
    date_str = latest["date"].strftime("%m/%d")
    update_date = latest["date"].strftime("%Y.%m.%d")

    idx = max(0, len(df) - 21)
    price_1m_ago = df.iloc[idx]["close"]
    ret_1m = (current_price / price_1m_ago - 1) * 100

    recent_30 = pd.to_numeric(df["return"], errors="coerce").dropna().tail(30)
    vol_30 = recent_30.std() * np.sqrt(252) * 100 if not recent_30.empty else None
    mdd_1y = pd.to_numeric(df["mdd"], errors="coerce").tail(252).min() * 100

    return {
        "current_price": current_price,
        "date_str": date_str,
        "update_date": update_date,
        "ret_1m": ret_1m,
        "vol_30": vol_30,
        "mdd_1y": mdd_1y,
    }


def _latest_finance_metrics(df_finance: pd.DataFrame | None) -> list[dict[str, str]]:
    if df_finance is None or df_finance.empty:
        return []

    latest = df_finance.iloc[-1]
    year_value = latest.get("year")
    year = str(int(year_value)) if _as_float(year_value) is not None else ""
    year_sub = f"({year})" if year else ""

    sales_growth = None
    if len(df_finance) >= 2:
        latest_sales = _as_float(latest.get("sales"))
        previous_sales = _as_float(df_finance.iloc[-2].get("sales"))
        if latest_sales is not None and previous_sales:
            sales_growth = (latest_sales / previous_sales - 1) * 100

    return [
        {
            "label": "매출성장률",
            "hint": "(YoY)",
            "value": _format_percent(sales_growth, digits=1, signed=True),
            "sub": year_sub,
        },
        {
            "label": "영업이익률",
            "hint": "",
            "value": _format_percent(latest.get("operating_margin"), digits=1),
            "sub": year_sub,
        },
        {
            "label": "ROE",
            "hint": "",
            "value": _format_percent(latest.get("roe"), digits=1),
            "sub": year_sub,
        },
        {
            "label": "부채비율",
            "hint": "",
            "value": _format_percent(latest.get("debt_ratio"), digits=1),
            "sub": year_sub,
        },
        {
            "label": "FCF",
            "hint": "",
            "value": _format_krw_amount(latest.get("fcf")),
            "sub": year_sub,
        },
        {
            "label": "유동성",
            "hint": "",
            "value": _format_percent(latest.get("current_ratio_%"), digits=0),
            "sub": year_sub,
        },
    ]


def _section_items(markdown: str, section_title: str, limit: int = 5) -> list[str]:
    if not markdown:
        return []

    pattern = rf"^##\s+\d+\.\s+{re.escape(section_title)}\s*$"
    lines = markdown.splitlines()
    capture = False
    items: list[str] = []

    for line in lines:
        stripped = line.strip()
        if re.match(pattern, stripped):
            capture = True
            continue
        if capture and stripped.startswith("## "):
            break
        if not capture:
            continue

        match = re.match(r"^(?:[-*]|\d+\.)\s+(.*)$", stripped)
        if match:
            text = re.sub(r"\*\*([^*]+)\*\*", r"\1", match.group(1))
            text = text.replace("`", "").strip()
            if text:
                items.append(text)
        if len(items) >= limit:
            break

    return items


def _fallback_summary_items(data: dict[str, Any]) -> list[str]:
    decision = _quantitative_decision(data)
    opinion = _final_opinion(data)
    weighted_signal = decision.get("weighted_signal")
    items = [f"최종 의견은 {opinion}이며, 종합 신호는 {_format_number(weighted_signal, 2)}입니다."]

    for agent_key in ("finance", "valuation", "tech"):
        agent = _agent_decisions(data).get(agent_key, {})
        basis = agent.get("basis") or []
        if basis:
            items.append(f"{AGENT_LABELS[agent_key]}: {basis[0]}")

    return items[:5]


def _summary_items(data: dict[str, Any]) -> list[str]:
    report = data.get("chair_report", "")
    return _section_items(report, "핵심 판단 요약", 5) or _fallback_summary_items(data)


def _agent_summary_rows(data: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for packet in _compact_packets(data):
        agent = _agent_key(packet)
        summary = _clean_text(packet.get("summary"))
        if not summary:
            continue
        rows.append(
            {
                "agent": _agent_label(agent),
                "tone": _agent_tone(agent),
                "summary": summary,
            }
        )
    return rows


def _agent_risk_rows(data: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for packet in _compact_packets(data):
        risks = packet.get("key_risks") or []
        first_risk = ""
        if isinstance(risks, str):
            first_risk = risks
        elif isinstance(risks, list) and risks:
            first_risk = str(risks[0])

        first_risk = _clean_text(first_risk)
        if not first_risk:
            continue

        agent = _agent_key(packet)
        rows.append(
            {
                "agent": _agent_label(agent),
                "tone": _agent_tone(agent),
                "risk": first_risk,
            }
        )
    return rows


def _signal_factor_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for packet in _compact_packets(data):
        agent = _agent_key(packet)
        signal = _as_float(packet.get("auditor_signal"))
        if signal is None:
            continue
        rows.append(
            {
                "agent": _agent_label(agent),
                "tone": _agent_tone(agent),
                "signal": signal,
            }
        )

    if rows:
        return rows

    for key, decision in _agent_decisions(data).items():
        signal = _as_float(decision.get("signal"))
        if signal is None:
            continue
        rows.append(
            {
                "agent": AGENT_LABELS.get(key, key),
                "tone": AGENT_TONES.get(key, "blue"),
                "signal": signal,
            }
        )
    return rows


def _stock_chart_frame(df_stock: pd.DataFrame | None, period: str) -> pd.DataFrame:
    if df_stock is None or df_stock.empty:
        return pd.DataFrame(columns=["date", "close"])
    if "date" not in df_stock.columns or "close" not in df_stock.columns:
        return pd.DataFrame(columns=["date", "close"])

    frame = df_stock[["date", "close"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame = frame.dropna(subset=["date", "close"]).sort_values("date").reset_index(drop=True)
    if frame.empty:
        return frame

    latest_date = frame["date"].max()
    return frame[frame["date"] >= latest_date - PERIOD_DELTAS[period]].reset_index(drop=True)


def _stock_price_figure(df_chart: pd.DataFrame) -> go.Figure:
    prices = df_chart["close"]
    min_price = float(prices.min())
    max_price = float(prices.max())
    padding = (max_price - min_price) * 0.08 or max_price * 0.04 or 1
    y_min = min_price - padding
    y_max = max_price + padding

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_chart["date"],
            y=[y_min] * len(df_chart),
            mode="lines",
            line={"width": 0},
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df_chart["date"],
            y=df_chart["close"],
            mode="lines",
            line={"color": "#1263ff", "width": 3},
            fill="tonexty",
            fillcolor="rgba(47, 111, 255, 0.12)",
            hovertemplate="%{x|%Y.%m.%d}<br><b>%{y:,.0f} 원</b><extra></extra>",
            showlegend=False,
        )
    )
    fig.update_layout(
        height=270,
        margin={"l": 48, "r": 12, "t": 8, "b": 32},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        hovermode="x",
        hoverlabel={
            "bgcolor": "#101828",
            "bordercolor": "rgba(0,0,0,0)",
            "font": {"color": "#ffffff", "size": 12},
        },
        font={
            "family": "Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif",
            "color": "#667085",
        },
    )
    fig.update_xaxes(
        fixedrange=True,
        showgrid=False,
        showline=False,
        zeroline=False,
        tickformat="%m/%d",
        tickfont={"size": 12, "color": "#667085"},
    )
    fig.update_yaxes(
        fixedrange=True,
        range=[y_min, y_max],
        showgrid=True,
        gridcolor="#edf1f7",
        showline=False,
        zeroline=False,
        tickformat=",d",
        tickfont={"size": 12, "color": "#667085"},
    )
    return fig


def _render_stock_chart_card(df_stock: pd.DataFrame | None, period: str) -> None:
    chart_frame = _stock_chart_frame(df_stock, period)

    with st.container(key="investor_chart_card"):
        title_col, tabs_col = st.columns([1.0, 1.05], vertical_alignment="center")
        with title_col:
            st.markdown('<div class="investor-card-title">주가 추이</div>', unsafe_allow_html=True)
        with tabs_col:
            tab_columns = st.columns(len(PERIOD_DELTAS), gap="small")
            for tab_column, item in zip(tab_columns, PERIOD_DELTAS):
                with tab_column:
                    st.button(
                        item,
                        key=f"investor_chart_period_{item}",
                        type="primary" if item == period else "secondary",
                        use_container_width=True,
                        on_click=_set_chart_period,
                        args=(item,),
                    )

        st.markdown('<div class="chart-unit">(원)</div>', unsafe_allow_html=True)
        if chart_frame.empty:
            st.markdown(
                '<div class="investor-empty">주식 데이터를 찾을 수 없습니다.</div>',
                unsafe_allow_html=True,
            )
            return

        st.plotly_chart(
            _stock_price_figure(chart_frame),
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True, "scrollZoom": False},
            key=f"investor_price_chart_{period}",
        )


def _metric_strip_html(metrics: dict[str, Any] | None) -> str:
    if not metrics:
        return _html(
            """
            <section class="investor-kpi-strip investor-kpi-empty">
                <div class="investor-empty">주식 데이터를 찾을 수 없습니다.</div>
            </section>
            """
        )

    ret_color = _text_color(metrics.get("ret_1m"))
    mdd_color = _text_color(metrics.get("mdd_1y"))
    return _html(
        f"""
        <section class="investor-kpi-strip">
            <div class="investor-kpi">
                <div class="investor-kpi-label">현재가</div>
                <div class="investor-kpi-value">{_format_price(metrics.get("current_price"))}</div>
                <div class="investor-kpi-sub">({escape(metrics.get("date_str", ""))} 종가)</div>
            </div>
            <div class="investor-kpi">
                <div class="investor-kpi-label">1개월 수익률</div>
                <div class="investor-kpi-value" style="color:{ret_color};">{_format_percent(metrics.get("ret_1m"), digits=2, signed=True)}</div>
                <div class="investor-kpi-sub">(1M)</div>
            </div>
            <div class="investor-kpi">
                <div class="investor-kpi-label">변동성 (30일)</div>
                <div class="investor-kpi-value">{_format_percent(metrics.get("vol_30"), digits=1)}</div>
                <div class="investor-kpi-sub">(연환산)</div>
            </div>
            <div class="investor-kpi">
                <div class="investor-kpi-label">MDD (1년)</div>
                <div class="investor-kpi-value" style="color:{mdd_color};">{_format_percent(metrics.get("mdd_1y"), digits=1)}</div>
                <div class="investor-kpi-sub">(고점 대비)</div>
            </div>
        </section>
        """
    )


def _summary_card_html(items: list[str]) -> str:
    item_html = "".join(f"<li>{escape(item)}</li>" for item in items[:5])
    return _html(
        f"""
        <section class="investor-card investor-summary-card">
            <div class="investor-card-title"><span class="title-icon blue">◆</span>핵심 요약</div>
            <ul class="investor-bullet-list">{item_html}</ul>
        </section>
        """
    )


def _finance_card_html(metrics: list[dict[str, str]]) -> str:
    if not metrics:
        body = '<div class="investor-empty">재무 데이터를 찾을 수 없습니다.</div>'
    else:
        tiles = []
        for metric in metrics:
            hint = f'<span>{escape(metric["hint"])}</span>' if metric.get("hint") else ""
            tiles.append(
                _html(
                    f"""
                    <div class="finance-metric-tile">
                        <div class="finance-metric-label">{escape(metric["label"])}{hint}</div>
                        <div class="finance-metric-value">{escape(metric["value"])}</div>
                        <div class="finance-metric-sub">{escape(metric["sub"])}</div>
                    </div>
                    """
                )
            )
        body = f'<div class="finance-metric-grid">{"".join(tiles)}</div>'

    return _html(
        f"""
        <section class="investor-card investor-finance-card">
            <div class="investor-card-title"><span class="title-icon blue">₩</span>재무 안정성 지표</div>
            {body}
        </section>
        """
    )


def _agent_summary_card_html(rows: list[dict[str, str]]) -> str:
    if rows:
        row_html = "".join(
            _html(
                f"""
                <div class="agent-opinion-row">
                    <span class="agent-icon {escape(row["tone"])}"></span>
                    <div class="agent-label">{escape(row["agent"])}</div>
                    <div class="agent-copy">{escape(row["summary"])}</div>
                </div>
                """
            )
            for row in rows
        )
    else:
        row_html = '<div class="investor-empty">에이전트 요약을 찾을 수 없습니다.</div>'

    return _html(
        f"""
        <section class="investor-card">
            <div class="investor-card-title"><span class="title-icon blue">◎</span>각 에이전트 의견서 요약</div>
            <div class="agent-opinion-list">{row_html}</div>
        </section>
        """
    )


def _risk_card_html(rows: list[dict[str, str]]) -> str:
    if rows:
        row_html = "".join(
            _html(
                f"""
                <div class="risk-row">
                    <span class="risk-dot">!</span>
                    <div class="risk-agent">{escape(row["agent"])}</div>
                    <div class="risk-copy">{escape(row["risk"])}</div>
                </div>
                """
            )
            for row in rows
        )
    else:
        row_html = '<div class="investor-empty">리스크 항목을 찾을 수 없습니다.</div>'

    return _html(
        f"""
        <section class="investor-card">
            <div class="investor-card-title"><span class="title-icon blue">□</span>리스크</div>
            <div class="risk-list">{row_html}</div>
        </section>
        """
    )


def _signal_name(value: Any) -> str:
    number = _as_float(value)
    if number is None:
        return "중립"
    if number >= 0.25:
        return "매수 쪽"
    if number >= 0.05:
        return "보유 우위"
    if number > -0.05:
        return "중립"
    if number > -0.25:
        return "축소 우위"
    return "매도 쪽"


def _signal_card_html(data: dict[str, Any]) -> str:
    decision = _quantitative_decision(data)
    weighted_signal = decision.get("weighted_signal")
    signal_value = _as_float(weighted_signal) or 0.0
    clamped = max(-1, min(1, signal_value))
    angle = -90 + ((clamped + 1) / 2 * 180)
    opinion = _final_opinion(data)
    opinion_bg, opinion_color = _opinion_tone(opinion)

    bars = ""
    for row in _signal_factor_rows(data):
        signal = max(-1, min(1, float(row["signal"])))
        width = abs(signal) * 50
        left = 50 - width if signal < 0 else 50
        tone = "positive" if signal >= 0 else "negative"
        bars += _html(
            f"""
            <div class="signal-factor">
                <span>{escape(row["agent"])}</span>
                <div class="signal-track">
                    <div class="signal-fill {tone}" style="left:{left:.1f}%;width:{width:.1f}%;"></div>
                </div>
                <em>{signal:+.2f}</em>
            </div>
            """
        )

    if not bars:
        bars = '<div class="investor-empty compact">신호 구성 요인을 찾을 수 없습니다.</div>'

    return _html(
        f"""
        <section class="investor-card investor-signal-card">
            <div class="investor-card-title"><span class="title-icon blue">✣</span>종합 방향성 신호 <span class="info-dot">i</span></div>
            <div class="signal-layout">
                <div class="gauge-panel">
                    <div class="gauge">
                        <div class="gauge-needle" style="transform:rotate({angle:.1f}deg);"></div>
                    </div>
                    <div class="gauge-scale">
                        <span>매도</span><span>축소</span><span>중립</span><span>확대</span><span>매수</span>
                    </div>
                    <div class="signal-opinion" style="background:{opinion_bg};color:{opinion_color};">{escape(opinion)}</div>
                    <div class="signal-score">신호 점수 <strong>{signal_value:+.2f}</strong> / 1.00</div>
                    <div class="signal-caption">{escape(_signal_name(signal_value))}에 가까운 의견 유지</div>
                </div>
                <div class="signal-factors">
                    <div class="signal-factor-title">신호 구성 요인</div>
                    {bars}
                    <div class="signal-range">-1 (매도) → +1 (매수)</div>
                </div>
            </div>
        </section>
        """
    )


def _render_empty_state(selected_sector: str) -> None:
    st.markdown(
        _html(
            f"""
            <main class="main-shell investor-shell">
                <div class="selection-row">
                    <span class="selection-pill">{selected_sector or "분야 미선택"}</span>
                </div>
                <h1 class="page-title">투자자 보고서</h1>
                <p class="page-copy">기업을 선택하면 Chair 투자자 보고서가 표시됩니다.</p>
            </main>
            """
        ),
        unsafe_allow_html=True,
    )


def render_investor_report() -> None:
    selected_sector = escape(st.session_state.selected_sector or "")
    selected_company_name = escape(st.session_state.company_name or "")
    company_dir = get_chair_report_dir()

    if company_dir is None:
        _render_empty_state(selected_sector)
        return

    data, df_stock, df_finance = load_data(company_dir)
    opinion = _final_opinion(data)
    opinion_bg, opinion_color = _opinion_tone(opinion)
    period = _selected_chart_period()

    stock_metrics = calc_metrics(df_stock) if df_stock is not None and not df_stock.empty else None
    update_date = stock_metrics["update_date"] if stock_metrics else "데이터 없음"

    with st.container(key="investor_shell"):
        st.markdown(
            _html(
                f"""
                <header class="investor-header">
                    <div>
                        <div class="investor-title-row">
                            <h1 class="page-title">{selected_company_name}</h1>
                            <span class="selection-pill neutral">{selected_sector}</span>
                            <span class="selection-pill opinion-pill" style="background:{opinion_bg};color:{opinion_color};">최종 의견: {escape(opinion)}</span>
                        </div>
                        <p class="investor-subtitle">Chair 투자자 보고서</p>
                    </div>
                    <div class="investor-update">최종 업데이트: {escape(update_date)} <span class="calendar-icon">□</span></div>
                </header>

                {_metric_strip_html(stock_metrics)}
                """
            ),
            unsafe_allow_html=True,
        )

        _render_stock_chart_card(df_stock, period)

        st.markdown(
            _html(
                f"""
                <div class="investor-grid-row investor-row-main">
                    {_summary_card_html(_summary_items(data))}
                    {_finance_card_html(_latest_finance_metrics(df_finance))}
                    {_signal_card_html(data)}
                </div>

                <div class="investor-grid-row investor-row-wide">
                    {_agent_summary_card_html(_agent_summary_rows(data))}
                    {_risk_card_html(_agent_risk_rows(data))}
                </div>
                """
            ),
            unsafe_allow_html=True,
        )
