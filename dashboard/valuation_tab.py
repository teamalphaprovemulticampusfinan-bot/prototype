
"""
단독 실행 테스트:
    streamlit run valuation_tab.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ──────────────────────────────────────────────────────────
# 포매팅 헬퍼
# ──────────────────────────────────────────────────────────

def _pct(v, digits: int = 1) -> str:
    try:
        return f"{float(v) * 100:.{digits}f}%"
    except Exception:
        return "–"

def _krw_억(v) -> str:
    try:
        return f"{round(float(v) / 1e8):,}억원"
    except Exception:
        return "–"

def _won(v) -> str:
    try:
        return f"{int(round(float(v))):,}원"
    except Exception:
        return "–"

def _score_color(score: float) -> str:
    if score >= 70:
        return "#27ae60"
    if score >= 50:
        return "#f39c12"
    return "#e74c3c"


# ──────────────────────────────────────────────────────────
# DCF 재계산 헬퍼
# ──────────────────────────────────────────────────────────

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
        rev *= 1 + rev_growth
        pv  += rev * fcf_margin / (1 + wacc) ** t
    tv    = rev * fcf_margin * (1 + tgr) / (wacc - tgr)
    pv_tv = tv / (1 + wacc) ** years
    return max((pv + pv_tv + cash - debt) / shares, 0.0)


# ──────────────────────────────────────────────────────────
# 섹션 1: 상단 KPI 카드
# ──────────────────────────────────────────────────────────

def _render_top_kpi(p: dict) -> None:
    sc   = p.get("summary_cards", {})
    av   = p.get("advanced_valuation", {})
    ff   = av.get("football_field", {})
    dcf  = p.get("dcf", {})

    latest_close  = float(sc.get("latest_close",  {}).get("value", 0) or 0)
    implied_price = float(sc.get("implied_price",  {}).get("value", 0) or 0)
    upside        = float(sc.get("upside_downside_pct", {}).get("value", 0) or 0)
    range_base    = float(sc.get("valuation_range_base_price", {}).get("value", 0) or 0)
    range_margin  = float(sc.get("valuation_range_margin", {}).get("value", 0) or 0)
    adv_score     = float(av.get("advanced_valuation_score", 0) or
                          sc.get("advanced_valuation_score", {}).get("value", 0) or 0)

    upside_color = "#27ae60" if upside >= 0 else "#e74c3c"
    score_color  = _score_color(adv_score)

    # 종합 가치평가 레이블 — football_field 범위 기준
    ff_low  = float(ff.get("low_price",  0) or 0)
    ff_high = float(ff.get("high_price", 0) or 0)
    vsc     = p.get("valuation_scorecard", {})
    ff_label = vsc.get("label_kr", "") or sc.get("valuation_scorecard_label", {}).get("value", "")
    if not ff_label:
        if ff_high > 0 and latest_close < ff_low:
            ff_label = "소폭 저평가"
        elif ff_high > 0 and latest_close > ff_high:
            ff_label = "고평가"
        else:
            ff_label = "적정"

    # 레이블별 색상
    if "저평가" in ff_label:
        lbl_color = "#27ae60"
    elif "고평가" in ff_label:
        lbl_color = "#e74c3c"
    else:
        lbl_color = "#3b82f6"

    margin_color = "#27ae60" if range_margin >= 0 else "#e74c3c"

    cols = st.columns(6)
    cards = [
        ("현재가",          _won(latest_close),               "(2024.05.17 종가)",  "#17213a"),
        ("DCF 적정가",      _won(implied_price),               "(기준 시나리오)",    "#17213a"),
        ("상승여력",        f"{upside*100:+.1f}%",             "(적정가 대비)",      upside_color),
        ("가치범위 중앙값", _won(range_base),                  "(가치 범위 기준)",   "#17213a"),
        ("종합 가치평가",   ff_label,                          "(적정가 대비)",      lbl_color),
        ("밸류 부담도",     f"{adv_score:.1f}점",              "(위험도 기준)",      score_color),
    ]
    for col, (label, value, sub, color) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div style="background:#f8fafc;border-radius:10px;padding:14px 10px;
                            text-align:center;border:1px solid #e2e8f0;min-height:95px">
                    <div style="font-size:11px;color:#64748b;margin-bottom:4px">{label}</div>
                    <div style="font-size:18px;font-weight:700;color:{color}">{value}</div>
                    <div style="font-size:11px;color:#94a3b8;margin-top:2px">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────────────────
# 섹션 2: Football Field — 현재가 vs 적정가
# 수정: x축 범위를 low~high 전체로 확장, 마커 3개 명확히 표시
# ──────────────────────────────────────────────────────────

def _render_football_field(p: dict) -> None:
    av  = p.get("advanced_valuation", {})
    ff  = av.get("football_field", {})
    sc  = p.get("summary_cards", {})
    dcf = p.get("dcf", {})

    low     = float(ff.get("low_price",  0) or 0)
    base_ff = float(ff.get("base_price", 0) or 0)
    high    = float(ff.get("high_price", 0) or 0)
    curr    = float(ff.get("current_price", 0) or
                    sc.get("latest_close", {}).get("value", 0) or 0)
    dcf_px  = float(sc.get("implied_price", {}).get("value", 0) or
                    dcf.get("implied_price", 0) or 0)
    peer_px = float(sc.get("valuation_range_base_price", {}).get("value", 0) or base_ff)

    if not (low and high and low < high):
        st.info("Football Field 데이터가 없습니다.")
        return

    pad   = (high - low) * 0.12
    x_min = low  - pad
    x_max = high + pad

    fig = go.Figure()

    # 저평가 구간 (low ~ peer_px)
    fig.add_shape(type="rect",
        x0=low, x1=peer_px, y0=0.15, y1=0.85,
        fillcolor="#dbeafe", line=dict(width=0), layer="below")

    # 적정 구간 (peer_px ~ high)
    fig.add_shape(type="rect",
        x0=peer_px, x1=high, y0=0.15, y1=0.85,
        fillcolor="#dcfce7", line=dict(width=0), layer="below")

    # 마커 3개: DCF 적정가 / Peer 기준가 / 현재가
    markers = [
        (dcf_px,  "#3b82f6", f"DCF 적정가<br>{_won(dcf_px)}",   0.92),
        (peer_px, "#6366f1", f"Peer 기준가<br>{_won(peer_px)}", 0.92),
        (curr,    "#ef4444", f"현재가<br>{_won(curr)}",          0.92),
    ]
    for x, color, label, ya in markers:
        if x <= 0:
            continue
        fig.add_shape(type="line",
            x0=x, x1=x, y0=0.1, y1=0.9,
            line=dict(color=color, width=2.5))
        fig.add_annotation(
            x=x, y=ya, text=label,
            showarrow=False, font=dict(size=9, color=color),
            yref="paper", align="center",
            bgcolor="rgba(255,255,255,0.85)",
            borderpad=2,
        )

    # 하단 범위값 레이블
    fig.add_annotation(x=low,  y=-0.18, text=f"하단값<br>{_won(low)}",
        showarrow=False, font=dict(size=9, color="#6b7280"), yref="paper")
    fig.add_annotation(x=high, y=-0.18, text=f"상단값<br>{_won(high)}",
        showarrow=False, font=dict(size=9, color="#6b7280"), yref="paper")

    fig.update_layout(
        height=160,
        margin=dict(l=20, r=20, t=55, b=35),
        xaxis=dict(
            range=[x_min, x_max],
            showgrid=False, zeroline=False, showticklabels=False,
        ),
        yaxis=dict(visible=False, range=[-0.35, 1.1]),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # 구간 레이블 행
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div style="text-align:center;font-size:12px;color:#3b82f6;font-weight:600">저평가 구간</div>', unsafe_allow_html=True)
    c2.markdown('<div style="text-align:center;font-size:12px;color:#6366f1;font-weight:600">적정 구간</div>',   unsafe_allow_html=True)
    c3.markdown('<div style="text-align:center;font-size:12px;color:#ef4444;font-weight:600">고평가 구간</div>', unsafe_allow_html=True)

    mos       = float(ff.get("margin_of_safety_pct", 0) or 0)
    mos_color = "#27ae60" if mos > 0 else "#e74c3c"
    st.markdown(
        f"""
        <div style="margin-top:8px;padding:10px 14px;border-radius:8px;
                    background:#f8faff;border:1px solid #e2e8f0;font-size:13px">
            ⓘ 가치 범위는 DCF 민감도(보수~낙관) 기준이며, 중앙값은 전체 범위의 중간값입니다.&nbsp;
            안전마진: <b style="color:{mos_color}">{mos*100:.1f}%</b>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────
