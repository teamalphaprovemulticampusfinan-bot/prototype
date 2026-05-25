from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .utils import clean_text, trim
from .workbook_schema import CANONICAL_SECTION_ORDER, SECTION_AXIS_MAP


COMMERCIALIZATION_TERMS = [
    "양산", "납품", "수주", "공급", "고객사", "고객", "채택", "승인", "인증",
    "qualification", "qual", "shipment", "mass production", "commercial", "revenue",
    "매출", "상용화", "레퍼런스", "공동개발", "라인", "증설", "생산", "검증",
]
CUSTOMER_TERMS = ["고객사", "고객", "삼성", "SK하이닉스", "하이닉스", "LG", "TSMC", "Intel", "NVIDIA", "AMD", "납품", "공급", "레퍼런스"]
PRODUCTION_TERMS = ["양산", "생산", "라인", "가동", "수율", "공정", "설비", "증설", "CAPEX", "인증", "품질", "검증", "qualification"]
REVENUE_TERMS = ["매출", "수익", "영업이익", "원가", "마진", "FCF", "현금흐름", "수익성", "원가절감", "가동률", "ASP"]
MOAT_TERMS = ["특허", "노하우", "진입장벽", "고순도", "정밀", "난이도", "공정 안정성", "신뢰성", "고밀도", "미세", "방열", "수율"]
LIMITATION_TERMS = ["확인 제한", "근거 부족", "미확인", "검증 제한", "추정", "불확실", "제한적", "보수적으로"]


@dataclass
class BridgeSignal:
    name: str
    score: float
    hits: list[str]
    evidence: list[str]
    limitation: str = ""


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(value)))


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _text_from_categories(categories: Any) -> str:
    parts: list[str] = []
    if isinstance(categories, dict):
        rows = categories.values()
    else:
        rows = categories or []
    for row in rows:
        if not isinstance(row, dict):
            parts.append(clean_text(row))
            continue
        for key in ("category", "result", "summary"):
            if clean_text(row.get(key)):
                parts.append(clean_text(row.get(key)))
        for item in row.get("items", []) or []:
            if isinstance(item, dict):
                parts.append(clean_text(item.get("name")))
                parts.append(clean_text(item.get("value")))
                for ev in item.get("evidence", []) or []:
                    parts.append(clean_text(ev))
            else:
                parts.append(clean_text(item))
        for key in ("evidence", "quant_points", "source_types"):
            for v in row.get(key, []) or []:
                parts.append(clean_text(v))
    return "\n".join(p for p in parts if p)


def _text_from_docs(docs: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for d in docs or []:
        if not isinstance(d, dict):
            continue
        for key in ("kind", "url", "text"):
            if clean_text(d.get(key)):
                parts.append(clean_text(d.get(key)))
        meta = d.get("meta")
        if isinstance(meta, dict):
            for v in meta.values():
                if isinstance(v, str) and clean_text(v):
                    parts.append(clean_text(v))
    return "\n".join(parts)


def _hits(text: str, terms: list[str]) -> list[str]:
    low = (text or "").lower()
    out: list[str] = []
    for term in terms:
        if term.lower() in low and term not in out:
            out.append(term)
    return out


def _numeric_signal_count(text: str) -> int:
    return len(re.findall(r"\d+(?:\.\d+)?\s*(?:%|배|건|개|회|종|명|억원|백만원|천원|원|년|nm|㎚|um|μm)", text or "", flags=re.IGNORECASE))


def _source_quality(docs: list[dict[str, Any]], evidences: list[dict[str, Any]]) -> tuple[float, dict[str, Any]]:
    url_count = 0
    official_count = 0
    news_count = 0
    filing_count = 0
    for d in docs or []:
        if not isinstance(d, dict):
            continue
        url = clean_text(d.get("url"))
        kind = clean_text(d.get("kind")).lower()
        if url.startswith("http"):
            url_count += 1
        if kind in {"homepage", "official", "business_pages", "product", "ir"} or any(x in url.lower() for x in ["nepes", "hanmi", "hansol", "ltcco", "dstp"]):
            official_count += 1
        if "news" in kind or "article" in url.lower():
            news_count += 1
        if "dart" in url.lower() or "kind.krx" in url.lower() or kind in {"report", "filing", "ir"}:
            filing_count += 1
    evidence_count = len([e for e in evidences or [] if isinstance(e, dict) and clean_text(e.get("snippet") or e.get("claim"))])
    score = 35 + min(url_count, 5) * 6 + min(official_count, 3) * 7 + min(filing_count, 2) * 6 + min(news_count, 3) * 3 + min(evidence_count, 8) * 2
    return _clamp(score, 20, 95), {
        "url_count": url_count,
        "official_count": official_count,
        "filing_or_ir_count": filing_count,
        "news_count": news_count,
        "evidence_count": evidence_count,
    }


def _section_score(score_report: dict[str, Any], axis: str) -> float:
    for row in score_report.get("axes", []) or []:
        if clean_text(row.get("axis")) == axis:
            try:
                return _clamp(float(row.get("score", 0)) / 5.0 * 100.0)
            except Exception:
                return 50.0
    return 50.0


def _build_signal(name: str, text: str, terms: list[str], base: float, per_hit: float, max_score: float, evidence_label: str) -> BridgeSignal:
    found = _hits(text, terms)
    limitations = _hits(text, LIMITATION_TERMS)
    score = base + min(len(found), 8) * per_hit - min(len(limitations), 5) * 4
    evidence = []
    if found:
        evidence.append(f"{evidence_label}: {', '.join(found[:8])}")
    if limitations:
        evidence.append(f"확인 제한 신호: {', '.join(limitations[:5])}")
    return BridgeSignal(
        name=name,
        score=_clamp(score, 15, max_score),
        hits=found[:12],
        evidence=evidence,
        limitation="; ".join(limitations[:5]) if limitations else "",
    )


def _grade(score: float) -> str:
    if score >= 80:
        return "STRONG_TECH_VALUE_LINK"
    if score >= 65:
        return "COMMERCIALIZATION_WATCH"
    if score >= 50:
        return "TECH_FINANCE_GAP"
    return "EVIDENCE_WEAK_OR_EARLY_STAGE"


def _opinion_from_bridge(tech_total: int, bridge_score: float) -> str:
    if bridge_score >= 72 and tech_total >= 26:
        return "매수"
    if bridge_score < 42 or tech_total < 14:
        return "매도"
    return "보유"


def build_bridge_payload(
    *,
    company: dict[str, Any],
    docs: list[dict[str, Any]],
    categories: Any,
    score_report: dict[str, Any],
    evidences: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a structured Tech-to-Value input packet for Auditor/Chair.

    This does not replace Finance/Market/Auditor.  It makes the Tech Agent's
    output more useful by separating four questions:
    1) Is the technology differentiated?
    2) Is it commercially adopted or still only a keyword?
    3) Is there evidence that it can convert to revenue/cash flow?
    4) Are the claims grounded enough for Chair to trust?
    """
    company_name = clean_text(company.get("corp_name") or company.get("name") or "기업")
    text = "\n".join([
        clean_text(company_name),
        clean_text(company.get("notes")),
        "\n".join(clean_text(x) for key in ("keywords", "core_keywords", "products", "tech_keywords") for x in _as_list(company.get(key))),
        _text_from_categories(categories),
        _text_from_docs(docs),
        "\n".join(clean_text(e.get("snippet") or e.get("claim") or e.get("rationale")) for e in evidences if isinstance(e, dict)),
    ])

    tech_strength = (
        0.35 * _section_score(score_report, "기술성")
        + 0.20 * _section_score(score_report, "진입장벽")
        + 0.15 * _section_score(score_report, "확장성")
        + 0.15 * _section_score(score_report, "투자 지속성")
        + 0.15 * _section_score(score_report, "양산성")
    )
    tech_signal = BridgeSignal(
        name="technology_strength_score",
        score=_clamp(tech_strength, 20, 95),
        hits=_hits(text, MOAT_TERMS + PRODUCTION_TERMS),
        evidence=[f"7축 기술점수 기반 환산: {round(tech_strength, 2)}"],
    )

    commercialization = _build_signal(
        "commercialization_evidence_score", text, COMMERCIALIZATION_TERMS, 35, 6.0, 90,
        "사업화/고객채택 키워드"
    )
    customer = _build_signal(
        "customer_adoption_evidence_score", text, CUSTOMER_TERMS, 30, 7.0, 90,
        "고객 채택/레퍼런스 키워드"
    )
    production = _build_signal(
        "production_readiness_score", text, PRODUCTION_TERMS, 35, 5.5, 90,
        "양산/품질/공정 키워드"
    )
    revenue = _build_signal(
        "revenue_cashflow_linkage_score", text, REVENUE_TERMS, 25, 6.0, 85,
        "매출/수익성/현금흐름 연결 키워드"
    )
    moat = _build_signal(
        "moat_ip_score", text, MOAT_TERMS, 35, 5.5, 90,
        "진입장벽/IP/공정난이도 키워드"
    )
    evidence_quality, source_debug = _source_quality(docs, evidences)
    numeric_count = _numeric_signal_count(text)
    numeric_score = _clamp(35 + min(numeric_count, 10) * 4.0, 25, 85)

    raw_score = (
        0.22 * tech_signal.score
        + 0.20 * commercialization.score
        + 0.15 * customer.score
        + 0.15 * production.score
        + 0.12 * revenue.score
        + 0.08 * moat.score
        + 0.08 * evidence_quality
    )
    adjusted = raw_score
    guardrails: list[str] = []

    if commercialization.score < 45:
        adjusted = min(adjusted, 59.0)
        guardrails.append("사업화 근거 부족: 고객사·납품·양산·공급 관련 직접 근거가 약해 상한 59 적용")
    if customer.score < 42 and production.score < 48:
        adjusted = min(adjusted, 54.0)
        guardrails.append("고객채택과 양산근거 동시 부족: 기술 키워드만으로 가치평가 가산 금지")
    if revenue.score < 40:
        adjusted = min(adjusted, 64.0)
        guardrails.append("매출·수익성·FCF 연결 근거 부족: Tech-to-Value 상한 64 적용")
    if evidence_quality < 50:
        adjusted = min(adjusted, 58.0)
        guardrails.append("원문 링크·근거 품질 부족: 추가 원문 검증 필요")

    score = round(_clamp(adjusted), 2)
    grade = _grade(score)
    tech_total = int(score_report.get("total_score") or score_report.get("total") or 0)
    opinion_bridge = _opinion_from_bridge(tech_total, score)

    if grade == "STRONG_TECH_VALUE_LINK":
        interpretation = f"{company_name}은 기술 차별성, 사업화 근거, 수익성 연결 가능성이 비교적 균형적으로 확인되는 구간입니다."
    elif grade == "COMMERCIALIZATION_WATCH":
        interpretation = f"{company_name}은 기술력은 확인되지만 고객사 채택·양산·매출 전환의 추가 검증이 필요한 구간입니다."
    elif grade == "TECH_FINANCE_GAP":
        interpretation = f"{company_name}은 기술 키워드와 잠재력은 있으나, 기술 우위가 매출·FCF·가치평가로 이어진다는 근거가 아직 충분하지 않은 구간입니다."
    else:
        interpretation = f"{company_name}은 기술 주장 대비 사업화·재무성과 연결 근거가 약해 보수 검토가 필요한 구간입니다."

    components = {
        tech_signal.name: round(tech_signal.score, 2),
        commercialization.name: round(commercialization.score, 2),
        customer.name: round(customer.score, 2),
        production.name: round(production.score, 2),
        revenue.name: round(revenue.score, 2),
        moat.name: round(moat.score, 2),
        "evidence_quality_score": round(evidence_quality, 2),
        "numeric_grounding_score": round(numeric_score, 2),
    }

    claim_text = (
        f"Tech-to-Value Bridge Score: {score}/100, 판정={grade}. "
        "기술 우위는 고객사 채택, 양산, 매출 전환, FCF 개선 근거와 연결될 때만 가치평가 가산 요인으로 반영한다."
    )
    evidence_text = (
        f"구성점수: 기술경쟁력 {components['technology_strength_score']}, "
        f"사업화근거 {components['commercialization_evidence_score']}, "
        f"고객채택 {components['customer_adoption_evidence_score']}, "
        f"양산준비 {components['production_readiness_score']}, "
        f"매출/현금흐름 연결 {components['revenue_cashflow_linkage_score']}, "
        f"근거품질 {components['evidence_quality_score']}."
    )

    return {
        "available": True,
        "module": "tech_agent_tech_to_value_bridge_inputs",
        "version": "tech_agent_v6_evidence_based_bridge_inputs",
        "company_name": company_name,
        "score": score,
        "grade": grade,
        "tech_agent_bridge_opinion": opinion_bridge,
        "interpretation": interpretation,
        "raw_score_before_guardrails": round(raw_score, 2),
        "components": components,
        "weights": {
            "technology_strength_score": 0.22,
            "commercialization_evidence_score": 0.20,
            "customer_adoption_evidence_score": 0.15,
            "production_readiness_score": 0.15,
            "revenue_cashflow_linkage_score": 0.12,
            "moat_ip_score": 0.08,
            "evidence_quality_score": 0.08,
        },
        "guardrails": guardrails,
        "signals": {
            "commercialization_hits": commercialization.hits,
            "customer_hits": customer.hits,
            "production_hits": production.hits,
            "revenue_cashflow_hits": revenue.hits,
            "moat_hits": moat.hits,
            "limitation_hits": _hits(text, LIMITATION_TERMS),
            "numeric_signal_count": numeric_count,
            **source_debug,
        },
        "chair_summary_lines": [
            f"Tech-to-Value Bridge Score: {score}/100, 판정={grade}.",
            f"해석: {interpretation}",
            "원칙: 기술 우위는 고객사 채택, 양산, 매출 전환, FCF 개선 근거와 연결될 때만 가치평가 가산 요인으로 반영합니다.",
        ],
        "claims": [
            {
                "claim_id": "tech.bridge.cl.001",
                "text": claim_text,
                "evidence_ids": ["tech.bridge.ev.001"],
            },
            {
                "claim_id": "tech.bridge.cl.002",
                "text": f"{company_name} 기술 분석은 {grade}로 분류되며, Chair는 기술점수 자체보다 사업화·재무성과 연결 근거를 우선 확인해야 한다.",
                "evidence_ids": ["tech.bridge.ev.001"],
            },
        ],
        "evidences": [
            {
                "evidence_id": "tech.bridge.ev.001",
                "source_type": "tech_agent_bridge_scorecard",
                "source": "tech_agent.categories + tech_agent.evidences + company.yaml",
                "metric": "Tech-to-Value Bridge Score",
                "value": score,
                "unit": "점/100",
                "period": None,
                "snippet": evidence_text,
            }
        ],
        "limitations": [
            "이 점수는 공식 투자추천이나 목표주가가 아니라 기술 claim의 사업화·가치평가 연결 가능성을 점검하는 Auditor 입력값입니다.",
            "고객사·양산·매출전환 근거가 공개 자료에서 직접 확인되지 않으면 기술점수가 높아도 가치평가 가산 근거로 과장하지 않습니다.",
            *guardrails,
        ],
        "debug": {
            "source_quality": source_debug,
            "top_evidence_preview": [trim(e.get("snippet") or e.get("claim") or "", 120) for e in evidences[:5] if isinstance(e, dict)],
            "canonical_sections": CANONICAL_SECTION_ORDER,
            "axis_map": SECTION_AXIS_MAP,
        },
    }
