from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .config import OUTPUT_DIR, ROOT_DIR
from .utils import clean_text, ensure_dir
from common.output_paths import agent_output_path

try:
    from .text_safety import deep_clean, is_probably_mojibake, normalize_spaces, repair_mojibake_text
except Exception:
    from tech_agent.text_safety import deep_clean, is_probably_mojibake, normalize_spaces, repair_mojibake_text

COMMERCIALIZATION_TERMS = ["고객", "고객사", "공급", "채택", "수주", "납품", "레퍼런스", "양산", "적용", "승인"]
PRODUCTION_TERMS = ["양산", "공정", "수율", "라인", "설비", "검증", "품질", "Qualification", "생산", "테스트"]
VALUE_TERMS = ["매출", "수익", "영업이익", "현금흐름", "FCF", "원가", "마진", "비중", "성장", "CAPEX"]
IP_TERMS = ["특허", "산업재산권", "청구항", "IPC", "CPC", "등록", "출원", "독자", "노하우"]

TECH_SECTION_ORDER = [
    "대표 기술",
    "핵심 제품/서비스",
    "고객 구매 이유",
    "경쟁 우위/대체가능성",
    "활용 및 확장 산업",
    "진입 부담/장벽",
    "R&D 강도",
]


def _lst(v: Any) -> list[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def _term_count(text: str, terms: list[str]) -> int:
    low = clean_text(text).lower()
    return sum(1 for t in terms if clean_text(t).lower() in low)


def _source_label(ev: dict[str, Any]) -> str:
    return clean_text(ev.get("source_url") or ev.get("source_path") or ev.get("source_title") or ev.get("source_type") or "source")


def _is_official(ev: dict[str, Any]) -> bool:
    return clean_text(ev.get("source_type")) in {"dart_filing", "official_homepage", "ir", "patent", "local_tech_source"}


def _evidence_strength(item: dict[str, Any]) -> tuple[int, int, int]:
    evidence = item.get("evidence") or []
    metrics = item.get("quant_metrics") or []
    return len(evidence), sum(1 for e in evidence if _is_official(e)), len(metrics)


def _metric_detail_text(m: dict[str, Any], max_items: int = 5) -> str:
    detail = m.get("detail")
    vals: list[str] = []
    if isinstance(detail, dict):
        vals = [f"{k} {v}회" for k, v in list(detail.items())[:max_items]]
    elif isinstance(detail, list):
        for x in detail[:max_items]:
            if isinstance(x, dict):
                vals.append(clean_text(x.get("context") or x.get("value") or x.get("metric_name")))
            else:
                vals.append(clean_text(x))
    vals = [v for v in vals if v]
    return ", ".join(vals)


def _format_metric_short(m: dict[str, Any]) -> str:
    name = clean_text(m.get("metric_name"))
    value = clean_text(m.get("value"))
    unit = clean_text(m.get("unit"))
    detail = _metric_detail_text(m, 4)
    if detail:
        return f"{name} {value}{unit}({detail})"
    return f"{name} {value}{unit}"


def _all_section_text(sec: dict[str, Any]) -> str:
    chunks: list[str] = []
    for item in sec.get("items") or []:
        chunks += [clean_text(e.get("snippet")) for e in item.get("evidence") or []]
        for m in item.get("quant_metrics") or []:
            chunks.append(clean_text(m.get("metric_name")))
            chunks.append(_metric_detail_text(m, 10))
    return "\n".join([c for c in chunks if c])


def _metric_value(sec: dict[str, Any], names: list[str]) -> Any:
    for item in sec.get("items") or []:
        for m in item.get("quant_metrics") or []:
            mn = clean_text(m.get("metric_name"))
            if any(n in mn for n in names):
                return m.get("value")
    return None


def _metric_detail(sec: dict[str, Any], names: list[str]) -> list[str]:
    for item in sec.get("items") or []:
        for m in item.get("quant_metrics") or []:
            mn = clean_text(m.get("metric_name"))
            if any(n in mn for n in names):
                detail = m.get("detail")
                if isinstance(detail, dict):
                    return list(detail.keys())[:8]
                if isinstance(detail, list):
                    vals = []
                    for x in detail[:8]:
                        if isinstance(x, dict):
                            vals.append(clean_text(x.get("context") or x.get("value") or x.get("metric_name")))
                        else:
                            vals.append(clean_text(x))
                    return [v for v in vals if v]
    return []


def _score_section(sec: dict[str, Any]) -> tuple[int, str]:
    evidence_count = int(sec.get("evidence_count") or 0)
    metric_count = int(sec.get("quant_metric_count") or 0)
    official = 0
    signal_text = _all_section_text(sec)
    for item in sec.get("items") or []:
        official += sum(1 for e in item.get("evidence") or [] if _is_official(e))
    score = 1
    if evidence_count >= 2:
        score += 1
    if official >= 2:
        score += 1
    if metric_count >= 2:
        score += 1
    if re.search(r"\d", signal_text) or _term_count(signal_text, ["양산", "고객", "공급", "특허", "매출", "연구개발", "수율", "공정"]) >= 2:
        score += 1
    score = max(1, min(5, score))
    reason = f"직접근거 {evidence_count}건, 공식/DART/IR/특허 근거 {official}건, 정량화 지표 {metric_count}건"
    return score, reason


def _company_core_terms(company: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for k in ["core_keywords", "tech_keywords", "products", "keywords"]:
        for v in _lst(company.get(k)):
            v = clean_text(v)
            if v and v not in out:
                out.append(v)
    return out[:8]


def _result_sentence(company: dict[str, Any], sec: dict[str, Any]) -> str:
    name = clean_text(company.get("corp_name") or company.get("name") or "해당 기업")
    category = clean_text(sec.get("category"))
    terms = _metric_detail(sec, ["확인 핵심 기술", "제품/서비스 축", "활용/확장 산업", "고객 효익", "진입장벽", "R&D"])
    core = terms or _company_core_terms(company)
    core_text = ", ".join(core[:3]) if core else "핵심 기술"
    freq = _metric_value(sec, ["기술 키워드 등장 빈도"])
    product_count = _metric_value(sec, ["적용 제품/공정 수", "제품/서비스 축 수"])
    benefit_count = _metric_value(sec, ["고객 효익 키워드 수"])
    barrier_count = _metric_value(sec, ["진입장벽/대체난이도 신호 수"])
    rd_count = _metric_value(sec, ["R&D/투자 신호 수"])
    industry_count = _metric_value(sec, ["활용/확장 산업 수"])
    numeric_count = _metric_value(sec, ["성능/공정 정량 수치", "매출/성장 정량 신호", "효익 관련 정량 수치", "장벽 관련 정량 수치", "R&D 관련 정량 수치"])

    if category == "대표 기술":
        freq_text = f"{freq}회" if freq is not None else f"근거 {sec.get('evidence_count', 0)}건"
        pc_text = f"{product_count}개" if product_count is not None else "확인된"
        num_text = f"수치 문맥 {numeric_count}건" if numeric_count else "양산·공정·기술 문맥"
        return f"{name}은 {core_text} 기반 기술/공정 기업으로, 관련 기술은 실제 원천에서 {freq_text} 확인됩니다. 해당 기술은 {pc_text} 제품·공정 영역과 연결되며, {num_text}을 통해 구현 방향을 판단합니다."
    if category == "핵심 제품/서비스":
        pc_text = f"{product_count}개" if product_count is not None else f"{len(core[:3])}개"
        return f"핵심 제품/서비스는 {core_text} 중심으로 확인됩니다. 실제 원천 기준 {pc_text} 제품·서비스 축이 추출되며, 매출·성장 정량 신호는 DART/IR 문맥과 결합해 수익성 기여 판단에 사용합니다."
    if category == "고객 구매 이유":
        bc_text = f"{benefit_count}개" if benefit_count is not None else "확인된"
        return f"고객 구매 이유는 {core_text} 관련 성능·품질·양산 효익으로 정리됩니다. 실제 근거에서 고객 효익 신호 {bc_text}가 확인되며, 단순 기술 키워드가 아니라 적용처·성능·양산 문맥과 함께 해석합니다."
    if category == "경쟁 우위/대체가능성":
        bt = f"{barrier_count}개" if barrier_count is not None else "확인된"
        return f"경쟁 우위는 {core_text}와 연결된 특허·공정·양산 경험을 중심으로 확인됩니다. 대체가능성 판단에는 특허 수 자체보다 고객 승인, 공정 난이도, 양산 경험 등 {bt} 장벽 신호를 함께 반영합니다."
    if category == "활용 및 확장 산업":
        it = f"{industry_count}개" if industry_count is not None else "확인된"
        return f"활용·확장 산업은 {core_text}로 확인됩니다. 실제 수집 근거에서 {it} 적용 산업/Application이 추출되어 기술 확장성을 보조적으로 설명합니다."
    if category == "진입 부담/장벽":
        bt = f"{barrier_count}개" if barrier_count is not None else "확인된"
        return f"진입 부담은 양산 공정, 고객 승인, 품질 검증, 노하우 축적 여부를 중심으로 판단됩니다. 현재 근거에서는 {bt} 장벽 신호가 확인되며, 이는 기술성보다 사업화 방어력 판단에 활용됩니다."
    if category == "R&D 강도":
        rt = f"{rd_count}개" if rd_count is not None else "확인된"
        return f"R&D 강도는 연구개발·설비투자·개발과제의 지속성을 기준으로 봅니다. 실제 근거에서 R&D/투자 신호 {rt}가 확인되며, 기술 유지·개선 가능성의 보조 지표로 사용합니다."
    return f"{category}는 실제 원천 근거 {sec.get('evidence_count', 0)}건과 정량화 지표 {sec.get('quant_metric_count', 0)}건을 기준으로 판단합니다."


def build_sections(harvest: dict[str, Any], company: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    by_cat = {clean_text(s.get("category")): s for s in harvest.get("section_items") or []}
    for cat in TECH_SECTION_ORDER:
        sec = by_cat.get(cat)
        if not sec:
            continue
        score, reason = _score_section(sec)
        new_sec = dict(sec)
        new_sec["score"] = score
        new_sec["score_reason"] = reason
        new_sec["result"] = _result_sentence(company, sec)
        out.append(new_sec)
    # 템플릿에 다른 대분류가 있으면 뒤에 추가
    for sec in harvest.get("section_items") or []:
        if clean_text(sec.get("category")) in TECH_SECTION_ORDER:
            continue
        score, reason = _score_section(sec)
        new_sec = dict(sec)
        new_sec["score"] = score
        new_sec["score_reason"] = reason
        new_sec["result"] = _result_sentence(company, sec)
        out.append(new_sec)
    return out


def build_score_report(company: dict[str, Any], sections: list[dict[str, Any]], harvest: dict[str, Any]) -> dict[str, Any]:
    axes: list[dict[str, Any]] = []
    for sec in sections:
        axes.append({
            "category": sec.get("category"),
            "axis": sec.get("axis"),
            "score": sec.get("score"),
            "reason": sec.get("score_reason"),
            "result": sec.get("result"),
        })
    total = sum(int(x.get("score") or 0) for x in axes)
    # 근거 빈약 시 과점 방지: 고품질을 원하므로 근거가 약하면 점수를 보수적으로 제한
    if len(harvest.get("docs") or []) < 2:
        total = min(total, 22)
    if len(harvest.get("quantitative_signals") or []) < 8:
        total = min(total, 25)
    total = max(7, min(35, total))
    if total >= 30:
        judgment = "기술-사업화 연결 우수형"
    elif total >= 25:
        judgment = "기술-사업화 연결 검증형"
    elif total >= 18:
        judgment = "기술 경쟁형"
    else:
        judgment = "기술 보완 검토형"
    return {
        "company_name": clean_text(company.get("corp_name") or company.get("name")),
        "axes": axes,
        "details": axes,
        "total_score": total,
        "max_score": 35,
        "strengths": [a["axis"] for a in axes if int(a.get("score") or 0) >= 4],
        "weaknesses": [a["axis"] for a in axes if int(a.get("score") or 0) <= 2],
        "judgment": judgment,
        "quality_flags": harvest.get("quality_flags", []),
    }


def build_tech_to_value_bridge(company: dict[str, Any], harvest: dict[str, Any], sections: list[dict[str, Any]], score_report: dict[str, Any]) -> dict[str, Any]:
    text = "\n".join(_all_section_text(s) for s in sections)
    commercial = _term_count(text, COMMERCIALIZATION_TERMS)
    production = _term_count(text, PRODUCTION_TERMS)
    value = _term_count(text, VALUE_TERMS)
    ip = _term_count(text, IP_TERMS)
    official_docs = sum(1 for d in harvest.get("docs", []) if clean_text(d.get("source_type")) in {"dart_filing", "official_homepage", "ir", "patent", "local_tech_source"})
    metric_count = len(harvest.get("quantitative_signals") or [])

    tech_agent_raw_score = round((int(score_report.get("total_score") or 0) / max(int(score_report.get("max_score") or 35), 1)) * 100, 2)

    base_signal_score = 8
    base_signal_score += min(22, commercial * 3.5)
    base_signal_score += min(18, production * 3)
    base_signal_score += min(24, value * 4)
    base_signal_score += min(14, ip * 2)
    base_signal_score += min(8, official_docs * 1.5)
    base_signal_score += min(6, metric_count // 3)

    score = base_signal_score
    penalties: list[str] = []
    if commercial < 2:
        score -= 8
        penalties.append("고객 채택/적용처 연결 근거 부족")
    if production < 2:
        score -= 6
        penalties.append("양산·공정 검증 근거 부족")
    if value < 2:
        score -= 10
        penalties.append("매출·수익성·FCF 연결 근거 부족")
    if official_docs < 2:
        score -= 7
        penalties.append("공식/DART/IR/특허 근거 부족")
    if value < 2 or commercial < 2:
        score = min(score, 72)

    auditor_adjusted_score = round(max(0, min(100, score)), 2)

    if auditor_adjusted_score >= 78:
        grade = "VALUE_CONVERSION_CONFIRMED"
    elif auditor_adjusted_score >= 55:
        grade = "COMMERCIALIZATION_WATCH"
    else:
        grade = "TECH_FINANCE_GAP"
    return {
        "score": auditor_adjusted_score,
        "tech_agent_raw_score": tech_agent_raw_score,
        "base_signal_score": round(max(0, min(100, base_signal_score)), 2),
        "auditor_adjusted_score": auditor_adjusted_score,
        "auditor_conservative_adjustment": round(tech_agent_raw_score - auditor_adjusted_score, 2),
        "grade": grade,
        "policy": "기술 우위는 고객사 채택, 양산, 매출 전환, FCF 개선 근거와 연결될 때만 가치평가 가산 요인으로 반영한다.",
        "interpretation": "기술·제품 근거가 가치평가 보조 근거로 쓰이려면 고객 적용, 양산, 매출/현금흐름 연결이 함께 확인되어야 합니다.",
        "components": {
            "commercialization_hits": commercial,
            "production_hits": production,
            "value_hits": value,
            "ip_hits": ip,
            "official_doc_count": official_docs,
            "quantitative_signal_count": metric_count,
        },
        "penalties": penalties,
        "evidence_samples": [e for s in sections for item in s.get("items", []) for e in item.get("evidence", [])][:8],
    }


def _safe_claim_text(value: Any, limit: int = 260) -> str:
    text = normalize_spaces(clean_text(value), limit=limit)
    return text or ""


def _is_bad_evidence_snippet(snippet: str) -> bool:
    s = normalize_spaces(snippet, limit=800)
    if not s:
        return True

    bad_patterns = [
        "본문기 KR EN",
        "맵 -->",
        "CAREERS",
        "FAQ",
        "company.yaml 등록 URL",
        "내용 없음",
        "Open API",
        "Instagram Badge",
    ]
    if any(p in s for p in bad_patterns):
        return True

    if is_probably_mojibake(s):
        return True

    # 홈페이지 메뉴만 긁힌 경우 제거
    menu_words = ["COMPANY", "BUSINESS", "IR", "ESG", "CAREERS", "R&D"]
    if sum(1 for w in menu_words if w in s) >= 5 and "반도체" not in s and "패키지" not in s:
        return True

    return False


def _evidence_source(ev: dict[str, Any]) -> str:
    source_url = ev.get("source_url") or ev.get("url") or ""
    source_path = ev.get("source_path") or ev.get("path") or ""
    source_title = ev.get("source_title") or ev.get("title") or ""

    if source_url:
        return normalize_spaces(source_url)
    if source_path:
        return normalize_spaces(source_path)
    if source_title:
        return normalize_spaces(source_title)
    return "source_not_specified"


def _source_type_rank(source_type: str) -> int:
    st = (source_type or "").lower()
    if "dart" in st or "filing" in st:
        return 0
    if "patent" in st or "kipris" in st:
        return 1
    if "ir" in st:
        return 2
    if "official" in st or "homepage" in st:
        return 3
    if "news" in st or "rss" in st:
        return 4
    return 9


def _collect_good_section_evidence(
    sections: list[dict[str, Any]],
    category_keywords: list[str],
    limit: int = 2,
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []

    for sec in sections:
        category = normalize_spaces(sec.get("category") or "")
        if not any(k in category for k in category_keywords):
            continue

        for item in sec.get("items") or []:
            for ev in item.get("evidence") or []:
                snippet = normalize_spaces(ev.get("snippet") or "", limit=700)
                source = _evidence_source(ev)
                source_type = normalize_spaces(ev.get("source_type") or "")

                if _is_bad_evidence_snippet(snippet):
                    continue
                if not source or source == "source_not_specified":
                    continue

                found.append(
                    {
                        "source_type": source_type,
                        "source": source,
                        "snippet": snippet,
                        "source_title": normalize_spaces(ev.get("source_title") or ev.get("title") or ""),
                    }
                )

    # DART/특허/IR 우선, 중복 제거
    found.sort(key=lambda x: _source_type_rank(str(x.get("source_type") or "")))

    unique: list[dict[str, Any]] = []
    seen = set()
    for ev in found:
        key = (ev.get("source"), ev.get("snippet")[:80])
        if key in seen:
            continue
        seen.add(key)
        unique.append(ev)
        if len(unique) >= limit:
            break

    return unique


def _append_evidence(
    evidences: list[dict[str, Any]],
    eid: str,
    source_type: str,
    source: str,
    metric: str,
    snippet: str,
    value: Any = None,
    unit: str | None = None,
    period: str | None = None,
) -> str:
    evidences.append(
        {
            "evidence_id": eid,
            "source_type": normalize_spaces(source_type),
            "source": normalize_spaces(source),
            "metric": normalize_spaces(metric),
            "value": value,
            "unit": normalize_spaces(unit) if unit else None,
            "period": normalize_spaces(period) if period else None,
            "snippet": normalize_spaces(snippet, limit=600),
        }
    )
    return eid


def _metric_value(ph: dict[str, Any], names: list[str], default: Any = 0) -> Any:
    for m in ph.get("metrics") or []:
        metric_name = normalize_spaces(m.get("metric_name") or "")
        if any(n in metric_name for n in names):
            return m.get("value", default)
    return default


def _metric_unit(ph: dict[str, Any], names: list[str], default: str = "건") -> str:
    for m in ph.get("metrics") or []:
        metric_name = normalize_spaces(m.get("metric_name") or "")
        if any(n in metric_name for n in names):
            return normalize_spaces(m.get("unit") or default)
    return default


def _patent_top_ipc(ph: dict[str, Any]) -> str:
    top_ipc = ph.get("top_ipc") or ph.get("top_ipc_prefixes") or []
    if isinstance(top_ipc, list) and top_ipc:
        vals = []
        for x in top_ipc[:5]:
            if isinstance(x, dict):
                vals.append(str(x.get("ipc") or x.get("code") or x.get("name") or ""))
            else:
                vals.append(str(x))
        vals = [normalize_spaces(v) for v in vals if normalize_spaces(v)]
        if vals:
            return ", ".join(vals)

    for m in ph.get("metrics") or []:
        metric_name = normalize_spaces(m.get("metric_name") or "")
        if "IPC" in metric_name or "CPC" in metric_name:
            detail = m.get("detail")
            if isinstance(detail, list):
                vals = [normalize_spaces(v) for v in detail[:5] if normalize_spaces(v)]
                if vals:
                    return ", ".join(vals)
            value = normalize_spaces(m.get("value") or "")
            if value:
                return value

    return "IPC/CPC 분류 확인"


def _representative_patent_snippet(ph: dict[str, Any]) -> str:
    reps = ph.get("representative_patents") or []
    if not reps:
        return "KIPRIS 정규화 파일에서 대표 특허 목록은 별도 확인이 필요합니다."

    parts = []
    for r in reps[:3]:
        title = normalize_spaces(r.get("title") or r.get("invention_title") or "특허명 미확인")
        status = normalize_spaces(r.get("register_status") or r.get("status") or "")
        year = normalize_spaces(r.get("application_year") or r.get("year") or "")
        hits = r.get("tech_keyword_hits") or []
        hit_text = ", ".join(normalize_spaces(h) for h in hits[:4] if normalize_spaces(h))
        parts.append(f"{title}({year}, {status}, 기술매칭: {hit_text or '확인 필요'})")
    return "; ".join(parts)


def build_claims_and_evidences(
    company: dict[str, Any],
    sections: list[dict[str, Any]],
    bridge: dict[str, Any],
    harvest: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Auditor 통과용 claims/evidences 생성 함수.

    핵심 원칙:
    - 보고서는 풍부하게 써도 되지만, claims에는 검증 가능한 주장만 넣는다.
    - R&D/고객사/매출 전환처럼 공개 근거가 약한 문장은 claim에서 제외한다.
    - 정량 수치는 반드시 source/value/unit/period 또는 KIPRIS/DART 원천과 함께 evidence로 만든다.
    - 한글 깨짐은 JSON 저장 전에 복구한다.
    """
    company_name = normalize_spaces(company.get("corp_name") or company.get("name") or "기업")
    claims: list[dict[str, Any]] = []
    evidences: list[dict[str, Any]] = []
    eid_num = 0

    def next_eid() -> str:
        nonlocal eid_num
        eid = f"tech.ev.{eid_num:03d}"
        eid_num += 1
        return eid

    # 1) Tech-to-Value Bridge 자체 근거
    bridge_score = bridge.get("score")
    bridge_grade = bridge.get("grade")
    bridge_policy = normalize_spaces(
        bridge.get("policy")
        or "기술 우위는 고객사 채택, 양산, 매출 전환, FCF 개선 근거와 연결될 때만 가치평가 가산 요인으로 반영한다."
    )

    bridge_eid = _append_evidence(
        evidences=evidences,
        eid=next_eid(),
        source_type="tech_to_value_bridge",
        source="Tech Agent internal scoring with actual-source evidence and KIPRIS patent overlay",
        metric="Tech-to-Value Bridge Score",
        value=bridge_score,
        unit="/100",
        period=None,
        snippet=f"Tech-to-Value Bridge Score: {bridge_score} / 100; 판정: {bridge_grade}; 원칙: {bridge_policy}",
    )

    claims.append(
        {
            "claim_id": "tech.cl.000",
            "text": f"{company_name}의 Tech-to-Value Bridge Score는 {bridge_score}/100이며 판정은 {bridge_grade}이다.",
            "evidence_ids": [bridge_eid],
        }
    )

    # 2) 대표 기술 / 핵심 제품은 DART·IR 근거 중심으로만 claim화
    tech_evs = _collect_good_section_evidence(sections, ["대표 기술", "핵심 제품"], limit=3)
    tech_eids: list[str] = []
    for ev in tech_evs:
        tech_eids.append(
            _append_evidence(
                evidences=evidences,
                eid=next_eid(),
                source_type=ev.get("source_type") or "technology",
                source=ev.get("source") or "",
                metric="대표 기술 및 핵심 제품",
                snippet=ev.get("snippet") or "",
            )
        )

    if tech_eids:
        claims.append(
            {
                "claim_id": f"tech.cl.{len(claims):03d}",
                "text": f"{company_name}는 원천 문서 기준 WLP/FOWLP·반도체 패키징·후공정 관련 기술 또는 제품 축을 보유한 기업으로 확인된다.",
                "evidence_ids": tech_eids,
            }
        )

    # 3) 사업화/확장성은 과장하지 않고 보수적으로 claim화
    commercialization_evs = _collect_good_section_evidence(
        sections,
        ["고객 구매 이유", "활용", "확장", "진입 부담", "경쟁 우위"],
        limit=3,
    )
    comm_eids: list[str] = []
    for ev in commercialization_evs:
        comm_eids.append(
            _append_evidence(
                evidences=evidences,
                eid=next_eid(),
                source_type=ev.get("source_type") or "technology",
                source=ev.get("source") or "",
                metric="사업화·확장성 보조 근거",
                snippet=ev.get("snippet") or "",
            )
        )

    if comm_eids:
        claims.append(
            {
                "claim_id": f"tech.cl.{len(claims):03d}",
                "text": f"{company_name}의 기술성은 사업화 가능성을 보조하지만, 최종 가치평가 가산에는 고객 채택·양산·매출 전환·FCF 개선 근거와의 결합 검증이 필요하다.",
                "evidence_ids": [bridge_eid] + comm_eids[:2],
            }
        )

    # 4) KIPRIS 특허 정량화 claim
    ph = harvest.get("patent_harvest") or {}
    if ph.get("normalized_record_count") or ph.get("company_matched_record_count"):
        normalized_count = ph.get("normalized_record_count") or 0
        matched_count = ph.get("company_matched_record_count") or 0
        registered_count = _metric_value(ph, ["등록 특허", "등록특허"], 0)
        alive_count = _metric_value(ph, ["존속", "유효"], 0)
        recent_count = _metric_value(ph, ["최근 5년", "최근5년"], 0)
        h01l_count = _metric_value(ph, ["H01L"], 0)
        ipc_text = _patent_top_ipc(ph)
        rep_text = _representative_patent_snippet(ph)

        patent_source = (
            ph.get("source_file")
            or ph.get("source_path")
            or ph.get("normalized_csv_path")
            or f"data/{company.get('output_category') or '반도체'}/{company.get('corp_name') or company_name}/tech/source/KIPRIS patent file"
        )

        patent_eid = _append_evidence(
            evidences=evidences,
            eid=next_eid(),
            source_type="kipris_patent",
            source=patent_source,
            metric="KIPRIS 특허 정량 지표",
            value=matched_count,
            unit="건",
            period=None,
            snippet=(
                f"KIPRIS 정규화 결과: 전체 정규화 {normalized_count}건, 회사 매칭 {matched_count}건, "
                f"등록 특허 {registered_count}건, 존속 가능 특허 {alive_count}건, 최근 5년 특허 {recent_count}건, "
                f"H01L 반도체 핵심 IPC {h01l_count}건, 주요 IPC/CPC: {ipc_text}. 대표 특허: {rep_text}"
            ),
        )

        claims.append(
            {
                "claim_id": f"tech.cl.{len(claims):03d}",
                "text": (
                    f"KIPRIS 정규화 데이터 기준 {company_name} 관련 특허는 회사 매칭 {matched_count}건, "
                    f"등록 특허 {registered_count}건, 최근 5년 특허 {recent_count}건으로 집계된다."
                ),
                "evidence_ids": [patent_eid],
            }
        )

    # 5) R&D 강도 claim은 일단 제외
    # 이유: 현재 Auditor가 R&D 관련 공개 근거를 unsupported로 판단하고 있으므로,
    # R&D 비용/비율/개발과제/설비투자 금액이 DART 표에서 안정 추출되기 전까지 claim으로 넘기지 않는다.

    claims = deep_clean(claims)
    evidences = deep_clean(evidences)

    # evidence_id 없는 claim 방지
    valid_eids = {e.get("evidence_id") for e in evidences}
    safe_claims = []
    for c in claims:
        ids = [eid for eid in c.get("evidence_ids", []) if eid in valid_eids]
        text = normalize_spaces(c.get("text") or "")
        if not ids:
            continue
        if not text:
            continue
        if is_probably_mojibake(text):
            continue
        c["evidence_ids"] = ids
        c["text"] = text
        safe_claims.append(c)

    return safe_claims[:8], evidences[:30]


def _opinion(total_score: int) -> str:
    if total_score >= 29:
        return "매수"
    if total_score >= 18:
        return "보유"
    return "매도"


def _best_item_line(item: dict[str, Any]) -> str:
    metrics = item.get("quant_metrics") or []
    metric_text = "; ".join(_format_metric_short(m) for m in metrics[:2]) if metrics else "정량 수치 직접 미확인"
    evs = item.get("evidence") or []
    ev_text = clean_text(evs[0].get("snippet")) if evs else "핵심 원천 근거 추가 필요"
    src_text = _source_label(evs[0]) if evs else "-"
    note = "정량화 가능" if metrics else "비고: 수치·단위·기간이 있는 DART/IR/KIPRIS 원천 필요"
    if not evs:
        note += "; 근거 보완 필요"
    return f"| {clean_text(item.get('item_name'))} | {metric_text} | {ev_text[:180]} | {src_text[:110]} | {note[:120]} |"


def make_markdown_report(company: dict[str, Any], sections: list[dict[str, Any]], score_report: dict[str, Any], bridge: dict[str, Any], harvest: dict[str, Any]) -> str:
    name = clean_text(company.get("corp_name") or company.get("name") or "기업")
    lines = [
        f"# {name} Tech Agent 실제 원천 기반 고도화 보고서 v12",
        "",
        "## 1. 기술 경쟁력 요약",
        f"- 총점: {score_report.get('total_score')} / 35",
        f"- 종합판정: {score_report.get('judgment')}",
        f"- 근거 수집: 실제 문서 {harvest.get('document_count')}건, 통과 URL {harvest.get('accepted_url_count')}건, 제외 URL {harvest.get('rejected_url_count')}건, 정량 신호 {len(harvest.get('quantitative_signals') or [])}건",
        "- 템플릿 사용 원칙: tech_template.xlsx 기업별 예시값은 복사하지 않고, 베이스/수식 시트의 대출처·중출처·정량화 규칙만 사용",
        "- v12 개선점: KIPRIS/IP 정량 신호 자동 반영, Tech Agent 원점수와 Auditor 보수 반영 점수 분리, 정량화 불가 항목 비고 처리",
        "",
        "## 2. Tech-to-Value Bridge Score",
        f"- Tech Agent 원점수: {bridge.get('tech_agent_raw_score')} / 100",
        f"- Auditor 보수 반영 점수: {bridge.get('auditor_adjusted_score')} / 100",
        f"- Tech-to-Value Bridge Score: {bridge.get('score')} / 100",
        f"- 판정: {bridge.get('grade')}",
        f"- 원칙: {bridge.get('policy')}",
        f"- 해석: {bridge.get('interpretation')}",
    ]
    if bridge.get("penalties"):
        lines.append(f"- 보정 사유: {', '.join(bridge.get('penalties') or [])}")
    lines += ["", "## 3. 엑셀 틀 기반 7개 기술평가 축별 직접 추출 결과"]
    for idx, sec in enumerate(sections, 1):
        lines += [
            f"### 3-{idx}. {sec.get('category')}",
            f"- 점수: {sec.get('score')} / 5 ({sec.get('axis')})",
            f"- 점수 근거: {sec.get('score_reason')}",
            f"- 대 출처 기준: {sec.get('major_source_plan')}",
            f"- 중 출처 기준: {sec.get('middle_source_plan')}",
            f"- 정량화 기준: {sec.get('quantifiable_plan')}",
            f"- 결과: {sec.get('result')}",
            "",
            "| 항목명 | 정량화 결과 | 핵심 근거 문장 | 출처 | 비고 |",
            "|---|---:|---|---|---|",
        ]
        for item in sec.get("items") or []:
            lines.append(_best_item_line(item))
        lines.append("")
    lines += ["## 4. URL·근거 품질 관리"]
    if harvest.get("quality_flags"):
        for flag in harvest.get("quality_flags") or []:
            lines.append(f"- {flag}")
    else:
        lines.append("- 주요 품질 플래그 없음")
    lines += [
        "",
        "## 5. Chair/Auditor 전달용 핵심 문장",
        f"- Tech Agent 원점수: {bridge.get('tech_agent_raw_score')} / 100",
        f"- Auditor 보수 반영 점수: {bridge.get('auditor_adjusted_score')} / 100",
        f"- Tech-to-Value Bridge Score: {bridge.get('score')} / 100",
        f"- 판정: {bridge.get('grade')}",
        f"- {bridge.get('policy')}",
        "- 기술 점수는 단독 투자 의견이 아니라, 고객 채택·양산·매출 전환·FCF 개선 근거와 결합될 때만 가치평가 보조 신호로 사용합니다.",
    ]
    return "\n".join(lines)


def write_outputs(
    company_dir: str,
    company: dict[str, Any],
    sections: list[dict[str, Any]],
    score_report: dict[str, Any],
    bridge: dict[str, Any],
    harvest: dict[str, Any],
    claims: list[dict[str, Any]],
    evidences: list[dict[str, Any]],
    output_dir: str | Path = OUTPUT_DIR,
) -> dict[str, str]:
    out = ensure_dir(Path(output_dir))
    packet_dir = ensure_dir(agent_output_path(company_dir, "tech", "tech.json").parent)
    packet = {
        "agent": "tech",
        "version": "v11_excel_frame_actual_source_concise_quantification",
        "company": clean_text(company.get("corp_name") or company.get("name") or company_dir),
        "company_dir": company_dir,
        "opinion": _opinion(int(score_report.get("total_score") or 0)),
        "tech_score": score_report.get("total_score"),
        "score_report": score_report,
        "tech_to_value_inputs": bridge,
        "claims": claims,
        "evidences": evidences,
        "categories": sections,
        "source_contexts": [
            {
                "title": d.get("title"),
                "source_type": d.get("source_type"),
                "url": d.get("url"),
                "path": d.get("path"),
                "snippet": clean_text(d.get("text"))[:450],
                "relevance_score": d.get("relevance_score"),
            }
            for d in (harvest.get("docs") or [])[:15]
        ],
        "limitations": [
            "tech_template.xlsx의 기업별 예시값은 복사 근거로 사용하지 않고, 대출처·중출처·정량화 규칙만 추출 설계로 사용합니다.",
            "기술 점수만으로 매수/매도 결론을 만들지 않고 Tech-to-Value Bridge로 고객 채택·양산·매출 전환·FCF 연결성을 확인합니다.",
            "회사 식별어가 약하거나 타기업 중심인 URL은 제외합니다.",
        ],
        "evidence_harvest_summary": {
            "document_count": harvest.get("document_count"),
            "accepted_url_count": harvest.get("accepted_url_count"),
            "rejected_url_count": harvest.get("rejected_url_count"),
            "quality_flags": harvest.get("quality_flags"),
            "template_usage": harvest.get("template_usage"),
        },
    }
    report_path = out / f"{company_dir}_tech_high_quality_report.md"
    packet_path = out / f"{company_dir}_tech_agent_packet.json"
    bridge_path = out / f"{company_dir}_tech_to_value_inputs.json"
    chair_packet_path = packet_dir / "tech.json"
    # JSON 저장 직전 전체 한글 깨짐 복구
    packet = deep_clean(packet)
    bridge = deep_clean(bridge)
    sections = deep_clean(sections)
    score_report = deep_clean(score_report)
    harvest = deep_clean(harvest)

    report_md = make_markdown_report(company, sections, score_report, bridge, harvest)
    report_md = repair_mojibake_text(report_md)

    report_path.write_text(report_md, encoding="utf-8")
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    bridge_path.write_text(json.dumps(bridge, ensure_ascii=False, indent=2), encoding="utf-8")
    chair_packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "report_md": str(report_path),
        "packet_json": str(packet_path),
        "chair_packet_json": str(chair_packet_path),
        "tech_to_value_json": str(bridge_path),
    }
