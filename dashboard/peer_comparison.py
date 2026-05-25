from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.state import DATA_DIR


SHEET_DASHBOARD = "00_대시보드"
SHEET_PEERS = "10_피어비교"
SHEET_UNIVERSE = "18_밸류에이션_유니버스"
SHEET_COMPOSITE = "22_종합가치평가"


def render_peer_comparison(payload: dict[str, Any] | None = None) -> None:
    selected_sector = st.session_state.get("selected_sector")
    company_name = st.session_state.get("company_name")

    if not selected_sector or not company_name:
        st.info("분야와 기업을 선택하면 동종기업 비교가 표시됩니다.")
        return

    valuation_dir = DATA_DIR / selected_sector / company_name / "valuation"
    workbook_path = _find_workbook(valuation_dir)
    if workbook_path is None:
        st.warning(f"valuation workbook을 찾을 수 없습니다: {valuation_dir}")
        return

    try:
        data = _load_peer_workbook(str(workbook_path), workbook_path.stat().st_mtime_ns)
    except Exception as exc:
        st.error(f"동종기업 비교 데이터를 읽는 중 오류가 발생했습니다: {exc}")
        return

    dashboard_map = _extract_dashboard_values(data["dashboard_raw"])
    focus_df = _prepare_peer_df(data["peer_df"])
    peer_df = _prepare_peer_df(data["peer_df"], exclude_company=company_name)
    universe_df = _prepare_universe_df(data["universe_raw"])
    conclusion = _extract_conclusion(data["composite_raw"])

    if universe_df.empty:
        st.warning("밸류에이션 유니버스 데이터를 찾을 수 없습니다.")
        return

    universe_unique = _dedupe_universe(universe_df)
    target_row = _find_company_row(universe_unique, company_name)
    focus_companies = set(focus_df.get("기업명", pd.Series(dtype=str)).dropna().astype(str))
    peer_group = _safe_text(target_row.get("피어 그룹")) if target_row is not None else "–"

    universe_count = _extract_summary_number(data["universe_raw"], "reference_universe_rows")
    if universe_count is None:
        universe_count = len(universe_unique)
    peer_group_size = _peer_group_size(universe_unique, peer_group)

    _inject_peer_css()
    _render_top_cards(
        universe_count=int(universe_count),
        focus_count=len(focus_df),
        peer_group=peer_group,
        peer_group_size=peer_group_size,
    )

    scatter_col, interp_col = st.columns([1.22, 1.0], gap="medium")
    with scatter_col:
        with st.container(border=True):
            st.markdown(
                '<div class="peer-section-title">밸류에이션 유니버스 내 위치 '
                '<span class="peer-info">i</span></div>',
                unsafe_allow_html=True,
            )
            fig = _build_universe_scatter(universe_unique, focus_companies, company_name)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with interp_col:
        with st.container(border=True):
            st.markdown(
                '<div class="peer-section-title">투자자용 해석 '
                '<span class="peer-info">i</span></div>',
                unsafe_allow_html=True,
            )
            _render_conclusion(conclusion)

    lower_left, lower_right = st.columns([1.22, 1.0], gap="medium")
    target_metrics = _build_target_metrics(dashboard_map, company_name, target_row, payload)
    with lower_left:
        with st.container(border=True):
            st.markdown('<div class="peer-section-title">주요 동종기업 비교</div>', unsafe_allow_html=True)
            _render_peer_table(peer_df, target_metrics)

        with st.container(border=True):
            st.markdown(
                f'<div class="peer-section-title">비교군 평균 vs {escape(company_name)}</div>',
                unsafe_allow_html=True,
            )
            bar_fig = _build_average_bar(peer_df, target_metrics, company_name)
            st.plotly_chart(bar_fig, use_container_width=True, config={"displayModeBar": False})

    with lower_right:
        with st.container(border=True):
            st.markdown(
                '<div class="peer-section-title">엑셀 연동 안내 '
                '<span class="peer-info">i</span></div>',
                unsafe_allow_html=True,
            )
            _render_excel_linkage()


