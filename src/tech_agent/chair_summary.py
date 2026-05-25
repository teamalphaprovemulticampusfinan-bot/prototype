from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from common.output_paths import agent_output_dir, output_candidates, read_json_first

ROOT = Path(__file__).resolve().parents[2]


try:
    from .ip_evidence_composite_merge import (
        append_ip_evidence_composite_to_markdown,
        merge_ip_evidence_composite_into_summary,
    )
except Exception:
    try:
        from tech_agent.ip_evidence_composite_merge import (
            append_ip_evidence_composite_to_markdown,
            merge_ip_evidence_composite_into_summary,
        )
    except Exception:
        append_ip_evidence_composite_to_markdown = None
        merge_ip_evidence_composite_into_summary = None



try:  # deterministic Chair summary should follow the same rubric as prompts.py.
    from .prompts import (
        CAPITAL_AND_DILUTION_POLICY,
        DATA_QUALITY_POLICY,
        EVIDENCE_DEDUP_POLICY,
        FINAL_TECH_SCORE_POLICY,
        INVESTOR_OUTPUT_POLICY,
        LITERATURE_APPLICATION_POLICY,
        TECH_TO_VALUE_BRIDGE_PROMPT,
    )
except Exception:  # pragma: no cover - script fallback
    try:
        from tech_agent.prompts import (
            CAPITAL_AND_DILUTION_POLICY,
            DATA_QUALITY_POLICY,
            EVIDENCE_DEDUP_POLICY,
            FINAL_TECH_SCORE_POLICY,
            INVESTOR_OUTPUT_POLICY,
            LITERATURE_APPLICATION_POLICY,
            TECH_TO_VALUE_BRIDGE_PROMPT,
        )
    except Exception:
        CAPITAL_AND_DILUTION_POLICY = ""
        DATA_QUALITY_POLICY = ""
        EVIDENCE_DEDUP_POLICY = ""
        FINAL_TECH_SCORE_POLICY = {"weights": {}, "grade_thresholds": {}}
        INVESTOR_OUTPUT_POLICY = ""
        LITERATURE_APPLICATION_POLICY = ""
        TECH_TO_VALUE_BRIDGE_PROMPT = ""


def _tech_prompt_policy_snapshot() -> Dict[str, Any]:
    return {
        "final_tech_score_policy": FINAL_TECH_SCORE_POLICY,
        "tech_to_value_bridge_prompt": TECH_TO_VALUE_BRIDGE_PROMPT,
        "investor_output_policy": INVESTOR_OUTPUT_POLICY,
        "literature_application_policy": LITERATURE_APPLICATION_POLICY,
        "data_quality_policy": DATA_QUALITY_POLICY,
        "capital_and_dilution_policy": CAPITAL_AND_DILUTION_POLICY,
        "evidence_dedup_policy": EVIDENCE_DEDUP_POLICY,
    }


def _policy_short(text: Any, limit: int = 180) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()[:limit]

def _rel_project_path(value: Any) -> str:
    """Return a project-relative path string for repo portability."""
    if value is None:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""
    raw = raw.replace("\\", "/")
    try:
        p = Path(raw)
        if p.is_absolute():
            return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        pass
    m = re.search(r"(?:^|.*?)(data[\/].*)$", raw)
    if m:
        return m.group(1).replace("\\", "/")
    m = re.search(r"(?:^|.*?)(workspace[\/].*)$", raw)
    if m:
        return m.group(1).replace("\\", "/")
    m = re.search(r"(?:^|.*?)(src[\/].*)$", raw)
    if m:
        return m.group(1).replace("\\", "/")
    return raw.replace("\\", "/")


def _relativize_dict_paths(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _relativize_dict_paths(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_relativize_dict_paths(v) for v in data]
    if isinstance(data, (str, Path)):
        s = str(data)
        if "data" in s or "workspace" in s or ":\\" in s or ":/" in s or s.startswith("/"):
            return _rel_project_path(s)
    return data


GRADE_LABELS = {
    "VALUE_CONVERSION_CONFIRMED": "가치 전환 확인형",
    "COMMERCIALIZATION_WATCH": "사업화 추적형",
    "TECH_FINANCE_GAP": "기술-재무 괴리형",
    "TECH_EVIDENCE_WEAK": "근거 보강 필요형",
    "TECH_TO_VALUE_READY": "가치전환 준비형",
    "INVESTOR_TECH_CONVICTION": "투자자용 기술 확신형",
    "EVIDENCE_WEAK_OR_EARLY": "근거 보강 초기/제한형",
    "DISTINCTIVE_TECH_LEADER": "차별화 선도형",
    "DIFFERENTIATED_TECH_POSITION": "차별화 확인형",
    "MODERATE_DIFFERENTIATION": "보통 차별화형",
    "LIMITED_DIFFERENTIATION": "차별화 제한형",
    "IP_EVIDENCE_STRONG_POSITIVE": "IP 근거 강한 긍정형",
    "IP_EVIDENCE_POSITIVE": "IP 근거 긍정형",
    "IP_EVIDENCE_NEUTRAL": "IP 근거 중립형",
    "IP_EVIDENCE_WEAK": "IP 근거 취약형",
}

DIMENSION_LABELS = {
    "customer_adoption": "고객 채택",
    "mass_production": "양산",
    "revenue_conversion": "매출 전환",
    "fcf_cashflow": "FCF/현금흐름",
}

STATUS_LABELS = {
    "DIRECT_CONFIRMED": "직접 근거",
    "DIRECT_BUT_LIMITED": "직접 근거 일부",
    "INDIRECT_ONLY": "간접 근거",
    "NOT_CONFIRMED": "확인 제한",
    "CONFIRMED": "직접 근거",
    "PARTIAL": "부분 확인",
    "WEAK": "간접 근거",
}

NOISE_PATTERNS = [
    r"0\s*(회|개|건)",
    r"agent_output_unverified",
    r"self_generated",
    r"unverified",
]


def _read_json(path: Path) -> Optional[Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None
    return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _clean(text: Any, limit: int = 240) -> str:
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    if not s:
        return "확인 제한"

    s = s.replace('"', "").replace("`", "")

    for pat in NOISE_PATTERNS:
        s = re.sub(pat, "확인 제한", s, flags=re.IGNORECASE)

    return s[:limit] + ("..." if len(s) > limit else "")


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except Exception:
        return None


def _fmt_score(value: Any, suffix: str = "/100") -> str:
    x = _as_float(value)
    if x is None:
        return "확인 제한"
    return f"{x:.2f}{suffix}"


def _fmt_num(value: Any, digits: int = 0, suffix: str = "") -> str:
    x = _as_float(value)
    if x is None:
        return "확인 제한"
    if digits <= 0:
        return f"{x:,.0f}{suffix}"
    return f"{x:,.{digits}f}{suffix}"


def _fmt_rate(value: Any, digits: int = 2) -> str:
    x = _as_float(value)
    if x is None:
        return "확인 제한"
    if abs(x) <= 1:
        x *= 100
    return f"{x:,.{digits}f}%"


def _label_grade(grade: Any) -> str:
    raw = str(grade or "").strip()
    if not raw:
        return "확인 제한"
    return f"{GRADE_LABELS.get(raw, raw)}({raw})" if raw in GRADE_LABELS else raw


def _first_dict(*values: Any) -> Dict[str, Any]:
    for v in values:
        if isinstance(v, dict):
            return v
    return {}


def _first_value(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _load_packet(company_dir: str, filename: str) -> Dict[str, Any]:
    candidates = [agent_output_dir(company_dir, "tech", root=ROOT) / filename]
    candidates.extend(output_candidates(company_dir, "tech", filename, root=ROOT))
    data = read_json_first(candidates)
    return data if isinstance(data, dict) else {}


def _candidate_feature_paths(
    company_dir: str,
    company_name: str,
    names: List[str],
) -> List[Path]:
    slug = str(company_dir or "").strip()
    candidates: List[Path] = []

    out_dir = agent_output_dir(slug, "tech", root=ROOT)

    for name in names:
        candidates.append(out_dir / name)
        candidates.extend(output_candidates(slug, "tech", name, root=ROOT))

    data_root = ROOT / "data"

    if company_name and data_root.exists():
        for field_dir in data_root.glob("*"):
            if not field_dir.is_dir():
                continue

            cdir = field_dir / str(company_name) / "tech"
            for name in names:
                candidates.append(cdir / name)

    if slug and data_root.exists():
        for p in data_root.glob("*/*/tech"):
            if not p.is_dir():
                continue

            p_text = str(p).replace("\\", "/").lower()
            for name in names:
                if slug.lower() in name.lower() or slug.lower() in p_text:
                    candidates.append(p / name)

    seen: set[str] = set()
    deduped: List[Path] = []

    for path in candidates:
        key = str(path).replace("\\", "/")
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)

    return deduped


def _load_feature_by_names(
    company_dir: str,
    company_name: str,
    names: List[str],
) -> Dict[str, Any]:
    for path in _candidate_feature_paths(company_dir, company_name, names):
        data = _read_json(path)
        if isinstance(data, dict) and data:
            data = dict(data)
            data.setdefault("_source_file", _rel_project_path(path))
            return data
    return {}


def _extract_excel_frame(sections: List[Dict[str, Any]], limit: int = 7) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for sec in sections or []:
        if not isinstance(sec, dict):
            continue

        category = sec.get("category") or sec.get("title") or sec.get("name") or "기술 항목"
        item = sec.get("item") or sec.get("metric_name") or sec.get("subtitle") or category
        quant = (
            sec.get("quantification")
            or sec.get("quantitative_expression")
            or sec.get("metric_value")
            or sec.get("score")
        )
        evidence = (
            sec.get("evidence")
            or sec.get("basis")
            or sec.get("basis_text")
            or sec.get("summary")
            or sec.get("result_sentence")
        )
        note = sec.get("note") or sec.get("limitation") or sec.get("remark")
        score = sec.get("score") or sec.get("raw_score") or sec.get("rating")

        score_num = _as_float(score)
        if score_num is None:
            grade = "정성 확인"
        elif score_num >= 4.5:
            grade = "강"
        elif score_num >= 3.2:
            grade = "중"
        else:
            grade = "보강 필요"

        rows.append(
            {
                "category": _clean(category, 60),
                "item": _clean(item, 70),
                "quantification": _clean(quant, 100) if quant not in (None, "") else "정량화 가능 자료 확인 필요",
                "evidence": _clean(evidence, 150),
                "grade": grade,
                "note": _clean(note, 120) if note not in (None, "") else "필요 시 원천 근거 확인",
            }
        )

    return rows[:limit]


def _extract_ip_signals(ip_ml: Dict[str, Any], patent_harvest: Dict[str, Any]) -> Dict[str, Any]:
    raw = _first_dict(
        ip_ml.get("raw_metrics"),
        ip_ml.get("raw_signals"),
        ip_ml.get("source_signals"),
        patent_harvest,
    )

    return {
        "normalized_patent_text_records": (
            raw.get("normalized_patent_text_records")
            or raw.get("normalized_patent_records")
            or raw.get("normalized_records")
            or raw.get("normalized_record_count")
            or patent_harvest.get("normalized_record_count")
        ),
        "company_matched_patents": (
            raw.get("company_matched_patents")
            or raw.get("company_matched_records")
            or raw.get("company_matched_record_count")
            or patent_harvest.get("company_matched_record_count")
        ),
        "registered_patents": raw.get("registered_patents") or patent_harvest.get("registered_patent_count"),
        "alive_patents": raw.get("alive_patents") or raw.get("active_patents") or patent_harvest.get("alive_patent_count"),
        "recent_5y_patents": raw.get("recent_5y_patents") or patent_harvest.get("recent_5y_patent_count"),
        "ipc_cpc_classes": raw.get("ipc_cpc_classes") or raw.get("ipc_diversity") or patent_harvest.get("ipc_cpc_class_count"),
        "core_ipc_h01l_patents": raw.get("core_ipc_h01l_patents") or patent_harvest.get("core_ipc_h01l_patent_count"),
        "keyword_matches": raw.get("patent_keyword_matches") or patent_harvest.get("keyword_match_count"),
    }


def _extract_business_gate(momentum: Dict[str, Any]) -> List[Dict[str, Any]]:
    ev = momentum.get("tech_to_value_evidence_confidence") or momentum.get("evidence_confidence") or {}
    dims = ev.get("dimensions") if isinstance(ev.get("dimensions"), dict) else {}

    rows: List[Dict[str, Any]] = []

    for key in ("customer_adoption", "mass_production", "revenue_conversion", "fcf_cashflow"):
        row = dims.get(key) if isinstance(dims.get(key), dict) else {}
        status = row.get("status_kr") or STATUS_LABELS.get(str(row.get("status") or ""), "확인 제한")

        rows.append(
            {
                "dimension": DIMENSION_LABELS.get(key, key),
                "status": status,
                "score": row.get("score"),
                "direct_evidence_count": row.get("direct_evidence_count"),
                "indirect_evidence_count": row.get("indirect_evidence_count"),
                "limited_evidence_count": row.get("limited_evidence_count"),
            }
        )

    return rows


def _load_ip_legal_features(company_dir: str, company_name: str = "") -> Dict[str, Any]:
    slug = str(company_dir or "").strip()
    names = [
        "tech_ip_legal_features.json",
        f"{slug}_tech_ip_legal_features.json",
        f"{slug}_kipris_tech_ml_features.json",
        "kipris_tech_ml_features.json",
    ]
    return _load_feature_by_names(company_dir, company_name, names)


def _extract_ip_legal_summary(ip_legal: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(ip_legal, dict) or not ip_legal:
        return {}

    counts = ip_legal.get("core_counts") if isinstance(ip_legal.get("core_counts"), dict) else {}
    rates = ip_legal.get("core_rates") if isinstance(ip_legal.get("core_rates"), dict) else {}
    coverage = ip_legal.get("coverage") if isinstance(ip_legal.get("coverage"), dict) else {}
    scores = ip_legal.get("scores") if isinstance(ip_legal.get("scores"), dict) else {}
    bridge = (
        ip_legal.get("tech_to_value_bridge_adjustment")
        if isinstance(ip_legal.get("tech_to_value_bridge_adjustment"), dict)
        else {}
    )

    return {
        "total_patents": _first_value(counts.get("total_patents"), ip_legal.get("total_patents")),
        "registered_patents_estimated": _first_value(
            counts.get("registered_patents_estimated"),
            counts.get("registered_patents"),
            ip_legal.get("registered_patents_estimated"),
        ),
        "alive_patents_estimated": _first_value(
            counts.get("alive_patents_estimated"),
            counts.get("alive_patents"),
            ip_legal.get("alive_patents_estimated"),
        ),
        "negative_disposal_patents_estimated": _first_value(
            counts.get("negative_disposal_patents_estimated"),
            ip_legal.get("negative_disposal_patents_estimated"),
        ),
        "registration_rate_estimated": _first_value(
            rates.get("registration_rate_estimated"),
            ip_legal.get("registration_rate_estimated"),
        ),
        "alive_rate_among_registered_estimated": _first_value(
            rates.get("alive_rate_among_registered_estimated"),
            ip_legal.get("alive_rate_among_registered_estimated"),
        ),
        "negative_disposal_rate_estimated": _first_value(
            rates.get("negative_disposal_rate_estimated"),
            ip_legal.get("negative_disposal_rate_estimated"),
        ),
        "right_holder_coverage": _first_value(
            coverage.get("right_holder"),
            rates.get("right_holder_coverage"),
            ip_legal.get("right_holder_coverage"),
        ),
        "right_transfer_history_coverage": _first_value(
            coverage.get("right_transfer_history"),
            rates.get("right_transfer_history_coverage"),
            ip_legal.get("right_transfer_history_coverage"),
        ),
        "fee_payment_status_coverage": _first_value(
            coverage.get("fee_payment_status"),
            rates.get("fee_payment_status_coverage"),
            ip_legal.get("fee_payment_status_coverage"),
        ),
        "abstract_coverage": _first_value(
            coverage.get("abstract"),
            rates.get("abstract_coverage"),
            ip_legal.get("abstract_coverage"),
        ),
        "drawing_coverage": _first_value(
            coverage.get("drawing"),
            rates.get("drawing_coverage"),
            ip_legal.get("drawing_coverage"),
        ),
        "legal_stability_score_estimated": _first_value(
            scores.get("legal_stability_score_estimated"),
            ip_legal.get("legal_stability_score_estimated"),
        ),
        "kipris_tech_ml_score": _first_value(
            scores.get("kipris_tech_ml_score"),
            ip_legal.get("kipris_tech_ml_score"),
        ),
        "bridge_adjustment_points": _first_value(
            bridge.get("bridge_adjustment_points"),
            ip_legal.get("bridge_adjustment_points"),
        ),
        "bridge_signal": _first_value(
            bridge.get("bridge_signal"),
            ip_legal.get("bridge_signal"),
        ),
        "usage_rule": _first_value(
            bridge.get("usage_rule"),
            ip_legal.get("usage_rule"),
            "권리 안정성은 Tech-to-Value Bridge의 보수적 보정 신호로만 사용하고, 직접 사업화 증거로 해석하지 않습니다.",
        ),
        "source_file": ip_legal.get("_source_file") or ip_legal.get("source_file"),
    }


def _load_ip_claim_features(company_dir: str, company_name: str = "") -> Dict[str, Any]:
    slug = str(company_dir or "").strip()
    names = [
        "tech_ip_claim_features.json",
        f"{slug}_tech_ip_claim_features.json",
    ]
    return _load_feature_by_names(company_dir, company_name, names)


def _extract_ip_claim_summary(ip_claim: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(ip_claim, dict) or not ip_claim:
        return {}

    counts = ip_claim.get("core_counts") if isinstance(ip_claim.get("core_counts"), dict) else {}
    rates = ip_claim.get("core_rates") if isinstance(ip_claim.get("core_rates"), dict) else {}
    scores = ip_claim.get("scores") if isinstance(ip_claim.get("scores"), dict) else {}
    bridge = (
        ip_claim.get("tech_to_value_bridge_adjustment")
        if isinstance(ip_claim.get("tech_to_value_bridge_adjustment"), dict)
        else {}
    )

    target_patent_count = _first_value(
        counts.get("target_patent_count"),
        ip_claim.get("target_patent_count"),
    )
    patents_with_claims = _first_value(
        counts.get("patents_with_claims"),
        ip_claim.get("patents_with_claims"),
    )
    claim_count = _first_value(
        counts.get("claim_count"),
        ip_claim.get("claim_count"),
    )
    independent_claim_count = _first_value(
        counts.get("independent_claim_count_estimated"),
        counts.get("independent_claim_count"),
        ip_claim.get("independent_claim_count_estimated"),
        ip_claim.get("independent_claim_count"),
    )

    avg_claims_per_patent = _first_value(
        rates.get("avg_claims_per_patent"),
        ip_claim.get("avg_claims_per_patent"),
    )

    if avg_claims_per_patent is None:
        try:
            if patents_with_claims and claim_count:
                avg_claims_per_patent = round(float(claim_count) / float(patents_with_claims), 4)
        except Exception:
            avg_claims_per_patent = None

    independent_claim_ratio = _first_value(
        rates.get("independent_claim_ratio"),
        ip_claim.get("independent_claim_ratio"),
    )

    if independent_claim_ratio is None:
        try:
            if claim_count and independent_claim_count is not None:
                independent_claim_ratio = round(float(independent_claim_count) / float(claim_count), 4)
        except Exception:
            independent_claim_ratio = None

    return {
        "status": ip_claim.get("status"),
        "target_patent_count": target_patent_count,
        "patents_with_claims": patents_with_claims,
        "claim_collection_coverage": _first_value(
            rates.get("claim_collection_coverage"),
            ip_claim.get("claim_collection_coverage"),
        ),
        "claim_count": claim_count,
        "independent_claim_count_estimated": independent_claim_count,
        "avg_claims_per_patent": avg_claims_per_patent,
        "independent_claim_ratio": independent_claim_ratio,
        "claim_defense_score_estimated": _first_value(
            scores.get("claim_defense_score_estimated"),
            ip_claim.get("claim_defense_score_estimated"),
        ),
        "parse_error_count": _first_value(
            counts.get("parse_error_count"),
            ip_claim.get("parse_error_count"),
        ),
        "bridge_adjustment_points": _first_value(
            bridge.get("bridge_adjustment_points"),
            ip_claim.get("bridge_adjustment_points"),
        ),
        "bridge_signal": _first_value(
            bridge.get("bridge_signal"),
            ip_claim.get("bridge_signal"),
        ),
        "usage_rule": _first_value(
            bridge.get("usage_rule"),
            ip_claim.get("usage_rule"),
            "청구항 폭/독립항 수는 Tech-to-Value Bridge의 보수적 IP 방어력 보정 신호로만 사용하고, 직접 사업화 증거로 해석하지 않습니다.",
        ),
        "source_file": ip_claim.get("_source_file") or ip_claim.get("source_file"),
    }


def _load_ip_citation_features(company_dir: str, company_name: str = "") -> Dict[str, Any]:
    slug = str(company_dir or "").strip()
    names = [
        "tech_ip_citation_features.json",
        f"{slug}_tech_ip_citation_features.json",
    ]
    return _load_feature_by_names(company_dir, company_name, names)


def _extract_ip_citation_summary(ip_citation: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(ip_citation, dict) or not ip_citation:
        return {}

    return {
        "status": ip_citation.get("status"),
        "target_patent_count": ip_citation.get("target_patent_count"),
        "patents_with_citation_data": ip_citation.get("patents_with_citation_data"),
        "citation_collection_coverage": ip_citation.get("citation_collection_coverage"),
        "forward_citation_count_total": ip_citation.get("forward_citation_count_total"),
        "backward_citation_count_total": ip_citation.get("backward_citation_count_total"),
        "self_forward_citation_count": ip_citation.get("self_forward_citation_count"),
        "external_forward_citation_count": ip_citation.get("external_forward_citation_count"),
        "external_forward_citation_rate": ip_citation.get("external_forward_citation_rate"),
        "avg_forward_citations_per_patent": ip_citation.get("avg_forward_citations_per_patent"),
        "max_forward_citations_single_patent": ip_citation.get("max_forward_citations_single_patent"),
        "cited_patent_count": ip_citation.get("cited_patent_count"),
        "cited_patent_rate": ip_citation.get("cited_patent_rate"),
        "top10_forward_citation_share": ip_citation.get("top10_forward_citation_share"),
        "ip_citation_impact_score_estimated": ip_citation.get("ip_citation_impact_score_estimated"),
        "bridge_adjustment_points": ip_citation.get("bridge_adjustment_points"),
        "bridge_signal": ip_citation.get("bridge_signal"),
        "parse_error_count": ip_citation.get("parse_error_count"),
        "usage_rule": ip_citation.get("usage_rule"),
        "top_cited_patents": ip_citation.get("top_cited_patents", [])[:10],
        "source_file": ip_citation.get("_source_file") or ip_citation.get("source_file"),
    }


def _load_ip_family_features(company_dir: str, company_name: str = "") -> Dict[str, Any]:
    slug = str(company_dir or "").strip()
    names = [
        "tech_ip_family_features.json",
        f"{slug}_tech_ip_family_features.json",
    ]
    return _load_feature_by_names(company_dir, company_name, names)


def _extract_ip_family_summary(ip_family: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(ip_family, dict) or not ip_family:
        return {}

    return {
        "status": ip_family.get("status"),
        "target_patent_count": ip_family.get("target_patent_count"),
        "family_record_count": ip_family.get("family_record_count"),
        "patents_with_family": ip_family.get("patents_with_family"),
        "patents_with_overseas_family": ip_family.get("patents_with_overseas_family"),
        "overseas_family_record_count": ip_family.get("overseas_family_record_count"),
        "family_collection_coverage": ip_family.get("family_collection_coverage"),
        "overseas_family_patent_rate": ip_family.get("overseas_family_patent_rate"),
        "pct_patents": ip_family.get("pct_patents"),
        "us_patents": ip_family.get("us_patents"),
        "jp_patents": ip_family.get("jp_patents"),
        "ep_patents": ip_family.get("ep_patents"),
        "cn_patents": ip_family.get("cn_patents"),
        "detected_overseas_regions": ip_family.get("detected_overseas_regions", []),
        "global_extension_score": ip_family.get("global_extension_score"),
        "bridge_adjustment_points": ip_family.get("bridge_adjustment_points"),
        "bridge_signal": ip_family.get("bridge_signal"),
        "parse_error_count": ip_family.get("parse_error_count"),
        "usage_rule": ip_family.get("usage_rule"),
        "top_overseas_family_patents": ip_family.get("top_overseas_family_patents", [])[:10],
        "source_file": ip_family.get("_source_file") or ip_family.get("source_file"),
    }


def _load_ip_evidence_composite_features(company_dir: str, company_name: str = "") -> Dict[str, Any]:
    slug = str(company_dir or "").strip()
    names = [
        "tech_ip_evidence_composite.json",
        f"{slug}_tech_ip_evidence_composite.json",
    ]
    return _load_feature_by_names(company_dir, company_name, names)


def _extract_ip_evidence_composite_summary(ip_comp: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(ip_comp, dict) or not ip_comp:
        return {}

    components = ip_comp.get("components") if isinstance(ip_comp.get("components"), dict) else {}

    compact_components: Dict[str, Any] = {}
    for key, item in components.items():
        if not isinstance(item, dict):
            continue

        compact_components[key] = {
            "status": item.get("status"),
            "score_estimated": item.get("score_estimated"),
            "weight": item.get("weight"),
            "weighted_contribution_points": item.get("weighted_contribution_points"),
            "bridge_signal": item.get("bridge_signal"),
            "bridge_adjustment_points": item.get("bridge_adjustment_points"),
        }

    return {
        "status": ip_comp.get("status"),
        "ip_evidence_composite_score": ip_comp.get("ip_evidence_composite_score"),
        "ip_evidence_data_coverage_rate": ip_comp.get("ip_evidence_data_coverage_rate"),
        "bridge_adjustment_points": ip_comp.get("bridge_adjustment_points"),
        "bridge_signal": ip_comp.get("bridge_signal"),
        "missing_components": ip_comp.get("missing_components", []),
        "components": compact_components,
        "strengths": ip_comp.get("strengths", []),
        "cautions": ip_comp.get("cautions", []),
        "usage_rule": (
            (ip_comp.get("tech_to_value_bridge") or {}).get("usage_rule")
            if isinstance(ip_comp.get("tech_to_value_bridge"), dict)
            else ip_comp.get("usage_rule")
        ),
        "source_file": ip_comp.get("_source_file") or ip_comp.get("source_file"),
    }


def _extract_selected_ml(
    peer_pct: Dict[str, Any],
    ip_ml: Dict[str, Any],
    diff: Dict[str, Any],
    momentum: Dict[str, Any],
    ip_legal: Optional[Dict[str, Any]] = None,
    ip_claim: Optional[Dict[str, Any]] = None,
    ip_citation: Optional[Dict[str, Any]] = None,
    ip_family: Optional[Dict[str, Any]] = None,
    ip_composite: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    pm = momentum.get("patent_momentum") or {}
    conf = momentum.get("tech_to_value_evidence_confidence") or momentum.get("evidence_confidence") or {}

    legal_summary = _extract_ip_legal_summary(ip_legal or {})
    claim_summary = _extract_ip_claim_summary(ip_claim or {})
    citation_summary = _extract_ip_citation_summary(ip_citation or {})
    family_summary = _extract_ip_family_summary(ip_family or {})
    composite_summary = _extract_ip_evidence_composite_summary(ip_composite or {})

    dominant_topic = None
    if isinstance(ip_ml.get("dominant_topics"), list) and ip_ml.get("dominant_topics"):
        first_topic = ip_ml.get("dominant_topics")[0] or {}
        if isinstance(first_topic, dict):
            dominant_topic = first_topic.get("topic_label")

    return {
        "peer_ml": {
            "peer_adjusted_bridge_score": peer_pct.get("peer_adjusted_bridge_score"),
            "peer_composite_percentile": peer_pct.get("peer_composite_percentile"),
            "peer_adjusted_grade": peer_pct.get("peer_adjusted_grade"),
            "cluster_name": peer_pct.get("cluster_name"),
        },
        "tech_ip_strength": {
            "score": ip_ml.get("tech_ip_strength_index") or ip_ml.get("tech_ip_strength_score"),
            "percentile": ip_ml.get("tech_ip_strength_percentile"),
            "patent_momentum_score": ip_ml.get("patent_momentum_score"),
            "dominant_topic": dominant_topic,
        },
        "technology_differentiation": {
            "score": diff.get("technology_differentiation_score"),
            "percentile": (
                diff.get("technology_differentiation_percentile")
                or diff.get("reference_percentile")
                or diff.get("percentile")
            ),
            "grade": diff.get("technology_differentiation_grade") or diff.get("grade"),
            "nearest_peer": (
                (diff.get("nearest_peer") or {}).get("company_name")
                if isinstance(diff.get("nearest_peer"), dict)
                else diff.get("nearest_peer")
            ),
            "dominant_topic": (
                (diff.get("dominant_topic") or {}).get("topic_label")
                if isinstance(diff.get("dominant_topic"), dict)
                else (diff.get("dominant_topic") or diff.get("dominant_nmf_topic"))
            ),
        },
        "patent_momentum": {
            "score": pm.get("patent_momentum_score"),
            "grade": pm.get("grade"),
        },
        "evidence_confidence": {
            "score": conf.get("tech_to_value_evidence_confidence_score") or conf.get("score"),
            "grade": conf.get("grade"),
            "direct_dimension_count": conf.get("direct_dimension_count"),
        },
        "ip_legal_stability": legal_summary,
        "ip_claim_scope": claim_summary,
        "ip_citation_impact": citation_summary,
        "ip_global_extension": family_summary,
        "ip_evidence_composite": composite_summary,
    }


def _build_tech_chair_summary_original(
    *,
    company_dir: str,
    company_name: str,
    opinion: str,
    sections: List[Dict[str, Any]],
    score_report: Dict[str, Any],
    bridge: Dict[str, Any],
    patent_harvest: Dict[str, Any],
    output_files: Dict[str, Any],
) -> Dict[str, Any]:
    """Build and save compact Chair summary + detailed Tech appendix."""

    peer_pct = _load_packet(company_dir, "tech_peer_percentile_bridge.json")
    ip_ml = _load_packet(company_dir, "tech_ip_ml.json")
    diff = _load_packet(company_dir, "tech_differentiation.json")
    momentum = _load_packet(company_dir, "tech_momentum_confidence.json")

    ip_legal = _load_ip_legal_features(company_dir, company_name)
    ip_claim = _load_ip_claim_features(company_dir, company_name)
    ip_citation = _load_ip_citation_features(company_dir, company_name)
    ip_family = _load_ip_family_features(company_dir, company_name)
    ip_composite = _load_ip_evidence_composite_features(company_dir, company_name)

    ip_legal_summary = _extract_ip_legal_summary(ip_legal)
    ip_claim_summary = _extract_ip_claim_summary(ip_claim)
    ip_citation_summary = _extract_ip_citation_summary(ip_citation)
    ip_family_summary = _extract_ip_family_summary(ip_family)
    ip_composite_summary = _extract_ip_evidence_composite_summary(ip_composite)

    raw_score = bridge.get("tech_agent_raw_score") or score_report.get("total_score")
    auditor_score = bridge.get("auditor_adjusted_score") or bridge.get("score")
    base_bridge_score = bridge.get("score")
    base_bridge_grade = bridge.get("grade")
    peer_score = peer_pct.get("peer_adjusted_bridge_score") or base_bridge_score
    peer_grade = peer_pct.get("peer_adjusted_grade") or base_bridge_grade

    excel_rows = _extract_excel_frame(sections, limit=7)
    ip_signals = _extract_ip_signals(ip_ml, patent_harvest)

    selected_ml = _extract_selected_ml(
        peer_pct,
        ip_ml,
        diff,
        momentum,
        ip_legal,
        ip_claim,
        ip_citation,
        ip_family,
        ip_composite,
    )

    business_gate = _extract_business_gate(momentum)

    primary_ml_choice = (
        "Technology Differentiation Score + Tech-to-Value Evidence Confidence + IP Evidence Composite Score"
    )
    primary_ml_reason = (
        "prompts.py의 공통 루브릭에 맞춰 R&D는 effort, 특허/IP는 intermediate output, "
        "고객 채택·양산·매출·마진·FCF는 commercial outcome으로 분리합니다. "
        "차별화 점수는 peer 대비 기술/IP 포트폴리오의 구별성을, Evidence Confidence는 고객 채택·양산·매출·FCF 연결 근거의 직접성을, "
        "IP Evidence Composite는 등록·존속 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합해 Chair 요약에 반영합니다."
    )

    summary: Dict[str, Any] = {
        "agent": "tech",
        "summary_version": "tech_compact_chair_v3_prompt_policy_aligned",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "field": "반도체",
        "company": company_name,
        "company_name": company_name,
        "company_dir": company_dir,
        "company_slug": company_dir,
        "opinion": opinion,
        "tech_to_value": {
            "tech_agent_raw_score": raw_score,
            "auditor_adjusted_score": auditor_score,
            "base_bridge_score": base_bridge_score,
            "base_bridge_grade": base_bridge_grade,
            "peer_adjusted_bridge_score": peer_score,
            "peer_adjusted_grade": peer_grade,
            "commercialization_watch_meaning": "기술성은 확인되지만 고객 채택·양산·매출 전환·FCF 개선까지 이어지는 연결고리를 계속 추적해야 하는 상태",
            "tech_finance_gap_meaning": "기술 포트폴리오는 존재하지만 수익성·현금흐름·재무안정성으로 전환되는 직접 근거가 약한 상태",
            "ip_legal_bridge_adjustment_points": ip_legal_summary.get("bridge_adjustment_points"),
            "ip_legal_bridge_signal": ip_legal_summary.get("bridge_signal"),
            "ip_claim_bridge_adjustment_points": ip_claim_summary.get("bridge_adjustment_points"),
            "ip_claim_bridge_signal": ip_claim_summary.get("bridge_signal"),
            "ip_citation_bridge_adjustment_points": ip_citation_summary.get("bridge_adjustment_points"),
            "ip_citation_bridge_signal": ip_citation_summary.get("bridge_signal"),
            "ip_family_bridge_adjustment_points": ip_family_summary.get("bridge_adjustment_points"),
            "ip_family_bridge_signal": ip_family_summary.get("bridge_signal"),
            "ip_evidence_composite_score": ip_composite_summary.get("ip_evidence_composite_score"),
            "ip_evidence_bridge_adjustment_points": ip_composite_summary.get("bridge_adjustment_points"),
            "ip_evidence_bridge_signal": ip_composite_summary.get("bridge_signal"),
            "rubric_source": "src/tech_agent/prompts.py",
            "bridge_policy_summary": _policy_short(TECH_TO_VALUE_BRIDGE_PROMPT, 260),
        },
        "excel_frame_summary": excel_rows,
        "ip_quant_signals": ip_signals,
        "selected_ml": selected_ml,
        "ip_legal_features": ip_legal_summary,
        "ip_legal_feature_merge_status": "MERGED" if ip_legal_summary else "NOT_FOUND",
        "ip_claim_features": ip_claim_summary,
        "ip_claim_feature_merge_status": "MERGED" if ip_claim_summary else "NOT_FOUND",
        "ip_citation_features": ip_citation_summary,
        "ip_citation_feature_merge_status": "MERGED" if ip_citation_summary else "NOT_FOUND",
        "ip_family_features": ip_family_summary,
        "ip_family_feature_merge_status": "MERGED" if ip_family_summary else "NOT_FOUND",
        "ip_evidence_composite_features": ip_composite_summary,
        "ip_evidence_composite_merge_status": "MERGED" if ip_composite_summary else "NOT_FOUND",
        "primary_ml_choice": primary_ml_choice,
        "primary_ml_reason": primary_ml_reason,
        "businessization_gate": business_gate,
        "chair_policy": [
            "Chair 최종 보고서에는 Tech 상세 표 전체를 붙이지 않고 compact summary만 반영합니다.",
            "상세 Excel-frame/ML 표는 Tech Agent 산출물과 부록 파일에서 확인합니다.",
            "기술 우위가 확인되어도 고객 채택·양산·매출 전환·FCF 직접 근거가 약하면 보수적으로 반영합니다.",
            "IP Evidence Composite Score는 직접 매출 근거가 아니라 특허 포트폴리오의 질적 보조 신호로만 사용합니다.",
            "prompts.py 기준에 따라 R&D 투입, 특허/IP 산출, 고객·양산·매출 결과를 분리해 해석합니다.",
            "CB/BW·유상증자·정부과제·기술이전은 성장투자와 희석/오버행 리스크를 분리한 watch point로만 사용합니다.",
        ],
        "prompt_policy_alignment": _tech_prompt_policy_snapshot(),
        "final_tech_score_policy": FINAL_TECH_SCORE_POLICY,
        "detail_files": _relativize_dict_paths(output_files),
    }

    out_dir = agent_output_dir(company_dir, "tech", root=ROOT)

    if merge_ip_evidence_composite_into_summary is not None:
        try:
            summary = merge_ip_evidence_composite_into_summary(
                summary,
                field="반도체",
                company_name=company_name,
                company_slug=company_dir,
                tech_dir=out_dir,
            )
        except Exception as exc:
            summary["ip_evidence_composite_merge_status"] = "MERGE_ERROR"
            summary["ip_evidence_composite_merge_error"] = repr(exc)

    summary_json = out_dir / "tech_chair_summary.json"
    summary_md = out_dir / f"{company_dir}_tech_chair_summary.md"
    deep_dive_md = out_dir / f"{company_dir}_tech_deep_dive.md"

    _write_json(summary_json, summary)

    md_text = render_tech_chair_summary_md(summary)

    if append_ip_evidence_composite_to_markdown is not None:
        try:
            composite_feature = summary.get("ip_evidence_composite") or ip_composite
            md_text = append_ip_evidence_composite_to_markdown(md_text, composite_feature)
        except Exception:
            pass

    _write_text(summary_md, md_text)
    _write_text(deep_dive_md, render_tech_deep_dive_md(summary))

    summary["summary_files"] = {
        "chair_summary_json": _rel_project_path(summary_json),
        "chair_summary_md": _rel_project_path(summary_md),
        "tech_deep_dive_md": _rel_project_path(deep_dive_md),
    }

    _write_json(summary_json, summary)

    return summary


def build_tech_chair_summary(*args, **kwargs) -> Dict[str, Any]:
    """Public entry point used by Tech Agent runner."""
    return _build_tech_chair_summary_original(*args, **kwargs)


def render_tech_chair_summary_md(summary: Dict[str, Any]) -> str:
    c = summary.get("company") or summary.get("company_dir") or "기업"
    tv = summary.get("tech_to_value") or {}
    ml = summary.get("selected_ml") or {}

    diff = ml.get("technology_differentiation") or {}
    conf = ml.get("evidence_confidence") or {}
    pm = ml.get("patent_momentum") or {}
    peer = ml.get("peer_ml") or {}

    ip_legal = ml.get("ip_legal_stability") or summary.get("ip_legal_features") or {}
    ip_claim = ml.get("ip_claim_scope") or summary.get("ip_claim_features") or {}
    ip_citation = ml.get("ip_citation_impact") or summary.get("ip_citation_features") or {}
    ip_family = ml.get("ip_global_extension") or summary.get("ip_family_features") or {}
    ip_composite = ml.get("ip_evidence_composite") or summary.get("ip_evidence_composite_features") or {}

    ip = summary.get("ip_quant_signals") or {}

    lines: List[str] = [
        f"# {c} Tech Chair Compact Summary",
        "",
        "## 1. Chair 반영용 핵심 판단",
        f"- **의견:** {summary.get('opinion') or '확인 제한'}",
        f"- **Tech-to-Value:** base {_fmt_score(tv.get('base_bridge_score'))} / {_label_grade(tv.get('base_bridge_grade'))}",
        f"- **Peer-adjusted:** {_fmt_score(tv.get('peer_adjusted_bridge_score'))} / {_label_grade(tv.get('peer_adjusted_grade'))}",
        f"- **IP Evidence Composite:** {_fmt_score(ip_composite.get('ip_evidence_composite_score'))} / {_label_grade(ip_composite.get('bridge_signal'))}",
        f"- **ML 우선 반영:** {summary.get('primary_ml_choice')}",
        f"- **해석:** {summary.get('primary_ml_reason')}",
        f"- **루브릭 원천:** `{(summary.get('tech_to_value') or {}).get('rubric_source') or 'src/tech_agent/prompts.py'}`",
        f"- **최종 Tech 점수 정책:** {_policy_short(((summary.get('final_tech_score_policy') or {}).get('description') if isinstance(summary.get('final_tech_score_policy'), dict) else ''), 180)}",
        "",
        "## 2. Excel-frame 핵심 요약",
        "| 대분류 | 항목 | 정량화 | 근거 | 등급 | 비고 |",
        "|---|---|---|---|---|---|",
    ]

    for row in summary.get("excel_frame_summary") or []:
        lines.append(
            f"| {row.get('category')} | {row.get('item')} | {row.get('quantification')} | "
            f"{row.get('evidence')} | {row.get('grade')} | {row.get('note')} |"
        )

    lines += [
        "",
        "## 3. 선택 ML/IP 요약",
        "| ML/IP 신호 | 값 | Chair 해석 |",
        "|---|---:|---|",
        f"| Technology Differentiation Score | {_fmt_score(diff.get('score'))} / {_fmt_num(diff.get('percentile'), 2, '%ile')} | peer 대비 기술/IP 포트폴리오 차별성 |",
        f"| Evidence Confidence | {_fmt_score(conf.get('score'))} | 고객 채택·양산·매출·FCF 근거의 직접성 |",
        f"| Patent Momentum | {_fmt_score(pm.get('score'))} | 최근 특허 활동의 현재성·지속성 |",
        f"| IP Legal Stability | {_fmt_score(ip_legal.get('legal_stability_score_estimated'))} | 등록률·존속률·소멸/거절/취하 비중 기반 권리 안정성 |",
        f"| IP Claim Defense | {_fmt_score(ip_claim.get('claim_defense_score_estimated'))} | 청구항 수·독립항 수·수집 커버리지 기반 특허 방어력 |",
        f"| IP Citation Impact | {_fmt_score(ip_citation.get('ip_citation_impact_score_estimated'))} | 피인용·외부인용 기반 기술 영향력/시장 참조 가치 |",
        f"| IP Global Extension | {_fmt_score(ip_family.get('global_extension_score'))} | 해외 패밀리·PCT/WO·미국/일본/유럽/중국 확장성 |",
        f"| IP Evidence Composite | {_fmt_score(ip_composite.get('ip_evidence_composite_score'))} | 법적 안정성·청구항·인용·패밀리 특허를 통합한 종합 IP 근거 점수 |",
        f"| IP Evidence Bridge Signal | {ip_composite.get('bridge_signal') or '확인 제한'} / {_fmt_num(ip_composite.get('bridge_adjustment_points'), 2, '점')} | Tech-to-Value Bridge 보수적 보정 신호 |",
        f"| Peer-adjusted Bridge | {_fmt_score(peer.get('peer_adjusted_bridge_score'))} | Reference Universe, KMeans, Cosine Similarity, UMAP, Peer Percentile 기반 보정 |",
        "",
        "## 4. KIPRIS/IP 정량 신호",
        "| 원천 신호 | 값 |",
        "|---|---:|",
        f"| 정규화 특허 텍스트 레코드 | {_fmt_num(ip.get('normalized_patent_text_records'), 0, '건')} |",
        f"| 회사 출원인/권리자 매칭 | {_fmt_num(ip.get('company_matched_patents'), 0, '건')} |",
        f"| 등록 특허 | {_fmt_num(ip.get('registered_patents'), 0, '건')} |",
        f"| 존속 가능 특허 | {_fmt_num(ip.get('alive_patents'), 0, '건')} |",
        f"| 최근 5년 특허 | {_fmt_num(ip.get('recent_5y_patents'), 0, '건')} |",
        f"| IPC/CPC 다양성 | {_fmt_num(ip.get('ipc_cpc_classes'), 0, '개')} |",
        f"| H01L 등 핵심 IPC 특허 | {_fmt_num(ip.get('core_ipc_h01l_patents'), 0, '건')} |",
        f"| KIPRIS 등록률(추정) | {_fmt_rate(ip_legal.get('registration_rate_estimated'))} |",
        f"| 등록특허 중 존속률(추정) | {_fmt_rate(ip_legal.get('alive_rate_among_registered_estimated'))} |",
        f"| 소멸·거절·취하 등 부정 처분 비중(추정) | {_fmt_rate(ip_legal.get('negative_disposal_rate_estimated'))} |",
        f"| 권리자 정보 반영률 | {_fmt_rate(ip_legal.get('right_holder_coverage'))} |",
        f"| 초록/도면 반영률 | {_fmt_rate(ip_legal.get('abstract_coverage'))} / {_fmt_rate(ip_legal.get('drawing_coverage'))} |",
        f"| 청구항 수집 커버리지 | {_fmt_rate(ip_claim.get('claim_collection_coverage'))} |",
        f"| 수집 청구항 / 독립항(추정) | {_fmt_num(ip_claim.get('claim_count'), 0, '항')} / {_fmt_num(ip_claim.get('independent_claim_count_estimated'), 0, '항')} |",
        f"| 특허당 평균 청구항 / 독립항 비중 | {_fmt_num(ip_claim.get('avg_claims_per_patent'), 2, '항')} / {_fmt_rate(ip_claim.get('independent_claim_ratio'))} |",
        f"| 피인용 총합 / 외부 피인용 | {_fmt_num(ip_citation.get('forward_citation_count_total'), 0, '건')} / {_fmt_num(ip_citation.get('external_forward_citation_count'), 0, '건')} |",
        f"| 외부 피인용률 | {_fmt_rate(ip_citation.get('external_forward_citation_rate'))} |",
        f"| 해외 패밀리 보유율 | {_fmt_rate(ip_family.get('overseas_family_patent_rate'))} |",
        f"| PCT/WO / US / JP / EP / CN | {_fmt_num(ip_family.get('pct_patents'), 0, '건')} / {_fmt_num(ip_family.get('us_patents'), 0, '건')} / {_fmt_num(ip_family.get('jp_patents'), 0, '건')} / {_fmt_num(ip_family.get('ep_patents'), 0, '건')} / {_fmt_num(ip_family.get('cn_patents'), 0, '건')} |",
        "",
        "## 5. IP Evidence Composite 세부 구성",
        "| 구성 요소 | Weight | Score | Contribution | Status |",
        "|---|---:|---:|---:|---|",
    ]

    components = ip_composite.get("components") if isinstance(ip_composite.get("components"), dict) else {}
    component_labels = {
        "legal_stability": "등록·존속 안정성",
        "claim_defense": "청구항 방어 범위",
        "citation_influence": "인용 기반 기술 영향력",
        "global_extension": "해외 패밀리 기반 글로벌 확장성",
    }

    for key in ["legal_stability", "claim_defense", "citation_influence", "global_extension"]:
        item = components.get(key) if isinstance(components.get(key), dict) else {}
        lines.append(
            f"| {component_labels.get(key, key)} | "
            f"{item.get('weight') or '확인 제한'} | "
            f"{_fmt_score(item.get('score_estimated'))} | "
            f"{_fmt_num(item.get('weighted_contribution_points'), 2, '점')} | "
            f"{item.get('status') or '확인 제한'} |"
        )

    lines += [
        "",
        "## 6. 사업화 연결 체크",
        "| 연결 항목 | 상태 | 점수 | 직접 | 간접 | 확인 제한 |",
        "|---|---|---:|---:|---:|---:|",
    ]

    for row in summary.get("businessization_gate") or []:
        lines.append(
            f"| {row.get('dimension')} | {row.get('status')} | {_fmt_score(row.get('score'))} | "
            f"{_fmt_num(row.get('direct_evidence_count'), 0, '건')} | "
            f"{_fmt_num(row.get('indirect_evidence_count'), 0, '건')} | "
            f"{_fmt_num(row.get('limited_evidence_count'), 0, '건')} |"
        )

    lines += [
        "",
        "## 7. Chair 반영 원칙",
    ]

    for policy in summary.get("chair_policy") or []:
        lines.append(f"- {policy}")

    prompt_policy = summary.get("prompt_policy_alignment") or {}
    score_policy = summary.get("final_tech_score_policy") or prompt_policy.get("final_tech_score_policy") or {}
    if isinstance(score_policy, dict) and score_policy:
        lines += [
            "",
            "## 8. prompts.py 루브릭 연동",
            f"- **최종 점수 설명:** {_policy_short(score_policy.get('description'), 240)}",
            f"- **가중치:** {score_policy.get('weights') or '확인 제한'}",
            f"- **판정 임계값:** {score_policy.get('grade_thresholds') or '확인 제한'}",
            "- **적용 원칙:** 특허 수보다 기술-사업화-가치평가 연결성을 우선하고, API/파일 권한 제한은 데이터 품질로 분리합니다.",
        ]

    return "\n".join(lines).strip() + "\n"


def render_tech_deep_dive_md(summary: Dict[str, Any]) -> str:
    """A reviewer-facing appendix. It remains outside the Chair main report."""
    c = summary.get("company") or summary.get("company_dir") or "기업"
    files = summary.get("detail_files") or {}

    lines = [
        f"# {c} Tech Deep-Dive Appendix",
        "",
        "이 파일은 Chair 최종 보고서에 길게 삽입하지 않고, Tech Agent 상세 산출물로 별도 보관합니다.",
        "",
        "## 1. Chair Compact Summary",
        render_tech_chair_summary_md(summary),
        "",
        "## 2. 원천 상세 파일 위치",
        "| 구분 | 경로 |",
        "|---|---|",
    ]

    for k, v in files.items():
        lines.append(f"| {k} | `{_rel_project_path(v)}` |")

    lines += [
        "",
        "## 3. 운영 원칙",
        "- Tech의 상세 Excel-frame, KIPRIS/IP, Peer ML, NMF, Differentiation, Momentum, Evidence Confidence는 Tech Agent 쪽에서 산출합니다.",
        "- First Auditor는 Tech Agent가 Chair에 넘긴 claim/evidence를 검증합니다.",
        "- Chair는 상세 부록을 반복 삽입하지 않고, 요약·충돌·최종 판단만 수행합니다.",
        "- IP Evidence Composite Score는 특허 수량이 아니라 법적 안정성, 청구항 방어력, 인용 영향력, 해외 패밀리 확장성을 종합한 보조 신호입니다.",
    ]

    return "\n".join(lines).strip() + "\n"

# === IP_EVIDENCE_BRIDGE_ADJUSTMENT_WRAPPER_START ===
# Auto-added: apply IP Evidence Composite adjustment to final Tech-to-Value Bridge score.
# Formula:
# final_tech_to_value_score
# = peer_adjusted_bridge_score_before_ip_evidence
# + ip_evidence_composite_adjustment_points

import json as _ipev_bridge_json
from pathlib import Path as _IpevBridgePath
from datetime import datetime as _IpevBridgeDatetime

from tech_agent.ip_evidence_bridge_adjustment import (
    apply_ip_evidence_composite_adjustment_to_bridge as _ipev_apply_bridge_adjustment,
    persist_ip_evidence_adjusted_bridge_packet as _ipev_persist_bridge_packet,
    resolve_tech_dir as _ipev_resolve_tech_dir,
    load_ip_evidence_composite as _ipev_load_composite,
)


def _ipev_clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def _ipev_float(value, default=None):
    try:
        if value is None:
            return default
        text = str(value).replace(",", "").replace("%", "").strip()
        if not text:
            return default
        return float(text)
    except Exception:
        return default


def _ipev_round2(value):
    x = _ipev_float(value)
    if x is None:
        return None
    return round(float(x), 2)


def _ipev_company_slug(summary, args=None, kwargs=None):
    args = args or ()
    kwargs = kwargs or {}

    candidates = [
        kwargs.get("company_slug"),
        kwargs.get("company_dir"),
        kwargs.get("slug"),
        summary.get("company_slug") if isinstance(summary, dict) else None,
        summary.get("company_dir") if isinstance(summary, dict) else None,
        summary.get("slug") if isinstance(summary, dict) else None,
    ]

    for value in candidates:
        value = _ipev_clean(value)
        if value:
            return value

    for value in args:
        if isinstance(value, str) and value and value.isascii():
            return value.strip()

    return ""


def _ipev_company_name(summary, args=None, kwargs=None):
    args = args or ()
    kwargs = kwargs or {}

    candidates = [
        kwargs.get("company_name"),
        kwargs.get("company"),
        kwargs.get("name"),
        summary.get("company_name") if isinstance(summary, dict) else None,
        summary.get("company") if isinstance(summary, dict) else None,
        summary.get("name") if isinstance(summary, dict) else None,
    ]

    for value in candidates:
        value = _ipev_clean(value)
        if value:
            return value

    for value in args:
        if isinstance(value, str) and value and not value.isascii():
            return value.strip()

    return ""


def _ipev_field(summary, kwargs=None):
    kwargs = kwargs or {}
    candidates = [
        kwargs.get("field"),
        kwargs.get("sector"),
        kwargs.get("industry_field"),
        summary.get("field") if isinstance(summary, dict) else None,
        summary.get("sector") if isinstance(summary, dict) else None,
        summary.get("industry_field") if isinstance(summary, dict) else None,
    ]

    for value in candidates:
        value = _ipev_clean(value)
        if value:
            return value

    return "반도체"


def _ipev_compact_composite(feature):
    if not isinstance(feature, dict):
        return {}

    return {
        "status": feature.get("status"),
        "ip_evidence_composite_score": feature.get("ip_evidence_composite_score"),
        "ip_evidence_data_coverage_rate": feature.get("ip_evidence_data_coverage_rate"),
        "bridge_signal": feature.get("bridge_signal"),
        "bridge_adjustment_points": feature.get("bridge_adjustment_points"),
        "components": feature.get("components", {}),
        "usage_rule": (
            feature.get("usage_rule")
            or (feature.get("tech_to_value_bridge") or {}).get("usage_rule")
            or "IP Evidence Composite는 법적 안정성, 청구항 방어력, 인용 영향력, 글로벌 패밀리 확장성을 종합한 Tech-to-Value Bridge 보조 조정 신호입니다."
        ),
        "source_file": feature.get("_source_file") or feature.get("source_file"),
    }


def _ipev_apply_to_summary(summary, args=None, kwargs=None):
    if not isinstance(summary, dict):
        return summary

    args = args or ()
    kwargs = kwargs or {}

    company_slug = _ipev_company_slug(summary, args=args, kwargs=kwargs)
    company_name = _ipev_company_name(summary, args=args, kwargs=kwargs)
    field = _ipev_field(summary, kwargs=kwargs)

    tv = summary.get("tech_to_value")
    if not isinstance(tv, dict):
        tv = {}
        summary["tech_to_value"] = tv

    feature, feature_path = _ipev_load_composite(
        field=field,
        company_name=company_name,
        company_slug=company_slug,
    )

    if not feature:
        summary["ip_evidence_bridge_adjustment_status"] = "FEATURE_FILE_NOT_FOUND"
        tv["ip_evidence_composite_adjustment_status"] = "FEATURE_FILE_NOT_FOUND"
        return summary

    # Chair summary 기준 최종 점수는 peer-adjusted score를 우선 기준으로 삼는다.
    peer_before = (
        tv.get("peer_adjusted_bridge_score_before_ip_evidence")
        or tv.get("peer_adjusted_bridge_score")
        or tv.get("base_bridge_score")
        or tv.get("ip_evidence_adjusted_score")
        or tv.get("score")
    )

    working_bridge = dict(tv)
    if _ipev_float(working_bridge.get("score")) is None:
        working_bridge["score"] = peer_before

    adjusted_bridge = _ipev_apply_bridge_adjustment(
        working_bridge,
        field=field,
        company_name=company_name,
        company_slug=company_slug,
    )

    adjustment = _ipev_float(
        adjusted_bridge.get("ip_evidence_composite_adjustment_points"),
        0.0,
    )

    peer_before_float = _ipev_float(peer_before)
    if peer_before_float is not None:
        final_score = max(0.0, min(100.0, peer_before_float + adjustment))
        final_score = round(final_score, 2)
    else:
        final_score = adjusted_bridge.get("ip_evidence_adjusted_score") or adjusted_bridge.get("score")

    tv["ip_evidence_composite_score"] = feature.get("ip_evidence_composite_score")
    tv["ip_evidence_composite_bridge_signal"] = feature.get("bridge_signal")
    tv["ip_evidence_composite_adjustment_points"] = adjustment
    tv["ip_evidence_composite_data_coverage_rate"] = feature.get("ip_evidence_data_coverage_rate")
    tv["ip_evidence_composite_source_file"] = (
        str(feature_path).replace("\\", "/") if feature_path else feature.get("_source_file")
    )

    tv["peer_adjusted_bridge_score_before_ip_evidence"] = _ipev_round2(peer_before)
    tv["final_bridge_score_after_ip_evidence"] = _ipev_round2(final_score)
    tv["peer_adjusted_bridge_score"] = _ipev_round2(final_score)
    tv["ip_evidence_adjusted_score"] = _ipev_round2(final_score)
    tv["ip_evidence_formula"] = (
        "final_bridge_score_after_ip_evidence = "
        "peer_adjusted_bridge_score_before_ip_evidence + "
        "ip_evidence_composite_adjustment_points"
    )

    if adjusted_bridge.get("ip_evidence_adjusted_grade"):
        tv["ip_evidence_adjusted_grade"] = adjusted_bridge.get("ip_evidence_adjusted_grade")
        tv["peer_adjusted_grade"] = adjusted_bridge.get("ip_evidence_adjusted_grade")

    summary["ip_evidence_bridge_adjustment_status"] = "APPLIED"
    summary["ip_evidence_bridge_adjustment_applied_at"] = _IpevBridgeDatetime.now().isoformat(timespec="seconds")
    summary["ip_evidence_composite"] = feature
    summary["ip_evidence_composite_merge_status"] = "MERGED"

    selected_ml = summary.get("selected_ml")
    if not isinstance(selected_ml, dict):
        selected_ml = {}
        summary["selected_ml"] = selected_ml

    selected_ml["ip_evidence_composite"] = _ipev_compact_composite(feature)
    selected_ml["ip_evidence_composite_score"] = feature.get("ip_evidence_composite_score")
    selected_ml["ip_evidence_bridge_signal"] = feature.get("bridge_signal")
    selected_ml["ip_evidence_bridge_adjustment_points"] = adjustment
    selected_ml["final_bridge_score_after_ip_evidence"] = _ipev_round2(final_score)

    try:
        _ipev_persist_bridge_packet(
            adjusted_bridge,
            field=field,
            company_name=company_name,
            company_slug=company_slug,
        )
    except Exception as exc:
        summary["ip_evidence_bridge_packet_persist_error"] = repr(exc)

    return summary


def _ipev_write_json(path, data):
    p = _IpevBridgePath(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        _ipev_bridge_json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _ipev_md_block(summary):
    if not isinstance(summary, dict):
        return ""

    tv = summary.get("tech_to_value") or {}

    lines = []
    lines.append("<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_START -->")
    lines.append("## IP Evidence Composite → Tech-to-Value Bridge 반영")
    lines.append("")
    lines.append("- 의미: KIPRIS 기반 IP Evidence Composite를 Tech-to-Value Bridge 최종 점수 산식에 정식 반영합니다.")
    lines.append("- 산식: final_bridge_score_after_ip_evidence = peer_adjusted_bridge_score_before_ip_evidence + ip_evidence_composite_adjustment_points")
    lines.append("")
    lines.append(f"- IP Evidence Composite Score: {tv.get('ip_evidence_composite_score')}")
    lines.append(f"- IP Evidence Bridge Signal: {tv.get('ip_evidence_composite_bridge_signal')}")
    lines.append(f"- IP Evidence Adjustment Points: {tv.get('ip_evidence_composite_adjustment_points')}")
    lines.append(f"- Peer-adjusted Score Before IP Evidence: {tv.get('peer_adjusted_bridge_score_before_ip_evidence')}")
    lines.append(f"- Final Bridge Score After IP Evidence: {tv.get('final_bridge_score_after_ip_evidence')}")
    lines.append(f"- Source: `{tv.get('ip_evidence_composite_source_file')}`")
    lines.append("")
    lines.append("해석:")
    lines.append("- 네패스처럼 IP Evidence 조정값이 0.0이면 최종 점수 변화가 없는 것이 정상입니다.")
    lines.append("- 다른 기업에서 +1.0, +2.0, -1.0이 나오면 이 구간에서 Tech-to-Value Bridge 최종 점수가 자동 조정됩니다.")
    lines.append("<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_END -->")
    lines.append("")
    return "\n".join(lines)


def _ipev_replace_or_append_md(path, block):
    p = _IpevBridgePath(path)
    if not p.exists() or not block:
        return

    text = p.read_text(encoding="utf-8", errors="replace")

    start = "<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_START -->"
    end = "<!-- IP_EVIDENCE_BRIDGE_ADJUSTMENT_END -->"

    if start in text and end in text:
        before = text.split(start, 1)[0].rstrip()
        after = text.split(end, 1)[1].lstrip()
        new_text = before + "\n\n" + block.strip() + "\n\n" + after
    else:
        new_text = text.rstrip() + "\n\n" + block.strip() + "\n"

    p.write_text(new_text, encoding="utf-8")


def _ipev_persist_summary(summary, args=None, kwargs=None):
    if not isinstance(summary, dict):
        return

    args = args or ()
    kwargs = kwargs or {}

    company_slug = _ipev_company_slug(summary, args=args, kwargs=kwargs)
    company_name = _ipev_company_name(summary, args=args, kwargs=kwargs)
    field = _ipev_field(summary, kwargs=kwargs)

    tech_dir = _ipev_resolve_tech_dir(
        field=field,
        company_name=company_name,
        company_slug=company_slug,
    )

    if tech_dir is None:
        return

    json_candidates = [
        tech_dir / "tech_chair_summary.json",
    ]

    if company_slug:
        json_candidates.append(tech_dir / f"{company_slug}_tech_chair_summary.json")

    wrote = False
    for path in json_candidates:
        if path.exists():
            _ipev_write_json(path, summary)
            wrote = True

    if not wrote:
        _ipev_write_json(tech_dir / "tech_chair_summary.json", summary)

    # === IP_EVIDENCE_ADJUSTED_PACKET_PERSIST_V1 ===
    # Audit/traceability artifact:
    # Save the final Tech-to-Value Bridge score after IP Evidence Composite adjustment.
    tv = summary.get("tech_to_value") if isinstance(summary.get("tech_to_value"), dict) else {}

    adjusted_packet = {
        "created_at": _IpevBridgeDatetime.now().isoformat(timespec="seconds"),
        "company_slug": company_slug,
        "company_name": company_name,
        "field": field,
        "status": summary.get("ip_evidence_bridge_adjustment_status"),
        "formula": tv.get("ip_evidence_formula")
            or "final_bridge_score_after_ip_evidence = peer_adjusted_bridge_score_before_ip_evidence + ip_evidence_composite_adjustment_points",
        "base_bridge_score": tv.get("base_bridge_score"),
        "peer_adjusted_bridge_score_before_ip_evidence": tv.get("peer_adjusted_bridge_score_before_ip_evidence"),
        "ip_evidence_composite_score": tv.get("ip_evidence_composite_score"),
        "ip_evidence_composite_bridge_signal": tv.get("ip_evidence_composite_bridge_signal"),
        "ip_evidence_composite_adjustment_points": tv.get("ip_evidence_composite_adjustment_points"),
        "final_bridge_score_after_ip_evidence": tv.get("final_bridge_score_after_ip_evidence"),
        "peer_adjusted_bridge_score": tv.get("peer_adjusted_bridge_score"),
        "ip_evidence_adjusted_score": tv.get("ip_evidence_adjusted_score"),
        "ip_evidence_adjusted_grade": tv.get("ip_evidence_adjusted_grade"),
        "source_file": tv.get("ip_evidence_composite_source_file"),
        "usage_rule": (
            "This packet is an audit artifact for the Tech-to-Value Bridge after "
            "IP Evidence Composite adjustment. It does not represent direct revenue, "
            "customer adoption, mass production, or FCF evidence by itself."
        ),
    }

    _ipev_write_json(
        tech_dir / "tech_to_value_bridge_ip_evidence_adjusted.json",
        adjusted_packet,
    )

    if company_slug:
        _ipev_write_json(
            tech_dir / f"{company_slug}_tech_to_value_bridge_ip_evidence_adjusted.json",
            adjusted_packet,
        )

    block = _ipev_md_block(summary)

    md_candidates = [
        tech_dir / "tech_chair_summary.md",
    ]

    if company_slug:
        md_candidates.append(tech_dir / f"{company_slug}_tech_chair_summary.md")

    for path in md_candidates:
        _ipev_replace_or_append_md(path, block)


_ipev_original_build_tech_chair_summary = globals().get("build_tech_chair_summary")

if callable(_ipev_original_build_tech_chair_summary):

    def build_tech_chair_summary(*args, **kwargs):
        summary = _ipev_original_build_tech_chair_summary(*args, **kwargs)

        if isinstance(summary, dict):
            summary = _ipev_apply_to_summary(summary, args=args, kwargs=kwargs)
            _ipev_persist_summary(summary, args=args, kwargs=kwargs)

        return summary

# === IP_EVIDENCE_BRIDGE_ADJUSTMENT_WRAPPER_END ===

# ---------------------------------------------------------------------------
# Investor scorecard merge wrapper
# ---------------------------------------------------------------------------
# Tech Agent v13+ 산출물은 개인투자자용 최종 Tech 점수판을 chair_summary.json/md에
# 반드시 병합한다. 기존 build_tech_chair_summary 함수의 결과를 보존하되,
# Excel 기반 정량 근거, IP Evidence, Tech-to-Value Bridge 근거를 하나의
# 최종 점수로 합성한 tech_investor_view를 추가한다.
try:  # pragma: no cover - runtime compatibility wrapper
    _ap_original_build_tech_chair_summary = build_tech_chair_summary  # type: ignore[name-defined]

    def build_tech_chair_summary(*args, **kwargs):  # type: ignore[no-redef]
        summary = _ap_original_build_tech_chair_summary(*args, **kwargs)
        try:
            company_dir = kwargs.get("company_dir")
            company_name = kwargs.get("company_name") or kwargs.get("company")
            if company_dir is None and args:
                company_dir = args[0]
            if company_name is None and len(args) >= 2:
                company_name = args[1]
            if company_dir:
                from .investor_tech_view import apply_investor_tech_view_saved_files

                merged = apply_investor_tech_view_saved_files(
                    str(company_dir),
                    str(company_name) if company_name else None,
                    summary_payload=summary if isinstance(summary, dict) else None,
                )
                if isinstance(merged, dict) and isinstance(merged.get("summary"), dict):
                    return merged["summary"]
        except Exception as exc:
            if isinstance(summary, dict):
                warnings = list(summary.get("warnings") or [])
                warnings.append(f"investor_tech_view_merge_failed: {exc}")
                summary["warnings"] = warnings
        return summary
except Exception:
    pass

# ---------------------------------------------------------------------------
# Tech Intake Value Evidence Bridge merge wrapper
# ---------------------------------------------------------------------------
# This wrapper keeps Tech Agent ownership intact while allowing tech_intake to
# enrich Chair-facing checkpoints with customer adoption / mass production /
# revenue conversion / IP quality / margin-FCF linkage evidence.
try:  # pragma: no cover - runtime compatibility wrapper
    _ap_value_evidence_original_build_tech_chair_summary = build_tech_chair_summary  # type: ignore[name-defined]

    def build_tech_chair_summary(*args, **kwargs):  # type: ignore[no-redef]
        summary = _ap_value_evidence_original_build_tech_chair_summary(*args, **kwargs)
        if not isinstance(summary, dict):
            return summary
        try:
            company_dir = kwargs.get("company_dir") or kwargs.get("company_slug") or kwargs.get("slug")
            company_name = kwargs.get("company_name") or kwargs.get("company") or kwargs.get("name")
            field = kwargs.get("field") or kwargs.get("sector") or summary.get("field") or "반도체"
            if company_dir is None and args:
                company_dir = args[0]
            if company_name is None and len(args) >= 2:
                company_name = args[1]
            company_dir = str(company_dir or summary.get("company_dir") or summary.get("company_slug") or "").strip()
            company_name = str(company_name or summary.get("company") or summary.get("company_name") or "").strip()
            if not company_dir:
                return summary

            from data_intake.tech_intake.value_evidence_bridge import (
                generate_value_evidence_bridge,
                merge_value_evidence_into_summary,
                render_value_evidence_bridge_md,
            )

            bridge = generate_value_evidence_bridge(
                company_dir=company_dir,
                company=company_name or None,
                field=str(field or "반도체"),
                write=True,
                merge_summary=False,
            )
            summary = merge_value_evidence_into_summary(summary, bridge)

            # Persist/update the dedicated summary files after the previous wrappers.
            try:
                tech_dir = _ipev_resolve_tech_dir(  # type: ignore[name-defined]
                    field=str(field or "반도체"),
                    company_name=company_name,
                    company_slug=company_dir,
                )
            except Exception:
                tech_dir = None
            if tech_dir is not None:
                import json as _ve_json
                from pathlib import Path as _VEPath
                slug = company_dir
                json_candidates = [
                    _VEPath(tech_dir) / "tech_chair_summary.json",
                    _VEPath(tech_dir) / f"{slug}_tech_chair_summary.json",
                ]
                for p in json_candidates:
                    try:
                        p.parent.mkdir(parents=True, exist_ok=True)
                        p.write_text(_ve_json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass
                md_block = "\n\n<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_START -->\n" + render_value_evidence_bridge_md(bridge).strip() + "\n<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_END -->\n"
                for p in [_VEPath(tech_dir) / "tech_chair_summary.md", _VEPath(tech_dir) / f"{slug}_tech_chair_summary.md"]:
                    try:
                        if p.exists():
                            txt = p.read_text(encoding="utf-8", errors="replace")
                            start = "<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_START -->"
                            end = "<!-- VALUE_EVIDENCE_BRIDGE_SUMMARY_END -->"
                            if start in txt and end in txt:
                                before = txt.split(start, 1)[0].rstrip()
                                after = txt.split(end, 1)[1].lstrip()
                                txt = before + md_block + after
                            else:
                                txt = txt.rstrip() + md_block
                            p.write_text(txt, encoding="utf-8")
                    except Exception:
                        pass
        except Exception as exc:
            warnings = list(summary.get("warnings") or [])
            warnings.append(f"value_evidence_bridge_merge_failed: {exc}")
            summary["warnings"] = warnings
        return summary
except Exception:
    pass

# ---------------------------------------------------------------------------
# Technology Lifecycle merge wrapper
# ---------------------------------------------------------------------------
# Adds tech_intake's technology lifecycle feature to Chair-facing Tech summary
# without changing the original Tech Agent scoring path. Missing external report
# data is treated as 확인 제한, not as a negative signal.
try:  # pragma: no cover - runtime compatibility wrapper
    _ap_lifecycle_original_build_tech_chair_summary = build_tech_chair_summary  # type: ignore[name-defined]

    def build_tech_chair_summary(*args, **kwargs):  # type: ignore[no-redef]
        summary = _ap_lifecycle_original_build_tech_chair_summary(*args, **kwargs)
        if not isinstance(summary, dict):
            return summary
        try:
            company_dir = kwargs.get("company_dir") or kwargs.get("company_slug") or kwargs.get("slug")
            company_name = kwargs.get("company_name") or kwargs.get("company") or kwargs.get("name")
            field = kwargs.get("field") or kwargs.get("sector") or summary.get("field") or "반도체"
            if company_dir is None and args:
                company_dir = args[0]
            if company_name is None and len(args) >= 2:
                company_name = args[1]
            company_dir = str(company_dir or summary.get("company_dir") or summary.get("company_slug") or "").strip()
            company_name = str(company_name or summary.get("company") or summary.get("company_name") or "").strip()
            if not company_dir:
                return summary

            from common.data_paths import company_agent_dir as _lc_company_agent_dir
            from data_intake.tech_intake.technology_lifecycle import (
                build_technology_lifecycle_features as _lc_build,
                merge_lifecycle_into_summary as _lc_merge,
                render_lifecycle_md as _lc_render_md,
            )
            from pathlib import Path as _LCPath
            import json as _lc_json

            tech_dir = _lc_company_agent_dir(company_dir, "tech", create=True)
            feature_path = _LCPath(tech_dir) / "tech_lifecycle_features.json"
            if feature_path.exists():
                feature = _lc_json.loads(feature_path.read_text(encoding="utf-8"))
            else:
                feature = _lc_build(company_dir=company_dir, company=company_name or None, field=str(field or "반도체"), write=True)

            summary = _lc_merge(summary, feature)

            for p in [_LCPath(tech_dir) / "tech_chair_summary.json", _LCPath(tech_dir) / f"{company_dir}_tech_chair_summary.json"]:
                try:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(_lc_json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass

            md_block = "\n\n<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_START -->\n" + _lc_render_md(feature).strip() + "\n<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_END -->\n"
            start = "<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_START -->"
            end = "<!-- TECHNOLOGY_LIFECYCLE_SUMMARY_END -->"
            for p in [_LCPath(tech_dir) / "tech_chair_summary.md", _LCPath(tech_dir) / f"{company_dir}_tech_chair_summary.md"]:
                try:
                    if p.exists():
                        txt = p.read_text(encoding="utf-8", errors="replace")
                        if start in txt and end in txt:
                            before = txt.split(start, 1)[0].rstrip()
                            after = txt.split(end, 1)[1].lstrip()
                            txt = before + md_block + after
                        else:
                            txt = txt.rstrip() + md_block
                        p.write_text(txt, encoding="utf-8")
                except Exception:
                    pass
        except Exception as exc:
            warnings = list(summary.get("warnings") or [])
            warnings.append(f"technology_lifecycle_merge_failed: {exc}")
            summary["warnings"] = warnings
        return summary
except Exception:
    pass

# ---------------------------------------------------------------------------
# Certification & Standards merge wrapper
# ---------------------------------------------------------------------------
# Adds tech_intake's certification/standards feature to Chair-facing Tech summary
# without changing the original Tech Agent scoring path. Missing certification
# data is treated as 확인 제한, not as a negative signal.
try:  # pragma: no cover - runtime compatibility wrapper
    _ap_certification_original_build_tech_chair_summary = build_tech_chair_summary  # type: ignore[name-defined]

    def build_tech_chair_summary(*args, **kwargs):  # type: ignore[no-redef]
        summary = _ap_certification_original_build_tech_chair_summary(*args, **kwargs)
        if not isinstance(summary, dict):
            return summary
        try:
            company_dir = kwargs.get("company_dir") or kwargs.get("company_slug") or kwargs.get("slug")
            company_name = kwargs.get("company_name") or kwargs.get("company") or kwargs.get("name")
            field = kwargs.get("field") or kwargs.get("sector") or summary.get("field") or "반도체"
            if company_dir is None and args:
                company_dir = args[0]
            if company_name is None and len(args) >= 2:
                company_name = args[1]
            company_dir = str(company_dir or summary.get("company_dir") or summary.get("company_slug") or "").strip()
            company_name = str(company_name or summary.get("company") or summary.get("company_name") or "").strip()
            if not company_dir:
                return summary

            from common.data_paths import company_agent_dir as _cert_company_agent_dir
            from data_intake.tech_intake.certification_standards import (
                build_certification_standard_features as _cert_build,
                merge_certification_into_summary as _cert_merge,
                render_certification_md as _cert_render_md,
            )
            from pathlib import Path as _CertPath
            import json as _cert_json

            tech_dir = _cert_company_agent_dir(company_dir, "tech", create=True)
            feature_path = _CertPath(tech_dir) / "tech_certification_features.json"
            if feature_path.exists():
                feature = _cert_json.loads(feature_path.read_text(encoding="utf-8"))
            else:
                feature = _cert_build(company_dir=company_dir, company=company_name or None, field=str(field or "반도체"), write=True)

            summary = _cert_merge(summary, feature)

            for p in [_CertPath(tech_dir) / "tech_chair_summary.json", _CertPath(tech_dir) / f"{company_dir}_tech_chair_summary.json"]:
                try:
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_text(_cert_json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass

            md_block = "\n\n<!-- CERTIFICATION_STANDARDS_SUMMARY_START -->\n" + _cert_render_md(feature).strip() + "\n<!-- CERTIFICATION_STANDARDS_SUMMARY_END -->\n"
            start = "<!-- CERTIFICATION_STANDARDS_SUMMARY_START -->"
            end = "<!-- CERTIFICATION_STANDARDS_SUMMARY_END -->"
            for p in [_CertPath(tech_dir) / "tech_chair_summary.md", _CertPath(tech_dir) / f"{company_dir}_tech_chair_summary.md"]:
                try:
                    if p.exists():
                        txt = p.read_text(encoding="utf-8", errors="replace")
                        if start in txt and end in txt:
                            before = txt.split(start, 1)[0].rstrip()
                            after = txt.split(end, 1)[1].lstrip()
                            txt = before + md_block + after
                        else:
                            txt = txt.rstrip() + md_block
                        p.write_text(txt, encoding="utf-8")
                except Exception:
                    pass
        except Exception as exc:
            warnings = list(summary.get("warnings") or [])
            warnings.append(f"certification_standards_merge_failed: {exc}")
            summary["warnings"] = warnings
        return summary
except Exception:
    pass
