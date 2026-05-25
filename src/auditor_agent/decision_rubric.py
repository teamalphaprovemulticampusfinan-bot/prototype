from __future__ import annotations

"""Deterministic 3rd-stage recommendation rubric for the First Auditor.

This module is intentionally independent from individual agent code. It reads the packets
already collected by the Chair adapters and converts them into an auditable, quantitative
매수/보유/매도 signal before the Chair report is generated.
"""

import json
import math
import os
import re
from typing import Any

from .dynamic_model_averaging import AGENT_ORDER, compute_dma_label_posterior, compute_dma_weights, compute_signal_dma_weights, normalize_recommendation_label

REMOVED_FIXED_WEIGHT_POLICY = "no_static_agent_weight; use compute_dma_weights()"

AGENT_KO: dict[str, str] = {
    "finance": "재무",
    "market": "시장",
    "tech": "기술",
    "valuation": "가치평가",
    "issue": "이슈",
    "macro": "거시",
}

# Backward-compatible name only.  Do not put fixed values here.
# Agent and component weights are computed by Dynamic Model Averaging.
AGENT_WEIGHTS: dict[str, float] = {}

POSITIVE_TERMS = [
    "성장", "개선", "흑자", "수혜", "확대", "회복", "견조", "호조", "반등",
    "수주", "계약", "채택", "양산", "등록", "존속", "특허", "정부과제", "기술이전",
    "positive", "buy", "bullish", "upside", "pass",
]

NEGATIVE_TERMS = [
    "적자", "손실", "악화", "둔화", "하락", "부진", "리스크", "소송", "규제",
    "차질", "지연", "감소", "고금리", "부채", "상장폐지", "오버행", "희석",
    "전환가액", "유상증자", "cb", "bw", "negative", "sell", "bearish", "downside",
]


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "확인 제한"}:
        return None
    text = text.replace(",", "").replace("%", "").replace("원", "").strip()
    try:
        return float(text)
    except Exception:
        return None


def _json_text(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        return str(value or "")


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))



def _component_dma_signal(group: str, components: dict[str, float]) -> tuple[float, dict[str, float], dict[str, Any]]:
    """Combine component signals with DMA instead of hard-coded component weights.

    Each component is treated as a candidate model.  When a component-level
    history CSV exists, set ALPHAPROVE_DMA_COMPONENT_HISTORY_CSV and include
    columns such as ``sales_growth_signal`` plus a realized target column.  If
    no such history exists, the objective fallback is the equal prior over
    available component signals.  No fixed preset component weights are
    used here.
    """

    clean: dict[str, float] = {}
    for key, value in components.items():
        num = _to_float(value)
        if num is None:
            continue
        clean[str(key)] = _clamp(float(num))

    if not clean:
        return 0.0, {}, {"method": "component_dma_no_available_signals", "group": group}

    aliases = {name: (f"{group}_{name}", f"{group}_{name}_signal", f"{name}_signal") for name in clean}
    try:
        dma = compute_signal_dma_weights(clean, model_aliases=aliases)
    except Exception as exc:
        # Fail safe: equal prior is objective when realized component history is unavailable.
        n = len(clean)
        dma = {
            "method": "component_dma_equal_prior_after_error",
            "error": str(exc),
            "history_used": False,
            "history_observations": 0,
            "weights_adjusted": {name: 1.0 / n for name in clean},
        }

    weights = {name: float((dma.get("weights_adjusted") or dma.get("weights") or {}).get(name, 0.0) or 0.0) for name in clean}
    total = sum(weights.values())
    if total <= 0:
        weights = {name: 1.0 / len(clean) for name in clean}
    else:
        weights = {name: weight / total for name, weight in weights.items()}

    signal = sum(clean[name] * weights.get(name, 0.0) for name in clean)
    return _clamp(signal), {name: round(weight, 6) for name, weight in weights.items()}, dma


def _pct_to_ratio_or_percent(value: Any) -> float | None:
    """Return a percentage-point value, e.g. 12.3 means 12.3%."""
    num = _to_float(value)
    if num is None:
        return None
    # Some packets store ratios as 0.123, others store percentage points as 12.3.
    if -1.5 <= num <= 1.5:
        return num * 100.0
    return num