def _find_workbook(valuation_dir: Path) -> Path | None:
    if not valuation_dir.exists():
        return None
    files = sorted(
        (path for path in valuation_dir.glob("*_valuation_workbook.xlsx") if not path.name.startswith("~$")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


@st.cache_data(show_spinner=False)
def _load_peer_workbook(workbook_path: str, mtime_ns: int) -> dict[str, pd.DataFrame]:
    path = Path(workbook_path)
    _ = mtime_ns
    return {
        "dashboard_raw": pd.read_excel(path, sheet_name=SHEET_DASHBOARD, header=None, engine="openpyxl"),
        "peer_df": pd.read_excel(path, sheet_name=SHEET_PEERS, header=1, engine="openpyxl"),
        "universe_raw": pd.read_excel(path, sheet_name=SHEET_UNIVERSE, header=None, engine="openpyxl"),
        "composite_raw": pd.read_excel(path, sheet_name=SHEET_COMPOSITE, header=None, engine="openpyxl"),
    }


def _prepare_peer_df(df: pd.DataFrame, exclude_company: str | None = None) -> pd.DataFrame:
    if df.empty:
        return df
    cleaned = df.copy()
    cleaned.columns = [str(col).strip() for col in cleaned.columns]
    if "기업명" in cleaned.columns:
        cleaned = cleaned[cleaned["기업명"].notna()]
        cleaned = cleaned[cleaned["기업명"].astype(str).str.strip() != ""]
        if exclude_company:
            cleaned = cleaned[cleaned["기업명"].astype(str).str.strip() != exclude_company]
    return cleaned.reset_index(drop=True)


def _prepare_universe_df(raw: pd.DataFrame) -> pd.DataFrame:
    header_idx = _find_header_row(raw, ["Universe 순번", "기업명", "Valuation 신뢰도", "Credit 신뢰도"])
    if header_idx is None:
        return pd.DataFrame()

    columns = raw.iloc[header_idx].fillna("").astype(str).str.strip().tolist()
    df = raw.iloc[header_idx + 1 :].copy()
    df.columns = columns
    df = df.loc[:, [col for col in df.columns if col]]
    if "기업명" not in df.columns:
        return pd.DataFrame()
    df = df[df["기업명"].notna()]
    df = df[df["기업명"].astype(str).str.strip() != ""]
    return df.reset_index(drop=True)


def _dedupe_universe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    subset = "기업명"
    cleaned = df.copy()
    cleaned[subset] = cleaned[subset].astype(str).str.strip()
    cleaned = cleaned[cleaned[subset] != ""]
    return cleaned.drop_duplicates(subset=[subset], keep="first").reset_index(drop=True)


def _find_header_row(raw: pd.DataFrame, required: list[str]) -> int | None:
    for idx, row in raw.iterrows():
        values = {str(value).strip() for value in row.dropna().tolist()}
        if all(item in values for item in required):
            return int(idx)
    return None


def _extract_dashboard_values(raw: pd.DataFrame) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for row_idx in range(len(raw) - 1):
        labels = raw.iloc[row_idx]
        values = raw.iloc[row_idx + 1]
        for col_idx, label in labels.items():
            if pd.isna(label):
                continue
            key = str(label).strip()
            if not key or key in {"핵심 해석", "데이터 독립성"}:
                continue
            value = values.iloc[col_idx] if col_idx < len(values) else None
            if pd.notna(value) and str(value).strip():
                result[key] = value
    return result


def _extract_summary_number(raw: pd.DataFrame, key: str) -> float | None:
    for _, row in raw.iterrows():
        cells = row.tolist()
        for idx, cell in enumerate(cells[:-1]):
            if str(cell).strip() == key:
                return _to_float(cells[idx + 1])
    return None


def _extract_conclusion(raw: pd.DataFrame) -> str:
    for _, row in raw.iterrows():
        cells = row.tolist()
        for idx, cell in enumerate(cells[:-1]):
            if str(cell).strip() == "결론":
                value = cells[idx + 1]
                return "" if pd.isna(value) else str(value).strip()
    return ""


def _find_company_row(df: pd.DataFrame, company_name: str) -> pd.Series | None:
    if "기업명" not in df.columns:
        return None
    matched = df[df["기업명"].astype(str).str.strip() == company_name]
    if matched.empty:
        return None
    return matched.iloc[0]


def _peer_group_size(df: pd.DataFrame, peer_group: str) -> int:
    if not peer_group or peer_group == "–" or "피어 그룹" not in df.columns:
        return 0
    return int((df["피어 그룹"].astype(str).str.strip() == peer_group).sum())


def _build_target_metrics(
    dashboard_map: dict[str, Any],
    company_name: str,
    target_row: pd.Series | None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    market = _safe_text(target_row.get("시장")) if target_row is not None else "–"
    payload = payload or {}
    latest_financials = payload.get("latest_financials", {}) if isinstance(payload, dict) else {}
    price_summary = payload.get("price_summary", {}) if isinstance(payload, dict) else {}
    summary_cards = payload.get("summary_cards", {}) if isinstance(payload, dict) else {}

    market_cap = _first_present(price_summary.get("market_cap"), dashboard_map.get("시가총액"))
    net_income = latest_financials.get("net_income")
    per = _ratio(market_cap, net_income)

    return {
        "기업명": company_name,
        "시장": market,
        "현재가": _first_present(dashboard_map.get("현재가"), price_summary.get("latest_close")),
        "P/S": _first_present(dashboard_map.get("P/S"), _card_value(summary_cards, "target_psr")),
        "PER": per,
        "영업이익률": latest_financials.get("op_margin"),
        "ROE": latest_financials.get("roe"),
        "1년 수익률": _first_present(dashboard_map.get("1년 수익률"), price_summary.get("return_1y")),
    }


def _build_universe_scatter(
    universe_df: pd.DataFrame,
    focus_companies: set[str],
    company_name: str,
) -> go.Figure:
    df = universe_df.copy()
    df["Valuation 신뢰도"] = pd.to_numeric(df.get("Valuation 신뢰도"), errors="coerce")
    df["Credit 신뢰도"] = pd.to_numeric(df.get("Credit 신뢰도"), errors="coerce")
    df = df.dropna(subset=["Valuation 신뢰도", "Credit 신뢰도"])
    df["기업명"] = df["기업명"].astype(str)

    target_df = df[df["기업명"] == company_name]
    focus_df = df[df["기업명"].isin(focus_companies) & (df["기업명"] != company_name)]
    base_df = df[~df["기업명"].isin(focus_companies | {company_name})]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=base_df["Valuation 신뢰도"],
            y=base_df["Credit 신뢰도"],
            mode="markers",
            name="유니버스 기업",
            marker={"size": 8, "color": "#c8ced8", "opacity": 0.72, "line": {"width": 0}},
            text=base_df["기업명"],
            customdata=base_df[["피어 그룹"]] if "피어 그룹" in base_df.columns else None,
            hovertemplate="<b>%{text}</b><br>Valuation 신뢰도 %{x:.1%}<br>Credit 신뢰도 %{y:.1%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=focus_df["Valuation 신뢰도"],
            y=focus_df["Credit 신뢰도"],
            mode="markers+text",
            name="동종 그룹 주요 기업",
            marker={"size": 11, "color": "#68a7ff", "opacity": 0.92, "line": {"width": 1, "color": "#ffffff"}},
            text=focus_df["기업명"],
            textposition="top center",
            textfont={"size": 11, "color": "#26344d"},
            hovertemplate="<b>%{text}</b><br>Valuation 신뢰도 %{x:.1%}<br>Credit 신뢰도 %{y:.1%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=target_df["Valuation 신뢰도"],
            y=target_df["Credit 신뢰도"],
            mode="markers+text",
            name=company_name,
            marker={"size": 16, "color": "#0b63f6", "opacity": 1.0, "line": {"width": 2, "color": "#ffffff"}},
            text=target_df["기업명"],
            textposition="top center",
            textfont={"size": 12, "color": "#0b63f6"},
            hovertemplate="<b>%{text}</b><br>Valuation 신뢰도 %{x:.1%}<br>Credit 신뢰도 %{y:.1%}<extra></extra>",
        )
    )
    fig.update_layout(
        height=315,
        margin={"l": 8, "r": 8, "t": 14, "b": 4},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "font": {"size": 12},
        },
        font={"family": "Inter, Pretendard, Apple SD Gothic Neo, sans-serif", "color": "#17213a"},
    )
    fig.update_xaxes(
        title="Valuation 신뢰도",
        tickformat=".0%",
        range=[0.4, 1.1],
        gridcolor="#edf1f7",
        zeroline=False,
    )
    fig.update_yaxes(
        title="Credit 신뢰도",
        tickformat=".0%",
        range=[0.4, 1.1],
        gridcolor="#edf1f7",
        zeroline=False,
    )
    return fig


