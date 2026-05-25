from __future__ import annotations

import re
from typing import Iterable

from .utils import clean_text, trim


CATEGORY_ORDER = [
    "대표 기술",
    "핵심 제품/서비스",
    "고객 구매 이유",
    "경쟁 우위/대체가능성",
    "활용 및 확장 산업",
    "진입 부담/장벽",
    "R&D 강도",
]

CANONICAL_ITEM_MAP = {
    "대표 기술": ["핵심 기술 키워드", "적용 방식", "핵심 성능 요소"],
    "핵심 제품/서비스": ["제품명/서비스명", "적용 기술", "주요 고객군"],
    "고객 구매 이유": ["고객 효익", "경쟁 제품 대비 장점", "실제 적용 사례"],
    "경쟁 우위/대체가능성": ["등록 특허", "제조 노하우", "고객사 레퍼런스"],
    "활용 및 확장 산업": ["현재 고객 산업", "기술 범용성", "타산업 적용 가능성"],
    "진입 부담/장벽": ["인증 종류", "개발 기간", "추가 검증 필요 여부"],
    "R&D 강도": ["연구개발비", "연구인력", "CAPEX"],
}

RESULT_ENDINGS = {
    "대표 기술": "관련 기술은 사업보고서와 공식 자료에서 확인됩니다.",
    "핵심 제품/서비스": "해당 제품은 전체 사업 포트폴리오에서 핵심 축을 형성합니다.",
    "고객 구매 이유": "고객 효익은 공개 자료 범위 내에서 보수적으로 해석했습니다.",
    "경쟁 우위/대체가능성": "기술 및 고객 승인 구조를 고려할 때 대체 가능성은 보수적으로 평가했습니다.",
    "활용 및 확장 산업": "현재 산업 적용 범위와 확장 가능성은 공개 자료 기준으로 정리했습니다.",
    "진입 부담/장벽": "진입 장벽 수준은 인증·검증·고객 승인 부담을 중심으로 판단했습니다.",
    "R&D 강도": "R&D 강도는 공개 자료에서 확인 가능한 투자 단서를 기준으로 요약했습니다.",
}


def normalize_category_pack(category_pack: dict, *, company_name: str = "") -> dict:
    category = clean_text(category_pack.get("category", ""))
    item_map = category_pack.get("item_map", {}) or {}
    quant_block = category_pack.get("quant_block", {}) or {}
    quant_lines = quant_block.get("quant_summary", []) or []
    evidence_pool = quant_block.get("evidence_pool", []) or []

    normalized_items = _normalize_items(category, item_map, quant_lines, evidence_pool)
    result_text = _normalize_result_text(
        company_name=company_name,
        category=category,
        items=normalized_items,
        raw_result=category_pack.get("result_text", ""),
        quant_lines=quant_lines,
    )

    category_pack["item_map"] = normalized_items
    category_pack["result_text"] = result_text
    category_pack["evidence_pool"] = evidence_pool[:8]
    return category_pack


def normalize_full_report(report: dict, *, company_name: str = "") -> dict:
    sections = report.get("sections", []) or []
    normalized_sections = []

    for section in sections:
        normalized_sections.append(normalize_category_pack(section, company_name=company_name))

    normalized_sections.sort(
        key=lambda x: CATEGORY_ORDER.index(x.get("category")) if x.get("category") in CATEGORY_ORDER else 999
    )

    report["sections"] = normalized_sections
    return report


def _normalize_items(category: str, item_map: dict, quant_lines: list[str], evidence_pool: list[str]) -> dict:
    canonical_items = CANONICAL_ITEM_MAP.get(category, [])
    normalized: dict = {}

    for item in canonical_items:
        row = item_map.get(item, {}) if isinstance(item_map, dict) else {}
        value = clean_text(row.get("value", "") if isinstance(row, dict) else "")
        evidence = row.get("evidence", []) if isinstance(row, dict) else []

        if not value:
            value = _fallback_value(category, item, quant_lines, evidence_pool)

        normalized[item] = {
            "value": trim(value, 280),
            "evidence": _normalize_evidence(evidence or evidence_pool[:2]),
        }

    return normalized


