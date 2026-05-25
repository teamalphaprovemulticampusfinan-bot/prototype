from __future__ import annotations

from typing import Any

from .normalizer import latest_row
from .utils import safe_div, to_float


def _percentile(values: list[float | None], target: float | None, *, higher_is_better: bool = True) -> float | None:
    clean = sorted(float(v) for v in values if v is not None)
    if target is None or not clean:
        return None
    if higher_is_better:
        return round(sum(1 for v in clean if v <= target) / len(clean) * 100.0, 2)
    return round(sum(1 for v in clean if v >= target) / len(clean) * 100.0, 2)


def _score(value: float | None, default: float = 50.0) -> float:
    if value is None:
        return default
    return max(0.0, min(100.0, float(value)))


def _latest_target_peer(peers: list[dict[str, Any]]) -> dict[str, Any]:
    for row in peers:
        v = row.get("is_target")
        if v is True or str(v).lower() in {"true", "1", "yes"}:
            return row
    return peers[0] if peers else {}


def _reference_target(reference_universe: list[dict[str, Any]], company_dir: str | None = None, company: str | None = None) -> dict[str, Any]:
    for row in reference_universe or []:
        if company_dir and str(row.get("company_dir") or "") == str(company_dir):
            return row
        if company and str(row.get("company_name") or row.get("company") or "") == str(company):
            return row
    return {}


def _reference_cluster(reference_universe: list[dict[str, Any]], target: dict[str, Any]) -> dict[str, Any]:
    if not reference_universe:
        return {"status": "NO_REFERENCE_UNIVERSE"}
    group = target.get("peer_group") if target else None
    group_rows = [r for r in reference_universe if group and r.get("peer_group") == group]
    def avg(rows: list[dict[str, Any]], key: str) -> float | None:
        vals = [to_float(r.get(key)) for r in rows]
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None
    return {
        "status": "OK" if group else "WARN_TARGET_GROUP_UNKNOWN",
        "target_peer_group": group or "해당 없음",
        "peer_group_size": len(group_rows),
        "peer_group_avg_valuation_proxy_score": avg(group_rows, "valuation_proxy_score"),
        "peer_group_avg_credit_risk_score": avg(group_rows, "credit_risk_score"),
        "universe_rows": len(reference_universe),
    }


def _label(score: float) -> tuple[str, str]:
    if score >= 70:
        return "VALUATION_SUPPORTIVE", "가치평가 보조근거 우호"
    if score >= 50:
        return "VALUATION_NEUTRAL", "가치평가 보조근거 중립"
    return "VALUATION_CAUTION", "가치평가 보조근거 주의"