# 섹션 3: 가치평가 방법별 결과 + Peer 비교
# 수정: 해석 컬럼 채우기, 회사명 동적 처리
# ──────────────────────────────────────────────────────────

def _render_methods_table(p: dict) -> None:
    av      = p.get("advanced_valuation", {})
    methods = av.get("valuation_methods", [])
    sc      = p.get("summary_cards", {})
    curr    = float(sc.get("latest_close", {}).get("value", 0) or 0)

    if not methods:
        st.info("가치평가 방법 데이터가 없습니다.")
        return

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown("**가치평가 방법별 결과**")
        rows = []
        for m in methods:
            base_px = float(m.get("base_implied_price", 0) or 0)

            # 해석 — JSON 필드 우선, 없으면 현재가 대비 상승여력으로 자동 판단
            verdict = (
                m.get("verdict_kr", "")
                or m.get("label_kr", "")
                or m.get("interpretation_kr", "")
            )
            if not verdict and curr and base_px:
                gap = (base_px / curr - 1) * 100
                if gap > 15:
                    verdict = "저평가"
                elif gap > 5:
                    verdict = "소폭 저평가"
                elif gap < -15:
                    verdict = "고평가"
                elif gap < -5:
                    verdict = "소폭 고평가"
                else:
                    verdict = "적정"

            rows.append({
                "평가 방법":       m.get("method_kr", ""),
                "적정가 (1주당)":  _won(base_px),
                "해석":            verdict,
            })

        df_m = pd.DataFrame(rows)

        def _color_verdict(val: str):
            if "저평가" in val:
                return "color: #27ae60; font-weight:600"
            if "고평가" in val:
                return "color: #e74c3c; font-weight:600"
            if "적정" in val:
                return "color: #3b82f6"
            return "color: #64748b"

        st.dataframe(
            df_m.style.map(_color_verdict, subset=["해석"]),
            use_container_width=True,
            hide_index=True,
        )

    with col_right:
        st.markdown("**Peer 밸류에이션 비교**")
        _render_peer_multiples_mini(p)