def _fallback_value(category: str, item: str, quant_lines: list[str], evidence_pool: list[str]) -> str:
    quant_text = " / ".join(clean_text(x) for x in quant_lines[:3] if clean_text(x))
    ev_text = clean_text(evidence_pool[0]) if evidence_pool else ""

    if item == "핵심 기술 키워드":
        if quant_text:
            return quant_text
        return "공개 자료 기준 핵심 기술 키워드는 확인되나, 수치형 요약은 제한적입니다."
    if item == "적용 방식":
        return ev_text or "공개 자료 기준 적용 공정·방식은 보수적으로 정리했습니다."
    if item == "핵심 성능 요소":
        return quant_text or ev_text or "핵심 성능 요소는 수치 근거가 제한적입니다."
    if item == "제품명/서비스명":
        return ev_text or "공식 자료 기준 제품·서비스명을 정리했습니다."
    if item == "적용 기술":
        return quant_text or ev_text or "적용 기술은 공개 자료 기준으로 요약했습니다."
    if item == "주요 고객군":
        return "주요 고객군은 사업보고서·홈페이지 등 공개 자료에서 직접 확인 가능한 범위로 정리했습니다."
    if item == "고객 효익":
        return quant_text or "고객 효익은 공개 자료 범위 내에서 보수적으로 해석했습니다."
    if item == "경쟁 제품 대비 장점":
        return quant_text or "경쟁 제품 대비 장점은 명시 근거가 제한적입니다."
    if item == "실제 적용 사례":
        return ev_text or "실제 적용 사례는 공개 자료 기준 확인 범위가 제한적입니다."
    if item == "등록 특허":
        return "등록 특허는 공개 자료에서 직접 확인되는 범위만 반영했습니다."
    if item == "제조 노하우":
        return ev_text or "제조 노하우는 장비/공정 축을 중심으로 요약했습니다."
    if item == "고객사 레퍼런스":
        return "고객사 레퍼런스는 공개 자료 범위 내에서 보수적으로 반영했습니다."
    if item == "현재 고객 산업":
        return ev_text or "현재 고객 산업은 공개 자료 기준 산업 키워드를 바탕으로 정리했습니다."
    if item == "기술 범용성":
        return quant_text or "기술 범용성은 적용 공정·산업 수를 바탕으로 판단했습니다."
    if item == "타산업 적용 가능성":
        return "타산업 적용 가능성은 공개 자료 기준 직접 확인 범위가 제한적입니다."
    if item == "인증 종류":
        return quant_text or "공개 자료에서 확인된 인증·규격 중심으로 정리했습니다."
    if item == "개발 기간":
        return quant_text or "개발 기간은 직접 수치 확인 범위가 제한적입니다."
    if item == "추가 검증 필요 여부":
        return "추가 검증 필요 여부는 고객 승인·평가 구조를 기준으로 보수적으로 판단했습니다."
    if item == "연구개발비":
        return quant_text or "연구개발비는 공개 자료에서 직접 확인 가능한 범위가 제한적입니다."
    if item == "연구인력":
        return quant_text or "연구인력은 공개 자료에서 직접 확인 가능한 범위가 제한적입니다."
    if item == "CAPEX":
        return quant_text or "CAPEX는 공개 자료에서 직접 확인 가능한 범위가 제한적입니다."

    return quant_text or ev_text or "공개 자료 기준으로 보수적으로 정리했습니다."


def _normalize_evidence(evidence: Iterable[str]) -> list[str]:
    out: list[str] = []
    for item in evidence:
        item = trim(clean_text(item), 140)
        if not item:
            continue
        if item not in out:
            out.append(item)
    return out[:3]


def _normalize_result_text(
    *,
    company_name: str,
    category: str,
    items: dict,
    raw_result: str,
    quant_lines: list[str],
) -> str:
    company_prefix = f"이 기업은 " if not company_name else f"{company_name}은 "
    clean_raw = clean_text(raw_result)

    first_item = next(iter(items.values()), {})
    first_value = clean_text(first_item.get("value", ""))

    if category == "대표 기술":
        tech = clean_text(items.get("핵심 기술 키워드", {}).get("value", ""))
        apply_ = clean_text(items.get("적용 방식", {}).get("value", ""))
        perf = clean_text(items.get("핵심 성능 요소", {}).get("value", ""))
        parts = [
            f"{company_prefix}{trim(tech, 90)} 기반 기업으로,",
            f"관련 기술은 {trim(_best_quant_phrase(quant_lines, fallback='사업보고서와 공식 자료에서 확인됩니다'), 80)}.",
            f"해당 기술은 {trim(apply_ or '적용 공정에 활용되며', 90)}",
            f"{trim(perf or '핵심 성능 요소를 중심으로 경쟁력을 형성합니다', 90)}.",
        ]
        return _join_sentence_parts(parts)

    if category == "핵심 제품/서비스":
        prod = clean_text(items.get("제품명/서비스명", {}).get("value", ""))
        tech = clean_text(items.get("적용 기술", {}).get("value", ""))
        cust = clean_text(items.get("주요 고객군", {}).get("value", ""))
        parts = [
            f"{company_prefix}{trim(prod, 100)} 등을 주력으로 하며,",
            f"적용 기술은 {trim(tech or '공개 자료 기준으로 정리됩니다', 85)}.",
            f"주요 고객군은 {trim(cust or '관련 산업 고객사 중심으로 해석했습니다', 85)}.",
        ]
        return _join_sentence_parts(parts)

    if clean_raw:
        return _polish_result(clean_raw, category)

    summary = _best_quant_phrase(quant_lines, fallback=RESULT_ENDINGS.get(category, "공개 자료 기준으로 보수적으로 정리했습니다."))
    return _polish_result(f"{company_prefix}{summary}", category)


def _best_quant_phrase(quant_lines: list[str], fallback: str) -> str:
    for line in quant_lines:
        line = clean_text(line)
        if not line:
            continue
        if re.search(r"\d", line):
            return line
    return fallback


def _join_sentence_parts(parts: list[str]) -> str:
    text = " ".join(clean_text(p) for p in parts if clean_text(p))
    text = re.sub(r"\s+", " ", text).strip()
    text = text.replace("..", ".")
    if text and text[-1] not in ".!?":
        text += "."
    return text


def _polish_result(text: str, category: str) -> str:
    text = clean_text(text)
    if not text:
        text = RESULT_ENDINGS.get(category, "공개 자료 기준으로 보수적으로 정리했습니다.")
    if text[-1] not in ".!?":
        text += "."
    return text