def _render_peer_table(peer_df: pd.DataFrame, target: dict[str, Any]) -> None:
    rows = [_format_target_table_row(target)]
    for _, row in peer_df.iterrows():
        rows.append(
            {
                "기업명": _safe_text(row.get("기업명")),
                "현재가": _format_price(row.get("latest_close")),
                "P/S": _format_multiple(row.get("P/S")),
                "PER": _format_multiple(row.get("PER")),
                "영업이익률": _format_percent_decimal(_value_from_row(row, ["영업이익률", "op_margin"])),
                "ROE": _format_percent_decimal(_value_from_row(row, ["ROE", "roe"])),
                "1년 수익률": _format_percent_decimal(row.get("1년 수익률")),
                "_target": False,
            }
        )

    headers = ["기업명", "현재가", "P/S(배)", "PER(배)", "영업이익률", "ROE", "1년 수익률"]
    head_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_html = []
    for row in rows:
        tr_class = "peer-target-row" if row.get("_target") else ""
        cells = "".join(f"<td>{escape(str(row.get(_table_value_key(header), '–')))}</td>" for header in headers)
        body_html.append(f'<tr class="{tr_class}">{cells}</tr>')

    st.markdown(
        '<div class="peer-table-wrap">'
        '<table class="peer-table">'
        f"<thead><tr>{head_html}</tr></thead>"
        f"<tbody>{''.join(body_html)}</tbody>"
        "</table>"
        "</div>",
        unsafe_allow_html=True,
    )


