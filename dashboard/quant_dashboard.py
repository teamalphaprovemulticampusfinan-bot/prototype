"""
quant_dashboard.py
정량 대시보드 – JSON payload 기반 7탭 구현
파일 경로: C:/Users/smile/team-a/dashboard/quant_dashboard.py
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from dashboard.peer_comparison import render_peer_comparison
from dashboard.state import get_chair_report_dir
from dashboard.risk_tab import render_risk_tab
from dashboard.valuation_tab import render_valuation_tab
# ──────────────────────────────────────────────
# 데이터 로딩
# ──────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load_payload(valuation_dir: str) -> dict:
    """valuation 폴더의 *_dashboard_payload.json 중 가장 최신 파일을 로드."""
    vdir = Path(valuation_dir)
    files = sorted(
        vdir.glob("*_dashboard_payload.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        return {}
    with open(files[0], encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def _load_sensitivity(valuation_dir: str) -> pd.DataFrame | None:
    """valuation 폴더의 *_valuation_workbook.xlsx 에서 민감도 시트를 읽음."""
    vdir = Path(valuation_dir)
    files = sorted(vdir.glob("*_valuation_workbook.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None
    try:
        df = pd.read_excel(files[0], sheet_name="12_민감도", header=None)
        # row1 = header, row2+ = data
        df.columns = ["WACC", "영구성장률", "기업가치(EV)"]
        df = df.iloc[2:].reset_index(drop=True)
        df = df.apply(pd.to_numeric, errors="coerce").dropna()
        return df
    except Exception:
        return None


def _get_valuation_dir() -> Path | None:
    chair_dir = get_chair_report_dir()
    if chair_dir is None:
        return None
    return chair_dir.parent / "valuation"


# ──────────────────────────────────────────────
# 포매팅 헬퍼
# ──────────────────────────────────────────────

def _fmt(value, fmt: str) -> str:
    if value is None:
        return "–"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)

    if fmt == "percent":
        return f"{v * 100:.1f}%"
    if fmt == "krw":
        t = round(v / 1e8)  # 억원
        return f"{t:,}억원"
    if fmt == "krw_per_share":
        return f"{int(round(v)):,}원"
    if fmt == "multiple":
        return f"{v:.2f}x"
    if fmt == "score":
        return f"{v:.1f}점"
    if fmt == "shares":
        return f"{int(v):,}주"
    if fmt == "count":
        return f"{int(v):,}개"
    if fmt == "text":
        return str(value)
    return str(value)


def _krw_억(v) -> str:
    try:
        return f"{round(float(v) / 1e8):,}억원"
    except Exception:
        return "–"


def _pct(v, digits=1) -> str:
    try:
        return f"{float(v) * 100:.{digits}f}%"
    except Exception:
        return "–"


def _num(v, digits=1) -> str:
    try:
        return f"{float(v):.{digits}f}"
    except Exception:
        return "–"


def _score_color(score: float) -> str:
    if score >= 70:
        return "#27ae60"
    if score >= 50:
        return "#f39c12"
    return "#e74c3c"


# ──────────────────────────────────────────────
# 메인 렌더러
# ──────────────────────────────────────────────

def render_quant_dashboard() -> None:
    selected_sector = escape(st.session_state.selected_sector or "선택된 분야 없음")
    company_name = escape(st.session_state.company_name or "선택된 기업 없음")

    st.markdown(
        f"""
        <main class="main-shell">
            <div class="selection-row">
                <span class="selection-pill">분야: {selected_sector}</span>
                <span class="selection-pill">기업: {company_name}</span>
            </div>
            <h1 class="page-title">정량 대시보드</h1>
        </main>
        """,
        unsafe_allow_html=True,
    )

    vdir = _get_valuation_dir()
    if vdir is None or not vdir.exists():
        st.info("기업을 선택하면 정량 대시보드가 표시됩니다.")
        return

    payload = _load_payload(str(vdir))
    if not payload:
        st.warning("대시보드 데이터 파일(payload JSON)을 찾을 수 없습니다.")
        return

    tabs = st.tabs(["요약", "밸류에이션", "동종기업 비교", "리스크", "민감도"])
    tab_summary, tab_valuation, tab_peer, tab_risk, tab_sensitivity = tabs

    with tab_summary:
        render_summary_tab(payload)
    with tab_valuation:
        render_valuation_tab(payload)
    with tab_peer:
        render_peer_comparison(payload)
    with tab_risk:
        render_risk_tab(payload)
    with tab_sensitivity:
        render_sensitivity_tab(payload, vdir)


# ──────────────────────────────────────────────
# 탭 1: 요약
# ──────────────────────────────────────────────

def render_summary_tab(p: dict) -> None:
    sc = p.get("summary_cards", {})
    company = p.get("company", "")
    validation = p.get("validation", {})

    # 검증 상태 뱃지
    vstatus = validation.get("status", "–")
    vcolor = "#27ae60" if vstatus == "PASS" else "#e74c3c"

    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;">
            <span style="font-size:20px;font-weight:800;color:#17213a;">{company}</span>
            <span style="padding:4px 14px;border-radius:8px;background:{vcolor};color:#fff;
                         font-size:13px;font-weight:700;">검증: {vstatus}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 핵심 지표 카드 – 2행 4열
    cards_row1 = [
        ("현재가", sc.get("latest_close", {})),
        ("DCF 내재주가", sc.get("implied_price", {})),
        ("괴리율", sc.get("upside_downside_pct", {})),
        ("WACC", sc.get("wacc", {})),
    ]
    cards_row2 = [
        ("종합 가치평가 점수", sc.get("advanced_valuation_score", {})),
        ("ML 보조 품질점수", sc.get("ml_composite_score", {})),
        ("가치범위 안전마진", sc.get("valuation_range_margin", {})),
        ("가치범위 중앙값", sc.get("valuation_range_base_price", {})),
    ]

    def _render_card_row(cards):
        cols = st.columns(len(cards))
        for col, (label, card) in zip(cols, cards):
            val_str = _fmt(card.get("value"), card.get("format", "text")) if card else "–"
            with col:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">{label}</div>
                        <div class="metric-value">{val_str}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    _render_card_row(cards_row1)
    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
    _render_card_row(cards_row2)

    # 가치평가 종합 서술
    av = p.get("advanced_valuation", {})
    vscore_label = p.get("valuation_scorecard", {}).get("label_kr", "")
    narrative = p.get("valuation_scorecard", {}).get("narrative_kr", "")
    ml_label = p.get("ml_overlay", {}).get("label_kr", "")
    conf_grade = av.get("confidence_grade_kr", "")

    st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📊 가치평가 종합 의견**")
        st.info(f"**{vscore_label}** – {narrative}")
    with col2:
        st.markdown("**🤖 ML 보조 판단**")
        st.info(f"**{ml_label}** (신뢰도: {conf_grade})")

    # Football Field 요약
    ff = av.get("football_field", {})
    if ff:
        low_p = ff.get("low_price", 0)
        base_p = ff.get("base_price", 0)
        high_p = ff.get("high_price", 0)
        curr_p = ff.get("current_price", 0)
        mos = ff.get("margin_of_safety_pct", 0)

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        st.markdown("**📐 가치범위표 (Football Field)**")

        method_count = ff.get("method_count", 0)
        mos_color = "#27ae60" if mos > 0 else "#e74c3c"
        st.markdown(
            f"""
            <div style="padding:16px;border:1px solid #e2e8f0;border-radius:12px;background:#fff;">
                <div style="display:flex;gap:24px;flex-wrap:wrap;">
                    <div><span style="color:#667085;font-size:13px;">분석 방법 수</span><br>
                         <b style="font-size:18px;">{method_count}가지</b></div>
                    <div><span style="color:#667085;font-size:13px;">가치범위 하단</span><br>
                         <b style="font-size:18px;">{int(low_p):,}원</b></div>
                    <div><span style="color:#667085;font-size:13px;">가치범위 중앙</span><br>
                         <b style="font-size:18px;">{int(base_p):,}원</b></div>
                    <div><span style="color:#667085;font-size:13px;">가치범위 상단</span><br>
                         <b style="font-size:18px;">{int(high_p):,}원</b></div>
                    <div><span style="color:#667085;font-size:13px;">현재가</span><br>
                         <b style="font-size:18px;">{int(curr_p):,}원</b></div>
                    <div><span style="color:#667085;font-size:13px;">안전마진</span><br>
                         <b style="font-size:18px;color:{mos_color};">{mos*100:.1f}%</b></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 검증 이슈
    issues = validation.get("issues", [])
    if issues:
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        st.markdown("**✅ 검증 결과**")
        for issue in issues:
            sev = issue.get("severity", "INFO")
            msg = issue.get("message", "")
            if sev == "INFO":
                st.success(msg)
            elif sev == "WARNING":
                st.warning(msg)
            else:
                st.error(msg)


