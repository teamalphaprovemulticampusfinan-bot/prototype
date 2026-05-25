from __future__ import annotations

from typing import Any

from .utils import to_float

MISSING_TEXT = "해당 없음"


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _safe(value: Any, default: float | None = None) -> float | None:
    num = to_float(value)
    return default if num is None else num


def _score_from_upside(upside: Any) -> float:
    """Map DCF upside to 0~100 around a neutral 50.

    +30% 이상이면 강한 우호, -30% 이하면 강한 비우호로 보되 극단값은 clipped 처리한다.
    """
    u = _safe(upside, 0.0) or 0.0
    return _clip(50.0 + (u / 0.30) * 50.0)


def _score_from_psr(peer: dict[str, Any]) -> float:
    score = _safe(peer.get("psr_peer_percentile_lower_better"))
    if score is not None:
        return _clip(score)
    target = _safe(peer.get("target_psr"))
    median = _safe(peer.get("median_psr"))
    if target is None or median in (None, 0):
        return 50.0
    # P/S가 peer 중앙값 대비 낮을수록 우호.  중앙값과 같으면 50.
    discount = 1.0 - (target / median)
    return _clip(50.0 + discount * 80.0)


def _score_from_reference(summary: dict[str, Any]) -> float:
    row = summary.get("target_reference_row") if isinstance(summary, dict) else {}
    if not isinstance(row, dict):
        return 50.0
    score = _safe(row.get("valuation_proxy_score"))
    if score is not None:
        # 원천 후보 파일의 score scale이 0~1 또는 0~100 모두 가능하므로 자동 보정.
        return _clip(score * 100.0 if score <= 1.5 else score)
    label = str(row.get("valuation_proxy_label") or row.get("valuation_pred_label") or "").upper()
    if "ATTRACTIVE" in label or "BUY" in label:
        return 70.0
    if "UNATTRACTIVE" in label or "SELL" in label:
        return 35.0
    return 50.0


def _score_from_liquidity_and_risk(price: dict[str, Any]) -> float:
    avg_value = _safe(price.get("avg_trading_value_20d"), 0.0) or 0.0
    vol = _safe(price.get("volatility_annualized"), 0.35) or 0.35
    mdd = abs(_safe(price.get("mdd"), 0.25) or 0.25)

    # 20일 평균 거래대금 50억원 미만은 낮게, 500억원 이상은 높게 점수화.
    if avg_value <= 0:
        liquidity = 50.0
    elif avg_value >= 50_000_000_000:
        liquidity = 90.0
    elif avg_value >= 10_000_000_000:
        liquidity = 70.0
    elif avg_value >= 5_000_000_000:
        liquidity = 60.0
    else:
        liquidity = 45.0

    risk_penalty = 0.0
    if vol > 0.45:
        risk_penalty += 12.0
    elif vol > 0.35:
        risk_penalty += 6.0
    if mdd > 0.50:
        risk_penalty += 12.0
    elif mdd > 0.35:
        risk_penalty += 6.0
    return _clip(liquidity - risk_penalty)


def _validation_score(validation: dict[str, Any]) -> float:
    status = str(validation.get("status") or "").upper()
    if status in {"PASS", "OK"}:
        return 100.0
    if status == "PASS_WITH_WARNINGS":
        return 75.0
    if status == "FAIL":
        return 20.0
    return 60.0


def _label(score: float) -> tuple[str, str, str]:
    if score >= 72:
        return "VALUATION_ATTRACTIVE", "가치평가 매력 우위", "DCF·Peer·품질·유동성 조합이 우호적입니다."
    if score >= 58:
        return "VALUATION_NEUTRAL_POSITIVE", "중립 이상", "핵심 지표는 중립권이나 일부 우호 요인이 있습니다."
    if score >= 45:
        return "VALUATION_NEUTRAL", "중립", "현 가격과 내재가치·상대가치가 크게 벌어지지 않은 구간입니다."
    return "VALUATION_RISK", "밸류에이션 부담", "DCF·상대가치 또는 품질 지표의 보수적 확인이 필요합니다."