def _format_target_table_row(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "기업명": _safe_text(target.get("기업명")),
        "현재가": _format_price(target.get("현재가")),
        "P/S": _format_multiple(target.get("P/S")),
        "PER": _format_multiple(target.get("PER")),
        "영업이익률": _format_percent_decimal(target.get("영업이익률")),
        "ROE": _format_percent_decimal(target.get("ROE")),
        "1년 수익률": _format_percent_decimal(target.get("1년 수익률")),
        "_target": True,
    }


def _build_average_bar(peer_df: pd.DataFrame, target: dict[str, Any], company_name: str) -> go.Figure:
    metrics = [
        ("P/S(배)", ["P/S"], "P/S", "배", 1.0),
        ("PER(배)", ["PER"], "PER", "배", 1.0),
        ("영업이익률 (%)", ["영업이익률", "op_margin"], "영업이익률", "%", 100.0),
        ("ROE (%)", ["ROE", "roe"], "ROE", "%", 100.0),
    ]

    labels: list[str] = []
    target_values: list[float] = []
    peer_values: list[float] = []
    text_target: list[str] = []
    text_peer: list[str] = []

    for label, peer_cols, target_key, unit, multiplier in metrics:
        peer_series = _numeric_series_from_columns(peer_df, peer_cols)
        if peer_series is None:
            continue
        peer_avg = peer_series.dropna().mean()
        target_value = _to_float(target.get(target_key))
        if pd.isna(peer_avg) or target_value is None:
            continue
        target_plot = target_value * multiplier if multiplier != 1.0 else target_value
        peer_plot = float(peer_avg) * multiplier
        labels.append(label)
        target_values.append(target_plot)
        peer_values.append(peer_plot)
        text_target.append(_bar_text(target_plot, unit))
        text_peer.append(_bar_text(peer_plot, unit))

    if not labels:
        fig = go.Figure()
        fig.add_annotation(text="비교 가능한 수치가 없습니다.", showarrow=False, x=0.5, y=0.5)
        fig.update_layout(height=250, margin={"l": 8, "r": 8, "t": 8, "b": 8})
        return fig

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=labels,
            x=target_values,
            name=company_name,
            orientation="h",
            marker_color="#0b63f6",
            text=text_target,
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.add_trace(
        go.Bar(
            y=labels,
            x=peer_values,
            name="동종 그룹 평균",
            orientation="h",
            marker_color="#b9d6ff",
            text=text_peer,
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.update_layout(
        height=275,
        barmode="group",
        margin={"l": 6, "r": 28, "t": 12, "b": 4},
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"size": 12},
        },
        font={"family": "Inter, Pretendard, Apple SD Gothic Neo, sans-serif", "color": "#17213a"},
    )
    fig.update_xaxes(gridcolor="#edf1f7", zeroline=True, zerolinecolor="#dfe5ef")
    fig.update_yaxes(autorange="reversed")
    return fig