def build_ml_overlay(
    financials: list[dict[str, Any]],
    peers: list[dict[str, Any]],
    price_summary: dict[str, Any],
    *,
    peer_comps: dict[str, Any] | None = None,
    reference_universe: list[dict[str, Any]] | None = None,
    company_dir: str | None = None,
    company: str | None = None,
) -> dict[str, Any]:
    """Build explainable ML-style overlay for valuation quality.

    This is not a future-return predictor.  It is an explainable, dashboard-safe
    overlay that combines live valuation inputs with a 208-company semiconductor
    reference universe.  It is intentionally deterministic so the dashboard and
    Chair report are reproducible.
    """

    latest = latest_row(financials)
    peers = peers or []
    peer_comps = peer_comps or {}
    reference_universe = reference_universe or []
    target_peer = _latest_target_peer(peers)
    ref_target = _reference_target(reference_universe, company_dir=company_dir, company=company)

    op_margin = to_float(latest.get("op_margin"))
    roe = to_float(latest.get("roe"))
    fcf_margin = to_float(latest.get("fcf_margin"))
    debt_ratio = to_float(latest.get("debt_ratio"))
    volatility = to_float(price_summary.get("volatility_annualized"))
    mdd = to_float(price_summary.get("mdd"))
    psr = to_float(peer_comps.get("target_psr") or target_peer.get("psr"))
    peer_psr_values = [to_float(r.get("psr")) for r in peers]

    factors: list[dict[str, Any]] = []
    factors.append({"factor": "영업이익률 peer percentile", "factor_code": "operating_margin_percentile", "score": _percentile([to_float(r.get("op_margin")) for r in peers], op_margin), "direction": "높을수록 우수"})
    factors.append({"factor": "ROE peer percentile", "factor_code": "roe_percentile", "score": _percentile([to_float(r.get("roe")) for r in peers], roe), "direction": "높을수록 우수"})
    factors.append({"factor": "FCF margin peer percentile", "factor_code": "fcf_margin_percentile", "score": _percentile([to_float(r.get("fcf_margin")) for r in peers], fcf_margin), "direction": "높을수록 우수"})
    factors.append({"factor": "부채비율 안정성", "factor_code": "debt_ratio_inverse_percentile", "score": _percentile([to_float(r.get("debt_ratio")) for r in peers], debt_ratio, higher_is_better=False), "direction": "낮을수록 우수"})
    factors.append({"factor": "PSR 상대 매력도", "factor_code": "psr_inverse_percentile", "score": _percentile(peer_psr_values, psr, higher_is_better=False), "direction": "낮은 PSR일수록 상대가치 부담이 낮음"})
    factors.append({"factor": "변동성 안정성", "factor_code": "volatility_inverse_score", "score": None if volatility is None else max(0.0, min(100.0, 100.0 - volatility * 160.0)), "direction": "낮을수록 우수"})
    factors.append({"factor": "MDD 방어력", "factor_code": "mdd_resilience_score", "score": None if mdd is None else max(0.0, min(100.0, 100.0 + mdd * 140.0)), "direction": "낙폭이 작을수록 우수"})

    ref_val_score = to_float(ref_target.get("valuation_proxy_score"))
    ref_credit_risk = to_float(ref_target.get("credit_risk_score"))
    ref_val_conf = to_float(ref_target.get("valuation_confidence"))
    ref_credit_conf = to_float(ref_target.get("credit_confidence"))
    if reference_universe:
        factors.append({
            "factor": "208개 반도체 valuation proxy percentile",
            "factor_code": "reference_208_valuation_proxy_percentile",
            "score": _percentile([to_float(r.get("valuation_proxy_score")) for r in reference_universe], ref_val_score),
            "direction": "높을수록 universe 내 가치평가 proxy 우호",
        })
        factors.append({
            "factor": "208개 반도체 credit risk inverse percentile",
            "factor_code": "reference_208_credit_risk_inverse_percentile",
            "score": _percentile([to_float(r.get("credit_risk_score")) for r in reference_universe], ref_credit_risk, higher_is_better=False),
            "direction": "낮은 신용위험 proxy일수록 우수",
        })
        if ref_val_conf is not None or ref_credit_conf is not None:
            conf = ((ref_val_conf or 0.0) + (ref_credit_conf or 0.0)) / (2 if ref_val_conf is not None and ref_credit_conf is not None else 1)
            factors.append({"factor": "208개 universe confidence", "factor_code": "reference_208_confidence_score", "score": max(0.0, min(100.0, conf * 100.0)), "direction": "높을수록 보조판단 신뢰도 우수"})

    weighted: list[tuple[float, float]] = []
    weights = {
        "operating_margin_percentile": 0.14,
        "roe_percentile": 0.13,
        "fcf_margin_percentile": 0.13,
        "debt_ratio_inverse_percentile": 0.12,
        "psr_inverse_percentile": 0.16,
        "volatility_inverse_score": 0.08,
        "mdd_resilience_score": 0.08,
        "reference_208_valuation_proxy_percentile": 0.08,
        "reference_208_credit_risk_inverse_percentile": 0.05,
        "reference_208_confidence_score": 0.03,
    }
    for f in factors:
        w = weights.get(str(f.get("factor_code")), 0.05)
        weighted.append((_score(to_float(f.get("score"))), w))
    total_w = sum(w for _, w in weighted) or 1.0
    composite = sum(s * w for s, w in weighted) / total_w
    label, label_kr = _label(composite)
    cluster = _reference_cluster(reference_universe, ref_target)

    psr_gap = peer_comps.get("psr_vs_peer_median_pct") if isinstance(peer_comps, dict) else None
    return {
        "method": "deterministic_live_peer_psr_plus_208_reference_universe_overlay",
        "method_kr": "실시간 DART·주가 기반 PSR/Peer + 208개 반도체 reference universe 보조판단",
        "composite_score": round(composite, 2),
        "label": label,
        "label_kr": label_kr,
        "factors": factors,
        "kmeans_peer_cluster": cluster.get("target_peer_group") or "해당 없음",
        "reference_cluster": cluster,
        "reference_universe_summary": {
            "reference_universe_rows": len(reference_universe),
            "target_reference_row": ref_target,
            "target_peer_group": cluster.get("target_peer_group"),
            "peer_group_size": cluster.get("peer_group_size"),
        },
        "psr_overlay": {
            "target_psr": psr,
            "peer_median_psr": peer_comps.get("median_psr") if isinstance(peer_comps, dict) else None,
            "psr_vs_peer_median_pct": psr_gap,
            "psr_peer_percentile_lower_better": peer_comps.get("psr_peer_percentile_lower_better") if isinstance(peer_comps, dict) else None,
            "psr_signal_kr": peer_comps.get("psr_signal_kr") if isinstance(peer_comps, dict) else "해당 없음",
        },
        "note": "This overlay is a deterministic decision-quality helper, not a realized-return predictor.",
        "note_kr": "미래수익률 예측모델이 아니라 대시보드/Chair용 설명가능 보조 가치평가 점수입니다.",
    }
