from __future__ import annotations

CANONICAL_SECTION_ORDER = [
    "대표 기술",
    "핵심 제품/서비스",
    "고객 구매 이유",
    "경쟁 우위/대체가능성",
    "활용 및 확장 산업",
    "진입 부담/장벽",
    "R&D 강도",
]

SECTION_FIELD_GUIDE = {
    "대표 기술": [
        "핵심 기술 키워드",
        "적용 방식",
        "핵심 성능 요소",
    ],
    "핵심 제품/서비스": [
        "제품명/서비스명",
        "적용 기술",
        "주요 고객군",
    ],
    "고객 구매 이유": [
        "고객 효익",
        "경쟁 제품 대비 장점",
        "실제 적용 사례",
    ],
    "경쟁 우위/대체가능성": [
        "등록 특허",
        "제조 노하우",
        "고객사 레퍼런스",
    ],
    "활용 및 확장 산업": [
        "현재 고객 산업",
        "기술 범용성",
        "타산업 적용 가능성",
    ],
    "진입 부담/장벽": [
        "인증 종류",
        "개발 기간",
        "추가 검증 필요 여부",
    ],
    "R&D 강도": [
        "연구개발비",
        "연구인력",
        "CAPEX",
    ],
}

SECTION_ALIAS = {
    "대표기술": "대표 기술",
    "핵심 기술": "대표 기술",
    "기술 개요": "대표 기술",
    "핵심 제품": "핵심 제품/서비스",
    "핵심 제품 서비스": "핵심 제품/서비스",
    "제품/서비스": "핵심 제품/서비스",
    "제품 서비스": "핵심 제품/서비스",
    "구매 이유": "고객 구매 이유",
    "고객구매이유": "고객 구매 이유",
    "경쟁 우위": "경쟁 우위/대체가능성",
    "경쟁우위": "경쟁 우위/대체가능성",
    "대체 가능성": "경쟁 우위/대체가능성",
    "경쟁 우위 요소": "경쟁 우위/대체가능성",
    "활용 및 확장": "활용 및 확장 산업",
    "활용 산업": "활용 및 확장 산업",
    "확장 산업": "활용 및 확장 산업",
    "현재 활용 산업 + 확장 산업": "활용 및 확장 산업",
    "진입 부담": "진입 부담/장벽",
    "진입 장벽": "진입 부담/장벽",
    "진입부담/장벽": "진입 부담/장벽",
    "r&d": "R&D 강도",
    "연구개발": "R&D 강도",
    "연구개발 강도": "R&D 강도",
    "투자 지속성": "R&D 강도",
}

AXIS_SECTION_MAP = {
    "기술성": "대표 기술",
    "수익성 기여": "핵심 제품/서비스",
    "고객 채택도": "고객 구매 이유",
    "진입장벽": "경쟁 우위/대체가능성",
    "확장성": "활용 및 확장 산업",
    "양산성": "진입 부담/장벽",
    "투자 지속성": "R&D 강도",
}

SECTION_AXIS_MAP = {v: k for k, v in AXIS_SECTION_MAP.items()}


def normalize_section_name(name: str) -> str:
    raw = (name or "").strip()
    if not raw:
        return ""

    compact = raw.replace(" ", "")
    if raw in SECTION_ALIAS:
        return SECTION_ALIAS[raw]
    if compact in SECTION_ALIAS:
        return SECTION_ALIAS[compact]

    for canonical in CANONICAL_SECTION_ORDER:
        if raw == canonical:
            return canonical
        if compact == canonical.replace(" ", ""):
            return canonical

    return ""


def empty_section(section_name: str) -> dict:
    return {
        "category": section_name,
        "result": "공개 자료 기준 직접 확인이 제한되어 보수적으로 정리함.",
        "items": [],
        "evidence": [],
        "quant_points": [],
        "source_types": [],
    }