def _find_number_after_labels(text: str, labels: list[str]) -> float | None:
    for label in labels:
        patterns = [
            rf"{re.escape(label)}[^-+0-9]{{0,18}}([-+]?\d[\d,]*(?:\.\d+)?)\s*%?",
            rf"([-+]?\d[\d,]*(?:\.\d+)?)\s*%?\s*(?:인|의)?\s*{re.escape(label)}",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                return _to_float(m.group(1))
    return None


def _nested_get(data: Any, keys: list[str]) -> Any:
    """Depth-first search for one of keys in dict/list structures."""
    if isinstance(data, dict):
        for key in keys:
            if key in data and data.get(key) not in (None, ""):
                return data.get(key)
        for value in data.values():
            found = _nested_get(value, keys)
            if found not in (None, ""):
                return found
    elif isinstance(data, list):
        for value in data:
            found = _nested_get(value, keys)
            if found not in (None, ""):
                return found
    return None


def _metric(packet: dict[str, Any], labels: list[str], text: str | None = None) -> float | None:
    raw = _nested_get(packet, labels)
    num = _to_float(raw)
    if num is not None:
        return num
    return _find_number_after_labels(text or _json_text(packet), labels)


def _ratio_score(value: float | None, good: float, bad: float, *, higher_is_better: bool = True) -> float:
    if value is None:
        return 0.0
    if higher_is_better:
        if value >= good:
            return 1.0
        if value <= bad:
            return -1.0
        return (value - bad) / max(1e-9, (good - bad)) * 2 - 1
    if value <= good:
        return 1.0
    if value >= bad:
        return -1.0
    return (bad - value) / max(1e-9, (bad - good)) * 2 - 1


def _signal_to_label(signal: float) -> str:
    """Direction-only fallback for old packets without categorical labels.

    There is no fixed ±0.25 band here.  Positive continuous signal is a Buy
    direction, negative continuous signal is a Sell direction, and only exact
    zero/missing direction remains Hold as a reject/no-trade placeholder.
    """
    try:
        v = float(signal or 0.0)
    except Exception:
        v = 0.0
    if v > 0:
        return "매수"
    if v < 0:
        return "매도"
    return "보유"


def _extract_packet_label(packet: dict[str, Any]) -> str | None:
    """Extract an explicit categorical label from an agent packet.

    No numeric signal threshold is used here.  If no categorical label exists,
    the caller may fall back to a diagnostic label, but final recommendation is
    decided by DMA categorical posterior.
    """
    candidates = [
        packet.get("auditor_recommendation"),
        packet.get("recommendation"),
        packet.get("final_recommendation"),
        packet.get("opinion"),
        packet.get("final_opinion"),
        packet.get("investment_view"),
    ]
    for key in ("decision", "signal", "summary", "result", "raw_payload"):
        value = packet.get(key)
        if isinstance(value, dict):
            candidates.extend([
                value.get("auditor_recommendation"),
                value.get("recommendation"),
                value.get("final_recommendation"),
                value.get("opinion"),
                value.get("final_opinion"),
                value.get("investment_view"),
            ])
    for value in candidates:
        label = normalize_recommendation_label(value)
        if label:
            return label
    return None


def _finance_signal(packet: dict[str, Any]) -> dict[str, Any]:
    text = _json_text(packet)
    sales_growth = _pct_to_ratio_or_percent(_metric(packet, ["sales_growth_%", "sales_growth", "매출성장률"], text))
    op_margin = _pct_to_ratio_or_percent(_metric(packet, ["operating_margin_%", "operating_margin", "영업이익률"], text))
    roe = _pct_to_ratio_or_percent(_metric(packet, ["ROE_%", "roe_%", "roe", "ROE"], text))
    fcf = _metric(packet, ["fcf", "FCF", "free_cash_flow", "잉여현금흐름"], text)
    debt_ratio = _pct_to_ratio_or_percent(_metric(packet, ["debt_ratio_%", "debt_ratio", "부채비율"], text))
    current_ratio = _pct_to_ratio_or_percent(_metric(packet, ["current_ratio_%", "current_ratio", "유동비율"], text))
    mdd = _pct_to_ratio_or_percent(_metric(packet, ["annual_mdd_%", "annual_mdd", "MDD", "연간 MDD"], text))
    warning = str(_nested_get(packet, ["warning_stock", "investment_warning", "투자경고"]) or "").lower()

    components = {
        "sales_growth": _ratio_score(sales_growth, good=12.0, bad=-5.0),
        "operating_margin": _ratio_score(op_margin, good=8.0, bad=-3.0),
        "roe": _ratio_score(roe, good=8.0, bad=-5.0),
        "fcf": 1.0 if fcf is not None and fcf > 0 else (-0.7 if fcf is not None and fcf < 0 else 0.0),
        "debt_ratio": _ratio_score(debt_ratio, good=100.0, bad=200.0, higher_is_better=False),
        "current_ratio": _ratio_score(current_ratio, good=130.0, bad=80.0),
        "mdd": _ratio_score(mdd, good=-10.0, bad=-35.0),
        "warning_stock": -1.0 if warning in {"true", "1", "yes", "y", "투자경고", "warning"} else 0.0,
    }
    signal, component_weights, component_dma_model = _component_dma_signal("finance", components)
    basis = []
    if sales_growth is not None:
        basis.append(f"매출성장률 {sales_growth:.2f}%")
    if op_margin is not None:
        basis.append(f"영업이익률 {op_margin:.2f}%")
    if roe is not None:
        basis.append(f"ROE {roe:.2f}%")
    if fcf is not None:
        basis.append(f"FCF {fcf:,.0f}")
    if debt_ratio is not None:
        basis.append(f"부채비율 {debt_ratio:.2f}%")
    if mdd is not None:
        basis.append(f"MDD {mdd:.2f}%")
    return {
        "signal": round(_clamp(signal), 4),
        "basis": basis,
        "components": components,
        "component_weights": component_weights,
        "component_dma_model": component_dma_model,
    }


def _market_signal(packet: dict[str, Any]) -> dict[str, Any]:
    text = _json_text(packet)
    total_score = _metric(packet, ["total_score", "market_score", "score"], text)
    annual_return = _pct_to_ratio_or_percent(_metric(packet, ["annual_return_%", "annual_return", "연수익률"], text))
    mdd = _pct_to_ratio_or_percent(_metric(packet, ["annual_mdd_%", "annual_mdd", "MDD", "연간 MDD"], text))
    volume_ratio = _metric(packet, ["volume_ma_ratio_mean", "volume_ratio", "거래량비율"], text)
    volatility = _metric(packet, ["volatility", "vkospi_mean", "변동성"], text)

    if total_score is not None and 0 <= total_score <= 100:
        score_component = (total_score - 55.0) / 35.0
    else:
        score_component = 0.0
    components = {
        "market_score": _clamp(score_component),
        "annual_return": _ratio_score(annual_return, good=15.0, bad=-15.0),
        "mdd": _ratio_score(mdd, good=-10.0, bad=-35.0),
        "liquidity": _ratio_score(volume_ratio, good=1.2, bad=0.6),
        "volatility": _ratio_score(volatility, good=18.0, bad=35.0, higher_is_better=False),
    }
    signal, component_weights, component_dma_model = _component_dma_signal("market", components)
    basis = []
    if total_score is not None:
        basis.append(f"market_score {total_score:.2f}/100")
    if annual_return is not None:
        basis.append(f"연수익률 {annual_return:.2f}%")
    if mdd is not None:
        basis.append(f"MDD {mdd:.2f}%")
    return {
        "signal": round(_clamp(signal), 4),
        "basis": basis,
        "components": components,
        "component_weights": component_weights,
        "component_dma_model": component_dma_model,
    }


def _original_view_signal(packet: dict[str, Any]) -> tuple[float, str | None]:
    """Use a specialist's original view as a small reference signal, not as a final answer."""
    candidates = [
        packet.get("opinion"),
        packet.get("final_opinion"),
        packet.get("recommendation"),
        packet.get("investment_view"),
    ]
    raw = packet.get("raw_payload") if isinstance(packet.get("raw_payload"), dict) else {}
    candidates.extend([raw.get("opinion"), raw.get("final_opinion"), raw.get("recommendation"), raw.get("investment_view")])
    for value in candidates:
        text = str(value or "").strip()
        if not text:
            continue
        upper = text.upper()
        if "매수" in text or "BUY" in upper:
            return 1.0, "매수"
        if "매도" in text or "SELL" in upper:
            return -1.0, "매도"
        if "보유" in text or "HOLD" in upper:
            return 0.0, "보유"
    return 0.0, None


def _score100_to_signal(value: Any, neutral: float = 60.0, scale: float = 35.0) -> float:
    num = _to_float(value)
    if num is None:
        return 0.0
    return _clamp((num - neutral) / max(scale, 1e-9))



def _tech_signal(packet: dict[str, Any]) -> dict[str, Any]:
    text = _json_text(packet)
    final_score = _metric(
        packet,
        [
            "final_tech_investor_score",
            "final_investor_tech_score",
            "final_bridge_score_after_ip_evidence",
            "tech_evidence_score",
            "investor_score",
        ],
        text,
    )
    bridge = _metric(packet, ["peer_adjusted_bridge_score", "tech_to_value_bridge_score", "bridge_score", "base_bridge_score"], text)
    peer_percentile = _metric(packet, ["peer_composite_percentile", "peer_percentile", "percentile"], text)
    ip_composite = _metric(packet, ["ip_evidence_composite_score", "ip_evidence_score", "ip_composite"], text)
    total = _metric(packet, ["total_score"], text)
    max_score = _metric(packet, ["max_score"], text) or 35.0
    legal_obj = _nested_get(packet, ["ip_legal_features", "ip_legal_stability"])
    if isinstance(legal_obj, dict):
        patents = _to_float(legal_obj.get("total_patents"))
        registered = _to_float(legal_obj.get("registered_patents_estimated") or legal_obj.get("registered_patents"))
        active = _to_float(legal_obj.get("alive_patents_estimated") or legal_obj.get("alive_patents"))
    else:
        patents = _metric(packet, ["normalized_patent_count", "patent_count", "patents", "특허"], text)
        registered = _metric(packet, ["registered_patent_count", "registered_patents", "등록특허"], text)
        active = _metric(packet, ["active_patent_count", "alive_patent_count", "alive_patents", "존속 가능 특허", "존속"], text)
    # Some rich Tech packets also contain claim_count/coverage rates; do not let those be mistaken for registered/alive patent counts.
    if patents is not None and registered is not None and registered > patents * 1.25:
        registered = None
    if patents is not None and active is not None and active > patents * 1.25:
        active = None
    if patents is not None and active is not None and active <= 1.5:
        active = None
    original_signal, original_label = _original_view_signal(packet)

    if final_score is None and bridge is not None:
        final_score = bridge
    if final_score is None and total is not None and max_score:
        final_score = total / max_score * 100.0

    score_component = _score100_to_signal(final_score, neutral=60.0, scale=35.0)
    peer_component = _score100_to_signal(peer_percentile, neutral=55.0, scale=35.0)
    ip_component = _score100_to_signal(ip_composite, neutral=50.0, scale=35.0)

    ip_quality = 0.0
    if patents and registered:
        ip_quality += 1.0 if registered / max(1.0, patents) >= 0.5 else -1.0
    if registered and active:
        ip_quality += 1.0 if active / max(1.0, registered) >= 0.6 else -1.0
    ip_quality = _clamp(ip_quality)

    has_commercial_terms = any(term in text for term in ["고객", "채택", "양산", "매출", "수익성", "CAPEX", "FCF", "사업화"])
    commercialization = 1.0 if has_commercial_terms else -1.0

    components = {
        "final_score": score_component,
        "peer_percentile": peer_component,
        "ip_composite": ip_component,
        "ip_quality": ip_quality,
        "commercialization": commercialization,
        "original_agent_view_reference": original_signal,
    }
    signal, component_weights, component_dma_model = _component_dma_signal("tech", components)
    basis = []
    if final_score is not None:
        basis.append(f"Tech 최종/Bridge 점수 {final_score:.2f}/100")
    if peer_percentile is not None:
        basis.append(f"peer percentile {peer_percentile:.2f}")
    if ip_composite is not None:
        basis.append(f"IP Evidence Composite {ip_composite:.2f}/100")
    if patents is not None:
        basis.append(f"특허 레코드 {patents:.0f}건")
    if registered is not None:
        basis.append(f"등록특허 {registered:.0f}건")
    if active is not None:
        basis.append(f"존속 가능 특허 {active:.0f}건")
    if original_label:
        basis.append(f"기존 Tech Agent 내부 판단 참고={original_label}")
    return {
        "signal": round(_clamp(signal), 4),
        "basis": basis,
        "components": components,
        "component_weights": component_weights,
        "component_dma_model": component_dma_model,
    }


def _valuation_signal(packet: dict[str, Any]) -> dict[str, Any]:
    text = _json_text(packet)
    upside = _pct_to_ratio_or_percent(_metric(packet, ["upside_downside_pct", "upside", "괴리율"], text))
    validation_status = str(_nested_get(packet, ["validation_status", "status"]) or "").upper()
    wacc = _pct_to_ratio_or_percent(_metric(packet, ["wacc", "WACC"], text))
    scorecard_obj = _nested_get(packet, ["scorecard", "valuation_scorecard"])
    if isinstance(scorecard_obj, dict):
        valuation_score = _to_float(scorecard_obj.get("score") or scorecard_obj.get("valuation_scorecard_score"))
    else:
        valuation_score = _metric(packet, ["valuation_scorecard_score", "valuation_score", "scorecard_score"], text)
    target_psr = _metric(packet, ["target_psr", "psr"], text)
    peer_median_psr = _metric(packet, ["peer_median_psr", "median_psr"], text)
    psr_gap = _pct_to_ratio_or_percent(_metric(packet, ["psr_gap", "P/S 중앙값 대비"], text))
    reference_score = _metric(packet, ["valuation_proxy_score", "reference_universe_score", "reference_score"], text)
    if reference_score is not None and abs(reference_score) <= 1.5:
        reference_score = reference_score * 100.0
    credit_label = str(_nested_get(packet, ["credit_proxy_label", "credit_proxy_label_kr"]) or "")
    original_signal, original_label = _original_view_signal(packet)

    components: dict[str, float] = {}
    components["dcf_upside"] = _ratio_score(upside, good=25.0, bad=-25.0)
    components["scorecard"] = _score100_to_signal(valuation_score, neutral=60.0, scale=35.0)
    # P/S is better when target is lower than comparable peer median. psr_gap is already target/median - 1.
    if psr_gap is not None:
        components["peer_psr"] = _ratio_score(psr_gap, good=-35.0, bad=25.0, higher_is_better=False)
    elif target_psr is not None and peer_median_psr:
        gap = (target_psr / max(peer_median_psr, 1e-9) - 1.0) * 100.0
        components["peer_psr"] = _ratio_score(gap, good=-35.0, bad=25.0, higher_is_better=False)
        psr_gap = gap
    else:
        components["peer_psr"] = 0.0
    components["reference_universe"] = _score100_to_signal(reference_score, neutral=55.0, scale=35.0)
    components["original_agent_view_reference"] = original_signal

    if validation_status and validation_status not in {"PASS", "OK", "PASS_WITH_WARNINGS"}:
        components["validation_penalty"] = -0.60
    else:
        components["validation_penalty"] = 0.0
    if credit_label and "RISK" in credit_label.upper() and "LOW" not in credit_label.upper():
        components["credit_risk_overlay"] = -1.0
    else:
        components["credit_risk_overlay"] = 0.0

    signal, component_weights, component_dma_model = _component_dma_signal("valuation", components)

    basis = []
    if upside is not None:
        basis.append(f"DCF 괴리율 {upside:.2f}%")
    if valuation_score is not None:
        basis.append(f"Valuation scorecard {valuation_score:.2f}/100")
    if target_psr is not None:
        basis.append(f"P/S {target_psr:.2f}배")
    if peer_median_psr is not None:
        basis.append(f"peer median P/S {peer_median_psr:.2f}배")
    if psr_gap is not None:
        basis.append(f"peer P/S gap {psr_gap:.2f}%")
    if reference_score is not None:
        basis.append(f"reference universe score {reference_score:.2f}/100")
    if wacc is not None:
        basis.append(f"WACC {wacc:.2f}%")
    if validation_status:
        basis.append(f"validation_status={validation_status}")
    if original_label:
        basis.append(f"기존 Valuation Agent 내부 판단 참고={original_label}")
    return {
        "signal": round(_clamp(signal), 4),
        "basis": basis,
        "components": components,
        "component_weights": component_weights,
        "component_dma_model": component_dma_model,
    }


def _issue_signal(packet: dict[str, Any]) -> dict[str, Any]:
    text = _json_text(packet).lower()
    positive = sum(text.count(term.lower()) for term in POSITIVE_TERMS)
    negative = sum(text.count(term.lower()) for term in NEGATIVE_TERMS)
    total = max(1, positive + negative)
    signal = _clamp((positive - negative) / total)
    if "확인 제한" in text or "뉴스 0" in text:
        signal = min(signal, 0.0)
    return {
        "signal": round(signal, 4),
        "basis": [f"긍정 키워드 {positive}회", f"부정/리스크 키워드 {negative}회"],
        "components": {"positive_terms": positive, "negative_terms": negative},
    }


def _macro_signal(packet: dict[str, Any]) -> dict[str, Any]:
    """Return a continuous macro signal without binary label cutoffs.

    Earlier history replay packets often contained a categorical macro view such
    as SELL/HOLD.  Mapping that label directly to -1/0 made macro_signal nearly
    binary.  In history mode, prefer the continuous robust-z macro signal that is
    computed from macro_월별/macro_일별 CSV rows.  The categorical packet label is
    ignored for macro when this continuous source exists; it can still be used as
    a fallback for old packets that do not have official macro rows.
    """
    text = _json_text(packet).lower()
    continuous = _metric(
        packet,
        [
            "macro_history_continuous_signal",
            "macro_continuous_signal",
            "macro_robust_z_signal",
            "history_macro_continuous_signal",
        ],
        text,
    )
    score = _metric(packet, ["macro_environment_score", "macro_score", "score"], text)
    raw_signal = str(_nested_get(packet, ["signal", "decision", "recommendation"]) or "").upper()

    basis: list[str] = []
    components: dict[str, Any] = {}
    ignore_packet_label = False

    if continuous is not None:
        signal = _clamp(float(continuous))
        basis.append(f"macro continuous robust-z signal {signal:.4f}")
        method = _nested_get(packet, ["macro_history_continuous_signal_method"])
        source_file = _nested_get(packet, ["macro_history_continuous_signal_source_file"])
        matched_date = _nested_get(packet, ["macro_history_continuous_signal_matched_date"])
        factor_count = _nested_get(packet, ["macro_history_continuous_signal_factor_count"])
        group_signals = _nested_get(packet, ["macro_history_continuous_signal_group_signals"])
        if method:
            basis.append(f"method={method}")
        if source_file:
            basis.append(f"source={source_file}")
        if matched_date:
            basis.append(f"matched_date={matched_date}")
        if factor_count:
            basis.append(f"factor_count={factor_count}")
        components = {
            "macro_history_continuous_signal": signal,
            "method": method or "continuous_macro_robust_z_by_factor_group_v9",
            "source_file": source_file or "",
            "matched_date": matched_date or "",
            "factor_count": factor_count or 0,
            "group_signals": group_signals or {},
        }
        ignore_packet_label = True
    elif score is not None and 0 <= score <= 100:
        # Convert a 0-100 macro score to a continuous diagnostic signal only.
        # This is a score normalization fallback, not a buy/hold/sell threshold.
        signal = _clamp((float(score) - 55.0) / 40.0)
        basis.append(f"macro_score {score:.2f}/100")
        components = {"macro_score_signal": signal}
        ignore_packet_label = True
    else:
        # Final fallback for old packets without macro CSV rows.  Keep it
        # continuous by keyword balance; use categorical packet label only when
        # no objective macro data or score is available.
        positive = sum(text.count(term.lower()) for term in ["완화", "금리 인하", "수요 증가", "공급 안정", "성장"])
        negative = sum(text.count(term.lower()) for term in ["긴축", "금리 상승", "환율", "침체", "공급 차질", "가격 급등", "불확실"])
        if positive + negative > 0:
            signal = (positive - negative) / max(1, positive + negative)
            components = {"positive_terms": positive, "negative_terms": negative}
        elif raw_signal in {"BUY", "매수"}:
            signal = 1.0
            components = {"legacy_raw_macro_label_signal": signal}
        elif raw_signal in {"SELL", "매도"}:
            signal = -1.0
            components = {"legacy_raw_macro_label_signal": signal}
        elif raw_signal in {"HOLD", "보유"}:
            signal = 0.0
            components = {"legacy_raw_macro_label_signal": signal}
        else:
            signal = 0.0
            components = {"macro_signal": signal}

    signal = _clamp(signal)
    if raw_signal:
        basis.append(f"raw_macro_label_seen_but_not_primary={raw_signal}")
    return {
        "signal": round(signal, 4),
        "basis": basis,
        "components": components,
        "ignore_packet_categorical_label": ignore_packet_label,
    }


def compute_agent_decision(agent: str, packet: dict[str, Any]) -> dict[str, Any]:
    agent = str(agent or packet.get("agent") or packet.get("agent_name") or "unknown").lower().replace("_agent", "")
    if agent == "finance":
        result = _finance_signal(packet)
    elif agent == "market":
        result = _market_signal(packet)
    elif agent == "tech":
        result = _tech_signal(packet)
    elif agent == "valuation":
        result = _valuation_signal(packet)
    elif agent == "issue":
        result = _issue_signal(packet)
    elif agent == "macro":
        result = _macro_signal(packet)
    else:
        result = {"signal": 0.0, "basis": ["unknown agent"], "components": {}}

    raw_signal = result.get("signal")
    if raw_signal is None or (float(raw_signal or 0.0) == 0.0 and packet.get("auditor_signal") is not None):
        raw_signal = packet.get("auditor_signal")
    signal = _clamp(float(raw_signal or 0.0))

    explicit_label = _extract_packet_label(packet)
    original_signal, original_label = _original_view_signal(packet)
    if agent == "macro" and result.get("ignore_packet_categorical_label"):
        # Macro categorical labels in old packets are often generated from coarse
        # risk-off rules and caused -1/0 binary behavior.  When an objective
        # continuous macro CSV signal exists, keep macro as a continuous signal
        # contributor and let DMA history/kernel calibration use macro_signal;
        # do not force a current buy/hold/sell label from the old packet.
        explicit_label = None
        original_label = None
    label = explicit_label or original_label or _signal_to_label(signal)
    if explicit_label:
        label_source = "explicit_packet_label"
    elif original_label:
        label_source = "original_agent_view"
    else:
        label_source = "signal_direction_no_fixed_band"
    if agent == "macro" and result.get("ignore_packet_categorical_label"):
        label_source = "macro_continuous_signal_no_categorical_cutoff"
    basis = list(result.get("basis") or result.get("reasons") or [])
    if label_source == "signal_direction_no_fixed_band":
        basis.append("명시적 매수/보유/매도 label이 없어 continuous signal의 방향을 사용함: ±0.25 같은 고정 중립 구간은 사용하지 않음")
    return {
        "agent": agent,
        "agent_ko": AGENT_KO.get(agent, agent),
        "signal": round(signal, 4),
        "auditor_signal": round(signal, 4),
        "original_recommendation": original_label or explicit_label or "",
        "recommendation_label_source": label_source,
        "auditor_recommendation": label,
        "recommendation": label,
        "basis": basis,
        "components": result.get("components") or {},
        "component_weights": result.get("component_weights") or {},
        "component_dma_model": result.get("component_dma_model") or {},
    }

def compute_portfolio_decision(agent_packets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Create the Chair-facing quantitative decision without changing specialist agents.

    Dynamic weighting policy
    ------------------------
    Fixed preset agent weights are not used.

    Each specialist agent is treated as one candidate model.  The initial prior
    is equal across the agents that actually produced packets, and the posterior
    weight is updated with Dynamic Model Averaging (DMA):

        pi_pred_i = pi_prev_i^alpha / sum_j(pi_prev_j^alpha)
        pi_post_i = pi_pred_i * L_i / sum_j(pi_pred_j * L_j)

    L_i is the predictive likelihood of the agent's past signal against the
    realized target when a local history CSV is available.  If no realized
    history is available, the system keeps the equal prior instead of inventing
    subjective agent ranges.

    Reference: Raftery et al. (2010); Catania & Nonejad (2018), eDMA.
    """

    available = {a: p for a, p in agent_packets.items() if isinstance(p, dict)}
    if not available:
        return {
            "method": "auditor_stage3_dma_no_available_packets",
            "weighted_signal": 0.0,
            "base_recommendation": "보유",
            "final_recommendation": "보유",
            "adjustment_reasons": ["사용 가능한 에이전트 packet이 없어 보유로 처리"],
            "weights_adjusted": {},
            "agent_decisions": {},
        }

    # Step 1: Compute each agent's deterministic signal from its existing packet.
    agent_decisions: dict[str, Any] = {}
    current_signals: dict[str, float] = {}
    for agent in AGENT_ORDER:
        packet = available.get(agent)
        if packet is None:
            continue
        dec = compute_agent_decision(agent, packet)
        agent_decisions[agent] = dec
        current_signals[agent] = float(dec.get("signal", 0.0) or 0.0)

    # Step 2: DMA posterior weights.  This function reads realized historical
    # signal/performance CSVs when available; otherwise it returns the equal
    # prior over available agents.
    dma_result = compute_dma_weights(available, signals=current_signals)
    weights = {
        agent: float(weight)
        for agent, weight in (dma_result.get("weights_adjusted") or dma_result.get("weights") or {}).items()
        if agent in agent_decisions
    }
    if not weights:
        weights = {a: 1.0 / len(agent_decisions) for a in agent_decisions}

    total_weight = sum(weights.values()) or 1.0
    weights = {a: w / total_weight for a, w in weights.items()}

    # Step 3: Weighted signal.
    weighted_signal = 0.0
    for agent, dec in agent_decisions.items():
        weight = float(weights.get(agent, 0.0))
        dec["weight"] = round(weight, 6)
        dec["dma_weight"] = round(weight, 6)
        dec["weight_range_95"] = (dma_result.get("weight_ranges_95") or {}).get(agent)
        dec["weighted_contribution"] = round(float(dec.get("signal", 0.0) or 0.0) * weight, 6)
        weighted_signal += float(dec.get("signal", 0.0) or 0.0) * weight

    # Step 4: DMA current-label posterior.
    #
    # No final buy/hold/sell label is created from arbitrary weighted_signal
    # thresholds.  Following the DMA logic, current agent categorical forecasts
    # are combined by posterior model weights:
    #     P_current(y=c|F_t)=sum_i pi_i,t * I(label_i,t=c)
    # Realized-history CSVs are retained only as calibration diagnostics and do
    # not override the current-label posterior final label.
    label_posterior_model = compute_dma_label_posterior(agent_decisions, weights)
    base = str(label_posterior_model.get("final_recommendation") or "보유")
    final = base
    adjustment_reasons: list[str] = [
        "Final recommendation uses DMA-weighted signal/label posterior; Hold is reject/no-trade, not a fixed weighted_signal band",
        "weighted_signal is retained only as a continuous direction/diagnostic value",
        "realized history is retained as calibration diagnostics and does not override the current-label posterior final label",
    ]
    if not label_posterior_model.get("history_used"):
        adjustment_reasons.append(
            "No realized target history was available; current-label posterior used DMA-weighted current agent labels"
        )

    # Step 5: Extract core pillar signals for diagnostics only.
    finance_signal = float(agent_decisions.get("finance", {}).get("signal", 0.0) or 0.0)
    valuation_signal = float(agent_decisions.get("valuation", {}).get("signal", 0.0) or 0.0)
    tech_signal = float(agent_decisions.get("tech", {}).get("signal", 0.0) or 0.0)
    market_signal = float(agent_decisions.get("market", {}).get("signal", 0.0) or 0.0)
    macro_signal = float(agent_decisions.get("macro", {}).get("signal", 0.0) or 0.0)
    issue_signal = float(agent_decisions.get("issue", {}).get("signal", 0.0) or 0.0)

    core_signals = {
        "finance": finance_signal,
        "valuation": valuation_signal,
        "tech": tech_signal,
    }
    core_positive_count = sum(1 for v in core_signals.values() if v > 0.0)
    core_negative_count = sum(1 for v in core_signals.values() if v < 0.0)

    return {
        "method": "auditor_stage3_dma_signal_soft_posterior_reject_option_v50",
        "weight_policy_base": "removed: no fixed finance/tech/valuation/macro/market/issue base weights",
        "weight_rationale": {
            "policy": "각 전문 에이전트를 후보 모델로 보고 DMA posterior probability로 가중치를 계산",
            "prior": "현재 packet이 있는 에이전트에 균등 prior 부여",
            "likelihood": "로컬 history CSV가 있으면 과거 signal과 realized target의 predictive likelihood로 갱신",
            "fallback": "실현 성과 history가 없으면 임의 가중치·임의 범위를 만들지 않고 균등 prior 유지",
        },
        "dma_model": dma_result,
        "weights_adjusted": {a: round(float(w), 6) for a, w in weights.items()},
        "weight_ranges_95": dma_result.get("weight_ranges_95", {}),
        "agent_decisions": agent_decisions,
        "weighted_signal": round(_clamp(weighted_signal), 4),
        "base_recommendation": base,
        "final_recommendation": final,
        "adjustment_reasons": adjustment_reasons,
        "decision_rule": {
            "type": "dma_current_label_posterior",
            "formula": "P_current(y=c|F_t)=sum_i pi_i,t * I(label_i,t=c)",
            "note": "No arbitrary weighted_signal buy/hold/sell cutoff is applied; realized history is calibration diagnostic only",
        },
        "label_posterior_model": label_posterior_model,
        "core_pillar_summary": {
            "finance_signal": round(finance_signal, 4),
            "valuation_signal": round(valuation_signal, 4),
            "tech_signal": round(tech_signal, 4),
            "market_signal": round(market_signal, 4),
            "macro_signal": round(macro_signal, 4),
            "issue_signal": round(issue_signal, 4),
            "core_positive_count": core_positive_count,
            "core_negative_count": core_negative_count,
        },
    }