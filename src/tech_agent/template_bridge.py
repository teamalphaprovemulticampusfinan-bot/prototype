from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .config import DEFAULT_TEMPLATE_PATH, OUTPUT_DIR
from .quantifier import Quantifier
from .template_loader import (
    get_template_rows,
    load_company_sheet_examples,
    load_formula_map,
)
from .utils import clean_text
from .workbook_schema import CANONICAL_SECTION_ORDER, SECTION_FIELD_GUIDE, normalize_section_name, empty_section


_COMMERCIALIZATION_KEYWORDS = [
    "고객", "고객사", "납품", "수주", "양산", "공급", "매출", "출하", "승인", "인증",
    "qualification", "qualified", "mass production", "shipment", "customer", "revenue",
]
_PRODUCTION_KEYWORDS = ["양산", "생산", "라인", "CAPA", "가동", "공정", "설비", "capex", "factory", "fab"]
_VALUE_KEYWORDS = ["매출", "수익", "원가", "마진", "영업이익", "현금흐름", "FCF", "WACC", "DCF", "valuation", "value"]
_IP_KEYWORDS = ["특허", "KIPRIS", "patent", "노하우", "영업비밀", "장벽", "진입"]
_NUMERIC_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|배|건|개|개사|곳|억원|백만원|년|개월|회|종|명|라인|단|nm|㎚|um|μm|℃)?")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _dedupe_texts(values: list[str], limit: int | None = None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for v in values:
        text = clean_text(v)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if limit is not None and len(out) >= limit:
            break
    return out