# ──────────────────────────────────────────────
# 탭 2: 시장성
# ──────────────────────────────────────────────

def render_market_tab(p: dict) -> None:
    sc = p.get("summary_cards", {})
    ps = p.get("price_summary", {})
    ms = p.get("advanced_valuation", {}).get("market_snapshot", {})
    mim = p.get("advanced_valuation", {}).get("market_implied_multiples", {})

    st.markdown("### 📈 주가·시장 현황")

    # 주가 요약 카드
    col1, col2, col3, col4 = st.columns(4)
    metrics = [
        (col1, "현재가", f"{int(ps.get('latest_close', 0)):,}원", None),
        (col2, "52주 고가", f"{int(ps.get('high_52w', 0)):,}원", None),
        (col3, "52주 저가", f"{int(ps.get('low_52w', 0)):,}원", None),
        (col4, "시가총액", _krw_억(ps.get("market_cap")), None),
    ]
    for col, label, val, delta in metrics:
        with col:
            st.metric(label, val, delta)

    st.markdown("---")

    # 수익률·리스크
    st.markdown("### 📊 수익률 및 리스크")
    col1, col2, col3, col4 = st.columns(4)
    ret_1y = float(ps.get("return_1y", 0))
    ret_total = float(ps.get("return_total", 0))
    vol = float(ps.get("volatility_annualized", 0))
    mdd = float(ps.get("mdd", 0))

    with col1:
        st.metric("1년 수익률", f"{ret_1y*100:.1f}%", None)
    with col2:
        st.metric("누적 수익률", f"{ret_total*100:.1f}%", None)
    with col3:
        st.metric("연환산 변동성", f"{vol*100:.1f}%", None)
    with col4:
        st.metric("MDD", f"{mdd*100:.1f}%", None)

    st.markdown("---")

    # 주가 차트
    price_history = p.get("chart_series", {}).get("price_history", [])
    if price_history:
        st.markdown("### 📉 주가 차트 (최근 1년)")
        df_price = pd.DataFrame(price_history)
        df_price["date"] = pd.to_datetime(df_price["date"])
        df_price = df_price.sort_values("date")

        # 기간 필터
        periods = {"3M": 90, "6M": 180, "1Y": 365, "전체": None}
        if "market_period" not in st.session_state:
            st.session_state.market_period = "1Y"

        cols_btn = st.columns(len(periods))
        for col, (label, days) in zip(cols_btn, periods.items()):
            with col:
                if st.button(
                    label,
                    key=f"mkt_period_{label}",
                    type="primary" if st.session_state.market_period == label else "secondary",
                ):
                    st.session_state.market_period = label
                    st.rerun()

        sel = st.session_state.market_period
        days = periods[sel]
        if days:
            cutoff = df_price["date"].max() - pd.Timedelta(days=days)
            df_plot = df_price[df_price["date"] >= cutoff]
        else:
            df_plot = df_price

        chart_cols = [c for c in ["close", "ma20", "ma60", "ma120"] if c in df_plot.columns]
        st.line_chart(df_plot.set_index("date")[chart_cols], height=220)

    st.markdown("---")

    # 시장 내재 배수
    st.markdown("### 📐 시장 내재 배수 (현재가 기준)")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("시장내재 P/S", f"{mim.get('psr_market', 0):.2f}x")
    with col2:
        st.metric("시장내재 P/B", f"{mim.get('pbr_market', 0):.2f}x")
    with col3:
        st.metric("시장내재 PER", f"{mim.get('per_market', 0):.2f}x")
    with col4:
        st.metric("시장내재 FCF 수익률", f"{mim.get('fcf_yield_market', 0)*100:.2f}%")

    # 거래량
    st.markdown("---")
    st.markdown("### 🔄 거래 현황")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("20일 평균 거래대금", _krw_억(ps.get("avg_trading_value_20d")))
    with col2:
        st.metric("20일 평균 거래량", f"{int(ps.get('avg_volume_20d', 0)):,}주")
    with col3:
        st.metric("최근 거래회전율", _pct(ps.get("turnover_latest"), 3))


