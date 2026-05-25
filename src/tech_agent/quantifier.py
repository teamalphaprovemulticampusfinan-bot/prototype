from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, List

from .utils import clean_text, contains_number, trim


FINANCE_NOISE = {
    "금융자산",
    "금융부채",
    "공정가치",
    "당기손익",
    "상각후원가",
    "지분증권",
    "리스부채",
    "파생상품",
    "기타포괄손익",
}

INDUSTRY_TERMS = [
    "반도체",
    "HBM",
    "패키징",
    "디스플레이",
    "이차전지",
    "배터리",
    "자동차",
    "전장",
    "AI",
    "데이터센터",
    "모바일",
    "서버",
    "메모리",
    "파운드리",
    "통신",
    "의료",
    "로봇",
]

CERT_TERMS = [
    "ISO",
    "UL",
    "CE",
    "RoHS",
    "REACH",
    "IATF",
    "AEC-Q",
    "FDA",
    "GMP",
    "NDA",
    "고객 승인",
    "Qualification",
]

COUNTABLE_UNITS = r"(회|건|개|종|곳|개사|명|억원|백만원|천만원|%|개월|년|라인|기|세대|nm|um|μm|℃|배|단)"


@dataclass
class QuantMetric:
    category: str
    label: str
    value: str
    unit: str = ""
    formula: str = ""
    description: str = ""
    source_kinds: list[str] = field(default_factory=list)
    source_snippets: list[str] = field(default_factory=list)
    confidence: float = 0.5

    def as_dict(self) -> dict:
        return {
            "category": self.category,
            "label": self.label,
            "value": self.value,
            "unit": self.unit,
            "formula": self.formula,
            "description": self.description,
            "source_kinds": self.source_kinds,
            "source_snippets": self.source_snippets,
            "confidence": self.confidence,
        }


class Quantifier:
    def __init__(self, company: dict):
        self.company = company
        self.company_keywords = self._collect_company_keywords(company)

    def analyze(self, *, row_meta: dict, docs: list[dict]) -> dict:
        category = clean_text(row_meta.get("category", ""))
        formula_metrics = row_meta.get("formula_metrics", []) or []
        text_by_kind = self._merge_docs(docs)
        merged_text = "\n".join(text_by_kind.values())

        metrics: list[QuantMetric] = []
        metrics.extend(self._keyword_frequency_metrics(category, merged_text))
        metrics.extend(self._category_specific_metrics(category, merged_text))
        metrics.extend(self._formula_reference_metrics(category, formula_metrics, merged_text))

        metrics = self._dedupe_metrics(metrics)
        quant_summary = self._build_quant_summary(category, metrics)
        evidence_pool = self._collect_evidence_pool(metrics)

        return {
            "category": category,
            "metrics": [m.as_dict() for m in metrics],
            "quant_summary": quant_summary,
            "evidence_pool": evidence_pool,
            "source_kinds": sorted({k for m in metrics for k in m.source_kinds}),
            "metric_count": len(metrics),
        }

    def _collect_company_keywords(self, company: dict) -> list[str]:
        values: list[str] = []
        for key in ["corp_name", "corp_name_en"]:
            value = clean_text(company.get(key, ""))
            if value:
                values.append(value)
        for key in ["keywords", "core_keywords", "products", "tech_keywords", "aliases"]:
            values.extend([clean_text(x) for x in company.get(key, []) or [] if clean_text(x)])
        return _unique([x for x in values if len(x) >= 2])

    def _merge_docs(self, docs: list[dict]) -> dict[str, str]:
        out: dict[str, str] = {}
        for doc in docs or []:
            kind = clean_text(doc.get("kind", ""))
            text = clean_text(doc.get("text", ""))
            if not text:
                continue
            out[kind] = clean_text(out.get(kind, "") + "\n" + text)
        return out

    def _keyword_frequency_metrics(self, category: str, text: str) -> list[QuantMetric]:
        if category not in {"대표 기술", "핵심 제품/서비스"}:
            return []

        metrics: list[QuantMetric] = []
        for keyword in self.company_keywords[:20]:
            if len(keyword) < 2:
                continue
            count = len(re.findall(re.escape(keyword), text, flags=re.IGNORECASE))
            if count >= 2 and not _is_finance_noise_text(keyword):
                metrics.append(
                    QuantMetric(
                        category=category,
                        label="핵심 키워드 출현 빈도",
                        value=str(count),
                        unit="회",
                        formula="문서 내 키워드 단순 출현 빈도",
                        description=f"{keyword} 관련 언급 {count}회",
                        source_kinds=["merged"],
                        source_snippets=[f"{keyword} {count}회 확인"],
                        confidence=0.75 if count >= 5 else 0.6,
                    )
                )
        return metrics

    def _category_specific_metrics(self, category: str, text: str) -> list[QuantMetric]:
        if category == "대표 기술":
            return self._technology_metrics(text)
        if category == "핵심 제품/서비스":
            return self._product_metrics(text)
        if category == "고객 구매 이유":
            return self._benefit_metrics(text)
        if category == "경쟁 우위/대체가능성":
            return self._barrier_metrics(text)
        if category == "활용 및 확장 산업":
            return self._industry_metrics(text)
        if category == "진입 부담/장벽":
            return self._entry_metrics(text)
        if category == "R&D 강도":
            return self._rd_metrics(text)
        return []

    def _formula_reference_metrics(self, category: str, formula_metrics: list[dict], text: str) -> list[QuantMetric]:
        metrics: list[QuantMetric] = []
        if not formula_metrics:
            return metrics

        for rule in formula_metrics:
            metric_name = clean_text(rule.get("metric_name", ""))
            formula = clean_text(rule.get("formula", ""))
            source_hint = clean_text(rule.get("source_hint", ""))
            description = clean_text(rule.get("description", ""))

            matched = self._find_sentences(text, [metric_name, source_hint], require_number=True, limit=2)
            if matched:
                metrics.append(
                    QuantMetric(
                        category=category,
                        label=metric_name or "수식 지표",
                        value=trim(matched[0], 80),
                        unit="문장",
                        formula=formula,
                        description=description or "수식 정리 시트 기준 참조 지표",
                        source_kinds=["formula_sheet", "merged"],
                        source_snippets=matched,
                        confidence=0.7,
                    )
                )
        return metrics

    def _technology_metrics(self, text: str) -> list[QuantMetric]:
        metrics: list[QuantMetric] = []

        freq_sum = 0
        freq_keywords = []
        for kw in self.company_keywords[:10]:
            count = len(re.findall(re.escape(kw), text, flags=re.IGNORECASE))
            if count > 0:
                freq_sum += count
                freq_keywords.append((kw, count))
        if freq_sum > 0:
            metrics.append(
                QuantMetric(
                    category="대표 기술",
                    label="핵심 기술 키워드 합산",
                    value=str(freq_sum),
                    unit="회",
                    formula="핵심 기술/제품 키워드 문서 내 출현 횟수 합산",
                    description=", ".join(f"{k} {v}회" for k, v in freq_keywords[:6]),
                    source_kinds=["merged"],
                    source_snippets=[f"핵심 기술 키워드 합산 {freq_sum}회"],
                    confidence=0.8,
                )
            )

        for sent in self._find_sentences(text, ["가동률", "순도", "수율", "정밀", "처리량", "μm", "nm"], require_number=True, limit=4):
            metrics.append(
                QuantMetric(
                    category="대표 기술",
                    label="핵심 성능/양산 지표",
                    value=trim(sent, 80),
                    unit="문장",
                    formula="문서 내 성능/가동/정밀 관련 수치 문장 추출",
                    description="대표 성능 지표 후보",
                    source_kinds=["merged"],
                    source_snippets=[sent],
                    confidence=0.7,
                )
            )

        applications = _unique(re.findall(r"([A-Za-z0-9\.\- ]{2,30}\s(?:Bonder|BONDER|Saw|SAW|Grinder|GRINDER|Laser|LASER|Placement|PLACEMENT))", text, flags=re.IGNORECASE))
        if applications:
            metrics.append(
                QuantMetric(
                    category="대표 기술",
                    label="적용 공정/장비 영역 수",
                    value=str(len(applications)),
                    unit="개",
                    formula="추출된 공정/장비명 distinct count",
                    description=", ".join(applications[:8]),
                    source_kinds=["merged"],
                    source_snippets=[", ".join(applications[:8])],
                    confidence=0.68,
                )
            )
        return metrics

    def _product_metrics(self, text: str) -> list[QuantMetric]:
        metrics: list[QuantMetric] = []
        product_candidates = _unique(re.findall(r"([A-Za-z0-9\.\- ]{2,40}\s(?:Bonder|BONDER|Saw|SAW|Grinder|GRINDER|Laser|LASER|Shield|SHIELD|Placement|PLACEMENT|Precursor|Resin))", text, flags=re.IGNORECASE))
        if product_candidates:
            metrics.append(
                QuantMetric(
                    category="핵심 제품/서비스",
                    label="확인 제품군 수",
                    value=str(len(product_candidates)),
                    unit="개",
                    formula="공식 문서에서 distinct 제품군 count",
                    description=", ".join(product_candidates[:10]),
                    source_kinds=["merged"],
                    source_snippets=[", ".join(product_candidates[:10])],
                    confidence=0.7,
                )
            )

        for sent in self._find_sentences(text, ["매출", "비중", "성장률", "수주", "출하"], require_number=True, limit=3):
            metrics.append(
                QuantMetric(
                    category="핵심 제품/서비스",
                    label="제품·매출 연계 지표",
                    value=trim(sent, 80),
                    unit="문장",
                    formula="제품/사업과 수익 연결 수치 문장 추출",
                    description="제품·서비스 사업성 관련 정량 단서",
                    source_kinds=["merged"],
                    source_snippets=[sent],
                    confidence=0.68,
                )
            )
        return metrics

    def _benefit_metrics(self, text: str) -> list[QuantMetric]:
        metrics: list[QuantMetric] = []
        for sent in self._find_sentences(text, ["개선", "절감", "단축", "향상", "효율", "수율", "정밀"], require_number=True, limit=4):
            metrics.append(
                QuantMetric(
                    category="고객 구매 이유",
                    label="고객 효익 정량 문장",
                    value=trim(sent, 80),
                    unit="문장",
                    formula="효익/개선 키워드 포함 수치 문장 추출",
                    description="실제 효익 또는 준정량 표현",
                    source_kinds=["merged"],
                    source_snippets=[sent],
                    confidence=0.7,
                )
            )
        return metrics

    def _barrier_metrics(self, text: str) -> list[QuantMetric]:
        metrics: list[QuantMetric] = []
        patterns = [
            ("등록 특허 수", r"특허[^\d]{0,15}(\d{1,4})\s*(건|개|종)"),
            ("고객사/레퍼런스 수", r"(고객사|레퍼런스)[^\d]{0,15}(\d{1,4})\s*(개사|건|곳|사)"),
            ("점유율/시장 지위", r"(\d{1,3}(?:\.\d+)?)\s*%"),
        ]
        for label, pattern in patterns:
            hit = re.search(pattern, text, flags=re.IGNORECASE)
            if hit:
                value = next((g for g in hit.groups() if g and re.search(r"\d", g)), "")
                unit = next((g for g in hit.groups() if g and not re.search(r"\d", g)), "")
                snippet = trim(hit.group(0), 120)
                metrics.append(
                    QuantMetric(
                        category="경쟁 우위/대체가능성",
                        label=label,
                        value=value or snippet,
                        unit=unit,
                        formula="정규식 기반 수치 추출",
                        description=label,
                        source_kinds=["merged"],
                        source_snippets=[snippet],
                        confidence=0.72,
                    )
                )
        return metrics

    def _industry_metrics(self, text: str) -> list[QuantMetric]:
        present = [term for term in INDUSTRY_TERMS if term.lower() in text.lower()]
        if not present:
            return []
        return [
            QuantMetric(
                category="활용 및 확장 산업",
                label="확인 산업 수",
                value=str(len(_unique(present))),
                unit="개",
                formula="산업 키워드 distinct count",
                description=", ".join(_unique(present)[:10]),
                source_kinds=["merged"],
                source_snippets=[", ".join(_unique(present)[:10])],
                confidence=0.68,
            )
        ]

    def _entry_metrics(self, text: str) -> list[QuantMetric]:
        metrics: list[QuantMetric] = []
        certs = [c for c in CERT_TERMS if c.lower() in text.lower()]
        if certs:
            metrics.append(
                QuantMetric(
                    category="진입 부담/장벽",
                    label="확인 인증/규격 수",
                    value=str(len(_unique(certs))),
                    unit="개",
                    formula="인증/규격 키워드 distinct count",
                    description=", ".join(_unique(certs)[:8]),
                    source_kinds=["merged"],
                    source_snippets=[", ".join(_unique(certs)[:8])],
                    confidence=0.66,
                )
            )

        for sent in self._find_sentences(text, ["검증", "인증", "평가", "승인", "파일럿", "pilot", "개월", "년"], require_number=True, limit=3):
            metrics.append(
                QuantMetric(
                    category="진입 부담/장벽",
                    label="검증/개발 기간 문장",
                    value=trim(sent, 80),
                    unit="문장",
                    formula="인증/검증/기간 키워드 포함 수치 문장",
                    description="추가 진입 부담 관련 문장",
                    source_kinds=["merged"],
                    source_snippets=[sent],
                    confidence=0.65,
                )
            )
        return metrics

    def _rd_metrics(self, text: str) -> list[QuantMetric]:
        metrics: list[QuantMetric] = []
        for sent in self._find_sentences(text, ["연구개발", "R&D", "연구인력", "설비투자", "CAPEX", "투자"], require_number=True, limit=6):
            metrics.append(
                QuantMetric(
                    category="R&D 강도",
                    label="R&D/CAPEX 수치 문장",
                    value=trim(sent, 80),
                    unit="문장",
                    formula="R&D/CAPEX 관련 수치 문장 추출",
                    description="연구개발 또는 설비투자 단서",
                    source_kinds=["merged"],
                    source_snippets=[sent],
                    confidence=0.7,
                )
            )
        return metrics

    def _build_quant_summary(self, category: str, metrics: list[QuantMetric]) -> list[str]:
        if not metrics:
            return ["공개 자료 기준 정량 지표가 충분하지 않아 보수적으로 해석했습니다."]

        lines: list[str] = []
        by_label: dict[str, list[QuantMetric]] = {}
        for metric in metrics:
            by_label.setdefault(metric.label, []).append(metric)

        for label, rows in by_label.items():
            first = rows[0]
            desc = first.description or first.value
            value_text = first.value + (first.unit or "")
            lines.append(f"{label}: {value_text} ({desc})")
        return lines[:5]

    def _collect_evidence_pool(self, metrics: list[QuantMetric]) -> list[str]:
        out: list[str] = []
        for metric in metrics:
            for snippet in metric.source_snippets[:2]:
                snippet = clean_text(snippet)
                if snippet and snippet not in out:
                    out.append(snippet)
        return out[:8]

    def _find_sentences(self, text: str, keywords: Iterable[str], *, require_number: bool, limit: int) -> list[str]:
        out: list[str] = []
        parts = re.split(r"(?<=[\.\!\?])\s+|\n+", clean_text(text))
        lowered_keywords = [clean_text(k).lower() for k in keywords if clean_text(k)]
        for part in parts:
            sent = clean_text(part)
            if len(sent) < 8 or len(sent) > 180:
                continue
            if _is_finance_noise_text(sent):
                continue
            if require_number and not contains_number(sent):
                continue
            lowered = sent.lower()
            if not any(k in lowered for k in lowered_keywords):
                continue
            out.append(trim(sent, 140))
            if len(out) >= limit:
                break
        return _unique(out)

    def _dedupe_metrics(self, metrics: list[QuantMetric]) -> list[QuantMetric]:
        seen = set()
        out = []
        for metric in metrics:
            key = (metric.category, metric.label, metric.value)
            if key in seen:
                continue
            seen.add(key)
            out.append(metric)
        return out


def _is_finance_noise_text(text: str) -> bool:
    lowered = clean_text(text).lower()
    hits = sum(1 for term in FINANCE_NOISE if term.lower() in lowered)
    return hits >= 2


def _unique(values: List[str]) -> List[str]:
    seen = set()
    out = []
    for value in values:
        value = clean_text(value)
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out