"""
risk_tab.py
리스크 탭 – JSON payload 기반 시각적 리스크 분석 구현
이미지(리스크.png) 레이아웃 기준

섹션 구성:
  1. 상단 6개 KPI 카드 (종합 리스크 수준, 하방 압력, 고객 집중 리스크, 업황 민감도, 재무 방어력, 모니터링 우선순위)
  2. 리스크 히트맵 (발생가능성 × 영향도) + 핵심 리스크 설명
  3. 다운사이드 시나리오 분석 + 리스크 노출도 구성 도넛차트
  4. 방어 요인 / 완충 장치
  5. 모니터링 체크리스트 + 이벤트 캘린더
"""

from __future__ import annotations

import math
import plotly.graph_objects as go
import streamlit as st


# ──────────────────────────────────────────────
# 헬퍼 함수
# ──────────────────────────────────────────────

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


def _score_color(score: float) -> str:
    if score >= 70:
        return "#22c55e"
    if score >= 40:
        return "#f59e0b"
    return "#ef4444"


def _risk_level(vol: float, mdd: float) -> tuple[str, str, str]:
    """변동성·MDD 기반 종합 리스크 수준 판단"""
    if vol > 0.55 or mdd < -0.65:
        return "높음", "#ef4444", "⚠"
    if vol > 0.35 or mdd < -0.45:
        return "보통", "#f59e0b", "⬡"
    return "낮음", "#22c55e", "✓"


# ──────────────────────────────────────────────
# 섹션 1: 상단 KPI 카드 6개
# ──────────────────────────────────────────────