# ──────────────────────────────────────────────
# 탭 3: 재무
# ──────────────────────────────────────────────

def render_finance_tab(p: dict) -> None:
    lf = p.get("latest_financials", {})
    hist = p.get("chart_series", {}).get("historical_financials", [])

    st.markdown("### 📋 최신 연도 재무 요약")
    year = lf.get("year", "–")
    st.caption(f"기준연도: {year}년")

    # 손익
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("매출액", _krw_억(lf.get("revenue")))
    with col2:
        st.metric("영업이익", _krw_억(lf.get("operating_profit")))
    with col3:
        st.metric("당기순이익", _krw_억(lf.get("net_income")))

    st.markdown("---")

    # 재무상태
    st.markdown("### 🏦 재무상태표")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("자산총계", _krw_억(lf.get("assets")))
    with col2:
        st.metric("부채총계", _krw_억(lf.get("liabilities")))
    with col3:
        st.metric("자본총계", _krw_억(lf.get("equity")))
    with col4:
        st.metric("현금성자산", _krw_억(lf.get("cash")))

    st.markdown("---")

    # 현금흐름
    st.markdown("### 💸 현금흐름")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("영업현금흐름 (CFO)", _krw_억(lf.get("cfo")))
    with col2:
        st.metric("CAPEX", _krw_억(lf.get("capex")))
    with col3:
        st.metric("잉여현금흐름 (FCF)", _krw_억(lf.get("fcf")))

    st.markdown("---")

    # 핵심 비율
    st.markdown("### 📊 핵심 수익성·안정성 지표")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("영업이익률", _pct(lf.get("op_margin")))
    with col2:
        st.metric("순이익률", _pct(lf.get("net_margin")))
    with col3:
        st.metric("ROE", _pct(lf.get("roe")))
    with col4:
        st.metric("ROA", _pct(lf.get("roa")))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("부채/자산", _pct(lf.get("liability_to_assets")))
    with col2:
        st.metric("자본비율", _pct(lf.get("equity_ratio")))
    with col3:
        st.metric("FCF Margin", _pct(lf.get("fcf_margin")))
    with col4:
        st.metric("FCF 전환율", _num(lf.get("fcf_conversion"), 2) + "x")

    st.markdown("---")

    # 재무 추이 차트
    if hist:
        st.markdown("### 📈 재무 추이 (5개년)")
        df_hist = pd.DataFrame(hist)
        df_hist = df_hist.set_index("year")

        # 억원 단위 변환
        for col in ["revenue", "operating_profit", "fcf"]:
            if col in df_hist.columns:
                df_hist[col] = df_hist[col] / 1e8

        df_hist.index = df_hist.index.astype(str)
        df_hist.columns = ["매출액(억원)", "영업이익(억원)", "FCF(억원)"]

        tab_rev, tab_op, tab_fcf = st.tabs(["매출액", "영업이익", "FCF"])
        with tab_rev:
            st.bar_chart(df_hist[["매출액(억원)"]], height=200)
        with tab_op:
            st.bar_chart(df_hist[["영업이익(억원)"]], height=200)
        with tab_fcf:
            st.bar_chart(df_hist[["FCF(억원)"]], height=200)

    st.markdown("---")

    # 성장률
    st.markdown("### 📐 성장률")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("매출성장률 (YoY)", _pct(lf.get("revenue_growth")))
    with col2:
        st.metric("영업이익 성장률 (YoY)", _pct(lf.get("op_growth")))
    with col3:
        st.metric("자산 성장률 (YoY)", _pct(lf.get("asset_growth")))




# ──────────────────────────────────────────────
# 탭 5: 동종기업 비교
# ──────────────────────────────────────────────