def _render_conclusion(conclusion: str) -> None:
    if not conclusion:
        st.markdown('<div class="peer-empty">22_종합가치평가 시트에서 결론 텍스트를 찾지 못했습니다.</div>', unsafe_allow_html=True)
        return
    st.markdown(
        '<div class="peer-conclusion-card">'
        '<div class="peer-conclusion-label">결론</div>'
        f'<div class="peer-conclusion-text">{escape(conclusion)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )


def _render_excel_linkage() -> None:
    sheets = [
        ("00_대시보드", "현재 기업 핵심 지표"),
        ("10_피어비교", "동종기업 재무·멀티플 비교"),
        ("18_밸류에이션_유니버스", "유니버스 스코어링과 산점도"),
        ("22_종합가치평가", "종합 결론 텍스트"),
    ]
    items = "".join(
        '<div class="peer-sheet-row">'
        '<span class="peer-sheet-icon">XLS</span>'
        f'<span class="peer-sheet-name">{escape(name)}</span>'
        f'<span class="peer-sheet-desc">{escape(desc)}</span>'
        "</div>"
        for name, desc in dict(sheets).items()
    )
    st.markdown(
        '<div class="peer-sheet-list">'
        '<div class="peer-footnote">이 화면은 아래 4개 시트를 중복 없이 연결해 구성했습니다.</div>'
        f"{items}"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_top_cards(universe_count: int, focus_count: int, peer_group: str, peer_group_size: int) -> None:
    cards = [
        ("Valuation Universe", f"{universe_count:,}개", "반도체 레퍼런스 유니버스", "U", "blue"),
        ("Focus Group", f"{focus_count:,}개", "분석 집중 비교군", "F", "blue"),
        ("Peer Group", peer_group or "–", "동종 세부 그룹", "P", "purple"),
        ("Peer Group Size", f"{peer_group_size:,}개", "직접 비교 가능한 기업 수", "N", "green"),
    ]
    card_html = "".join(
        '<div class="peer-kpi-card">'
        "<div>"
        f'<div class="peer-kpi-label">{escape(label)}</div>'
        f'<div class="peer-kpi-value">{escape(value)}</div>'
        f'<div class="peer-kpi-sub">{escape(sub)}</div>'
        "</div>"
        f'<div class="peer-kpi-icon {theme}">{escape(icon)}</div>'
        "</div>"
        for label, value, sub, icon, theme in cards
    )
    st.markdown(f'<div class="peer-kpi-grid">{card_html}</div>', unsafe_allow_html=True)


def _inject_peer_css() -> None:
    st.markdown(
        """
        <style>
        .peer-kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
            margin: 10px 0 14px;
        }
        .peer-kpi-card {
            min-height: 118px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            padding: 20px 22px;
            border: 1px solid #dfe5ef;
            border-radius: 10px;
            background: #ffffff;
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.025);
        }
        .peer-kpi-card > div:first-child {
            min-width: 0;
        }
        .peer-kpi-label {
            color: #17213a;
            font-size: 15px;
            font-weight: 850;
            line-height: 1.25;
        }
        .peer-kpi-value {
            margin-top: 8px;
            color: #101828;
            font-size: 25px;
            line-height: 1.1;
            font-weight: 900;
            word-break: keep-all;
            overflow-wrap: anywhere;
        }
        .peer-kpi-sub {
            margin-top: 8px;
            color: #667085;
            font-size: 13px;
            font-weight: 700;
        }
        .peer-kpi-icon {
            flex: 0 0 54px;
            width: 54px;
            height: 54px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            font-weight: 900;
        }
        .peer-kpi-icon.blue {
            color: #0b63f6;
            background: #eaf2ff;
        }
        .peer-kpi-icon.purple {
            color: #6f38ff;
            background: #f0e9ff;
        }
        .peer-kpi-icon.green {
            color: #16a45d;
            background: #e8fbef;
        }
        .peer-section-title {
            display: flex;
            align-items: center;
            gap: 7px;
            margin: 0 0 8px;
            color: #17213a;
            font-size: 17px;
            line-height: 1.3;
            font-weight: 900;
        }
        .peer-info {
            width: 16px;
            height: 16px;
            border: 1px solid #b8c2d2;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #667085;
            font-size: 10px;
            font-weight: 900;
        }
        .peer-conclusion-card {
            min-height: 270px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 14px;
            padding: 22px 22px;
            border-radius: 10px;
            background: linear-gradient(180deg, #fbfdff 0%, #f6f9ff 100%);
            border: 1px solid #e2e8f0;
        }
        .peer-conclusion-label {
            width: fit-content;
            padding: 5px 11px;
            border-radius: 9px;
            background: #eaf2ff;
            color: #0b63f6;
            font-size: 13px;
            font-weight: 900;
        }
        .peer-conclusion-text {
            color: #17213a;
            font-size: 18px;
            line-height: 1.65;
            font-weight: 780;
            word-break: keep-all;
        }
        .peer-table-wrap {
            overflow-x: auto;
        }
        .peer-table {
            width: 100%;
            border-collapse: collapse;
            color: #17213a;
            font-size: 13px;
            font-variant-numeric: tabular-nums;
        }
        .peer-table th {
            padding: 8px 9px;
            border-bottom: 1px solid #dfe5ef;
            color: #344054;
            font-size: 12px;
            font-weight: 900;
            text-align: right;
            white-space: nowrap;
        }
        .peer-table th:first-child {
            text-align: left;
        }
        .peer-table td {
            padding: 7px 9px;
            border-bottom: 1px solid #edf1f7;
            text-align: right;
            white-space: nowrap;
            font-weight: 720;
        }
        .peer-table td:first-child {
            text-align: left;
        }
        .peer-target-row td {
            background: #eaf2ff;
            color: #0b4fe8;
            border-top: 1px solid #0b63f6;
            border-bottom: 1px solid #0b63f6;
            font-weight: 900;
        }
        .peer-footnote {
            margin-top: 8px;
            color: #667085;
            font-size: 12px;
            font-weight: 700;
            line-height: 1.45;
        }
        .peer-sheet-list {
            display: grid;
            gap: 8px;
            padding-bottom: 2px;
        }
        .peer-sheet-row {
            display: grid;
            grid-template-columns: 44px minmax(120px, 0.75fr) minmax(140px, 1fr);
            align-items: center;
            gap: 10px;
            min-height: 44px;
            padding: 8px 12px;
            border-radius: 9px;
            background: #f7f9fc;
            box-sizing: border-box;
            overflow: hidden;
        }
        .peer-sheet-icon {
            width: 32px;
            height: 24px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 7px;
            background: #e8fbef;
            color: #149653;
            font-size: 10px;
            font-weight: 900;
        }
        .peer-sheet-name {
            color: #17213a;
            font-size: 13px;
            font-weight: 900;
            white-space: nowrap;
        }
        .peer-sheet-desc {
            color: #667085;
            font-size: 12px;
            font-weight: 700;
            line-height: 1.35;
        }
        .peer-empty {
            min-height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 16px;
            border: 1px dashed #d7deea;
            border-radius: 10px;
            background: #fbfcff;
            color: #667085;
            font-size: 14px;
            font-weight: 760;
            text-align: center;
        }
        @media (max-width: 980px) {
            .peer-kpi-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .peer-sheet-row {
                grid-template-columns: 38px 1fr;
            }
            .peer-sheet-desc {
                grid-column: 2;
            }
        }
        @media (max-width: 640px) {
            .peer-kpi-grid {
                grid-template-columns: 1fr;
            }
            .peer-kpi-card {
                min-height: 104px;
                padding: 16px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _safe_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return "–"
    text = str(value).strip()
    return text if text else "–"


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        try:
            if pd.isna(value):
                continue
        except TypeError:
            pass
        if str(value).strip():
            return value
    return None


def _card_value(cards: dict[str, Any], key: str) -> Any:
    value = cards.get(key)
    if isinstance(value, dict):
        return value.get("value")
    return value


def _ratio(numerator: Any, denominator: Any) -> float | None:
    top = _to_float(numerator)
    bottom = _to_float(denominator)
    if top is None or bottom in (None, 0):
        return None
    return top / bottom


def _value_from_row(row: pd.Series, columns: list[str]) -> Any:
    for col in columns:
        if col in row.index:
            value = row.get(col)
            if value is not None and not pd.isna(value):
                return value
    return None


def _numeric_series_from_columns(df: pd.DataFrame, columns: list[str]) -> pd.Series | None:
    for col in columns:
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce")
    return None


def _format_dashboard_value(value: Any) -> str:
    text = _safe_text(value)
    return text


def _to_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text == "–":
        return None
    is_percent = "%" in text
    text = (
        text.replace(",", "")
        .replace("억원", "")
        .replace("원", "")
        .replace("배", "")
        .replace("x", "")
        .replace("X", "")
        .replace("개", "")
        .replace("행", "")
        .replace("/100", "")
        .replace("%", "")
        .strip()
    )
    try:
        number = float(text)
    except ValueError:
        return None
    return number / 100.0 if is_percent else number


def _format_price(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "–"
    return f"{number:,.0f}원"


def _format_won_to_uk(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "–"
    return f"{number / 1e8:,.1f}억원"


def _format_multiple(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "–"
    return f"{number:.2f}"


def _format_percent_decimal(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "–"
    return f"{number * 100:.1f}%"


def _format_score(value: Any) -> str:
    number = _to_float(value)
    if number is None:
        return "–"
    return f"{number * 100:.1f}점"


def _bar_text(value: float, unit: str) -> str:
    if unit == "%":
        return f"{value:.1f}%"
    return f"{value:.2f}"


def _table_value_key(header: str) -> str:
    return {"P/S(배)": "P/S", "PER(배)": "PER"}.get(header, header)
