from __future__ import annotations

import re

from .utils import clean_text
from .workbook_schema import (
    AXIS_SECTION_MAP,
    CANONICAL_SECTION_ORDER,
    SECTION_AXIS_MAP,
    empty_section,
)


_NUMBER_RE = re.compile(r"\b\d+(?:[\.,]\d+)?\b")

_DIRECT_VALUE_TERMS = [
    "양산", "납품", "수주", "공급", "고객사", "고객", "채택", "승인", "인증",
    "매출", "수익성", "영업이익", "FCF", "현금흐름", "특허", "qualification",
]
_LIMITATION_TERMS = ["확인 제한", "근거 부족", "미확인", "검증 제한", "추정", "불확실", "보수적으로"]


def _section_text(section: dict) -> str:
    parts: list[str] = [clean_text(section.get("result", ""))]
    for item in section.get("items", []) or []:
        if isinstance(item, dict):
            parts.append(clean_text(item.get("name", "")))
            parts.append(clean_text(item.get("value", "")))
            for ev in item.get("evidence", []) or []:
                parts.append(clean_text(ev))
        else:
            parts.append(clean_text(item))
    for key in ("evidence", "quant_points", "source_types"):
        for v in section.get(key, []) or []:
            parts.append(clean_text(v))
    return "\n".join(p for p in parts if p)


def _count_quant_signals(section: dict) -> int:
    count = 0

    result = clean_text(section.get("result", ""))
    count += len(_NUMBER_RE.findall(result))

    for item in section.get("items", []) or []:
        text = clean_text(item.get("value", ""))
        count += len(_NUMBER_RE.findall(text))
        for ev in item.get("evidence", []) or []:
            count += len(_NUMBER_RE.findall(clean_text(ev)))

    return count


def _count_evidence_signals(section: dict) -> int:
    count = 0

    result = clean_text(section.get("result", ""))
    if result and "확인 제한" not in result and "보수적으로 정리" not in result:
        count += 1

    for item in section.get("items", []) or []:
        if clean_text(item.get("name", "")) and clean_text(item.get("value", "")):
            count += 1
        if item.get("evidence"):
            count += len([x for x in item.get("evidence", []) if clean_text(x)])

    count += len(section.get("evidence", []) or [])
    count += len(section.get("source_types", []) or [])

    return count


def _conservative_score(section: dict) -> tuple[int, str]:
    quant_count = _count_quant_signals(section)
    evidence_count = _count_evidence_signals(section)
    item_count = len(section.get("items", []) or [])
    result = clean_text(section.get("result", ""))
    section_text = _section_text(section)
    source_types = [clean_text(x).lower() for x in section.get("source_types", []) or []]
    direct_hits = [term for term in _DIRECT_VALUE_TERMS if term.lower() in section_text.lower()]
    limitation_hits = [term for term in _LIMITATION_TERMS if term in section_text]
    has_external_source = any(st not in {"seed", "company_yaml_seed"} for st in source_types)

    # 기본 보수 로직
    if not item_count and ("확인 제한" in result or "보수적으로 정리" in result):
        return 1, "공개 자료상 근거 부족으로 보수 점수 부여"

    score = 0
    reasons = []

    if result:
        score += 1
        reasons.append("결과 문장 존재")
    if item_count >= 2:
        score += 1
        reasons.append("핵심 항목 2개 이상 정리")
    if evidence_count >= 2:
        score += 1
        reasons.append("근거 표현 2건 이상")
    if quant_count >= 1:
        score += 1
        reasons.append("정량 신호 1건 이상")
    if quant_count >= 3 or evidence_count >= 5:
        score += 1
        reasons.append("정량/근거 신호 충분")

    score = max(1, min(score, 5))

    # v6: Tech-to-Value 관점 보정. 고객채택/양산/매출전환 근거가 없으면 고점 남발 방지.
    if not direct_hits and score > 3:
        score = 3
        reasons.append("고객채택·양산·매출전환 직접 신호 부족으로 상한 3")
    if limitation_hits and score > 3:
        score = 3
        reasons.append("확인 제한 표현 포함으로 상한 보정")
    if not has_external_source and score > 3:
        score = 3
        reasons.append("company.yaml 중심 근거이므로 외부 원문 확인 전 상한 3")
    if len(direct_hits) >= 3 and has_external_source and evidence_count >= 5 and score < 4:
        score = 4
        reasons.append("사업화/양산/고객 관련 직접 신호와 외부 근거 존재")

    reason = ", ".join(reasons) if reasons else "보수 점수 부여"
    return score, reason


def score_report(company: dict, categories: list[dict]) -> dict:
    section_map = {clean_text(c.get("category", "")): c for c in categories or []}

    details = []
    axes = []
    total = 0

    for section_name in CANONICAL_SECTION_ORDER:
        section = section_map.get(section_name) or empty_section(section_name)
        axis_name = SECTION_AXIS_MAP[section_name]

        score, reason = _conservative_score(section)
        quant_count = _count_quant_signals(section)
        evidence_count = _count_evidence_signals(section)

        total += score

        details.append(
            {
                "section": section_name,
                "axis": axis_name,
                "score": score,
                "reason": reason,
                "quant_count": quant_count,
                "evidence_count": evidence_count,
            }
        )

        axes.append(
            {
                "axis": axis_name,
                "name": axis_name,
                "section": section_name,
                "score": score,
                "reason": reason,
                "quant_count": quant_count,
                "evidence_count": evidence_count,
            }
        )

    strengths = [d["axis"] for d in details if d["score"] >= 4]
    weaknesses = [d["axis"] for d in details if d["score"] <= 2]

    if total >= 28:
        judgment = "기술 선도형"
    elif total >= 21:
        judgment = "기술 경쟁형"
    elif total >= 14:
        judgment = "기술 검토형"
    else:
        judgment = "보수 검토형"

    return {
        "company_name": clean_text(company.get("corp_name", "")),
        "axes": axes,
        "details": details,
        "total_score": total,
        "max_score": 35,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "judgment": judgment,
        "report_quality": "conservative",
    }