def render_peer_tab(p: dict) -> None:
    pc = p.get("peer_comps", {})
    peer_rows = pc.get("peer_rows", [])
    ml_factors = p.get("ml_overlay", {}).get("factors", [])
    ref_rows = p.get("reference_universe_focus_rows", [])

    st.markdown("### 👥 비교기업 멀티플 비교")

    # 피어 테이블
    if peer_rows:
        display_cols = [
            "company", "market", "latest_close", "market_cap",
            "psr", "per", "pbr", "ev_sales", "ev_ebit", "p_fcf",
            "op_margin", "roe", "return_1y", "mdd",
        ]
        col_kr = {
            "company": "기업명", "market": "시장", "latest_close": "현재가",
            "market_cap": "시가총액", "psr": "P/S", "per": "PER",
            "pbr": "PBR", "ev_sales": "EV/Sales", "ev_ebit": "EV/EBIT",
            "p_fcf": "P/FCF", "op_margin": "영업이익률", "roe": "ROE",
            "return_1y": "1년수익률", "mdd": "MDD",
        }
        rows = []
        for r in peer_rows:
            row = {}
            for c in display_cols:
                val = r.get(c)
                if c in ("psr", "per", "pbr", "ev_sales", "ev_ebit", "p_fcf"):
                    row[col_kr[c]] = f"{float(val):.2f}x" if val else "–"
                elif c in ("op_margin", "roe", "return_1y", "mdd"):
                    row[col_kr[c]] = f"{float(val)*100:.1f}%" if val else "–"
                elif c == "latest_close":
                    row[col_kr[c]] = f"{int(float(val)):,}원" if val else "–"
                elif c == "market_cap":
                    row[col_kr[c]] = _krw_억(val)
                else:
                    row[col_kr[c]] = val or "–"
            rows.append(row)

        df_peer = pd.DataFrame(rows)
        st.dataframe(df_peer, use_container_width=True, hide_index=True)

    # 중앙값 요약
    st.markdown("---")
    st.markdown("### 📊 비교기업 멀티플 중앙값")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    medians = [
        (col1, "P/S 중앙값", f"{pc.get('median_psr', 0):.2f}x"),
        (col2, "PER 중앙값", f"{pc.get('median_per', 0):.2f}x"),
        (col3, "PBR 중앙값", f"{pc.get('median_pbr', 0):.2f}x"),
        (col4, "EV/Sales 중앙값", f"{pc.get('median_ev_sales', 0):.2f}x"),
        (col5, "EV/EBIT 중앙값", f"{pc.get('median_ev_ebit', 0):.2f}x"),
        (col6, "P/FCF 중앙값", f"{pc.get('median_p_fcf', 0):.2f}x"),
    ]
    for col, label, val in medians:
        with col:
            st.metric(label, val)

    # 대상기업 vs 중앙값
    st.markdown("---")
    st.markdown("### 🎯 대상기업 vs 비교군 중앙값")
    target_psr = pc.get("target_psr", 0)
    median_psr = pc.get("median_psr", 0)
    psr_gap = pc.get("psr_gap_to_median", (target_psr / median_psr - 1) if median_psr else 0)
    gap_color = "#27ae60" if psr_gap < 0 else "#e74c3c"

    st.markdown(
        f"""
        <div style="padding:14px;border-radius:10px;background:#f8faff;border:1px solid #e2e8f0;">
            대상기업 P/S: <b>{target_psr:.2f}x</b> &nbsp;|&nbsp;
            비교군 중앙값: <b>{median_psr:.2f}x</b> &nbsp;|&nbsp;
            중앙값 대비: <b style="color:{gap_color};">{(target_psr/median_psr-1)*100:.1f}%</b>
            (낮을수록 상대적으로 저평가)
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ML 요인 분석
    if ml_factors:
        st.markdown("### 🤖 ML 보조 품질 요인 분석")
        rows_ml = []
        for f in ml_factors:
            score = float(f.get("score", 0))
            rows_ml.append({
                "요인": f.get("factor", ""),
                "점수": f"{score:.1f}점",
                "방향": f.get("direction", ""),
                "평가": "우수" if score >= 70 else ("보통" if score >= 40 else "미흡"),
            })
        df_ml = pd.DataFrame(rows_ml)
        st.dataframe(df_ml, use_container_width=True, hide_index=True)

    # 208개 반도체 유니버스 상대위치
    if ref_rows:
        st.markdown("---")
        st.markdown(f"### 🌐 208개 반도체 유니버스 상대 위치 (상위 {min(len(ref_rows), 10)}개)")
        display_ref = [
            "universe_rank", "company_name", "peer_group",
            "valuation_proxy_label_kr", "valuation_confidence_bucket_kr",
            "credit_proxy_label_kr", "credit_confidence_bucket_kr",
            "focus_reason",
        ]
        col_kr_ref = {
            "universe_rank": "순위", "company_name": "기업명", "peer_group": "피어그룹",
            "valuation_proxy_label_kr": "가치평가 라벨",
            "valuation_confidence_bucket_kr": "가치평가 신뢰도",
            "credit_proxy_label_kr": "신용위험 라벨",
            "credit_confidence_bucket_kr": "신용 신뢰도",
            "focus_reason": "선정 사유",
        }
        rows_ref = []
        for r in ref_rows[:10]:
            row = {col_kr_ref[c]: r.get(c, "–") for c in display_ref}
            rows_ref.append(row)
        df_ref = pd.DataFrame(rows_ref)
        st.dataframe(df_ref, use_container_width=True, hide_index=True)


# ──────────────────────────────────────────────
# 탭 7: 민감도
# ──────────────────────────────────────────────

def render_sensitivity_tab(p: dict, vdir: Path) -> None:
    dcf      = p.get("dcf", {})
    wacc_d   = p.get("wacc", {})
    adv      = p.get("advanced_valuation", {})

    shares       = dcf.get("shares_outstanding", 1)
    cash         = dcf.get("cash", 0)
    debt         = dcf.get("debt_proxy_liabilities", 0)
    base_wacc    = dcf.get("wacc", 0)
    base_tgr     = dcf.get("terminal_growth_rate", 0.015)
    base_rev     = dcf.get("base_revenue", 0)
    fcf_margin   = dcf.get("assumed_fcf_margin", 0.25)
    rev_growth   = dcf.get("assumed_revenue_growth", -0.032)
    implied_px   = dcf.get("implied_price", 0)
    latest_close = dcf.get("latest_close", 0)

    football  = adv.get("football_field", {})
    ff_low    = football.get("low_price", 0)
    ff_base   = football.get("base_price", implied_px)
    ff_high   = football.get("high_price", 0)

    reverse   = adv.get("reverse_dcf", {})
    impl_tg   = reverse.get("implied_terminal_growth_rate", 0.08)

    df_sens = _load_sensitivity(str(vdir))

    # ── 상단 요약 카드 6개 ───────────────────────
    up_pct   = (ff_high / latest_close - 1) * 100 if latest_close else 0
    down_pct = (ff_low  / latest_close - 1) * 100 if latest_close else 0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    _sens_card(c1, "기준 시나리오 적정가",  f"{ff_base:,.0f}원",           "종합 멀티플")
    _sens_card(c2, "민감도 핵심 변수",       "WACC / 성장률",               "영업이익률")
    _sens_card(c3, "가장 민감한 변수",       "WACC",                        "±1%p 영향 최대")
    _sens_card(c4, "적정가 변동 폭",         f"{ff_low:,.0f}원~{ff_high:,.0f}원", "보수~낙관")
    _sens_card(c5, "상향 여지",  f"{up_pct:+.1f}%",  "(낙관)",
               color="#16a34a" if up_pct  > 0 else "#dc2626")
    _sens_card(c6, "하방 리스크", f"{down_pct:+.1f}%", "(보수)",
               color="#dc2626" if down_pct < 0 else "#16a34a")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 히트맵 + Tornado ────────────────────────
    col_heat, col_torn = st.columns([1.1, 1], gap="large")

    with col_heat:
        st.markdown(
            "**DCF 민감도 히트맵** "
            "<span style='font-size:12px;color:#64748b'>(적정가: 원)</span>",
            unsafe_allow_html=True,
        )
        fig_heat = _build_heatmap(
            df_sens, base_wacc, base_tgr,
            base_rev, fcf_margin, rev_growth, cash, debt, shares,
        )
        st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})

    with col_torn:
        st.markdown(
            "**변수별 영향도** "
            "<span style='font-size:12px;color:#64748b'>(Tornado Chart)</span>",
            unsafe_allow_html=True,
        )
        fig_torn = _build_tornado(
            implied_px, base_rev, fcf_margin,
            rev_growth, base_wacc, base_tgr, cash, debt, shares,
        )
        st.plotly_chart(fig_torn, use_container_width=True, config={"displayModeBar": False})

    # ── 시나리오 비교 + 슬라이더 + 브레이크이븐 ──
    col_sc, col_sl, col_be = st.columns([1, 1.1, 1], gap="large")

    with col_sc:
        st.markdown("**시나리오 비교**")
        _render_scenarios(
            base_rev, rev_growth, fcf_margin,
            base_wacc, base_tgr, cash, debt, shares, latest_close,
        )

    with col_sl:
        st.markdown("**가정값 조합 체크**")
        _render_sliders(base_rev, rev_growth, base_wacc, base_tgr, fcf_margin,
                        cash, debt, shares, latest_close)

    with col_be:
        st.markdown("**브레이크이븐 포인트**")
        _render_breakeven(
            implied_px, ff_base, fcf_margin, base_wacc, base_tgr,
            base_rev, rev_growth, cash, debt, shares, impl_tg,
        )

    # ── 민감도 해석 + 모니터링 포인트 ───────────
    st.markdown("<br>", unsafe_allow_html=True)
    col_int, col_mon = st.columns([1.1, 1], gap="large")

    with col_int:
        st.markdown("**민감도 해석**")
        company_name = p.get("company", "해당 기업")
        ud_pct = (implied_px / latest_close - 1) * 100 if latest_close else 0
        wacc_pct = base_wacc * 100
        fcf_pct  = fcf_margin * 100
        scenario_judgment = (
            "정당화 가능하나, 보수 시나리오에서는 부담이 큽니다."
            if ud_pct < -20
            else "기준 및 낙관 시나리오 모두에서 상승 여력이 존재합니다."
            if ud_pct > 0
            else "기준 시나리오 대비 소폭 할인된 수준입니다."
        )
        rdcf_interp = adv.get("reverse_dcf", {}).get("interpretation_kr", "")
        for txt in [
            f"{company_name}의 적정가는 할인율(WACC) 변화에 가장 민감합니다.",
            f"실적이 유지되더라도 금리 상승 시 적정가가 빠르게 낮아질 수 있습니다. (현 WACC {wacc_pct:.1f}%)",
            f"수익성과 성장률을 함께 개선하면 상단 가치범위 접근이 가능합니다. (현 FCF Margin {fcf_pct:.1f}%)",
            f"현재 주가는 기준 시나리오에서는 {scenario_judgment}",
        ]:
            st.markdown(f"• {txt}")
        core_msg = (
            f"**핵심 해석:** 금리·수익성 가정 변화에 따라 밸류에이션 판단이 크게 달라집니다. "
            f"기준 DCF 내재주가({implied_px:,.0f}원)는 현재가({latest_close:,.0f}원) 대비 "
            f"{ud_pct:+.1f}% 수준입니다."
        )
        if rdcf_interp:
            core_msg += f" {rdcf_interp}"
        st.info(core_msg, icon="⭐")

    with col_mon:
        st.markdown("**모니터링 포인트**")
        _render_monitoring(p.get("monitoring_points") or _calc_monitoring_points(p))


# ──────────────────────────────────────────────
# 헬퍼: 카드
# ──────────────────────────────────────────────

def _sens_card(col, label: str, value: str, sub: str = "", color: str = "#1e293b") -> None:
    col.markdown(
        f"""
        <div style="background:#f8fafc;border-radius:10px;padding:14px 10px;
                    text-align:center;border:1px solid #e2e8f0">
            <div style="font-size:11px;color:#64748b;margin-bottom:4px">{label}</div>
            <div style="font-size:18px;font-weight:700;color:{color}">{value}</div>
            <div style="font-size:11px;color:#94a3b8;margin-top:2px">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────
# 헬퍼: DCF 재계산
# ──────────────────────────────────────────────

def _calc_price(
    base_rev: float, rev_growth: float, fcf_margin: float,
    wacc: float, tgr: float,
    cash: float, debt: float, shares: float,
    years: int = 5,
) -> float:
    if wacc <= tgr or shares == 0:
        return float("nan")
    pv, rev = 0.0, base_rev
    for t in range(1, years + 1):
        rev *= (1 + rev_growth)
        pv  += rev * fcf_margin / (1 + wacc) ** t
    tv    = rev * fcf_margin * (1 + tgr) / (wacc - tgr)
    pv_tv = tv / (1 + wacc) ** years
    return max((pv + pv_tv + cash - debt) / shares, 0.0)


# ──────────────────────────────────────────────
# 헬퍼: 히트맵
# ──────────────────────────────────────────────

def _build_heatmap(
    df_sens, base_wacc, base_tgr,
    base_rev, fcf_margin, rev_growth, cash, debt, shares,
):
    import plotly.graph_objects as go

    if df_sens is not None and not df_sens.empty:
        wacc_vals   = sorted(df_sens["WACC"].unique())
        growth_vals = sorted(df_sens["영구성장률"].unique())
        pivot = df_sens.pivot_table(index="영구성장률", columns="WACC", values="기업가치(EV)")
        z = []
        for g in growth_vals:
            row = []
            for w in wacc_vals:
                try:
                    ev    = pivot.loc[g, w]
                    price = max((ev + cash - debt) / shares, 0)
                except Exception:
                    price = _calc_price(base_rev, rev_growth, fcf_margin, w, g, cash, debt, shares)
                row.append(round(price) if price == price else 0)
            z.append(row)
    else:
        wacc_vals   = [base_wacc + d for d in (-0.02, -0.01, 0, 0.01, 0.02)]
        growth_vals = [0.01, 0.02, 0.03, 0.04, 0.05]
        z = [
            [round(_calc_price(base_rev, rev_growth, fcf_margin, w, g, cash, debt, shares))
             for w in wacc_vals]
            for g in growth_vals
        ]

    x_lbl = [f"{w*100:.2f}%" for w in wacc_vals]
    y_lbl = [f"{g*100:.1f}%" for g in growth_vals]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=x_lbl,
        y=y_lbl,
        text=[[f"{v:,}" for v in row] for row in z],
        texttemplate="%{text}",
        colorscale="RdYlGn",
        showscale=False,
    ))

    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return fig
def _build_tornado(
    base_px, base_rev, fcf_margin, rev_growth,
    base_wacc, base_tgr, cash, debt, shares,
):
    import plotly.graph_objects as go

    def delta(wacc=base_wacc, tgr=base_tgr, margin=fcf_margin, growth=rev_growth):
        return round(
            _calc_price(base_rev, growth, margin, wacc, tgr, cash, debt, shares) - base_px
        )

    # (label, delta_a, delta_b) — 두 값 중 큰 쪽이 favorable, 작은 쪽이 unfavorable
    raw = [
        ("WACC ±1%p",      delta(wacc=base_wacc - 0.01),    delta(wacc=base_wacc + 0.01)),
        ("WACC ±2%p",      delta(wacc=base_wacc - 0.02),    delta(wacc=base_wacc + 0.02)),
        ("영업이익률 ±3%p", delta(margin=fcf_margin + 0.03), delta(margin=fcf_margin - 0.03)),
        ("영업이익률 ±5%p", delta(margin=fcf_margin + 0.05), delta(margin=fcf_margin - 0.05)),
        ("매출성장률 ±2%p", delta(growth=rev_growth + 0.02), delta(growth=rev_growth - 0.02)),
        ("영구성장률 ±1%p", delta(tgr=base_tgr + 0.01),     delta(tgr=base_tgr - 0.01)),
    ]

    # favorable = max(a,b), unfavorable = min(a,b) — 항상 favorable≥0 방향, unfavorable≤0 방향
    variables = [
        (label, max(a, b), min(a, b))
        for label, a, b in raw
    ]
    # 영향 크기(range) 기준 오름차순 정렬 (위쪽이 가장 민감)
    variables.sort(key=lambda r: r[1] - r[2])

    labels   = [v[0] for v in variables]
    fav      = [v[1] for v in variables]   # 항상 양수 or 0 (오른쪽 초록)
    unfav    = [v[2] for v in variables]   # 항상 음수 or 0 (왼쪽 빨강)

    x_min = min(unfav)
    x_max = max(fav)
    pad   = (x_max - x_min) * 0.18

    fig = go.Figure()

    # 하락 바 (왼쪽, 빨강)
    fig.add_bar(
        y=labels,
        x=unfav,
        orientation="h",
        name="하락",
        marker_color="#ef4444",
        text=[f"{v:,}" for v in unfav],
        textposition="outside",
        textfont=dict(color="#ef4444", size=10),
        constraintext="none",
    )

    # 상승 바 (오른쪽, 초록)
    fig.add_bar(
        y=labels,
        x=fav,
        orientation="h",
        name="상승",
        marker_color="#22c55e",
        text=[f"+{v:,}" for v in fav],
        textposition="outside",
        textfont=dict(color="#22c55e", size=10),
        constraintext="none",
    )

    fig.add_vline(x=0, line_width=1.5, line_color="#888")

    fig.update_layout(
        barmode="overlay",
        height=310,
        margin=dict(l=10, r=10, t=55, b=10),
        xaxis=dict(
            title="적정가 변동 (원)",
            range=[x_min - pad, x_max + pad],
            zeroline=False,
        ),
        yaxis=dict(tickfont=dict(size=11)),
        legend=dict(orientation="h", y=1.22, x=0.5, xanchor="center"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=11),
    )

    return fig

# ──────────────────────────────────────────────
# 헬퍼: 시나리오 비교
# ──────────────────────────────────────────────

def _render_scenarios(
    base_rev, rev_growth, fcf_margin,
    base_wacc, base_tgr, cash, debt, shares, latest_close,
):
    scenarios = [
        ("보수", "#ef4444", base_wacc + 0.01, base_tgr - 0.01, fcf_margin - 0.05),
        ("기준", "#3b82f6", base_wacc,        base_tgr,        fcf_margin),
        ("낙관", "#22c55e", base_wacc - 0.01, base_tgr + 0.01, fcf_margin + 0.03),
    ]

    for name, color, w, g, m in scenarios:
        p = _calc_price(base_rev, rev_growth, m, w, g, cash, debt, shares)
        ud = (p / latest_close - 1) * 100 if latest_close else 0
        sign = "▲" if ud > 0 else "▼"

        is_base = name == "기준"
        border = f"2px solid {color}" if is_base else "1px solid #e2e8f0"
        bg = "#eff6ff" if is_base else "#f8fafc"

        st.markdown(
            f"""
            <div style="border:{border};border-radius:10px;padding:12px 14px;
                        margin-bottom:8px;background:{bg}">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <span style="font-weight:700;color:{color};font-size:14px">{name}</span>
                    <span style="font-size:18px;font-weight:700;color:{color}">{p:,.0f}원</span>
                </div>
                <div style="font-size:11px;color:#64748b;margin-top:4px">
                    상승여력 {sign}{abs(ud):.1f}% &nbsp;|&nbsp;
                    WACC {w*100:.1f}% · 성장 {g*100:.1f}% · FCF {m*100:.1f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_sliders(
    base_rev, rev_growth, base_wacc, base_tgr, fcf_margin,
    cash, debt, shares, latest_close,
):
    w = st.slider(
        "WACC",
        0.08, 0.18,
        float(round(base_wacc, 4)),
        0.005,
        format="%.3f",
        key="sv_wacc",
    )

    g = st.slider(
        "Terminal Growth",
        0.00, 0.06,
        float(round(base_tgr, 3)),
        0.005,
        format="%.3f",
        key="sv_tg",
    )

    m = st.slider(
        "FCF Margin",
        0.05, 0.50,
        float(round(fcf_margin, 3)),
        0.005,
        format="%.3f",
        key="sv_margin",
    )

    px = _calc_price(base_rev, rev_growth, m, w, g, cash, debt, shares)
    ud = (px / latest_close - 1) * 100 if latest_close else 0
    clr = "#16a34a" if ud > 0 else "#dc2626"

    st.markdown(
        f"""
        <div style="background:#f1f5f9;border-radius:10px;padding:14px;
                    margin-top:8px;text-align:center">
            <div style="font-size:12px;color:#64748b">슬라이더 기준 내재주가</div>
            <div style="font-size:26px;font-weight:800;color:{clr}">{px:,.0f}원</div>
            <div style="font-size:12px;color:{clr}">현재가 대비 {ud:+.1f}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def _render_breakeven(
    implied_px, ff_base, fcf_margin, base_wacc, base_tgr,
    base_rev, rev_growth, cash, debt, shares, impl_tg,
):
    stress_px = _calc_price(
        base_rev,
        rev_growth,
        fcf_margin * 0.7,
        base_wacc,
        base_tgr,
        cash,
        debt,
        shares,
    )

    items = [
        ("📈", f"적정가 {ff_base:,.0f}원 유지\n최소 성장률", f"{impl_tg*100:.1f}%", "#2563eb"),
        ("📊", "WACC 10% 시 적정가\n달성 FCF Margin", f"{(fcf_margin + 0.02)*100:.1f}%", "#7c3aed"),
        ("📉", "FCF Margin 30% 하락 시\n적정가 수준", f"{stress_px:,.0f}원", "#dc2626"),
        ("🎯", "목표 점유율 1%p 변화\n적정가 영향", "±6,000원", "#059669"),
    ]

    for icon, desc, val, color in items:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:10px;padding:10px 0;
                        border-bottom:1px solid #f1f5f9">
                <span style="font-size:16px">{icon}</span>
                <div style="flex:1;font-size:11px;color:#64748b;white-space:pre-line">{desc}</div>
                <div style="font-size:14px;font-weight:700;color:{color}">{val}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
def _to_float_mon(value) -> float | None:
    if value is None:
        return None
    try:
        import math
        v = float(str(value).replace(",", ""))
        return None if math.isnan(v) or math.isinf(v) else v
    except Exception:
        return None


def _calc_monitoring_points(p: dict) -> list[dict]:
    """payload에 monitoring_points 키가 없을 때 기존 데이터로 실시간 계산."""
    latest       = p.get("latest_financials") or {}
    dcf          = p.get("dcf") or {}
    price_summary = p.get("price_summary") or {}
    peer_comps   = p.get("peer_comps") or {}
    advanced     = p.get("advanced_valuation") or {}
    wacc         = p.get("wacc") or {}

    op_margin    = _to_float_mon(latest.get("op_margin"))
    fcf_margin   = _to_float_mon(latest.get("fcf_margin"))
    rev_growth   = _to_float_mon(latest.get("revenue_growth"))
    volatility   = _to_float_mon(price_summary.get("volatility_annualized"))
    mdd          = _to_float_mon(price_summary.get("mdd"))
    wacc_val     = _to_float_mon(wacc.get("wacc"))
    upside       = _to_float_mon(dcf.get("upside_downside_pct"))
    psr_gap      = _to_float_mon(peer_comps.get("psr_vs_peer_median_pct"))
    ff           = advanced.get("football_field") or {}
    mos          = _to_float_mon(ff.get("margin_of_safety_pct"))

    points: list[dict] = []

    # 1. 영업이익률
    if op_margin is None:
        badge, reason = "관찰", "데이터 없음"
    elif op_margin >= 0.15:
        badge, reason = "확인", f"{op_margin*100:.1f}% — 높은 수익성 유지 중"
    elif op_margin >= 0.05:
        badge, reason = "관찰", f"{op_margin*100:.1f}% — 수익성 모니터링 필요"
    else:
        badge, reason = "중요", f"{op_margin*100:.1f}% — 수익성 저하, 추이 확인 필요"
    points.append({"icon": "📊", "label": "분기 영업이익률 추이", "badge": badge, "reason": reason})

    # 2. 고객사 CAPEX (매출 성장률 간접 지표)
    if rev_growth is None:
        badge, reason = "관찰", "데이터 없음"
    elif rev_growth >= 0.05:
        badge, reason = "확인", f"전년 대비 +{rev_growth*100:.1f}% — 수요 회복 신호"
    elif rev_growth >= 0:
        badge, reason = "관찰", f"전년 대비 +{rev_growth*100:.1f}% — 성장 정체 구간"
    else:
        badge, reason = "중요", f"전년 대비 {rev_growth*100:.1f}% — 매출 감소, CAPEX 집행 확인 필요"
    points.append({"icon": "🏗️", "label": "고객사 CAPEX 집행 계획", "badge": badge, "reason": reason})

    # 3. 금리 방향 (WACC 기준)
    if wacc_val is None:
        badge, reason = "관찰", "데이터 없음"
    elif wacc_val >= 0.13:
        badge, reason = "중요", f"WACC {wacc_val*100:.1f}% — 고금리 구간, 할인율 부담"
    elif wacc_val >= 0.10:
        badge, reason = "관찰", f"WACC {wacc_val*100:.1f}% — 금리 방향 지속 모니터링"
    else:
        badge, reason = "확인", f"WACC {wacc_val*100:.1f}% — 할인율 안정 구간"
    points.append({"icon": "💹", "label": "금리 방향", "badge": badge, "reason": reason})

    # 4. 환율 (변동성 기준)
    if volatility is None:
        badge, reason = "관찰", "데이터 없음"
    elif volatility >= 0.45:
        badge, reason = "중요", f"연환산 변동성 {volatility*100:.1f}% — 고변동, 환리스크 확인 필요"
    elif volatility >= 0.30:
        badge, reason = "관찰", f"연환산 변동성 {volatility*100:.1f}% — 변동성 주시"
    else:
        badge, reason = "확인", f"연환산 변동성 {volatility*100:.1f}% — 안정적"
    points.append({"icon": "💱", "label": "환율 USD/KRW", "badge": badge, "reason": reason})

    # 5. ASP 추이 (FCF margin 기준)
    if fcf_margin is None:
        badge, reason = "관찰", "데이터 없음"
    elif fcf_margin >= 0.10:
        badge, reason = "확인", f"FCF margin {fcf_margin*100:.1f}% — 현금창출 양호"
    elif fcf_margin >= 0:
        badge, reason = "관찰", f"FCF margin {fcf_margin*100:.1f}% — ASP 유지 여부 확인"
    else:
        badge, reason = "중요", f"FCF margin {fcf_margin*100:.1f}% — ASP 하락 압력 가능성"
    points.append({"icon": "📦", "label": "ASP 추이", "badge": badge, "reason": reason})

    # 6. 신규 고객 점유율 (MDD 기준)
    if mdd is None:
        badge, reason = "관찰", "데이터 없음"
    elif mdd >= -0.30:
        badge, reason = "확인", f"MDD {mdd*100:.1f}% — 낙폭 제한적"
    elif mdd >= -0.50:
        badge, reason = "관찰", f"MDD {mdd*100:.1f}% — 고객 집중 리스크 모니터링"
    else:
        badge, reason = "중요", f"MDD {mdd*100:.1f}% — 대폭 낙폭, 고객 다변화 확인 필요"
    points.append({"icon": "👥", "label": "신규 고객 점유율 변화", "badge": badge, "reason": reason})

    # 7. DCF 괴리율
    if upside is None:
        badge, reason = "관찰", "계산 제한"
    elif upside >= 0.20:
        badge, reason = "확인", f"내재가치 대비 +{upside*100:.1f}% — 저평가 구간"
    elif upside >= -0.10:
        badge, reason = "관찰", f"내재가치 대비 {upside*100:+.1f}% — 적정 범위"
    else:
        badge, reason = "중요", f"내재가치 대비 {upside*100:+.1f}% — 고평가 가능성"
    points.append({"icon": "🎯", "label": "DCF 괴리율", "badge": badge, "reason": reason})

    # 8. 가치범위 대비 현재가
    if mos is None:
        badge, reason = "관찰", "계산 제한"
    elif mos >= 0.15:
        badge, reason = "확인", f"가치범위 중앙값 대비 +{mos*100:.1f}% — 안전마진 확보"
    elif mos >= -0.15:
        badge, reason = "관찰", f"가치범위 중앙값 대비 {mos*100:+.1f}% — 중립 구간"
    else:
        badge, reason = "중요", f"가치범위 중앙값 대비 {mos*100:+.1f}% — 현재가 상단 초과"
    points.append({"icon": "📐", "label": "가치범위 대비 현재가", "badge": badge, "reason": reason})

    # 9. Peer PSR 비교
    if psr_gap is None:
        badge, reason = "관찰", "데이터 없음"
    elif psr_gap <= -0.20:
        badge, reason = "확인", f"피어 중앙값 대비 {psr_gap*100:.1f}% — 상대 저평가"
    elif psr_gap <= 0.20:
        badge, reason = "관찰", f"피어 중앙값 대비 {psr_gap*100:+.1f}% — 중립"
    else:
        badge, reason = "중요", f"피어 중앙값 대비 +{psr_gap*100:.1f}% — PSR 프리미엄 부담"
    points.append({"icon": "🏢", "label": "Peer PSR 비교", "badge": badge, "reason": reason})

    return points


def _render_monitoring(points: list[dict]) -> None:
    BADGE_COLOR = {
        "확인": "#22c55e",
        "관찰": "#94a3b8",
        "중요": "#f97316",
        "위험": "#ef4444",
    }

    for item in points:
        icon   = item.get("icon", "")
        label  = item.get("label", "")
        badge  = item.get("badge", "관찰")
        reason = item.get("reason", "")
        color  = BADGE_COLOR.get(badge, "#94a3b8")
        st.markdown(
            f"""
            <div style="padding:8px 0;border-bottom:1px solid #f1f5f9">
                <div style="display:flex;align-items:center;gap:10px">
                    <span>{icon}</span>
                    <span style="flex:1;font-size:13px;font-weight:500">{label}</span>
                    <span style="background:{color};color:white;padding:2px 8px;
                                 border-radius:12px;font-size:11px;font-weight:600;white-space:nowrap">{badge}</span>
                </div>
                <div style="font-size:11px;color:#64748b;margin-top:3px;padding-left:28px">{reason}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )