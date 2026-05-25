from __future__ import annotations

from typing import Dict, Any
from datetime import datetime


def make_decision(score_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    scorer.py에서 계산한 score_result를 받아서
    BUY / SELL / HOLD 최종 판단을 만든다.

    coverage_ratio가 낮을수록 confidence에 penalty를 적용한다.
    - coverage_ratio >= 0.85: penalty 없음
    - coverage_ratio >= 0.57: -0.10
    - coverage_ratio >= 0.43: -0.20
    - coverage_ratio <  0.43: -0.30
    """
    score = score_result.get("score", 0)
    reasons = score_result.get("reasons", [])
    details = dict(score_result.get("details", {}))

    llm_analysis = score_result.get("llm_analysis")
    if llm_analysis:
        details["llm_analysis"] = llm_analysis

    if score_result.get("macro_numeric_criteria"):
        details["macro_numeric_criteria"] = score_result.get("macro_numeric_criteria")

    signal = decide_signal(score)
    risk_level = decide_risk_level(score)

    # coverage_ratio 기반 confidence penalty
    coverage = score_result.get("data_coverage") or {}
    coverage_ratio = coverage.get("coverage_ratio", 1.0)
    base_confidence = calculate_confidence(score)
    confidence, coverage_penalty = apply_coverage_penalty(base_confidence, coverage_ratio)

    # coverage 정보를 details에 포함
    details["data_coverage"] = {
        "available": coverage.get("available", []),
        "missing": coverage.get("missing", []),
        "coverage_ratio": coverage_ratio,
        "coverage_penalty": coverage_penalty,
    }

    return {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "signal": signal,
        "score": score,
        "risk_level": risk_level,
        "confidence": confidence,
        "coverage_ratio": coverage_ratio,
        "summary": build_summary(signal, score, risk_level, coverage_ratio),
        "reasons": reasons,
        "details": details,
    }


def apply_coverage_penalty(base_confidence: float, coverage_ratio: float) -> tuple[float, float]:
    """coverage_ratio에 따라 confidence에 penalty를 적용한다.

    반환: (penalized_confidence, penalty_amount)

    기준:
    - coverage_ratio >= 0.85 → penalty 0.00  (6~7개 데이터: 충분)
    - coverage_ratio >= 0.57 → penalty 0.10  (4~5개 데이터: 보통)
    - coverage_ratio >= 0.43 → penalty 0.20  (3개 데이터: 부족)
    - coverage_ratio <  0.43 → penalty 0.30  (0~2개 데이터: 매우 부족)
    """
    if coverage_ratio >= 0.85:
        penalty = 0.00
    elif coverage_ratio >= 0.57:
        penalty = 0.10
    elif coverage_ratio >= 0.43:
        penalty = 0.20
    else:
        penalty = 0.30

    penalized = round(max(0.0, base_confidence - penalty), 2)
    return penalized, penalty


def decide_signal(score: int | float) -> str:
    """
    점수 기준으로 매수/매도/관망 판단
    """

    if score >= 3:
        return "BUY"
    elif score <= -3:
        return "SELL"
    else:
        return "HOLD"


def decide_risk_level(score: int | float) -> str:
    """
    점수 기준으로 시장 위험도 판단
    """

    if score <= -5:
        return "HIGH"
    elif score <= -3:
        return "MEDIUM_HIGH"
    elif score < 3:
        return "NEUTRAL"
    elif score < 5:
        return "MEDIUM_LOW"
    else:
        return "LOW"


def calculate_confidence(score: int | float) -> float:
    """
    점수 절댓값이 클수록 판단 신뢰도 증가
    최대 1.0
    """

    confidence = min(abs(score) / 6, 1.0)
    return round(confidence, 2)


def build_summary(signal: str, score: int | float, risk_level: str, coverage_ratio: float = 1.0) -> str:
    """
    리포트에 들어갈 한 줄 요약
    """
    coverage_note = (
        f" (데이터 커버리지 {int(coverage_ratio * 100)}% — 신뢰도 제한)"
        if coverage_ratio < 0.85
        else ""
    )

    if signal == "BUY":
        return f"매크로 환경 점수는 {score}점으로, 위험자산에 우호적인 환경입니다. 위험도는 {risk_level}입니다.{coverage_note}"

    if signal == "SELL":
        return f"매크로 환경 점수는 {score}점으로, 위험자산에 비우호적인 환경입니다. 위험도는 {risk_level}입니다.{coverage_note}"

    return f"매크로 환경 점수는 {score}점으로, 뚜렷한 매수/매도 우위가 없어 관망 판단입니다. 위험도는 {risk_level}입니다.{coverage_note}"