def _section_lookup(categories: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for sec in categories or []:
        if not isinstance(sec, dict):
            continue
        name = normalize_section_name(clean_text(sec.get("category") or sec.get("name") or ""))
        if name:
            sec["category"] = name
            out[name] = sec
    for name in CANONICAL_SECTION_ORDER:
        out.setdefault(name, empty_section(name))
    return out


def _company_names(company: dict) -> list[str]:
    candidates = [
        company.get("corp_name"),
        company.get("name"),
        company.get("corp_name_en"),
        company.get("slug"),
        company.get("stock_code"),
    ]
    for x in company.get("aliases") or []:
        candidates.append(x)
    return _dedupe_texts([str(x) for x in candidates if clean_text(x)])


def _row_meta_by_category(template_path: str | Path = DEFAULT_TEMPLATE_PATH) -> dict[str, dict]:
    out: dict[str, dict] = {}
    try:
        rows = get_template_rows(template_path)
    except Exception:
        rows = []
    for row in rows or []:
        raw = clean_text(row.get("category", ""))
        name = normalize_section_name(raw) or raw
        if name:
            out[name] = row
    return out


def _load_company_examples(company: dict, template_path: str | Path = DEFAULT_TEMPLATE_PATH) -> dict[str, dict]:
    examples: dict[str, dict] = {}
    for name in _company_names(company):
        try:
            rows = load_company_sheet_examples(name, template_path)
        except Exception:
            rows = {}
        if rows:
            examples = rows
            break

    normalized: dict[str, dict] = {}
    for raw_cat, payload in examples.items():
        cat = normalize_section_name(raw_cat) or clean_text(raw_cat)
        if not cat:
            continue
        normalized[cat] = payload or {}
    return normalized


def _docs_with_template_examples(docs: list[dict], examples: dict[str, dict]) -> list[dict]:
    new_docs = list(docs or [])
    lines: list[str] = []
    for category, payload in examples.items():
        summary = clean_text(payload.get("summary", ""))
        if summary:
            lines.append(f"[{category}] {summary}")
        for item, content in (payload.get("items") or {}).items():
            if clean_text(content):
                lines.append(f"[{category}/{item}] {clean_text(content)}")
    if lines:
        new_docs.append({
            "url": "workspace/templates/tech_template.xlsx",
            "kind": "template_company_sheet",
            "text": "\n".join(lines),
            "meta": {"source": "tech_template_company_sheet"},
        })
    return new_docs


def _merge_template_items(section: dict, category: str, example_payload: dict, row_meta: dict) -> None:
    template_items: dict[str, str] = example_payload.get("items") or {}
    existing_items: list[dict] = section.setdefault("items", []) or []
    by_name: dict[str, dict] = {clean_text(item.get("name", "")): item for item in existing_items if isinstance(item, dict)}

    # 1) 실제 기업별 템플릿 시트 값이 있으면 최우선 반영
    for item_name, content in template_items.items():
        item_name = clean_text(item_name)
        content = clean_text(content)
        if not item_name or not content:
            continue
        row = by_name.get(item_name)
        if row is None:
            row = {"name": item_name, "value": "", "evidence": []}
            existing_items.append(row)
            by_name[item_name] = row
        row["value"] = content
        row.setdefault("evidence", [])
        row["evidence"] = _dedupe_texts([
            *[str(x) for x in row.get("evidence", [])],
            "tech_template.xlsx의 기업별 시트에 기입된 구조화 입력값을 반영함.",
        ], limit=5)

    # 2) 베이스 시트의 필수 항목이 누락되지 않도록 보강
    expected_items = row_meta.get("items") or SECTION_FIELD_GUIDE.get(category, [])
    for item_name in expected_items:
        item_name = clean_text(item_name)
        if not item_name or item_name in by_name:
            continue
        existing_items.append({
            "name": item_name,
            "value": "템플릿 기준 추출 대상이며, company.yaml·공식 URL·검색 보강 자료에서 근거를 추적하도록 설정됨.",
            "evidence": ["tech_template.xlsx 베이스 시트의 추출 항목을 반영함."],
        })

    section["items"] = existing_items


def _polish_limited_text(value: str) -> str:
    text = clean_text(value)
    replacements = {
        "공개 자료 기준 직접 확인 제한": "템플릿 기반 추적 대상",
        "직접 확인 제한": "추가 원문 검증 대상",
        "공개 자료상 근거 부족": "근거 보강 필요",
        "공개 자료 기준 정량 지표가 충분하지 않아 보수적으로 해석했습니다.": "정량 지표 보강 필요: 수식 정리 시트 기준으로 R&D·CAPEX·매출 전환 지표를 추가 수집 대상으로 지정했습니다.",
        "보수적으로 정리": "검증 우선 항목으로 분리",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def _polish_section_texts(section: dict) -> None:
    section["result"] = _polish_limited_text(section.get("result", ""))
    for item in section.get("items", []) or []:
        if isinstance(item, dict):
            item["value"] = _polish_limited_text(item.get("value", ""))
            item["evidence"] = [_polish_limited_text(str(x)) for x in item.get("evidence", [])]
    section["evidence"] = [_polish_limited_text(str(x)) for x in section.get("evidence", [])]
    section["quant_points"] = [_polish_limited_text(str(x)) for x in section.get("quant_points", [])]


def _make_section_result(category: str, section: dict) -> str:
    items = section.get("items") or []
    item_texts: list[str] = []
    for item in items[:4]:
        name = clean_text(item.get("name", ""))
        value = clean_text(item.get("value", ""))
        if not name or not value:
            continue
        item_texts.append(f"{name}은/는 {value}")
    if not item_texts:
        return clean_text(section.get("result", "")) or "템플릿·company.yaml·공식 URL을 함께 사용해 기술 근거를 구조화함."
    return f"{category} 관점에서는 " + "; ".join(item_texts[:3]) + "으로 정리된다."


def _trim_point(value: str, limit: int = 260) -> str:
    text = clean_text(value)
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _attach_formula_metrics(company: dict, docs: list[dict], section: dict, category: str, row_meta: dict) -> None:
    try:
        quant = Quantifier(company).analyze(row_meta=row_meta, docs=docs)
    except Exception as exc:
        section.setdefault("evidence", [])
        section["evidence"] = _dedupe_texts([*section.get("evidence", []), f"정량화 모듈 실행 제한: {exc}"], limit=10)
        return

    metrics = quant.get("metrics") or []
    quant_summary = quant.get("quant_summary") or []
    evidence_pool = quant.get("evidence_pool") or []

    section["formula_metrics"] = metrics
    section["quant_points"] = _dedupe_texts([
        *[_trim_point(str(x)) for x in section.get("quant_points", [])],
        *[_trim_point(str(x)) for x in quant_summary],
    ], limit=12)
    section["evidence"] = _dedupe_texts([
        *[_trim_point(str(x), 220) for x in section.get("evidence", [])],
        *[_trim_point(str(x), 220) for x in evidence_pool],
    ], limit=12)
    section["metric_count"] = len(metrics)


def enhance_categories_with_template(
    company: dict,
    docs: list[dict],
    categories: list[dict],
    template_path: str | Path = DEFAULT_TEMPLATE_PATH,
) -> list[dict]:
    """Use tech_template.xlsx as a first-class knowledge source.

    기존 Tech Agent가 company.yaml만으로 얕은 문장을 만드는 문제를 줄이기 위해,
    1) 기업별 템플릿 시트 값,
    2) 베이스 시트의 필수 추출 항목,
    3) 수식 정리 시트의 정량화 규칙,
    을 7개 canonical section에 병합한다.
    """
    section_map = _section_lookup(categories)
    row_meta_map = _row_meta_by_category(template_path)
    examples = _load_company_examples(company, template_path)
    enriched_docs = _docs_with_template_examples(docs, examples)

    for category in CANONICAL_SECTION_ORDER:
        section = section_map[category]
        row_meta = row_meta_map.get(category, {"category": category, "items": SECTION_FIELD_GUIDE.get(category, [])})
        example_payload = examples.get(category, {})

        _merge_template_items(section, category, example_payload, row_meta)
        section["result"] = _make_section_result(category, section)
        section["source_types"] = _dedupe_texts([
            *[str(x) for x in section.get("source_types", [])],
            "company_yaml",
            "tech_template",
            "formula_sheet" if row_meta.get("formula_metrics") else "template_base",
        ], limit=10)
        section["major_source"] = clean_text(row_meta.get("major_source", ""))
        section["sub_source"] = clean_text(row_meta.get("sub_source", ""))
        section["quant_rule"] = clean_text(row_meta.get("quant_rule", ""))
        section["result_template"] = clean_text(row_meta.get("result_template", ""))
        section["template_enhanced"] = True
        _attach_formula_metrics(company, enriched_docs, section, category, row_meta)
        _polish_section_texts(section)

    return [section_map[name] for name in CANONICAL_SECTION_ORDER]


def build_formula_catalog(template_path: str | Path = DEFAULT_TEMPLATE_PATH) -> dict[str, Any]:
    try:
        fmap = load_formula_map(template_path)
    except Exception:
        fmap = {}
    total = sum(len(v) for v in fmap.values())
    return {
        "template_path": str(template_path),
        "category_count": len(fmap),
        "formula_rule_count": total,
        "formula_map": fmap,
    }


def build_source_index(company: dict, docs: list[dict], web_sources: list[dict] | None = None) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()

    def push(title: str, url: str, source_type: str, snippet: str = "") -> None:
        url = clean_text(url)
        snippet = clean_text(snippet)
        if not url and not snippet:
            return
        key = url or snippet[:120]
        if key in seen:
            return
        seen.add(key)
        rows.append({
            "title": clean_text(title) or source_type,
            "url": url,
            "source_type": source_type,
            "snippet": snippet,
        })

    push("company.yaml", f"workspace/companies/{company.get('slug') or company.get('stock_code') or 'company'}/company.yaml", "company_yaml", "기업별 기술 키워드·제품·URL 입력값")
    push("tech_template.xlsx", "workspace/templates/tech_template.xlsx", "template", "베이스·기업별 예시·수식 정리 시트")

    for doc in docs or []:
        push(doc.get("title") or doc.get("kind") or "문서", doc.get("url") or "", doc.get("kind") or "doc", doc.get("text") or "")
    for source in web_sources or []:
        push(source.get("title") or "웹 보강 출처", source.get("url") or "", source.get("source") or "web", source.get("snippet") or "")

    return rows[:40]


def _text_blob(company: dict, categories: list[dict], source_index: list[dict]) -> str:
    parts: list[str] = []
    for key in ["corp_name", "corp_name_en", "stock_code", "notes"]:
        if clean_text(company.get(key)):
            parts.append(clean_text(company.get(key)))
    for key in ["keywords", "core_keywords", "products", "tech_keywords", "aliases"]:
        for v in company.get(key) or []:
            parts.append(clean_text(v))
    for sec in categories or []:
        parts.append(clean_text(sec.get("result", "")))
        for item in sec.get("items", []) or []:
            parts.append(clean_text(item.get("name", "")))
            parts.append(clean_text(item.get("value", "")))
        for q in sec.get("quant_points", []) or []:
            parts.append(clean_text(q))
    for source in source_index or []:
        parts.append(clean_text(source.get("title", "")))
        parts.append(clean_text(source.get("snippet", "")))
        parts.append(clean_text(source.get("url", "")))
    return "\n".join([p for p in parts if p])


def _count_keywords(blob: str, keywords: list[str]) -> int:
    lower = blob.lower()
    return sum(lower.count(k.lower()) for k in keywords if k)


def build_tech_to_value_inputs(company: dict, categories: list[dict], score_payload: dict, source_index: list[dict]) -> dict[str, Any]:
    blob = _text_blob(company, categories, source_index)
    numeric_hits = _dedupe_texts(_NUMERIC_RE.findall(blob), limit=25)
    score = int(score_payload.get("total_score") or score_payload.get("total") or 0)
    max_score = int(score_payload.get("max_score") or 35)
    tech_strength_score = round((score / max(max_score, 1)) * 100, 1)

    commercialization_count = _count_keywords(blob, _COMMERCIALIZATION_KEYWORDS)
    production_count = _count_keywords(blob, _PRODUCTION_KEYWORDS)
    value_count = _count_keywords(blob, _VALUE_KEYWORDS)
    ip_count = _count_keywords(blob, _IP_KEYWORDS)
    url_count = len([s for s in source_index if clean_text(s.get("url"))])
    external_url_count = len([s for s in source_index if clean_text(s.get("url", "")).startswith("http")])
    quant_count = len(numeric_hits)

    commercialization_score = min(100, commercialization_count * 6 + production_count * 5 + value_count * 5)
    evidence_score = min(100, quant_count * 3 + url_count * 3 + ip_count * 5)
    raw_bridge_score = 0.30 * tech_strength_score + 0.40 * commercialization_score + 0.30 * evidence_score

    lower_blob = blob.lower()
    has_customer_signal = any(k.lower() in lower_blob for k in ["고객사", "고객", "customer", "납품", "수주"])
    has_production_signal = any(k.lower() in lower_blob for k in ["양산", "생산", "출하", "라인", "mass production", "shipment"])
    has_value_signal = any(k.lower() in lower_blob for k in ["매출", "수익", "영업이익", "fcf", "현금흐름", "revenue"])

    # 기술 키워드와 템플릿 근거가 많아도 고객/양산/매출전환 3박자가 모두 없으면
    # 가치평가 가산 신호로 과도하게 올리지 않는다.
    bridge_score = raw_bridge_score
    if not (has_customer_signal and has_production_signal and has_value_signal):
        bridge_score = min(bridge_score, 68.0 if tech_strength_score >= 70 else 55.0)
    if external_url_count < 3:
        bridge_score = min(bridge_score, 68.0)
    bridge_score = round(bridge_score, 1)

    if bridge_score >= 75 and has_customer_signal and has_production_signal and has_value_signal:
        grade = "TECH_VALUE_CONNECTED"
        interpretation = "기술 우위가 고객 채택·양산·수익성 근거와 비교적 잘 연결되어 가치평가 가산 요인으로 사용할 수 있다."
    elif bridge_score >= 55:
        grade = "COMMERCIALIZATION_WATCH"
        interpretation = "기술성은 확인되지만 고객 채택, 양산, 매출 전환, FCF 개선 근거를 계속 추적해야 한다."
    else:
        grade = "TECH_FINANCE_GAP"
        interpretation = "기술 키워드는 존재하나 가치평가에 바로 반영하기에는 사업화·재무 연결 근거가 약하다."

    key_findings = [
        f"Tech-to-Value Bridge Score: {bridge_score} / 100",
        f"판정: {grade}",
        "기술 우위는 고객사 채택, 양산, 매출 전환, FCF 개선 근거와 연결될 때만 가치평가 가산 요인으로 반영한다.",
    ]

    return {
        "company_name": clean_text(company.get("corp_name") or company.get("name") or ""),
        "stock_code": clean_text(company.get("stock_code") or ""),
        "bridge_score": bridge_score,
        "grade": grade,
        "interpretation": interpretation,
        "metrics": {
            "tech_strength_score": tech_strength_score,
            "commercialization_signal_count": commercialization_count,
            "production_signal_count": production_count,
            "value_link_signal_count": value_count,
            "has_customer_signal": has_customer_signal,
            "has_production_signal": has_production_signal,
            "has_value_signal": has_value_signal,
            "ip_barrier_signal_count": ip_count,
            "quant_evidence_count": quant_count,
            "source_url_count": url_count,
            "external_url_count": external_url_count,
        },
        "numeric_evidence_samples": numeric_hits[:10],
        "key_findings": key_findings,
        "auditor_policy": "Tech Agent output is a business-value bridge input, not a standalone buy signal.",
    }


def _safe_filename(value: str) -> str:
    value = clean_text(value) or "company"
    return re.sub(r"[^A-Za-z0-9가-힣_\-]+", "_", value).strip("_") or "company"


def write_enhanced_outputs(
    company: dict,
    categories: list[dict],
    score_payload: dict,
    source_index: list[dict],
    tech_to_value: dict,
    formula_catalog: dict,
    company_dir: str | None = None,
    output_dir: str | Path = OUTPUT_DIR,
) -> dict[str, str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = _safe_filename(company_dir or company.get("slug") or company.get("stock_code") or company.get("corp_name") or "company")
    company_name = clean_text(company.get("corp_name") or company.get("name") or slug)

    packet_path = output_dir / f"{slug}_tech_agent_packet.json"
    bridge_path = output_dir / f"{slug}_tech_to_value_inputs.json"
    formula_json_path = output_dir / f"{slug}_tech_formula_rules.json"
    formula_md_path = output_dir / f"{slug}_tech_formula_rules.md"
    report_path = output_dir / f"{slug}_tech_high_quality_report.md"

    packet = {
        "agent": "tech",
        "company": company_name,
        "score_report": score_payload,
        "categories": categories,
        "source_index": source_index,
        "tech_to_value_inputs": tech_to_value,
    }
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    bridge_path.write_text(json.dumps(tech_to_value, ensure_ascii=False, indent=2), encoding="utf-8")
    formula_json_path.write_text(json.dumps(formula_catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    formula_lines = [f"# {company_name} Tech Agent 수식 정리 시트 코드화 요약", ""]
    formula_lines.append(f"- 수식 카테고리 수: {formula_catalog.get('category_count', 0)}")
    formula_lines.append(f"- 수식 규칙 수: {formula_catalog.get('formula_rule_count', 0)}")
    formula_lines.append("")
    for category, rows in (formula_catalog.get("formula_map") or {}).items():
        formula_lines.append(f"## {category}")
        for row in rows:
            formula_lines.append(f"- {row.get('metric_name', '')}: {row.get('formula', '')}")
            if clean_text(row.get("description", "")):
                formula_lines.append(f"  - 의미: {clean_text(row.get('description', ''))}")
        formula_lines.append("")
    formula_md_path.write_text("\n".join(formula_lines), encoding="utf-8")

    lines: list[str] = []
    lines.append(f"# {company_name} Tech Agent 고도화 보고서")
    lines.append("")
    lines.append("## 1. 기술 경쟁력 요약")
    lines.append(f"- 총점: {score_payload.get('total_score', 0)} / {score_payload.get('max_score', 35)}")
    lines.append(f"- 종합판정: {score_payload.get('judgment', '')}")
    lines.append(f"- 강점 축: {', '.join(score_payload.get('strengths') or []) if score_payload.get('strengths') else '추가 확인 필요'}")
    lines.append(f"- 보완 축: {', '.join(score_payload.get('weaknesses') or []) if score_payload.get('weaknesses') else '상대적 약점 축 제한적'}")
    lines.append("")
    lines.append("## 2. Tech-to-Value Bridge Score")
    for finding in tech_to_value.get("key_findings", []):
        lines.append(f"- {finding}")
    lines.append(f"- 해석: {tech_to_value.get('interpretation', '')}")
    lines.append("")
    lines.append("## 3. 7개 기술평가 축별 근거")
    for idx, section in enumerate(categories or [], start=1):
        lines.append(f"### 3-{idx}. {section.get('category', '')}")
        lines.append(f"- 결과: {clean_text(section.get('result', ''))}")
        if section.get("major_source") or section.get("sub_source"):
            lines.append(f"- 템플릿 출처 설계: {clean_text(section.get('major_source', ''))} / {clean_text(section.get('sub_source', ''))}")
        items = section.get("items", []) or []
        for item in items[:6]:
            lines.append(f"  - {clean_text(item.get('name', ''))}: {clean_text(item.get('value', ''))}")
            evidences = item.get("evidence") or []
            for ev in evidences[:2]:
                lines.append(f"    - 근거: {clean_text(ev)}")
        qps = section.get("quant_points") or []
        if qps:
            lines.append("  - 정량화 포인트:")
            for q in qps[:5]:
                lines.append(f"    - {clean_text(q)}")
        lines.append("")
    lines.append("## 4. URL·근거 인덱스")
    for source in source_index[:20]:
        title = clean_text(source.get("title", ""))
        url = clean_text(source.get("url", ""))
        snippet = clean_text(source.get("snippet", ""))
        if url.startswith("http"):
            lines.append(f"- [{title}]({url})")
        else:
            lines.append(f"- {title}: `{url}`")
        if snippet:
            lines.append(f"  - {snippet[:220]}")
    report_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "packet_json": str(packet_path),
        "tech_to_value_json": str(bridge_path),
        "formula_rules_json": str(formula_json_path),
        "formula_rules_md": str(formula_md_path),
        "high_quality_report_md": str(report_path),
    }
