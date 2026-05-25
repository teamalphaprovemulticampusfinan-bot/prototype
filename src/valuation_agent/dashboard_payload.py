from __future__ import annotations

from typing import Any


def _last_n(rows: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    return rows[-n:] if len(rows) > n else rows


def build_dashboard_payload(
    company_dir: str,
    company: str,
    normalized: list[dict[str, Any]],
    wacc: dict[str, Any],
    dcf: dict[str, Any],
    peer: dict[str, Any],
    ml: dict[str, Any],
    validation: dict[str, Any],
    *,
    price_history: list[dict[str, Any]] | None = None,
    price_summary: dict[str, Any] | None = None,
    reference_universe: list[dict[str, Any]] | None = None,
    reference_focus: list[dict[str, Any]] | None = None,
    reference_summary: dict[str, Any] | None = None,
    scorecard: dict[str, Any] | None = None,
    advanced: dict[str, Any] | None = None,
) -> dict[str, Any]:
    latest = normalized[-1] if normalized else {}
    projection = dcf.get("projection") or []
    peer_rows = peer.get("peer_rows") or []
    price_history = price_history or []
    price_summary = price_summary or {}
    reference_universe = reference_universe or []
    reference_focus = reference_focus or []
    reference_summary = reference_summary or {}
    scorecard = scorecard or {}
    advanced = advanced or {}
    football = advanced.get("football_field") or {}
    reverse_dcf = advanced.get("reverse_dcf") or {}
    owner = advanced.get("owner_earnings") or {}
    market_multiples = advanced.get("market_implied_multiples") or {}

    price_chart = [
        {
            "date": r.get("date"),
            "close": r.get("close"),
            "ma20": r.get("ma20"),
            "ma60": r.get("ma60"),
            "ma120": r.get("ma120"),
            "drawdown": r.get("drawdown"),
            "rolling_vol_20": r.get("rolling_vol_20"),
            "return_60d": r.get("return_60d"),
            "trading_value": r.get("trading_value"),
            "turnover_ratio": r.get("turnover_ratio"),
        }
        for r in _last_n(price_history, 260)
    ]

    reference_chart = [
        {
            "company": r.get("company_name") or r.get("company"),
            "ticker6": r.get("ticker6"),
            "peer_group": r.get("peer_group"),
            "valuation_proxy_score": r.get("valuation_proxy_score"),
            "credit_risk_score": r.get("credit_risk_score"),
            "focus_reason": r.get("focus_reason"),
            "is_target": r.get("is_target"),
            "is_focal_5": r.get("is_focal_5"),
            "psr": r.get("psr") or r.get("target_psr") or r.get("psr_market"),
        }
        for r in reference_focus[:60]
    ]

    return {
        "agent": "valuation",
        "company_dir": company_dir,
        "company": company,
        "status": validation.get("status"),
        "korean_label": "독립 가치평가 에이전트",
        "summary_cards": {
            "wacc": {"label": "WACC", "value": wacc.get("wacc"), "format": "percent"},
            "enterprise_value": {"label": "DCF 기업가치", "value": dcf.get("enterprise_value"), "format": "krw"},
            "equity_value": {"label": "DCF 지분가치", "value": dcf.get("equity_value"), "format": "krw"},
            "latest_close": {"label": "현재가", "value": price_summary.get("latest_close") or dcf.get("latest_close"), "format": "krw_per_share"},
            "implied_price": {"label": "DCF 내재주가", "value": dcf.get("implied_price"), "format": "krw_per_share"},
            "upside_downside_pct": {"label": "현재가 대비 괴리율", "value": dcf.get("upside_downside_pct"), "format": "percent"},
            "target_psr": {"label": "P/S", "value": peer.get("target_psr"), "format": "multiple"},
            "median_psr": {"label": "비교기업 P/S 중앙값", "value": peer.get("median_psr"), "format": "multiple"},
            "psr_gap": {"label": "P/S 중앙값 대비", "value": peer.get("psr_vs_peer_median_pct"), "format": "percent"},
            "reference_rows": {"label": "208개 반도체 비교군", "value": reference_summary.get("reference_universe_rows") or len(reference_universe), "format": "count"},
            "reference_peer_group": {"label": "기준 비교군 그룹", "value": reference_summary.get("target_peer_group"), "format": "text"},
            "return_1y": {"label": "1년 수익률", "value": price_summary.get("return_1y"), "format": "percent"},
            "mdd": {"label": "MDD", "value": price_summary.get("mdd"), "format": "percent"},
            "volatility": {"label": "연환산 변동성", "value": price_summary.get("volatility_annualized"), "format": "percent"},
            "market_cap": {"label": "시가총액", "value": price_summary.get("market_cap"), "format": "krw"},
            "shares_outstanding": {"label": "발행주식 수", "value": price_summary.get("shares_outstanding"), "format": "shares"},
            "avg_trading_value_20d": {"label": "20일 평균 거래대금", "value": price_summary.get("avg_trading_value_20d"), "format": "krw"},
            "turnover_latest": {"label": "최근 거래회전율", "value": price_summary.get("turnover_latest"), "format": "percent"},
            "ml_composite_score": {"label": "ML 보조 품질점수", "value": ml.get("composite_score"), "format": "score"},
            "ml_label": {"label": "ML 보조 라벨", "value": ml.get("label_kr") or ml.get("label"), "format": "text"},
            "valuation_scorecard": {"label": "보조 가치평가 점수", "value": scorecard.get("score"), "format": "score"},
            "valuation_scorecard_label": {"label": "보조 가치평가 라벨", "value": scorecard.get("label_kr") or scorecard.get("label"), "format": "text"},
            "advanced_valuation_score": {"label": "종합 가치평가 점수", "value": advanced.get("advanced_valuation_score"), "format": "score"},
            "valuation_range_base_price": {"label": "가치범위 중앙값", "value": football.get("base_price"), "format": "krw_per_share"},
            "valuation_range_margin": {"label": "가치범위 안전마진", "value": football.get("margin_of_safety_pct"), "format": "percent"},
            "reverse_dcf_growth": {"label": "역산 영구성장률", "value": reverse_dcf.get("implied_terminal_growth_rate"), "format": "percent"},
            "owner_earnings_price": {"label": "오너 이익 주당가치", "value": owner.get("owner_earnings_value_per_share"), "format": "krw_per_share"},
            "market_psr": {"label": "시장내재 P/S", "value": market_multiples.get("psr_market"), "format": "multiple"},
            "market_pbr": {"label": "시장내재 P/B", "value": market_multiples.get("pbr_market"), "format": "multiple"},
            "market_fcf_yield": {"label": "시장내재 FCF 수익률", "value": market_multiples.get("fcf_yield_market"), "format": "percent"},
            "validation_status": {"label": "검증 상태", "value": validation.get("status"), "format": "text"},
        },
        "latest_financials": latest,
        "price_summary": price_summary,
        "wacc": wacc,
        "dcf": {k: v for k, v in dcf.items() if k != "projection"},
        "chart_series": {
            "historical_financials": [
                {"year": r.get("year"), "revenue": r.get("revenue"), "operating_profit": r.get("operating_profit"), "fcf": r.get("fcf")}
                for r in normalized
            ],
            "price_history": price_chart,
            "fcf_projection": [
                {"year": r.get("year"), "revenue": r.get("revenue"), "fcf": r.get("fcf"), "pv_fcf": r.get("pv_fcf")}
                for r in projection
            ],
            "peer_multiples": [
                {"company": r.get("company"), "psr": r.get("psr"), "per": r.get("per"), "pbr": r.get("pbr"), "ev_sales": r.get("ev_sales")}
                for r in peer_rows
            ],
            "reference_universe_focus": reference_chart,
        },
        "peer_comps": peer,
        "reference_universe_summary": reference_summary,
        "reference_universe_focus_rows": reference_focus,
        "ml_overlay": ml,
        "valuation_scorecard": scorecard,
        "advanced_valuation": advanced,
        "market_implied_multiples": market_multiples,
        "valuation_quality_diagnostics": advanced.get("valuation_quality_diagnostics") or [],
        "validation": validation,
        "display_labels_kr": {
            "summary_cards": "핵심 요약 카드",
            "price_history": "주가 차트",
            "historical_financials": "재무 추이",
            "fcf_projection": "FCF 추정",
            "peer_multiples": "비교기업 멀티플 비교",
            "reference_universe_focus": "208개 반도체 비교군 상대위치",
            "advanced_valuation": "종합 가치평가",
            "download_workbook": "엑셀 다운로드",
        },
        "dashboard_usage_note": "Streamlit/React 대시보드에서 한국어 카드, 주가 차트, DCF·P/S·P/B·PER·가치범위표, 208개 기준 비교군 표/산점도, 검증 배지, 엑셀 다운로드 버튼에 바로 연결할 수 있습니다.",
    }