def _render_peer_multiples_mini(p: dict) -> None:
    sc  = p.get("summary_cards", {})
    av  = p.get("advanced_valuation", {})
    mim = p.get("market_implied_multiples", {})
    ms  = av.get("market_snapshot", {})
    pc  = p.get("peer_comps", {})

    # 대상 기업명 동적 처리
    company_name = p.get("company", "") or ms.get("company", "") or "대상기업"

    target_psr = float(sc.get("target_psr", {}).get("value", 0) or 0)
    median_psr = float(sc.get("median_psr", {}).get("value", 0) or 0)
    per_tgt    = float(ms.get("per_auto",  0) or mim.get("per_market",  0) or 0)
    pbr_tgt    = float(ms.get("pbr_auto",  0) or mim.get("pbr_market",  0) or 0)
    median_per = float(pc.get("median_per", 18.0) or 18.0)
    median_pbr = float(pc.get("median_pbr",  3.0) or  3.0)

    metrics = [
        ("P/S", target_psr, median_psr),
        ("PER", per_tgt,    median_per),
        ("P/B", pbr_tgt,    median_pbr),
    ]

    fig = go.Figure()
    labels = [m[0] for m in metrics]

    fig.add_bar(
        name=company_name,
        y=labels, x=[m[1] for m in metrics],
        orientation="h", marker_color="#3b82f6",
        text=[f"{m[1]:.1f}배" for m in metrics],
        textposition="outside",
    )
    fig.add_bar(
        name="동종 평균",
        y=labels, x=[m[2] for m in metrics],
        orientation="h", marker_color="#cbd5e1",
        text=[f"{m[2]:.1f}배" for m in metrics],
        textposition="outside",
    )

    fig.update_layout(
        barmode="group",
        height=200,
        margin=dict(l=10, r=65, t=30, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(tickfont=dict(size=12)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=1.18, x=0, font=dict(size=11)),
        font=dict(size=11),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    psr_gap   = (target_psr / median_psr - 1) * 100 if median_psr else 0
    gap_color = "#27ae60" if psr_gap < 0 else "#e74c3c"
    st.markdown(
        f"""
        <div style="font-size:12px;padding:8px 12px;background:#f8faff;
                    border-radius:8px;border:1px solid #e2e8f0">
            PER 기준 부담은 크지 않지만 P/S 기준 프리미엄이 존재합니다.
            &nbsp; P/S 갭: <b style="color:{gap_color}">{psr_gap:+.1f}%</b>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────
# 섹션 4: 역산 DCF + 민감도 시나리오
# ──────────────────────────────────────────────────────────

def _render_reverse_dcf_and_sensitivity(p: dict) -> None:
    av   = p.get("advanced_valuation", {})
    rdcf = av.get("reverse_dcf", {})
    sc   = p.get("summary_cards", {})
    dcf  = p.get("dcf", {})

    col_rdcf, col_sens = st.columns([1, 1], gap="large")

    # ── 역산 DCF ──────────────────────────────────
    with col_rdcf:
        st.markdown("**역산 DCF**")
        impl_tg    = float(
            rdcf.get("implied_terminal_growth_rate")
            or sc.get("reverse_dcf_growth", {}).get("value", 0.08)
            or 0.08
        )
        model_grow = float(dcf.get("terminal_growth_rate", 0.015) or 0.015)
        interp     = rdcf.get("interpretation_kr", "")

        st.markdown(
            f"""
            <div style="border:1px solid #e2e8f0;border-radius:10px;
                        padding:16px;background:#fff;min-height:140px">
                <div style="font-size:12px;color:#64748b;margin-bottom:6px">
                    현재 주가에 내재된 성장률
                </div>
                <div style="font-size:34px;font-weight:700;color:#3b82f6">
                    {impl_tg*100:.1f}%
                </div>
                <div style="font-size:12px;color:#94a3b8;margin-top:4px">
                    기준 성장률 가정 <b>{model_grow*100:.1f}%</b>
                </div>
                <div style="font-size:12px;color:#64748b;margin-top:8px">
                    {interp or "현재 주가가 요구하는 FCF yield와 영구성장률을 역산해 DCF 가정의 현실성을 점검합니다."}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── 민감도 시나리오 ───────────────────────────
    with col_sens:
        st.markdown("**민감도 요약 (DCF 기준)**")

        latest     = float(dcf.get("latest_close", 0) or 0)
        base_wacc  = float(dcf.get("wacc", 0.133) or 0.133)
        base_tgr   = float(dcf.get("terminal_growth_rate", 0.015) or 0.015)
        base_rev   = float(dcf.get("base_revenue", 0) or 0)
        fcf_margin = float(dcf.get("assumed_fcf_margin", 0.25) or 0.25)
        rev_growth = float(dcf.get("assumed_revenue_growth", -0.032) or -0.032)
        cash       = float(dcf.get("cash", 0) or 0)
        debt       = float(dcf.get("debt_proxy_liabilities", 0) or 0)
        shares     = float(dcf.get("shares_outstanding", 1) or 1)

        scenarios = [
            ("보수", "#ef4444", base_wacc + 0.01, base_tgr - 0.01, fcf_margin - 0.05),
            ("기준", "#3b82f6", base_wacc,         base_tgr,         fcf_margin),
            ("낙관", "#22c55e", base_wacc - 0.01,  base_tgr + 0.01,  fcf_margin + 0.03),
        ]

        for name, color, w, g, m in scenarios:
            px   = _calc_price(base_rev, rev_growth, m, w, g, cash, debt, shares)
            ud   = (px / latest - 1) * 100 if latest else 0
            sign = "▲" if ud > 0 else "▼"
            is_base = name == "기준"
            border  = f"2px solid {color}" if is_base else "1px solid #e2e8f0"
            bg      = "#eff6ff" if is_base else "#f8fafc"
            st.markdown(
                f"""
                <div style="border:{border};border-radius:10px;padding:10px 14px;
                            margin-bottom:8px;background:{bg}">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <span style="font-weight:700;color:{color};font-size:13px">{name}</span>
                        <span style="font-size:17px;font-weight:700;color:{color}">{_won(px)}</span>
                    </div>
                    <div style="font-size:11px;color:#64748b;margin-top:3px">
                        상승여력 {sign}{abs(ud):.1f}% &nbsp;|&nbsp;
                        WACC {w*100:.1f}% · 성장 {g*100:.1f}% · FCF {m*100:.1f}%
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────────────────
# 섹션 5: WACC 구성 + FCF 추정 테이블
# ──────────────────────────────────────────────────────────

def _render_wacc_and_fcf(p: dict) -> None:
    wacc_d   = p.get("wacc", {})
    dcf      = p.get("dcf", {})
    fcf_proj = p.get("chart_series", {}).get("fcf_projection", [])

    col_wacc, col_fcf = st.columns([1, 1.2], gap="large")

    with col_wacc:
        st.markdown("**WACC 구성**")
        wacc_items = [
            ("WACC",              wacc_d.get("wacc"),                   "percent"),
            ("자기자본비용",       wacc_d.get("cost_of_equity"),         "percent"),
            ("타인자본비용(세후)", wacc_d.get("after_tax_cost_of_debt"), "percent"),
            ("베타",              wacc_d.get("beta"),                   "num"),
            ("무위험수익률",      wacc_d.get("risk_free_rate"),         "percent"),
            ("자기자본 비중",     wacc_d.get("equity_weight"),          "percent"),
            ("타인자본 비중",     wacc_d.get("debt_weight"),            "percent"),
        ]
        for label, val, fmt in wacc_items:
            if val is None:
                continue
            try:
                v = float(val)
            except Exception:
                continue
            display = f"{v*100:.2f}%" if fmt == "percent" else f"{v:.2f}"
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;
                            padding:5px 0;border-bottom:1px solid #f1f5f9;font-size:13px">
                    <span style="color:#64748b">{label}</span>
                    <span style="font-weight:600;color:#17213a">{display}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**DCF 주요 가정**")
        for label, val in [
            ("매출 성장률 가정",  dcf.get("assumed_revenue_growth")),
            ("영업이익률 가정",   dcf.get("assumed_op_margin")),
            ("FCF Margin 가정",   dcf.get("assumed_fcf_margin")),
            ("영구성장률 (TGR)", dcf.get("terminal_growth_rate")),
        ]:
            if val is None:
                continue
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;
                            padding:5px 0;border-bottom:1px solid #f1f5f9;font-size:13px">
                    <span style="color:#64748b">{label}</span>
                    <span style="font-weight:600;color:#17213a">{_pct(val)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_fcf:
        st.markdown("**FCF 추정 (5개년)**")
        if fcf_proj:
            df_fcf = pd.DataFrame(fcf_proj)
            disp   = df_fcf.copy()
            for c in ["revenue", "fcf", "pv_fcf"]:
                if c in disp.columns:
                    disp[c] = disp[c].apply(lambda x: f"{round(float(x)/1e8):,}억원")
            col_map = {"year": "연도", "revenue": "추정 매출액",
                       "fcf": "추정 FCF", "pv_fcf": "FCF 현재가치"}
            disp = disp[[c for c in col_map if c in disp.columns]]
            disp.rename(columns=col_map, inplace=True)
            st.dataframe(disp, use_container_width=True, hide_index=True)
        else:
            st.info("FCF 추정 데이터가 없습니다.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**DCF 기업가치 구성**")
        for label, val in [
            ("PV (FCF 5년)",         dcf.get("pv_fcf")),
            ("PV (Terminal Value)",   dcf.get("pv_terminal_value")),
            ("DCF 기업가치 (EV)",    dcf.get("enterprise_value")),
            ("현금 (+)",             dcf.get("cash")),
            ("부채 Proxy (-)",       dcf.get("debt_proxy_liabilities")),
            ("DCF 지분가치",         dcf.get("equity_value")),
            ("DCF 내재주가",         dcf.get("implied_price")),
        ]:
            if val is None:
                continue
            try:
                v = float(val)
            except Exception:
                continue
            is_share = "주가" in label
            display  = _won(v) if is_share else _krw_억(v)
            weight   = "700" if ("지분가치" in label or "내재주가" in label) else "400"
            st.markdown(
                f"""
                <div style="display:flex;justify-content:space-between;
                            padding:5px 0;border-bottom:1px solid #f1f5f9;font-size:13px">
                    <span style="color:#64748b">{label}</span>
                    <span style="font-weight:{weight};color:#17213a">{display}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────────────────
# 섹션 6: 오너이익 · EPV · Graham Number (expander)
# ──────────────────────────────────────────────────────────

def _render_owner_earnings(p: dict) -> None:
    av = p.get("advanced_valuation", {})
    oe = av.get("owner_earnings", {})
    sc = p.get("summary_cards", {})

    oe_price = float(
        oe.get("owner_earnings_value_per_share")
        or sc.get("owner_earnings_price", {}).get("value", 0)
        or 0
    )
    epv    = float(oe.get("epv_price",     0) or 0)
    graham = float(oe.get("graham_number", 0) or 0)
    eps    = float(oe.get("eps",           0) or 0)
    note   = oe.get("method_note_kr", "")

    cols = st.columns(4)
    for col, (label, val) in zip(cols, [
        ("오너이익 주당가치", _won(oe_price)),
        ("EPV 주당가치",      _won(epv)),
        ("Graham Number",     _won(graham)),
        ("EPS",               _won(eps)),
    ]):
        with col:
            st.metric(label, val)

    if note:
        st.caption(note)


# ──────────────────────────────────────────────────────────
# 섹션 7: 투자판단 해석 + 종합점수
# 수정: 판단 텍스트를 JSON 데이터 기준으로 정확하게 생성
# ──────────────────────────────────────────────────────────

def _render_investment_verdict(p: dict) -> None:
    """
    투자자가 바로 이해할 수 있도록 점수 나열 대신
    DCF·Peer·밸류 부담을 문장형 해석으로 요약합니다.
    """
    av  = p.get("advanced_valuation", {})
    vsc = p.get("valuation_scorecard", {})
    ml  = p.get("ml_overlay", {})
    sc  = p.get("summary_cards", {})
    dcf = p.get("dcf", {})
    ff  = av.get("football_field", {})
    pc  = p.get("peer_comps", {})
    ms  = av.get("market_snapshot", {})
    mim = p.get("market_implied_multiples", {})

    latest = float(
        sc.get("latest_close", {}).get("value", 0)
        or dcf.get("latest_close", 0)
        or ff.get("current_price", 0)
        or 0
    )
    implied = float(
        sc.get("implied_price", {}).get("value", 0)
        or dcf.get("implied_price", 0)
        or 0
    )
    upside = float(
        sc.get("upside_downside_pct", {}).get("value", 0)
        or dcf.get("upside_downside_pct", 0)
        or ((implied / latest - 1) if latest and implied else 0)
    )

    target_psr = float(sc.get("target_psr", {}).get("value", 0) or pc.get("target_psr", 0) or 0)
    median_psr = float(sc.get("median_psr", {}).get("value", 0) or pc.get("median_psr", 0) or 0)
    psr_gap = (target_psr / median_psr - 1) * 100 if target_psr and median_psr else None

    per_tgt = float(ms.get("per_auto", 0) or mim.get("per_market", 0) or 0)
    median_per = float(pc.get("median_per", 0) or 0)
    per_gap = (per_tgt / median_per - 1) * 100 if per_tgt and median_per else None

    ff_low = float(ff.get("low_price", 0) or 0)
    ff_high = float(ff.get("high_price", 0) or 0)
    vsc_label = vsc.get("label_kr", "") or sc.get("valuation_scorecard_label", {}).get("value", "")
    narrative = vsc.get("narrative_kr", "")

    adv_score = float(av.get("advanced_valuation_score", 0) or sc.get("advanced_valuation_score", {}).get("value", 0) or 0)
    scorecard_score = float(vsc.get("score", 0) or sc.get("valuation_scorecard", {}).get("value", 0) or 0)
    ml_score = float(ml.get("composite_score", 0) or sc.get("ml_composite_score", {}).get("value", 0) or 0)

    # 핵심 판단 라벨
    if vsc_label:
        final_label = vsc_label
    elif ff_low and ff_high and latest:
        if latest < ff_low:
            final_label = "소폭 저평가"
        elif latest > ff_high:
            final_label = "고평가"
        else:
            final_label = "적정"
    elif upside > 0.15:
        final_label = "저평가"
    elif upside > 0.03:
        final_label = "소폭 저평가"
    elif upside < -0.15:
        final_label = "고평가"
    elif upside < -0.03:
        final_label = "소폭 고평가"
    else:
        final_label = "적정"

    if "저평가" in final_label:
        label_color = "#16a34a"
        label_bg = "#ecfdf3"
        label_border = "#bbf7d0"
    elif "고평가" in final_label:
        label_color = "#dc2626"
        label_bg = "#fef2f2"
        label_border = "#fecaca"
    else:
        label_color = "#2563eb"
        label_bg = "#eff6ff"
        label_border = "#bfdbfe"

    # 투자자용 해석 문장 생성
    bullets: list[str] = []

    if implied and latest:
        if upside >= 0:
            bullets.append(f"DCF 기준 적정가는 {_won(implied)}으로, 현재가 대비 약 {upside*100:.1f}% 상승여력이 있습니다.")
        else:
            bullets.append(f"DCF 기준 적정가는 {_won(implied)}으로, 현재가 대비 약 {abs(upside)*100:.1f}% 낮아 가격 부담이 있습니다.")

    if per_gap is not None:
        if per_gap <= -5:
            bullets.append(f"PER 기준으로는 동종기업 평균보다 약 {abs(per_gap):.1f}% 낮아 과도한 고평가로 보기는 어렵습니다.")
        elif per_gap >= 5:
            bullets.append(f"PER 기준으로는 동종기업 평균보다 약 {per_gap:.1f}% 높아 이익 대비 밸류 부담이 있습니다.")
        else:
            bullets.append("PER 기준으로는 동종기업 평균과 비슷한 수준입니다.")

    if psr_gap is not None:
        if psr_gap >= 10:
            bullets.append(f"P/S 기준으로는 동종기업 평균보다 약 {psr_gap:.1f}% 높아 매출 성장 둔화 시 부담이 커질 수 있습니다.")
        elif psr_gap <= -10:
            bullets.append(f"P/S 기준으로는 동종기업 평균보다 약 {abs(psr_gap):.1f}% 낮아 매출 대비 가격 부담은 제한적입니다.")
        else:
            bullets.append("P/S 기준으로는 동종기업 평균과 큰 차이가 없습니다.")

    if ff_low and ff_high and latest:
        bullets.append(f"가치 범위({_won(ff_low)}~{_won(ff_high)}) 기준으로 현재 주가는 '{final_label}' 구간에 있습니다.")

    if not bullets:
        bullets.append(narrative or "현재 주가는 내재가치와 상대가치를 함께 확인하며 판단할 필요가 있습니다.")

    # 종합 한 줄 결론
    if narrative:
        summary_text = narrative
    elif "저평가" in final_label:
        summary_text = f"종합 해석: 실적 유지 시 정당화 가능한 {final_label} 구간"
    elif "고평가" in final_label:
        summary_text = f"종합 해석: 현재 가격은 부담이 있는 {final_label} 구간"
    else:
        summary_text = "종합 해석: 현재 주가는 적정가와 크게 벌어지지 않은 중립 구간"

    bullet_html = "".join(
        f"""
        <li style="display:flex;gap:8px;margin:7px 0;line-height:1.55;">
            <span style="color:#2563eb;font-size:14px;line-height:1.55;">•</span>
            <span>{item}</span>
        </li>
        """
        for item in bullets[:5]
    )

    st.markdown(
        f"""
        <ul style="list-style:none;padding:0;margin:0;color:#334155;font-size:13px;">
            {bullet_html}
        </ul>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────────────────
# 메인 렌더 함수
# ──────────────────────────────────────────────────────────

def render_valuation_tab(p: dict) -> None:
    """
    밸류에이션 탭 전체 렌더링.

    Parameters
    ----------
    p : dict
        *_dashboard_payload.json 을 json.load() 한 딕셔너리
    """
    _render_top_kpi(p)

    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
    st.markdown("### 현재가 vs 적정가 (가치 범위)")
    _render_football_field(p)

    st.divider()

    st.markdown("### 가치평가 방법별 결과")
    _render_methods_table(p)

    st.divider()

    st.markdown("### 역산 DCF  &  민감도 요약")
    _render_reverse_dcf_and_sensitivity(p)

    st.divider()

    with st.expander("💡 오너 이익 · EPV · Graham Number", expanded=False):
        _render_owner_earnings(p)

    st.divider()

    st.markdown("### 투자판단 해석")
    _render_investment_verdict(p)


# ──────────────────────────────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    st.set_page_config(page_title="밸류에이션 탭 테스트", layout="wide")
    st.title("밸류에이션 탭 — 단독 테스트")

    uploaded = st.sidebar.file_uploader("dashboard_payload.json 업로드", type="json")
    default_path = Path(__file__).parent / "dbhitek_dashboard_payload.json"

    if uploaded:
        payload = json.load(uploaded)
        st.sidebar.success(f"로드 완료: {uploaded.name}")
    elif default_path.exists():
        with open(default_path, encoding="utf-8") as f:
            payload = json.load(f)
        st.sidebar.info(f"기본 파일 사용: {default_path.name}")
    else:
        st.warning("JSON 파일을 사이드바에서 업로드하거나, 같은 폴더에 *_dashboard_payload.json 파일을 두세요.")
        st.stop()

    render_valuation_tab(payload)