def build_valuation_scorecard(
    *,
    dcf: dict[str, Any],
    peer: dict[str, Any],
    ml: dict[str, Any],
    price_summary: dict[str, Any] | None = None,
    reference_summary: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    advanced: dict[str, Any] | None = None,
) -> dict[str, Any]:
    price_summary = price_summary or {}
    reference_summary = reference_summary or {}
    validation = validation or {}
    advanced = advanced or {}

    advanced_score = _clip(_safe(advanced.get("advanced_valuation_score"), 50.0) or 50.0)

    factors = [
        {
            "factor_code": "DCF_UPSIDE",
            "factor": "DCF 현재가 대비 괴리율",
            "weight": 0.25,
            "raw_value": _safe(dcf.get("upside_downside_pct"), 0.0),
            "score": _score_from_upside(dcf.get("upside_downside_pct")),
            "interpretation": "내재주가가 현재가보다 높을수록 우호",
        },
        {
            "factor_code": "PEER_PSR",
            "factor": "Peer P/S 상대 매력도",
            "weight": 0.15,
            "raw_value": _safe(peer.get("target_psr"), None),
            "score": _score_from_psr(peer),
            "interpretation": "P/S가 동종 피어 대비 낮을수록 우호",
        },
        {
            "factor_code": "QUALITY_ML",
            "factor": "수익성·현금흐름·안정성 ML 보조점수",
            "weight": 0.15,
            "raw_value": _safe(ml.get("composite_score"), 50.0),
            "score": _clip(_safe(ml.get("composite_score"), 50.0) or 50.0),
            "interpretation": "Valuation Agent 자체 peer percentile composite",
        },
        {
            "factor_code": "REFERENCE_UNIVERSE",
            "factor": "208개 반도체 Reference Universe 위치",
            "weight": 0.10,
            "raw_value": _score_from_reference(reference_summary),
            "score": _score_from_reference(reference_summary),
            "interpretation": "업로드/기존 universe 후보 파일의 valuation proxy 기반 상대 위치",
        },

        {
            "factor_code": "ADVANCED_VALUATION",
            "factor": "가치범위표·역산 DCF·오너 이익 교차검증",
            "weight": 0.20,
            "raw_value": advanced_score,
            "score": advanced_score,
            "interpretation": "DCF 하나에 의존하지 않고 복수 가치평가 방법의 중앙값·안전마진·역산가정을 함께 평가",
        },
        {
            "factor_code": "LIQUIDITY_RISK",
            "factor": "유동성·변동성 리스크",
            "weight": 0.10,
            "raw_value": _safe(price_summary.get("avg_trading_value_20d"), 0.0),
            "score": _score_from_liquidity_and_risk(price_summary),
            "interpretation": "거래대금은 높을수록, 변동성과 MDD는 낮을수록 우호",
        },
        {
            "factor_code": "DATA_VALIDATION",
            "factor": "데이터 검증 상태",
            "weight": 0.05,
            "raw_value": validation.get("status") or MISSING_TEXT,
            "score": _validation_score(validation),
            "interpretation": "PASS이면 workbook/dashboard용 주요 데이터 준비 완료",
        },
    ]
    weighted_score = sum(float(f["score"]) * float(f["weight"]) for f in factors)
    code, label_kr, narrative = _label(weighted_score)
    return {
        "method": "DCF_25_PSR_15_QUALITY_15_REFERENCE_10_ADVANCED_20_LIQUIDITY_10_VALIDATION_5",
        "method_kr": "DCF 25% + Peer P/S 15% + 품질 ML 15% + 208개 Universe 10% + 가치범위표/역산 DCF/오너 이익 20% + 유동성/리스크 10% + 검증 5%",
        "score": round(weighted_score, 2),
        "label": code,
        "label_kr": label_kr,
        "narrative_kr": narrative,
        "factors": factors,
        "dashboard_note_kr": "Chair 최종 가중합을 대체하지 않는 보조 밸류에이션 스코어입니다. DCF 단일값보다 다중 방법 검증을 우선합니다. 대시보드/엑셀 다운로드/투자자 요약에서 사용합니다.",
    }