def _render_kpi_cards(p: dict) -> None:
    ps  = p.get("price_summary", {})
    lf  = p.get("latest_financials", {})
    sc  = p.get("summary_cards", {})
    ml  = p.get("ml_overlay", {})
    av  = p.get("advanced_valuation", {})
    vsc = p.get("valuation_scorecard", {})

    vol = float(ps.get("volatility_annualized", 0))
    mdd = float(ps.get("mdd", 0))
    debt_ratio  = float(lf.get("debt_ratio", 0))
    fcf_margin  = float(lf.get("fcf_margin", 0))
    op_margin   = float(lf.get("op_margin", 0))

    risk_label, risk_color, risk_icon = _risk_level(vol, mdd)

    # 하방 압력: DCF 괴리율 기준
    upside = float(p.get("dcf", {}).get("upside_downside_pct", 0))
    down_label = "중상" if upside < -0.4 else "중간" if upside < 0 else "낮음"
    down_color = "#ef4444" if upside < -0.4 else "#f59e0b" if upside < 0 else "#22c55e"
    down_desc  = "유의할 하방 압력" if upside < -0.4 else "제한적 하방" if upside < 0 else "상향 여력"

    # 고객 집중 리스크 (PSR 기반 proxy)
    psr_pct = float(ml.get("psr_overlay", {}).get("psr_peer_percentile_lower_better", 50))
    cust_label = "높음" if psr_pct < 20 else "보통" if psr_pct < 60 else "낮음"
    cust_color = "#ef4444" if psr_pct < 20 else "#f59e0b" if psr_pct < 60 else "#22c55e"

    # 업황 민감도 (베타 기반)
    beta = float(p.get("wacc", {}).get("beta", 1.0))
    sens_label = "높음" if beta > 1.5 else "중간" if beta > 1.0 else "낮음"
    sens_color = "#ef4444" if beta > 1.5 else "#f59e0b" if beta > 1.0 else "#22c55e"
    sens_desc  = f"사이클 영향 {'높음' if beta > 1.5 else '중간'}"

    # 재무 방어력 (FCF Margin + 영업이익률 기반)
    defense_score = (fcf_margin + op_margin) / 2
    def_label = "양호" if defense_score > 0.15 else "보통" if defense_score > 0.08 else "미흡"
    def_color = "#22c55e" if defense_score > 0.15 else "#f59e0b" if defense_score > 0.08 else "#ef4444"

    # 모니터링 우선순위 (valuation_quality_diagnostics 기반)
    diag = av.get("valuation_quality_diagnostics", [])
    warn_count = sum(1 for d in diag if d.get("상태") in ("보수적", "주의"))
    mon_label = f"{warn_count + 3}개"
    mon_desc  = "집중 모니터링 필요" if warn_count >= 2 else "일반 모니터링"

    cards = [
        {
            "title": "종합 리스크 수준",
            "value": risk_label,
            "desc": f"({risk_label} 수준의 리스크)",
            "color": risk_color,
            "icon": "🛡",
            "icon_bg": "#fff7ed",
        },
        {
            "title": "하방 압력",
            "value": down_label,
            "desc": f"({down_desc})",
            "color": down_color,
            "icon": "📉",
            "icon_bg": "#fef2f2",
        },
        {
            "title": "고객 집중 리스크",
            "value": cust_label,
            "desc": "(상위 고객 비중 높음)" if cust_label == "높음" else "(분산된 고객 구조)",
            "color": cust_color,
            "icon": "👥",
            "icon_bg": "#fef2f2",
        },
        {
            "title": "업황 민감도",
            "value": sens_label,
            "desc": f"({sens_desc})",
            "color": "#a855f7",
            "icon": "⚙",
            "icon_bg": "#faf5ff",
        },
        {
            "title": "재무 방어력",
            "value": def_label,
            "desc": "(재무 완충력 양호)" if def_label == "양호" else "(추가 개선 필요)",
            "color": "#3b82f6",
            "icon": "💰",
            "icon_bg": "#eff6ff",
        },
        {
            "title": "모니터링 우선순위",
            "value": mon_label,
            "desc": f"({mon_desc})",
            "color": "#64748b",
            "icon": "📋",
            "icon_bg": "#f8fafc",
        },
    ]

    cols = st.columns(6)
    for col, card in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div style="border:1px solid #e2e8f0;border-radius:12px;padding:14px 10px;
                            background:#fff;text-align:center;height:120px;display:flex;
                            flex-direction:column;align-items:center;justify-content:center;gap:4px">
                    <div style="font-size:22px;width:38px;height:38px;border-radius:50%;
                                background:{card['icon_bg']};display:flex;align-items:center;
                                justify-content:center;margin-bottom:2px">{card['icon']}</div>
                    <div style="font-size:11px;color:#64748b;font-weight:500">{card['title']}</div>
                    <div style="font-size:20px;font-weight:800;color:{card['color']};line-height:1.1">{card['value']}</div>
                    <div style="font-size:11px;color:#94a3b8">{card['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────
# 섹션 2: 리스크 히트맵 + 핵심 리스크 설명
# ──────────────────────────────────────────────

def _build_risk_heatmap(p: dict) -> go.Figure:
    """발생가능성 × 영향도 산점도형 리스크 히트맵"""

    lf  = p.get("latest_financials", {})
    ps  = p.get("price_summary", {})
    dcf = p.get("dcf", {})
    wacc_d = p.get("wacc", {})

    vol     = float(ps.get("volatility_annualized", 0))
    mdd     = float(ps.get("mdd", 0))
    upside  = float(dcf.get("upside_downside_pct", 0))
    beta    = float(wacc_d.get("beta", 1.0))
    debt_r  = float(lf.get("debt_ratio", 0))
    fcf_m   = float(lf.get("fcf_margin", 0))
    rev_g   = float(lf.get("revenue_growth", 0))

    # 각 리스크 항목: (이름, 발생가능성 1-3, 영향도 1-3, 색상)
    # 발생가능성: 높음=3, 중간=2, 낮음=1  / 영향도: 동일
    risks = [
        {
            "name": "고객사 투자 지연",
            "prob": 2.7 if beta > 1.5 else 2.0,
            "impact": 2.8,
            "color": "#ef4444",
            "size": 22,
        },
        {
            "name": "반도체 업황 둔화",
            "prob": 1.8,
            "impact": 2.5,
            "color": "#f97316",
            "size": 18,
        },
        {
            "name": "원가 상승",
            "prob": 2.0,
            "impact": 1.8,
            "color": "#f59e0b",
            "size": 16,
        },
        {
            "name": "환율 변동",
            "prob": 2.3,
            "impact": 2.2,
            "color": "#f97316",
            "size": 17,
        },
        {
            "name": "신제품 램프 지연",
            "prob": 1.5,
            "impact": 2.0,
            "color": "#f59e0b",
            "size": 15,
        },
        {
            "name": "CAPEX 집행 부담",
            "prob": 1.3,
            "impact": 1.5,
            "color": "#22c55e",
            "size": 14,
        },
        {
            "name": "재고 조정 장기화",
            "prob": 2.0,
            "impact": 1.7,
            "color": "#3b82f6",
            "size": 15,
        },
    ]

    fig = go.Figure()

    # 배경 색상 구간 (3×3 그리드)
    zone_colors = {
        (1, 1): "#f0fdf4",  # 낮음-낮음 → 녹
        (1, 2): "#fefce8",
        (1, 3): "#fff7ed",
        (2, 1): "#fefce8",
        (2, 2): "#fff7ed",
        (2, 3): "#fef2f2",
        (3, 1): "#fff7ed",
        (3, 2): "#fef2f2",
        (3, 3): "#fef2f2",  # 높음-높음 → 적
    }
    for (px_, py_), bg in zone_colors.items():
        fig.add_shape(
            type="rect",
            x0=px_ - 1, x1=px_,
            y0=py_ - 1, y1=py_,
            fillcolor=bg,
            line=dict(color="#e2e8f0", width=0.5),
            layer="below",
        )

    for r in risks:
        # jitter for overlap
        jx = (hash(r["name"]) % 20 - 10) * 0.015
        jy = (hash(r["name"][::-1]) % 20 - 10) * 0.015
        fig.add_trace(go.Scatter(
            x=[r["prob"] + jx],
            y=[r["impact"] + jy],
            mode="markers+text",
            marker=dict(size=r["size"], color=r["color"], opacity=0.85,
                        line=dict(color="#fff", width=1.5)),
            text=[r["name"]],
            textposition="top center",
            textfont=dict(size=9, color="#374151"),
            name=r["name"],
            showlegend=False,
            hovertemplate=f"<b>{r['name']}</b><br>발생가능성: {r['prob']:.1f}<br>영향도: {r['impact']:.1f}<extra></extra>",
        ))

    fig.update_layout(
        height=320,
        margin=dict(l=40, r=20, t=20, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title="발생 가능성",
            range=[0, 3],
            tickvals=[0.5, 1.5, 2.5],
            ticktext=["낮음", "중간", "높음"],
            tickfont=dict(size=10),
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            title="영향도",
            range=[0, 3],
            tickvals=[0.5, 1.5, 2.5],
            ticktext=["낮음", "중간", "높음"],
            tickfont=dict(size=10),
            showgrid=False,
            zeroline=False,
        ),
        font=dict(size=10),
    )
    return fig


def _render_core_risk_desc(p: dict) -> None:
    """핵심 리스크 설명 목록 (이미지 오른쪽 패널)"""

    lf   = p.get("latest_financials", {})
    dcf  = p.get("dcf", {})
    wacc_d = p.get("wacc", {})
    av   = p.get("advanced_valuation", {})

    beta    = float(wacc_d.get("beta", 1.0))
    fcf_m   = float(lf.get("fcf_margin", 0))
    op_m    = float(lf.get("op_margin", 0))
    rev_g   = float(lf.get("revenue_growth", 0))

    items = [
        {
            "icon": "👥",
            "color": "#ef4444",
            "text": "고객사 설비투자 일정 지연 시 실적 변동성이 커질 수 있습니다.",
        },
        {
            "icon": "⚙",
            "color": "#f97316",
            "text": "업황 회복이 늦어지면 테스트 수요 증가 속도가 둔화될 수 있습니다.",
        },
        {
            "icon": "💱",
            "color": "#f59e0b",
            "text": "환율 및 원가 변동은 수익성에 단기 압력을 줄 수 있습니다.",
        },
        {
            "icon": "🏗",
            "color": "#3b82f6",
            "text": "생산능력 확대 국면에서는 CAPEX 효율을 함께 확인해야 합니다.",
        },
        {
            "icon": "🛡",
            "color": "#22c55e",
            "text": f"높은 영업이익률({op_m*100:.1f}%)과 FCF({fcf_m*100:.1f}%)가 일부 완충 역할을 합니다.",
        },
    ]

    for item in items:
        st.markdown(
            f"""
            <div style="display:flex;align-items:flex-start;gap:10px;padding:8px 0;
                        border-bottom:1px solid #f1f5f9">
                <span style="font-size:16px;width:24px;text-align:center;flex-shrink:0">{item['icon']}</span>
                <span style="font-size:12px;color:#374151;line-height:1.5">{item['text']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 핵심 해석 박스
    ml = p.get("ml_overlay", {})
    psr_sig = ml.get("psr_overlay", {}).get("psr_signal_kr", "")
    st.markdown(
        f"""
        <div style="margin-top:12px;padding:10px 14px;border-radius:8px;
                    background:#eff6ff;border-left:3px solid #3b82f6">
            <span style="font-size:12px;color:#1d4ed8;font-weight:600">
                핵심 해석: 성장성은 유효하지만 실적 민감도 관리가 중요
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ──────────────────────────────────────────────
# 섹션 3: 다운사이드 시나리오 + 리스크 노출도 도넛
# ──────────────────────────────────────────────

def _render_downside_scenarios(p: dict) -> None:
    """다운사이드 시나리오 분석 테이블"""
    lf  = p.get("latest_financials", {})
    dcf = p.get("dcf", {})

    rev_g  = float(dcf.get("assumed_revenue_growth", 0))
    op_m   = float(lf.get("op_margin", 0))
    net_m  = float(lf.get("net_margin", 0))

    SCENARIOS = [
        ("경미",  "#22c55e", rev_g * 100 * 0.4,  op_m * 100 * 0.6,  net_m * 100 * 0.6,  "관리 가능"),
        ("기준",  "#f59e0b", rev_g * 100 * 0.65, op_m * 100 * 0.77, net_m * 100 * 0.77, "중립"),
        ("심화",  "#ef4444", rev_g * 100 * 1.0,  op_m * 100 * 1.0,  net_m * 100 * 1.0,  "주의"),
    ]

    # 헤더
    st.markdown(
        """
        <div style="display:grid;grid-template-columns:80px 1fr 1fr 1fr 80px;
                    gap:4px;padding:6px 0;border-bottom:2px solid #e2e8f0;
                    font-size:11px;font-weight:700;color:#64748b;margin-bottom:4px">
            <div></div>
            <div style="text-align:center">매출 영향</div>
            <div style="text-align:center">영업이익 영향</div>
            <div style="text-align:center">적정가 영향</div>
            <div style="text-align:center">판단</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for name, color, rev_impact, op_impact, adj_impact, verdict in SCENARIOS:
        verdict_bg = "#f0fdf4" if verdict == "관리 가능" else "#fff7ed" if verdict == "중립" else "#fef2f2"
        verdict_color = "#16a34a" if verdict == "관리 가능" else "#d97706" if verdict == "중립" else "#dc2626"

        st.markdown(
            f"""
            <div style="display:grid;grid-template-columns:80px 1fr 1fr 1fr 80px;
                        gap:4px;padding:8px 4px;border-bottom:1px solid #f1f5f9;align-items:center">
                <div style="font-weight:700;color:{color};font-size:13px">{name}</div>
                <div style="text-align:center;font-size:12px;color:#374151">
                    {rev_impact:+.0f}% ~ {rev_impact*0.5:+.0f}%
                </div>
                <div style="text-align:center;font-size:12px;color:#374151">
                    {op_impact*1.2:+.0f}% ~ {op_impact*0.8:+.0f}%
                </div>
                <div style="text-align:center;font-size:12px;color:#374151">
                    {adj_impact*1.5:+.0f}% 이상
                </div>
                <div style="text-align:center">
                    <span style="padding:2px 8px;border-radius:10px;font-size:11px;
                                 font-weight:700;background:{verdict_bg};color:{verdict_color}">
                        {verdict}
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _build_exposure_donut(p: dict) -> go.Figure:
    """리스크 노출도 구성 도넛 차트"""
    ps  = p.get("price_summary", {})
    lf  = p.get("latest_financials", {})
    wacc_d = p.get("wacc", {})

    vol  = float(ps.get("volatility_annualized", 0))
    beta = float(wacc_d.get("beta", 1.0))

    # 리스크 구성비 – 데이터 기반 proxy
    customer_weight = min(35, max(20, beta * 18))
    industry_weight = min(30, max(15, vol * 45))
    profit_weight   = min(20, max(10, (1 - float(lf.get("op_margin", 0.15))) * 25))
    fx_weight       = 10
    production_weight = max(5, 100 - customer_weight - industry_weight - profit_weight - fx_weight)

    labels = ["고객 집중도", "업황/수요", "수익성/원가", "환율/거시", "생산/실행"]
    values = [customer_weight, industry_weight, profit_weight, fx_weight, production_weight]
    colors = ["#ef4444", "#f97316", "#f59e0b", "#3b82f6", "#8b5cf6"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color="#fff", width=2)),
        textinfo="percent",
        textfont=dict(size=10),
        hovertemplate="%{label}: %{value:.0f}%<extra></extra>",
    ))

    fig.update_layout(
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(
            orientation="v",
            x=1.0, y=0.5,
            xanchor="left",
            yanchor="middle",
            font=dict(size=10),
            itemsizing="constant",
        ),
    )
    return fig


# ──────────────────────────────────────────────
# 섹션 4: 방어 요인 / 완충 장치
# ──────────────────────────────────────────────

def _render_defense_factors(p: dict) -> None:
    """방어 요인 카드 2×2 그리드"""
    lf   = p.get("latest_financials", {})
    ps   = p.get("price_summary", {})
    dcf  = p.get("dcf", {})

    op_m   = float(lf.get("op_margin", 0))
    fcf_m  = float(lf.get("fcf_margin", 0))
    cash   = float(dcf.get("cash", 0))
    capex  = float(lf.get("capex", 0))
    cfo    = float(lf.get("cfo", 0))

    factors = [
        {
            "icon": "📊",
            "title": "높은 영업이익률",
            "sub": f"{op_m*100:.1f}% 영업이익률",
            "desc": "건전한 재무구조의 수익성 유지",
            "color": "#22c55e",
            "bg": "#f0fdf4",
        },
        {
            "icon": "💵",
            "title": "순현금/양호한 유동성",
            "sub": f"현금 {round(cash/1e8):,}억원 보유",
            "desc": "충분한 유동성 확보",
            "color": "#3b82f6",
            "bg": "#eff6ff",
        },
        {
            "icon": "📦",
            "title": "제품 포트폴리오 확장",
            "sub": "다양한 응용처로 수요 변동성 완화",
            "desc": "단일 제품 의존도 축소",
            "color": "#f59e0b",
            "bg": "#fefce8",
        },
        {
            "icon": "🏭",
            "title": "CAPEX 대비 높은 현금창출",
            "sub": f"FCF {fcf_m*100:.1f}% / CFO {round(cfo/1e8):,}억원",
            "desc": "운영 현금흐름이 투자 집행을 안정적으로 뒷받침",
            "color": "#22c55e",
            "bg": "#f0fdf4",
        },
    ]

    col1, col2 = st.columns(2)
    for i, factor in enumerate(factors):
        col = col1 if i % 2 == 0 else col2
        with col:
            st.markdown(
                f"""
                <div style="border:1px solid #e2e8f0;border-radius:10px;padding:14px;
                            background:{factor['bg']};margin-bottom:10px">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                        <span style="font-size:18px">{factor['icon']}</span>
                        <span style="font-weight:700;font-size:13px;color:{factor['color']}">{factor['title']}</span>
                    </div>
                    <div style="font-size:12px;font-weight:600;color:#374151;margin-bottom:2px">{factor['sub']}</div>
                    <div style="font-size:11px;color:#64748b">{factor['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ──────────────────────────────────────────────
# 섹션 5: 모니터링 체크리스트 + 이벤트 캘린더
# ──────────────────────────────────────────────

def _render_monitoring_checklist(p: dict) -> None:
    """모니터링 체크리스트"""
    lf  = p.get("latest_financials", {})
    ps  = p.get("price_summary", {})
    av  = p.get("advanced_valuation", {})

    fcf_m    = float(lf.get("fcf_margin", 0))
    mdd      = float(ps.get("mdd", 0))
    op_m     = float(lf.get("op_margin", 0))
    rev_g    = float(lf.get("revenue_growth", 0))

    STATUS_ICON = {"주의": "🔴", "관찰": "🟡", "양호": "🟢"}
    STATUS_COLOR = {"주의": "#ef4444", "관찰": "#f59e0b", "양호": "#22c55e"}

    items = [
        {
            "icon": "🏗",
            "label": "고객사 CAPEX 공시",
            "status": "주의" if mdd < -0.5 else "관찰",
        },
        {
            "icon": "📊",
            "label": "일별 수주/가동률 추이",
            "status": "관찰",
        },
        {
            "icon": "💱",
            "label": "환율 흐름",
            "status": "양호" if op_m > 0.15 else "관찰",
        },
        {
            "icon": "📦",
            "label": "재고자산 증가율",
            "status": "양호" if fcf_m > 0.15 else "관찰",
        },
        {
            "icon": "🔬",
            "label": "신제품 인증/양산 일정",
            "status": "관찰",
        },
        {
            "icon": "📋",
            "label": "분기 실적 가이던스",
            "status": "양호" if rev_g > 0.1 else "관찰",
        },
    ]

    for item in items:
        status = item["status"]
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:10px;padding:8px 4px;
                        border-bottom:1px solid #f1f5f9">
                <span style="font-size:15px;width:22px">{item['icon']}</span>
                <span style="flex:1;font-size:12px;color:#374151">{item['label']}</span>
                <span style="font-size:14px">{STATUS_ICON[status]}</span>
                <span style="font-size:11px;font-weight:600;color:{STATUS_COLOR[status]};
                             width:36px;text-align:right">{status}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_event_calendar(p: dict) -> None:
    """이벤트 캘린더 타임라인"""

    events = [
        {"label": "2Q 실적 발표", "date": "2024.05", "desc": "실적 및 가이던스 확인", "icon": "📊"},
        {"label": "고객사 투자 계획 업데이트", "date": "2024.06~07", "desc": "설비투자 일정 및 규모 파악", "icon": "🏗"},
        {"label": "신제품 양산 개시", "date": "2024.08~09", "desc": "신규 제품의 양산 본격화", "icon": "🔬"},
        {"label": "환율/금리 체크포인트", "date": "2024.10", "desc": "거시 변수 모니터링 강화", "icon": "💱"},
        {"label": "업황 회복 업그레이드 구간", "date": "2024.11~12", "desc": "수요 회복 및 업황 모멘텀 확인", "icon": "⚙"},
    ]

    items_html = ""
    for ev in events:
        items_html += f"""
        <div style="flex:1;text-align:center;position:relative;z-index:1">
            <div style="width:40px;height:40px;border-radius:50%;background:#f1f5f9;
                        border:2px solid #cbd5e1;display:flex;align-items:center;
                        justify-content:center;margin:0 auto 8px;font-size:16px">
                {ev['icon']}
            </div>
            <div style="font-size:10px;font-weight:700;color:#374151;margin-bottom:4px">
                {ev['label']}
            </div>
            <div style="font-size:9px;color:#3b82f6;font-weight:600;margin-bottom:4px">
                {ev['date']}
            </div>
            <div style="font-size:9px;color:#94a3b8;line-height:1.4">
                {ev['desc']}
            </div>
        </div>
        """

    html = f"""
    <div style="position:relative;width:100%;padding-top:4px">
        <div style="position:absolute;top:24px;left:10%;right:10%;
                    height:2px;background:#e2e8f0;z-index:0"></div>
        <div style="display:flex;gap:18px;align-items:flex-start;position:relative;z-index:1">
            {items_html}
        </div>
    </div>
    """

    if hasattr(st, "html"):
        st.html(html)
    else:
        st.markdown(html, unsafe_allow_html=True)


# ──────────────────────────────────────────────
# 메인 렌더러
# ──────────────────────────────────────────────

def render_risk_tab(p: dict) -> None:
    """
    리스크 탭 메인 렌더링
    - payload dict 를 인자로 받아 전체 리스크 뷰를 구성합니다.
    """
    ps  = p.get("price_summary", {})
    lf  = p.get("latest_financials", {})

    # ── 1. 상단 KPI 카드
    _render_kpi_cards(p)

    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)

    # ── 2. 리스크 히트맵 + 핵심 설명
    col_heat, col_desc = st.columns([1.3, 1], gap="large")

    with col_heat:
        st.markdown(
            "**리스크 히트맵** "
            "<span style='font-size:11px;color:#94a3b8'>ⓘ 발생가능성 × 영향도</span>",
            unsafe_allow_html=True,
        )
        fig_heat = _build_risk_heatmap(p)
        st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})

    with col_desc:
        st.markdown(
            "**핵심 리스크 설명** "
            "<span style='font-size:11px;color:#94a3b8'>ⓘ</span>",
            unsafe_allow_html=True,
        )
        _render_core_risk_desc(p)

    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)

    # ── 3. 다운사이드 시나리오 + 리스크 노출도 도넛 + 방어 요인
    col_down, col_donut, col_def = st.columns([1.1, 0.9, 1], gap="large")

    with col_down:
        st.markdown(
            "**다운사이드 시나리오 분석** "
            "<span style='font-size:11px;color:#94a3b8'>ⓘ</span>",
            unsafe_allow_html=True,
        )
        _render_downside_scenarios(p)

    with col_donut:
        st.markdown(
            "**리스크 노출도 구성** "
            "<span style='font-size:11px;color:#94a3b8'>ⓘ</span>",
            unsafe_allow_html=True,
        )
        fig_donut = _build_exposure_donut(p)
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

    with col_def:
        st.markdown(
            "**방어 요인 / 완충 장치** "
            "<span style='font-size:11px;color:#94a3b8'>ⓘ</span>",
            unsafe_allow_html=True,
        )
        _render_defense_factors(p)

    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)

    # ── 4. 모니터링 체크리스트 + 이벤트 캘린더
    col_check, col_cal = st.columns([1, 1.6], gap="large")

    with col_check:
        st.markdown(
            "**모니터링 체크리스트** "
            "<span style='font-size:11px;color:#94a3b8'>ⓘ</span>",
            unsafe_allow_html=True,
        )
        _render_monitoring_checklist(p)

    with col_cal:
        st.markdown(
            "**이벤트 캘린더** "
            "<span style='font-size:11px;color:#94a3b8'>ⓘ</span>",
            unsafe_allow_html=True,
        )
        _render_event_calendar(p)

    # ── 5. 하단 투자자 메모
    vol = float(ps.get("volatility_annualized", 0))
    mdd = float(ps.get("mdd", 0))
    st.markdown("<div style='margin-top:20px'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="padding:12px 16px;border-radius:8px;background:#f8fafc;
                    border:1px solid #e2e8f0;border-left:4px solid #3b82f6">
            <span style="font-size:12px;color:#374151">
                <b>ℹ 투자자 메모:</b>&nbsp;
                리스크 탭은 '무엇이 실적과 주가에 가장 큰 하방 압력을 줄 수 있는가'를 빠르게 확인하는 용도입니다.
                현재 연환산 변동성 <b>{vol*100:.1f}%</b> · MDD <b>{mdd*100:.1f}%</b>를 감안하여
                포지션 규모 및 모니터링 주기를 조정하시기 바랍니다.
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )