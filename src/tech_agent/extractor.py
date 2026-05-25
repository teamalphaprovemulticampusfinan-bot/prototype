from __future__ import annotations

import re
from collections import Counter

from .utils import clean_text, guess_doc_kind_from_url
from .workbook_schema import (
    CANONICAL_SECTION_ORDER,
    SECTION_FIELD_GUIDE,
    empty_section,
    normalize_section_name,
)

_NUMBER_RE = re.compile(r"\b\d+(?:[\.,]\d+)?\b")
_KOREAN_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|배|건|개|회|종|명|억원|천원|백만원)")
_NOISE_PATTERNS = [
    "뉴스검색",
    "메뉴 영역으로 바로가기",
    "본문 영역으로 바로가기",
    "로그인",
    "회원가입",
    "검색어 입력",
    "자동완성",
    "검색 옵션",
    "naver",
    "google news",
]


def _safe_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [clean_text(x) for x in value if clean_text(x)]
    return [clean_text(value)] if clean_text(value) else []


def _flatten_company_terms(company: dict) -> dict[str, list[str]]:
    return {
        "aliases": _safe_list(company.get("aliases")),
        "keywords": _safe_list(company.get("keywords")),
        "core_keywords": _safe_list(company.get("core_keywords")),
        "products": _safe_list(company.get("products")),
        "tech_keywords": _safe_list(company.get("tech_keywords")),
    }


def _clean_noise_lines(text: str) -> str:
    text = clean_text(text)
    if not text:
        return ""

    kept = []
    for raw_line in text.splitlines():
        line = clean_text(raw_line)
        if not line:
            continue

        lowered = line.lower()
        if any(p.lower() in lowered for p in _NOISE_PATTERNS):
            continue

        kept.append(line)

    return "\n".join(kept)


def _count_occurrences(text: str, term: str) -> int:
    text = clean_text(text).lower()
    term = clean_text(term).lower()
    if not text or not term:
        return 0
    return text.count(term)


def _pick_top_terms(text: str, candidates: list[str], top_n: int = 6) -> list[tuple[str, int]]:
    counter = []
    for term in candidates:
        cnt = _count_occurrences(text, term)
        if cnt > 0:
            counter.append((term, cnt))
    counter.sort(key=lambda x: (-x[1], x[0]))
    return counter[:top_n]


def _extract_numeric_snippets(text: str, limit: int = 5) -> list[str]:
    text = clean_text(text)
    if not text:
        return []

    lines = []
    for line in text.splitlines():
        ln = clean_text(line)
        if not ln:
            continue
        if _KOREAN_NUMBER_RE.search(ln) or _NUMBER_RE.search(ln):
            lines.append(ln)

    uniq = []
    seen = set()
    for line in lines:
        if line not in seen:
            seen.add(line)
            uniq.append(line)

    return uniq[:limit]


def _infer_industries(company: dict, corpus: str) -> list[str]:
    pool = " ".join(
        _safe_list(company.get("keywords"))
        + _safe_list(company.get("core_keywords"))
        + _safe_list(company.get("products"))
        + _safe_list(company.get("tech_keywords"))
        + [corpus]
    ).lower()

    industries = []
    if "반도체" in pool:
        industries.append("반도체")
    if "디스플레이" in pool:
        industries.append("디스플레이")
    if "이차전지" in pool or "2차전지" in pool:
        industries.append("이차전지")
    if "전자재료" in pool:
        industries.append("전자재료")
    return industries


def _infer_customer_group(company: dict, corpus: str) -> str:
    industries = _infer_industries(company, corpus)
    if "반도체" in industries:
        return "반도체 제조 및 공정 관련 기업"
    if "디스플레이" in industries:
        return "디스플레이 소재 및 공정 관련 기업"
    if industries:
        return ", ".join(industries) + " 관련 기업"
    return "공개 자료 기준 직접 확인 제한"


def _merge_section(base: dict, incoming: dict) -> dict:
    base_result = clean_text(base.get("result", ""))
    inc_result = clean_text(incoming.get("result", ""))

    if len(inc_result) > len(base_result):
        base["result"] = inc_result

    items = incoming.get("items", []) or []
    if isinstance(items, list):
        base["items"].extend(items)

    for key in ["evidence", "quant_points", "source_types"]:
        merged = (base.get(key, []) or []) + (incoming.get(key, []) or [])
        uniq = []
        seen = set()
        for v in merged:
            vv = clean_text(v)
            if not vv or vv in seen:
                continue
            seen.add(vv)
            uniq.append(vv)
        base[key] = uniq

    return base


def _canonicalize_categories(raw_categories: list[dict]) -> list[dict]:
    bucket = {name: empty_section(name) for name in CANONICAL_SECTION_ORDER}

    for row in raw_categories or []:
        if not isinstance(row, dict):
            continue

        raw_name = clean_text(row.get("category") or row.get("title") or row.get("name") or "")
        canonical = normalize_section_name(raw_name)
        if not canonical:
            continue

        normalized = {
            "category": canonical,
            "result": clean_text(row.get("result") or row.get("summary") or ""),
            "items": row.get("items", []) or [],
            "evidence": row.get("evidence", []) or [],
            "quant_points": row.get("quant_points", []) or [],
            "source_types": row.get("source_types", []) or [],
        }
        bucket[canonical] = _merge_section(bucket[canonical], normalized)

    final_sections = []
    for section_name in CANONICAL_SECTION_ORDER:
        sec = bucket[section_name]

        uniq_items = []
        seen = set()
        for item in sec.get("items", []) or []:
            name = clean_text(item.get("name", ""))
            value = clean_text(item.get("value", ""))
            key = (name, value)
            if not name:
                continue
            if key in seen:
                continue
            seen.add(key)
            uniq_items.append(
                {
                    "name": name,
                    "value": value,
                    "evidence": [clean_text(x) for x in (item.get("evidence", []) or []) if clean_text(x)],
                }
            )

        sec["items"] = uniq_items
        if not clean_text(sec.get("result", "")):
            sec["result"] = "공개 자료 기준 직접 확인이 제한되어 보수적으로 정리함."

        final_sections.append(sec)

    return final_sections


def collect_docs(company: dict) -> list[dict]:
    docs: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    def _norm(v) -> str:
        return clean_text(v if v is not None else "")

    def _is_blocked_url(url: str) -> bool:
        u = _norm(url).lower()
        if not u:
            return False

        blocked_tokens = [
            "search.naver.com/search.naver",
            "news.google.com/search",
            "kpat.kipris.or.kr/kpat/searchlogina",
            "finance.naver.com/sise/",
            "finance.naver.com/search/",
        ]

        blocked_exact = {
            "https://dart.fss.or.kr/",
            "http://dart.fss.or.kr/",
            "https://kind.krx.co.kr/",
            "http://kind.krx.co.kr/",
        }

        if u in blocked_exact:
            return True

        return any(token in u for token in blocked_tokens)

    def _push(url: str = "", kind: str = "", text: str = "", meta: dict | None = None):
        url = _norm(url)
        kind = _norm(kind)
        text = _clean_noise_lines(text)
        meta = meta or {}

        if not url and not text:
            return

        if url and _is_blocked_url(url):
            return

        inferred_kind = kind or guess_doc_kind_from_url(url)
        key = (url, inferred_kind, text[:300])

        if key in seen:
            return
        seen.add(key)

        row = {
            "url": url,
            "kind": inferred_kind,
            "text": text,
        }
        if meta:
            row["meta"] = meta

        docs.append(row)

    # 1) company.yaml 메타데이터 seed
    seed_lines: list[str] = []

    if clean_text(company.get("corp_name")):
        seed_lines.append(f"기업명: {clean_text(company.get('corp_name'))}")
    if clean_text(company.get("corp_name_en")):
        seed_lines.append(f"영문명: {clean_text(company.get('corp_name_en'))}")
    if clean_text(company.get("stock_code")):
        seed_lines.append(f"종목코드: {clean_text(company.get('stock_code'))}")

    for label, key in [
        ("별칭", "aliases"),
        ("일반 키워드", "keywords"),
        ("핵심 기술 키워드", "core_keywords"),
        ("주요 제품", "products"),
        ("기술 키워드", "tech_keywords"),
    ]:
        vals = _safe_list(company.get(key))
        if vals:
            seed_lines.append(f"{label}: " + ", ".join(vals))

    if clean_text(company.get("notes")):
        seed_lines.append("비고:")
        seed_lines.append(clean_text(company.get("notes")))

    if seed_lines:
        _push(kind="seed", text="\n".join(seed_lines), meta={"source": "company_yaml_seed"})

    # 2) docs 블록
    for row in company.get("docs", []) or []:
        if not isinstance(row, dict):
            continue
        _push(
            url=row.get("url", ""),
            kind=row.get("kind", ""),
            text=row.get("text", ""),
            meta={"source": "docs_block"},
        )

    # 3) 단일 URL 키
    _push(url=company.get("homepage_url", ""), kind="homepage", meta={"source": "homepage_url"})
    _push(url=company.get("ir_url", ""), kind="ir", meta={"source": "ir_url"})

    # 4) urls 블록
    url_map = company.get("urls", {}) or {}
    if isinstance(url_map, dict):
        for kind, value in url_map.items():
            if isinstance(value, list):
                for v in value:
                    _push(url=v, kind=kind, meta={"source": "urls_block", "bucket": kind})
            else:
                _push(url=value, kind=kind, meta={"source": "urls_block", "bucket": kind})

    # 5) extra_urls 구버전 호환
    extra_url_map = company.get("extra_urls", {}) or {}
    if isinstance(extra_url_map, dict):
        for kind, value in extra_url_map.items():
            if isinstance(value, list):
                for v in value:
                    _push(url=v, kind=kind, meta={"source": "extra_urls_block", "bucket": kind})
            else:
                _push(url=value, kind=kind, meta={"source": "extra_urls_block", "bucket": kind})

    # 6) text fallback
    text_fields = {
        "homepage_text": "homepage",
        "report_text": "report",
        "ir_text": "ir",
        "research_text": "research",
        "seed_text": "seed",
    }
    for field_name, kind_name in text_fields.items():
        if company.get(field_name):
            _push(kind=kind_name, text=company.get(field_name), meta={"source": field_name})

    return docs


class Extractor:
    """
    최소 실행 가능한 휴리스틱 추출기.
    - company.yaml 메타데이터
    - docs의 text
    - docs의 URL kind
    를 바탕으로 7개 canonical section에 들어갈 재료를 만든다.
    """

    def build_company_report(self, company: dict, docs: list[dict], template_path: str | None = None) -> list[dict]:
        del template_path  # 현재 버전에서는 사용하지 않음

        corpus = self._build_corpus(company, docs)
        source_types = self._collect_source_types(docs)
        company_terms = _flatten_company_terms(company)

        categories = [
            self._build_rep_tech(company, company_terms, corpus, source_types),
            self._build_products(company, company_terms, corpus, source_types),
            self._build_customer_reason(company, company_terms, corpus, source_types),
            self._build_advantage(company, company_terms, corpus, source_types),
            self._build_expansion(company, company_terms, corpus, source_types),
            self._build_barrier(company, company_terms, corpus, source_types),
            self._build_rd(company, company_terms, corpus, source_types),
        ]
        return categories

    def _build_corpus(self, company: dict, docs: list[dict]) -> str:
        parts = []

        for key in ["corp_name", "corp_name_en", "stock_code", "notes"]:
            if clean_text(company.get(key)):
                parts.append(clean_text(company.get(key)))

        for key in ["aliases", "keywords", "core_keywords", "products", "tech_keywords"]:
            vals = _safe_list(company.get(key))
            if vals:
                parts.append("\n".join(vals))

        for doc in docs or []:
            if clean_text(doc.get("text")):
                parts.append(_clean_noise_lines(doc.get("text")))

            # URL도 약한 힌트로 보존
            if clean_text(doc.get("url")):
                parts.append(clean_text(doc.get("url")))

            if isinstance(doc.get("meta"), dict):
                for mv in doc["meta"].values():
                    if isinstance(mv, str) and clean_text(mv):
                        parts.append(clean_text(mv))

        return clean_text("\n".join(parts))

    def _collect_source_types(self, docs: list[dict]) -> list[str]:
        kinds = []
        for doc in docs or []:
            kind = clean_text(doc.get("kind", ""))
            if kind:
                kinds.append(kind)
        uniq = []
        seen = set()
        for k in kinds:
            if k not in seen:
                seen.add(k)
                uniq.append(k)
        return uniq

    def _top_keyword_summary(self, corpus: str, terms: list[str], fallback_terms: list[str] | None = None) -> tuple[str, list[str]]:
        fallback_terms = fallback_terms or []
        picked = _pick_top_terms(corpus, terms, top_n=6)
        evidence = []

        if picked:
            joined = ", ".join([f"{term} {cnt}회" for term, cnt in picked])
            top_terms = ", ".join([term for term, _ in picked])
            evidence.append(f"텍스트 집계 기준: {joined}")
            return top_terms, evidence

        if fallback_terms:
            top_terms = ", ".join(fallback_terms[:6])
            evidence.append("company.yaml 기준 핵심 키워드/제품명을 우선 반영함.")
            return top_terms, evidence

        return "공개 자료 기준 직접 확인 제한", ["관련 키워드 직접 확인 제한"]

    def _default_perf_terms(self, company_terms: dict[str, list[str]]) -> list[str]:
        candidates = []
        for key in ["tech_keywords", "core_keywords", "keywords"]:
            candidates.extend(company_terms.get(key, []))

        preferred = []
        for token in candidates:
            if any(k in token for k in ["고순도", "안정성", "신뢰성", "미세", "정밀", "선택비", "수율"]):
                preferred.append(token)

        if preferred:
            return list(dict.fromkeys(preferred))[:6]
        return list(dict.fromkeys(candidates))[:6]

    def _build_rep_tech(self, company: dict, terms: dict[str, list[str]], corpus: str, source_types: list[str]) -> dict:
        section_name = "대표 기술"
        section = empty_section(section_name)

        keyword_candidates = terms["core_keywords"] + terms["tech_keywords"] + terms["products"]
        top_terms, keyword_evidence = self._top_keyword_summary(corpus, keyword_candidates, keyword_candidates)

        perf_terms = self._default_perf_terms(terms)
        perf_summary = ", ".join(perf_terms) if perf_terms else "공개 자료 기준 직접 확인 제한"

        industries = _infer_industries(company, corpus)
        apply_summary = ", ".join(industries) + " 공정/소재 영역" if industries else "공개 자료 기준 직접 확인 제한"

        quant_points = _extract_numeric_snippets(corpus, limit=4)

        if keyword_evidence and "텍스트 집계 기준" in keyword_evidence[0]:
            result = (
                f"이 기업은 {top_terms} 기반 제품/기술 기업으로, 관련 기술은 텍스트 집계 기준으로 확인된다. "
                f"해당 기술은 {apply_summary}에 적용되며, {perf_summary} 중심의 성능 요소가 관찰된다."
            )
        else:
            result = (
                f"이 기업은 {top_terms} 기반 제품/기술 기업으로 파악되며, "
                f"관련 기술은 {apply_summary}에 적용되고 {perf_summary}가 핵심 성능 요소로 정리된다."
            )

        section["result"] = result
        section["items"] = [
            {
                "name": "핵심 기술 키워드",
                "value": top_terms,
                "evidence": keyword_evidence,
            },
            {
                "name": "적용 방식",
                "value": apply_summary,
                "evidence": [
                    "company.yaml의 제품/키워드와 텍스트 문맥을 바탕으로 적용 영역을 요약함."
                ],
            },
            {
                "name": "핵심 성능 요소",
                "value": perf_summary,
                "evidence": [
                    "기술 키워드 중 성능·품질 관련 표현을 우선 반영함."
                ],
            },
        ]
        section["quant_points"] = quant_points
        section["source_types"] = source_types
        return section

    def _build_products(self, company: dict, terms: dict[str, list[str]], corpus: str, source_types: list[str]) -> dict:
        section_name = "핵심 제품/서비스"
        section = empty_section(section_name)

        products = terms["products"] or terms["core_keywords"][:4]
        product_text = ", ".join(products) if products else "공개 자료 기준 직접 확인 제한"

        tech_text = ", ".join((terms["core_keywords"] + terms["tech_keywords"])[:6]) or "공개 자료 기준 직접 확인 제한"
        customer_group = _infer_customer_group(company, corpus)

        section["result"] = (
            f"이 기업은 {product_text}를 중심으로 사업 포트폴리오를 구성하는 것으로 정리되며, "
            f"주요 적용 기술은 {tech_text}이고, 주요 고객군은 {customer_group}으로 해석된다."
        )
        section["items"] = [
            {
                "name": "제품명/서비스명",
                "value": product_text,
                "evidence": ["company.yaml의 products 항목을 우선 반영함."],
            },
            {
                "name": "적용 기술",
                "value": tech_text,
                "evidence": ["핵심 기술 키워드와 기술 키워드의 결합 결과."],
            },
            {
                "name": "주요 고객군",
                "value": customer_group,
                "evidence": ["산업 키워드 기반으로 보수적으로 추론함."],
            },
        ]
        section["quant_points"] = _extract_numeric_snippets(corpus, limit=4)
        section["source_types"] = source_types
        return section

    def _build_customer_reason(self, company: dict, terms: dict[str, list[str]], corpus: str, source_types: list[str]) -> dict:
        section_name = "고객 구매 이유"
        section = empty_section(section_name)

        perf_terms = self._default_perf_terms(terms)
        benefit = ", ".join(perf_terms[:4]) if perf_terms else "공개 자료 기준 직접 확인 제한"

        advantage_terms = []
        for token in perf_terms:
            if token not in advantage_terms:
                advantage_terms.append(token)
        if not advantage_terms:
            advantage_terms = ["공개 자료 기준 직접 확인 제한"]

        ref_candidates = []
        if "sk하이닉스" in corpus.lower():
            ref_candidates.append("SK하이닉스 관련 문맥 확인")
        if "삼성" in corpus.lower():
            ref_candidates.append("삼성 관련 문맥 확인")
        reference_text = ", ".join(ref_candidates) if ref_candidates else "공개 자료 기준 직접 확인 제한"

        section["result"] = (
            f"제공 자료 기준 고객 구매 이유는 {benefit} 중심으로 해석되나, "
            f"경쟁 제품 대비 우위 수치나 실제 적용 사례는 공개 자료 기준 직접 확인이 제한되어 보수적으로 정리한다."
        )
        section["items"] = [
            {
                "name": "고객 효익",
                "value": benefit,
                "evidence": ["기술 키워드 중 성능·품질 표현을 고객 효익 후보로 반영함."],
            },
            {
                "name": "경쟁 제품 대비 장점",
                "value": ", ".join(advantage_terms[:4]),
                "evidence": ["고순도·안정성·신뢰성·미세공정 등 품질 중심 표현을 우선 반영함."],
            },
            {
                "name": "실제 적용 사례",
                "value": reference_text,
                "evidence": ["고객사·레퍼런스 관련 문구 직접 확인 여부를 기준으로 정리함."],
            },
        ]
        section["quant_points"] = _extract_numeric_snippets(corpus, limit=3)
        section["source_types"] = source_types
        return section

    def _build_advantage(self, company: dict, terms: dict[str, list[str]], corpus: str, source_types: list[str]) -> dict:
        section_name = "경쟁 우위/대체가능성"
        section = empty_section(section_name)

        patent_signal = "공개 자료 기준 직접 확인 제한"
        if "특허" in corpus:
            patent_signal = "특허 관련 문구 확인"
        elif "kipris" in corpus.lower():
            patent_signal = "KIPRIS 검색 링크 존재"

        knowhow = ", ".join((terms["products"] + terms["core_keywords"])[:6]) or "공개 자료 기준 직접 확인 제한"

        ref_text = "공개 자료 기준 직접 확인 제한"
        if "sk하이닉스" in corpus.lower():
            ref_text = "SK하이닉스 관련 문맥 확인"
        elif "고객" in corpus:
            ref_text = "고객 관련 문맥 일부 확인"

        section["result"] = (
            f"이 기업의 경쟁 우위는 {knowhow} 중심의 제품·소재 포트폴리오와 품질/공정 노하우에서 도출되며, "
            f"특허 및 고객사 레퍼런스는 공개 자료 기준 직접 확인 수준에 따라 보수적으로 반영한다."
        )
        section["items"] = [
            {
                "name": "등록 특허",
                "value": patent_signal,
                "evidence": ["특허/KIPRIS 관련 직접 문구 존재 여부를 기준으로 판단함."],
            },
            {
                "name": "제조 노하우",
                "value": knowhow,
                "evidence": ["제품/핵심 기술 키워드 조합을 제조·공정 노하우 신호로 사용함."],
            },
            {
                "name": "고객사 레퍼런스",
                "value": ref_text,
                "evidence": ["고객사명 또는 고객 관련 문맥 직접 확인 여부를 기준으로 정리함."],
            },
        ]
        section["quant_points"] = _extract_numeric_snippets(corpus, limit=3)
        section["source_types"] = source_types
        return section

    def _build_expansion(self, company: dict, terms: dict[str, list[str]], corpus: str, source_types: list[str]) -> dict:
        section_name = "활용 및 확장 산업"
        section = empty_section(section_name)

        industries = _infer_industries(company, corpus)
        current_industry = ", ".join(industries) if industries else "공개 자료 기준 직접 확인 제한"

        product_count = len(terms["products"])
        keyword_count = len(terms["core_keywords"]) + len(terms["tech_keywords"])
        generality = (
            f"제품 {product_count}개, 기술 키워드 {keyword_count}개 기준으로 복수 공정/소재 영역 대응 가능성 존재"
            if (product_count or keyword_count)
            else "공개 자료 기준 직접 확인 제한"
        )

        if len(industries) >= 2:
            cross_industry = ", ".join(industries[1:]) + " 확장 가능성 검토"
        else:
            cross_industry = "공개 자료 기준 직접 확인 제한"

        section["result"] = (
            f"현재 활용 산업은 {current_industry} 중심으로 정리되며, "
            f"기술 범용성은 {generality}로 해석된다. 타산업 적용 가능성은 공개 자료 기준 직접 확인 범위 내에서 보수적으로 반영한다."
        )
        section["items"] = [
            {
                "name": "현재 고객 산업",
                "value": current_industry,
                "evidence": ["키워드·제품군에서 산업명을 추출함."],
            },
            {
                "name": "기술 범용성",
                "value": generality,
                "evidence": ["제품 수와 기술 키워드 수를 기반으로 범용성을 정리함."],
            },
            {
                "name": "타산업 적용 가능성",
                "value": cross_industry,
                "evidence": ["복수 산업 키워드 존재 여부를 기준으로 보수적으로 정리함."],
            },
        ]
        section["quant_points"] = [
            f"제품군 {product_count}개",
            f"기술 키워드 {keyword_count}개",
        ]
        section["source_types"] = source_types
        return section

    def _build_barrier(self, company: dict, terms: dict[str, list[str]], corpus: str, source_types: list[str]) -> dict:
        section_name = "진입 부담/장벽"
        section = empty_section(section_name)

        industries = _infer_industries(company, corpus)
        if "반도체" in industries:
            validation_text = "반도체 고객사 기준 품질 검증 및 공정 적합성 확인 필요"
        else:
            validation_text = "고객사별 추가 검증 가능성 존재"

        cert_text = "공개 자료 기준 직접 확인 제한"
        if "iso" in corpus.lower():
            cert_text = "ISO 관련 문구 확인"

        dev_period_text = "공개 자료 기준 직접 확인 제한"
        numeric = _extract_numeric_snippets(corpus, limit=5)
        if numeric:
            dev_period_text = "공개 자료 내 수치 문맥 일부 확인"

        section["result"] = (
            f"신규 진입 시에는 {validation_text}가 요구될 가능성이 높으며, "
            f"인증 종류와 개발 기간은 공개 자료 기준 직접 확인 범위 내에서 보수적으로 정리한다."
        )
        section["items"] = [
            {
                "name": "인증 종류",
                "value": cert_text,
                "evidence": ["인증 관련 직접 문구 존재 여부 기준."],
            },
            {
                "name": "개발 기간",
                "value": dev_period_text,
                "evidence": ["개발/기간 관련 수치 문구 직접 확인 여부 기준."],
            },
            {
                "name": "추가 검증 필요 여부",
                "value": validation_text,
                "evidence": ["산업 특성상 고객사 품질 검증 가능성을 보수적으로 반영함."],
            },
        ]
        section["quant_points"] = numeric[:3]
        section["source_types"] = source_types
        return section

    def _build_rd(self, company: dict, terms: dict[str, list[str]], corpus: str, source_types: list[str]) -> dict:
        section_name = "R&D 강도"
        section = empty_section(section_name)

        rd_text = "공개 자료 기준 직접 확인 제한"
        if "연구개발" in corpus or "r&d" in corpus.lower():
            rd_text = "연구개발 관련 문구 일부 확인"

        manpower_text = "공개 자료 기준 직접 확인 제한"
        if "연구인력" in corpus or "인력" in corpus:
            manpower_text = "인력 관련 문구 일부 확인"

        capex_text = "공개 자료 기준 직접 확인 제한"
        if "capex" in corpus.lower() or "설비투자" in corpus or "유형자산" in corpus:
            capex_text = "설비투자 관련 문구 일부 확인"

        numeric = _extract_numeric_snippets(corpus, limit=5)

        section["result"] = (
            f"이 기업의 R&D 강도는 연구개발비, 연구인력, CAPEX 관련 공개 자료 확인 수준에 따라 보수적으로 평가하며, "
            f"직접 수치가 부족한 경우 과대 해석하지 않는다."
        )
        section["items"] = [
            {
                "name": "연구개발비",
                "value": rd_text,
                "evidence": ["연구개발비/R&D 직접 문구 존재 여부 기준."],
            },
            {
                "name": "연구인력",
                "value": manpower_text,
                "evidence": ["연구인력/인력 관련 직접 문구 존재 여부 기준."],
            },
            {
                "name": "CAPEX",
                "value": capex_text,
                "evidence": ["CAPEX/설비투자/유형자산 관련 직접 문구 존재 여부 기준."],
            },
        ]
        section["quant_points"] = numeric[:3]
        section["source_types"] = source_types
        return section


def extract_categories(company: dict, docs: list[dict], template_path: str | None = None) -> list[dict]:
    extractor = Extractor()
    raw_categories = extractor.build_company_report(company, docs, template_path=template_path)
    return _canonicalize_categories(raw_categories)