from __future__ import annotations

import csv
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

try:
    from common.data_paths import (
        ROOT_DIR,
        company_agent_dir,
        company_name as canonical_company_name,
        company_slug,
        rel_project_path,
        read_json,
        write_json,
        write_text,
    )
except Exception:  # pragma: no cover - script fallback
    ROOT_DIR = Path(__file__).resolve().parents[2]

    def company_slug(value: Any, default: str | None = None) -> str:
        mapping = {"네패스": "nepes", "한미반도체": "hanmi", "한솔케미칼": "hansol", "덕산테코피아": "duksan", "엘티씨": "ltc", "LTC": "ltc"}
        raw = str(value or default or "").strip()
        return mapping.get(raw, raw.lower() or "unknown")

    def canonical_company_name(value: Any) -> str:
        mapping = {"nepes": "네패스", "hanmi": "한미반도체", "hansol": "한솔케미칼", "duksan": "덕산테코피아", "ltc": "엘티씨"}
        return mapping.get(str(value), str(value))

    def company_agent_dir(value: Any, agent: str, *, create: bool = True) -> Path:
        slug = company_slug(value)
        name = canonical_company_name(slug)
        p = ROOT_DIR / "data" / "반도체" / name / agent
        if create:
            p.mkdir(parents=True, exist_ok=True)
        return p

    def rel_project_path(value: Any, **_: Any) -> str:
        try:
            return str(Path(str(value)).resolve().relative_to(ROOT_DIR.resolve())).replace("\\", "/")
        except Exception:
            return str(value).replace("\\", "/")

    def read_json(path: Path) -> Any | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def write_json(path: Path, data: Any) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def write_text(path: Path, text: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path


try:  # prompt/rubric policy is the single source of truth for deterministic outputs too.
    from .prompts import (
        CAPITAL_AND_DILUTION_POLICY,
        DATA_QUALITY_POLICY,
        EVIDENCE_DEDUP_POLICY,
        EVIDENCE_SOURCE_PRIORITY,
        FINAL_TECH_SCORE_POLICY,
        INVESTOR_OUTPUT_POLICY,
        LITERATURE_APPLICATION_POLICY,
        TECH_EVALUATION_CRITERIA_MAP,
        TECH_TO_VALUE_BRIDGE_PROMPT,
    )
except Exception:  # pragma: no cover - script fallback
    try:
        from tech_agent.prompts import (
            CAPITAL_AND_DILUTION_POLICY,
            DATA_QUALITY_POLICY,
            EVIDENCE_DEDUP_POLICY,
            EVIDENCE_SOURCE_PRIORITY,
            FINAL_TECH_SCORE_POLICY,
            INVESTOR_OUTPUT_POLICY,
            LITERATURE_APPLICATION_POLICY,
            TECH_EVALUATION_CRITERIA_MAP,
            TECH_TO_VALUE_BRIDGE_PROMPT,
        )
    except Exception:
        CAPITAL_AND_DILUTION_POLICY = ""
        DATA_QUALITY_POLICY = ""
        EVIDENCE_DEDUP_POLICY = ""
        EVIDENCE_SOURCE_PRIORITY = []
        FINAL_TECH_SCORE_POLICY = {
            "description": "개인투자자용 최종 Tech 점수 정책을 불러오지 못해 기본 가중치를 사용합니다.",
            "weights": {
                "tech_to_value_bridge": 0.45,
                "ip_evidence_composite": 0.20,
                "excel_quantified_evidence": 0.20,
                "evidence_confidence": 0.15,
            },
            "grade_thresholds": {
                "INVESTOR_TECH_CONVICTION": 82,
                "TECH_TO_VALUE_READY": 68,
                "COMMERCIALIZATION_WATCH": 52,
                "EVIDENCE_WEAK_OR_EARLY": 0,
            },
        }
        INVESTOR_OUTPUT_POLICY = ""
        LITERATURE_APPLICATION_POLICY = ""
        TECH_EVALUATION_CRITERIA_MAP = {}
        TECH_TO_VALUE_BRIDGE_PROMPT = ""


def _policy_weights() -> dict[str, float]:
    raw = FINAL_TECH_SCORE_POLICY.get("weights") if isinstance(FINAL_TECH_SCORE_POLICY, dict) else {}
    if not isinstance(raw, dict) or not raw:
        raw = {
            "tech_to_value_bridge": 0.45,
            "ip_evidence_composite": 0.20,
            "excel_quantified_evidence": 0.20,
            "evidence_confidence": 0.15,
        }
    weights: dict[str, float] = {}
    for key, value in raw.items():
        try:
            weights[str(key)] = float(value)
        except Exception:
            continue
    total = sum(weights.values())
    if total > 0 and abs(total - 1.0) > 0.0001:
        weights = {k: round(v / total, 6) for k, v in weights.items()}
    return weights


def _policy_grade_labels() -> list[tuple[float, str, str]]:
    thresholds = FINAL_TECH_SCORE_POLICY.get("grade_thresholds") if isinstance(FINAL_TECH_SCORE_POLICY, dict) else {}
    if not isinstance(thresholds, dict) or not thresholds:
        thresholds = {
            "INVESTOR_TECH_CONVICTION": 82,
            "TECH_TO_VALUE_READY": 68,
            "COMMERCIALIZATION_WATCH": 52,
            "EVIDENCE_WEAK_OR_EARLY": 0,
        }
    descriptions = (FINAL_TECH_SCORE_POLICY.get("interpretation") if isinstance(FINAL_TECH_SCORE_POLICY, dict) else {}) or {}
    default_labels = {
        "INVESTOR_TECH_CONVICTION": "기술-사업화 근거가 강한 확신형",
        "TECH_TO_VALUE_READY": "사업화 연결성이 확인되는 준비형",
        "COMMERCIALIZATION_WATCH": "사업화 전환을 추적할 관찰형",
        "EVIDENCE_WEAK_OR_EARLY": "근거 보강이 필요한 초기/제한형",
    }
    rows: list[tuple[float, str, str]] = []
    for code, threshold in thresholds.items():
        try:
            rows.append((float(threshold), str(code), str(descriptions.get(code) or default_labels.get(code) or code)))
        except Exception:
            continue
    return sorted(rows, key=lambda x: x[0], reverse=True)


def _prompt_policy_snapshot() -> dict[str, Any]:
    return {
        "final_score_policy": FINAL_TECH_SCORE_POLICY,
        "criteria_map": TECH_EVALUATION_CRITERIA_MAP,
        "tech_to_value_bridge_prompt": TECH_TO_VALUE_BRIDGE_PROMPT,
        "investor_output_policy": INVESTOR_OUTPUT_POLICY,
        "literature_application_policy": LITERATURE_APPLICATION_POLICY,
        "data_quality_policy": DATA_QUALITY_POLICY,
        "capital_and_dilution_policy": CAPITAL_AND_DILUTION_POLICY,
        "evidence_dedup_policy": EVIDENCE_DEDUP_POLICY,
        "evidence_source_priority": EVIDENCE_SOURCE_PRIORITY,
    }


INVESTOR_VIEW_VERSION = "tech-investor-scorecard-v2"

CRITERIA_KR = dict(TECH_EVALUATION_CRITERIA_MAP) or {
    "technical_differentiation": "기술 차별성",
    "manufacturability": "양산성",
    "customer_adoption": "고객 채택도",
    "profit_contribution": "수익성 기여",
    "scalability": "확장성",
    "entry_barrier": "진입장벽",
    "investment_continuity": "투자 지속성",
}


FINAL_SCORE_WEIGHTS = _policy_weights()

GRADE_LABELS = _policy_grade_labels()

MARKER_START = "<!-- TECH_INVESTOR_SCORECARD_START -->"
MARKER_END = "<!-- TECH_INVESTOR_SCORECARD_END -->"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _clean(value: Any, limit: int = 260, none: str = "확인 제한") -> str:
    if value is None:
        return none
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return none
    text = re.sub(r"\s+", " ", str(value)).replace("\ufeff", "").strip()
    if not text or text.lower() in {"nan", "none", "null", "n/a"}:
        return none
    return text[:limit] + ("..." if len(text) > limit else "")


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            x = float(value)
            if math.isnan(x) or math.isinf(x):
                return None
            return x
        except Exception:
            return None
    text = str(value).replace(",", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        x = float(m.group(0))
        if math.isnan(x) or math.isinf(x):
            return None
        return x
    except Exception:
        return None


def _clamp_score(value: Any, default: float | None = None) -> float | None:
    x = _to_float(value)
    if x is None:
        return default
    if 0 <= x <= 35:
        # Tech Agent 원점수 35점 체계로 들어온 경우 100점 환산
        return round((x / 35.0) * 100.0, 2)
    return round(max(0.0, min(100.0, x)), 2)


def _first_present(*values: Any, default: Any = None) -> Any:
    for v in values:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if isinstance(v, (list, dict)) and len(v) == 0:
            continue
        return v
    return default


def _norm_dedupe_key(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    text = re.sub(r"[\W_]+", "", text)
    return text[:120]


def _dedupe_list(values: Iterable[Any], *, limit: int = 20) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        text = _clean(v, 420, none="")
        if not text:
            continue
        key = _norm_dedupe_key(text)
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _read_json_any(paths: Iterable[Path]) -> tuple[Any | None, Path | None]:
    for path in paths:
        if path.exists():
            data = read_json(path)
            if data is not None:
                return data, path
    return None, None


def _read_csv_rows(paths: Iterable[Path]) -> tuple[list[dict[str, Any]], Path | None]:
    for path in paths:
        if not path.exists():
            continue
        for enc in ("utf-8-sig", "utf-8", "cp949"):
            try:
                with path.open("r", encoding=enc, newline="") as f:
                    rows = list(csv.DictReader(f))
                return rows, path
            except Exception:
                continue
    return [], None


def _tech_dir(company_dir: str) -> Path:
    return company_agent_dir(company_dir, "tech", create=True)


def _artifact_paths(slug: str, tech_dir: Path) -> dict[str, list[Path]]:
    return {
        "summary": [tech_dir / "tech_chair_summary.json", tech_dir / f"{slug}_tech_chair_summary.json"],
        "summary_md": [tech_dir / f"{slug}_tech_chair_summary.md", tech_dir / "tech_chair_summary.md"],
        "agent_packet": [tech_dir / f"{slug}_tech_agent_packet.json", tech_dir / f"{slug}_tech.json", tech_dir / "tech.json"],
        "bridge": [
            tech_dir / "tech_to_value_bridge_ip_evidence_adjusted.json",
            tech_dir / f"{slug}_tech_to_value_bridge_ip_evidence_adjusted.json",
            tech_dir / f"{slug}_tech_to_value_inputs.json",
            tech_dir / "tech_to_value_bridge.json",
        ],
        "excel_frame": [tech_dir / "tech_excel_frame_full.json", tech_dir / "source" / f"{slug}_tech_excel_frame_evidence.json"],
        "quantified": [tech_dir / "quantified_metrics.csv", tech_dir / "quanified_metrix.csv", tech_dir / "tech_excel_frame_metrics.csv"],
        "ip_composite": [tech_dir / "tech_ip_evidence_composite.json", tech_dir / f"{slug}_tech_ip_evidence_composite.json"],
        "legal": [tech_dir / "tech_ip_legal_features.json", tech_dir / f"{slug}_tech_ip_legal_features.json"],
        "claim": [tech_dir / "tech_ip_claim_features.json", tech_dir / f"{slug}_tech_ip_claim_features.json"],
        "citation": [tech_dir / "tech_ip_citation_features.json", tech_dir / f"{slug}_tech_ip_citation_features.json"],
        "family": [tech_dir / "tech_ip_family_features.json", tech_dir / f"{slug}_tech_ip_family_features.json"],
        "patent": [tech_dir / f"{slug}_tech_patent_evidence.json", tech_dir / "tech_patent_evidence.json"],
        "deep_dive_md": [tech_dir / f"{slug}_tech_deep_dive.md"],
        "full_appendix_md": [tech_dir / f"{slug}_tech_full_appendix.md"],
    }


def _extract_final_bridge(summary: dict[str, Any], bridge: dict[str, Any] | None) -> tuple[float | None, dict[str, Any]]:
    bridge = bridge or {}
    tv = summary.get("tech_to_value") or {}
    selected = summary.get("selected_ml") or {}
    candidate = _first_present(
        tv.get("final_bridge_score_after_ip_evidence"),
        selected.get("final_bridge_score_after_ip_evidence"),
        bridge.get("final_bridge_score_after_ip_evidence"),
        tv.get("peer_adjusted_bridge_score"),
        tv.get("base_bridge_score"),
        bridge.get("peer_adjusted_bridge_score"),
        bridge.get("score"),
        summary.get("tech_to_value_bridge_score"),
    )
    score = _clamp_score(candidate)
    meta = {
        "raw_value": candidate,
        "base_bridge_score": _first_present(tv.get("base_bridge_score"), bridge.get("base_bridge_score"), bridge.get("score")),
        "peer_adjusted_bridge_score": _first_present(tv.get("peer_adjusted_bridge_score"), bridge.get("peer_adjusted_bridge_score")),
        "final_bridge_score_after_ip_evidence": _first_present(tv.get("final_bridge_score_after_ip_evidence"), bridge.get("final_bridge_score_after_ip_evidence")),
        "grade": _first_present(tv.get("peer_adjusted_grade"), tv.get("base_bridge_grade"), bridge.get("grade"), bridge.get("final_grade")),
        "signal": _first_present(tv.get("ip_evidence_composite_bridge_signal"), bridge.get("ip_evidence_composite_bridge_signal"), bridge.get("signal")),
    }
    return score, meta


def _extract_ip_composite(ip_comp: dict[str, Any] | None, feature_docs: dict[str, dict[str, Any]]) -> tuple[float | None, dict[str, Any]]:
    ip_comp = ip_comp or {}
    score = _clamp_score(
        _first_present(
            ip_comp.get("ip_evidence_composite_score"),
            ip_comp.get("composite_score"),
            ip_comp.get("score"),
        )
    )
    components: dict[str, Any] = {}
    raw_components = ip_comp.get("component_scores") or ip_comp.get("components") or {}
    if isinstance(raw_components, dict):
        components.update(raw_components)

    defaults = {
        "legal_stability": ("legal", ["legal_stability_score_estimated", "legal_stability_score", "score"]),
        "claim_defense": ("claim", ["claim_defense_score_estimated", "claim_defense_score", "score"]),
        "citation_impact": ("citation", ["citation_impact_score", "technology_influence_score", "score"]),
        "global_extension": ("family", ["global_extension_score", "family_extension_score", "score"]),
    }
    for out_key, (doc_key, keys) in defaults.items():
        if _to_float(components.get(out_key)) is not None:
            continue
        doc = feature_docs.get(doc_key) or {}
        for k in keys:
            if _to_float(doc.get(k)) is not None:
                components[out_key] = doc.get(k)
                break

    if score is None:
        vals = [_clamp_score(v) for v in components.values()]
        vals = [v for v in vals if v is not None]
        if vals:
            score = round(sum(vals) / len(vals), 2)

    meta = {
        "score": score,
        "bridge_signal": _first_present(ip_comp.get("bridge_signal"), ip_comp.get("ip_evidence_bridge_signal")),
        "bridge_adjustment_points": _first_present(ip_comp.get("bridge_adjustment_points"), ip_comp.get("adjustment_points")),
        "data_coverage": _first_present(ip_comp.get("data_coverage"), ip_comp.get("coverage")),
        "component_scores": components,
    }
    return score, meta


def _score_excel_quantified(excel_frame: dict[str, Any] | None, metric_rows: list[dict[str, Any]]) -> tuple[float, dict[str, Any]]:
    excel_frame = excel_frame or {}
    company_items = excel_frame.get("company_items") or []
    company_item_count = int(_to_float(excel_frame.get("company_item_count")) or len(company_items) or 0)
    filled_count = int(_to_float(excel_frame.get("content_filled_count")) or 0)
    numeric_signal_count = int(_to_float(excel_frame.get("numeric_signal_count")) or 0)
    formula_rule_count = int(_to_float(excel_frame.get("formula_rule_count")) or 0)

    if metric_rows:
        value_rows = 0
        content_rows = 0
        categories = set()
        metrics = set()
        for row in metric_rows:
            categories.add(_clean(row.get("category"), 80, none=""))
            metrics.add(_clean(row.get("metric_name") or row.get("item_name"), 80, none=""))
            if _to_float(row.get("metric_value")) is not None:
                value_rows += 1
            if str(row.get("content_present") or "").lower() in {"true", "1", "yes", "y"} or _clean(row.get("content"), 40, none=""):
                content_rows += 1
        metric_count = len(metric_rows)
        if company_item_count <= 0:
            company_item_count = max(metric_count, 1)
        filled_count = max(filled_count, content_rows)
        numeric_signal_count = max(numeric_signal_count, value_rows)
        category_count = len({c for c in categories if c})
        unique_metric_count = len({m for m in metrics if m})
    else:
        metric_count = 0
        category_count = len({str(x.get("category") or "").strip() for x in company_items if isinstance(x, dict) and str(x.get("category") or "").strip()})
        unique_metric_count = 0

    coverage = filled_count / company_item_count if company_item_count else 0.0
    numeric_density = numeric_signal_count / company_item_count if company_item_count else 0.0
    category_coverage = min(1.0, category_count / 7.0) if category_count else 0.0
    formula_bonus = min(1.0, formula_rule_count / 7.0) if formula_rule_count else 0.0

    score = 30.0
    score += coverage * 25.0
    score += min(1.0, numeric_density) * 20.0
    score += category_coverage * 15.0
    score += formula_bonus * 10.0
    score = round(max(0.0, min(100.0, score)), 2)

    meta = {
        "score": score,
        "company_item_count": company_item_count,
        "filled_count": filled_count,
        "metric_row_count": metric_count,
        "numeric_signal_count": numeric_signal_count,
        "category_count": category_count,
        "unique_metric_count": unique_metric_count,
        "formula_rule_count": formula_rule_count,
        "coverage_ratio": round(coverage, 4),
        "numeric_density": round(numeric_density, 4),
    }
    return score, meta


def _extract_evidence_confidence(summary: dict[str, Any], agent_packet: dict[str, Any] | None, patent_doc: dict[str, Any] | None, excel_meta: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    selected = summary.get("selected_ml") or {}
    conf_raw = _first_present(
        selected.get("tech_to_value_evidence_confidence_score"),
        selected.get("evidence_confidence_score"),
        summary.get("tech_to_value_evidence_confidence_score"),
    )
    score = _clamp_score(conf_raw)

    evidence_count = 0
    claim_count = 0
    if isinstance(agent_packet, dict):
        evidence_count = len(agent_packet.get("evidences") or agent_packet.get("evidence") or [])
        claim_count = len(agent_packet.get("claims") or [])
    patent_doc = patent_doc or {}
    patent_count = int(_to_float(_first_present(patent_doc.get("normalized_record_count"), patent_doc.get("patent_count"), patent_doc.get("company_matched_record_count"))) or 0)

    if score is None:
        score = 35.0
        score += min(1.0, evidence_count / 20.0) * 20.0
        score += min(1.0, claim_count / 10.0) * 10.0
        score += min(1.0, patent_count / 300.0) * 20.0
        score += min(1.0, float(excel_meta.get("coverage_ratio") or 0)) * 15.0
        score = round(max(0.0, min(100.0, score)), 2)

    meta = {
        "score": score,
        "evidence_count": evidence_count,
        "claim_count": claim_count,
        "patent_count": patent_count,
        "excel_coverage_ratio": excel_meta.get("coverage_ratio"),
    }
    return score, meta



def _score_commercialization_and_funding_signal(
    summary: dict[str, Any],
    metric_rows: list[dict[str, Any]],
    feature_docs: dict[str, dict[str, Any]],
    patent_doc: dict[str, Any] | None,
    bridge_meta: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    """Score the prompt-policy layer for commercialization/funding continuity.

    This is deliberately conservative: it rewards explicit company data about R&D,
    patents, production/customer/commercialization, government projects, technology
    transfer, or growth-purpose CAPEX/funding, and it does not infer those events
    from generic market narratives.
    """
    signals: list[str] = []
    warnings: list[str] = []
    score = 45.0

    text_pool: list[str] = []
    for row in metric_rows[:300]:
        if not isinstance(row, dict):
            continue
        text_pool.append(
            " ".join(
                _clean(row.get(k), 220, none="")
                for k in ("category", "item_name", "metric_name", "content", "quantifiable_plan", "metric_value_source", "source_text")
            )
        )
    for value in summary.get("key_takeaways") or summary.get("takeaways") or []:
        text_pool.append(_clean(value, 260, none=""))

    joined = " ".join(x for x in text_pool if x)
    keyword_groups = {
        "rd": ["R&D", "연구개발", "연구 개발", "개발비", "r&d"],
        "commercial": ["양산", "고객", "납품", "매출", "수주", "인증", "공급", "라인"],
        "government": ["정부과제", "국책과제", "과제 수주", "정부 R&D", "지원사업"],
        "transfer": ["기술이전", "라이선스", "license", "licensing"],
        "funding": ["CAPEX", "설비투자", "시설투자", "CB", "BW", "유상증자", "메자닌", "전환사채"],
    }
    detected: dict[str, bool] = {}
    for group, keys in keyword_groups.items():
        hit = any(k.lower() in joined.lower() for k in keys)
        detected[group] = hit
        if hit:
            signals.append(group)

    if detected.get("rd"):
        score += 8.0
    if detected.get("commercial"):
        score += 14.0
    if detected.get("government"):
        score += 5.0
    if detected.get("transfer"):
        score += 4.0
    if detected.get("funding"):
        score += 3.0

    patent_doc = patent_doc or {}
    recent_patents = _to_float(_first_present(patent_doc.get("recent_5y_patents"), patent_doc.get("recent_patents"), patent_doc.get("recent_patent_count")))
    if recent_patents is not None and recent_patents > 0:
        score += min(10.0, recent_patents / 20.0)
        signals.append("recent_patent_activity")

    for feature_key, doc in feature_docs.items():
        if not isinstance(doc, dict) or not doc:
            warnings.append(f"{feature_key}_feature_missing_or_limited")
            continue
        coverage_values = [v for k, v in doc.items() if "coverage" in str(k).lower() or "rate" in str(k).lower()]
        numeric = [_to_float(v) for v in coverage_values]
        numeric = [v for v in numeric if v is not None]
        if numeric and max(numeric) > 0:
            score += 1.5

    bridge_signal = _clean(bridge_meta.get("signal") or bridge_meta.get("grade"), 120, none="")
    if bridge_signal:
        if any(token in bridge_signal for token in ["WEAK", "GAP", "취약", "괴리"]):
            score -= 8.0
        elif any(token in bridge_signal for token in ["READY", "POSITIVE", "CONFIRMED", "확인", "긍정"]):
            score += 6.0

    if not detected.get("commercial"):
        warnings.append("customer_mass_production_revenue_signal_limited")
        score = min(score, 72.0)
    if not detected.get("rd") and recent_patents is None:
        warnings.append("rd_or_recent_patent_continuity_limited")
    if not detected.get("funding"):
        warnings.append("capital_raising_signal_not_explicitly_detected")

    score = round(max(0.0, min(100.0, score)), 2)
    return score, {
        "score": score,
        "detected_signal_groups": sorted(set(signals)),
        "detected_flags": detected,
        "recent_5y_patents": recent_patents,
        "warnings": _dedupe_list(warnings, limit=12),
        "policy_reference": "CAPITAL_AND_DILUTION_POLICY + TECH_TO_VALUE_BRIDGE_PROMPT",
    }


def _grade(score: float | None) -> dict[str, Any]:
    if score is None:
        return {"code": "UNKNOWN", "label": "확인 제한", "threshold": None}
    for threshold, code, label in GRADE_LABELS:
        if score >= threshold:
            return {"code": code, "label": label, "threshold": threshold}
    return {"code": "UNKNOWN", "label": "확인 제한", "threshold": None}


def _component_rows(components: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for key, item in components.items():
        rows.append({
            "component": key,
            "label": item.get("label"),
            "score": item.get("score"),
            "weight": item.get("weight"),
            "weighted_score": round((float(item.get("score") or 0) * float(item.get("weight") or 0)), 4),
            "meaning": item.get("meaning"),
        })
    return rows


def _build_evidence_pool(
    *,
    company: str,
    summary: dict[str, Any],
    metric_rows: list[dict[str, Any]],
    excel_frame: dict[str, Any] | None,
    feature_docs: dict[str, dict[str, Any]],
    patent_doc: dict[str, Any] | None,
    bridge_meta: dict[str, Any],
    ip_meta: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []

    def add(source: str, title: str, detail: Any, value: Any = None, unit: Any = None, path: Any = None, strength: str = "중") -> None:
        text = _clean(detail, 520, none="")
        if not text:
            return
        item = {
            "source": source,
            "title": _clean(title, 120, none=source),
            "detail": text,
            "value": value,
            "unit": unit,
            "path": rel_project_path(path) if path else None,
            "strength": strength,
        }
        evidence.append(item)

    add(
        "tech_to_value",
        "최종 Tech-to-Value Bridge",
        f"{company}의 최종 기술-사업화 연결 점수는 {bridge_meta.get('raw_value')}이며, Chair에는 기술성보다 고객 채택·양산·매출 전환 가능성을 우선 반영합니다.",
        bridge_meta.get("raw_value"),
        "점",
        strength="상" if _to_float(bridge_meta.get("raw_value")) is not None else "중",
    )

    if ip_meta.get("score") is not None:
        add(
            "kipris_ip_evidence",
            "IP Evidence Composite",
            f"법적 안정성·청구항 방어력·인용 영향력·해외 패밀리 확장성을 합성한 IP Evidence Composite Score는 {ip_meta.get('score')}입니다.",
            ip_meta.get("score"),
            "점",
            strength="상",
        )

    for key, doc in feature_docs.items():
        if not isinstance(doc, dict) or not doc:
            continue
        if key == "legal":
            add("kipris_legal", "권리 안정성", f"등록률 {doc.get('registration_rate_estimated')}, 존속률 {doc.get('alive_rate_among_registered_estimated')}, 권리 안정성 점수 {doc.get('legal_stability_score_estimated')}를 확인했습니다.", doc.get("legal_stability_score_estimated"), "점")
        elif key == "claim":
            add("kipris_claim", "청구항 방어력", f"청구항 수 {doc.get('claim_count')}, 독립항 추정 {doc.get('independent_claim_count_estimated')}, claim defense score {doc.get('claim_defense_score_estimated')}입니다.", doc.get("claim_defense_score_estimated"), "점")
        elif key == "citation":
            add("kipris_citation", "인용 영향력", f"전방/후방 인용 및 기술 영향력 점수 기준 {doc.get('bridge_signal') or doc.get('citation_bridge_signal') or '신호 확인'}입니다.", doc.get("technology_influence_score") or doc.get("citation_impact_score"), "점")
        elif key == "family":
            add("kipris_family", "글로벌 패밀리 확장성", f"해외 패밀리 비중 {doc.get('overseas_family_patent_rate')}, 감지 지역 {doc.get('detected_overseas_regions')}, global extension score {doc.get('global_extension_score')}입니다.", doc.get("global_extension_score"), "점")

    # Excel-frame quantified metrics: 개인투자자가 보는 근거를 늘리되 중복은 제거한다.
    valuable_rows = []
    for row in metric_rows:
        val = _to_float(row.get("metric_value"))
        content = _clean(row.get("content") or row.get("quantifiable_plan") or row.get("metric_value_source"), 320, none="")
        if val is None and not content:
            continue
        valuable_rows.append(row)
    valuable_rows = valuable_rows[:12]
    for row in valuable_rows:
        title = _clean(row.get("metric_name") or row.get("item_name") or row.get("category"), 120, none="Excel 기반 정량 근거")
        detail = _clean(
            _first_present(
                row.get("content"),
                row.get("quantifiable_plan"),
                row.get("metric_value_source"),
                f"{row.get('category')} / {row.get('item_name')} 항목에서 정량 신호를 확인했습니다.",
            ),
            420,
        )
        add(
            "excel_frame",
            title,
            detail,
            row.get("metric_value"),
            row.get("metric_unit"),
            strength="상" if _to_float(row.get("metric_value")) is not None else "중",
        )

    # Summary takeaways already generated by Tech Agent.
    for text in (summary.get("key_takeaways") or summary.get("takeaways") or [])[:5]:
        add("tech_summary", "Tech Agent 핵심 해석", text, strength="중")

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in evidence:
        key = _norm_dedupe_key(f"{item.get('source')} {item.get('title')} {item.get('detail')}")
        if key in seen:
            continue
        seen.add(key)
        item["evidence_id"] = f"tech.inv.ev.{len(deduped)+1:03d}"
        deduped.append(item)
        if len(deduped) >= 18:
            break
    return deduped


def _build_takeaways(company: str, final_score: float, grade: dict[str, Any], evidence: list[dict[str, Any]], components: dict[str, dict[str, Any]]) -> list[str]:
    bridge = components.get("tech_to_value_bridge", {}).get("score")
    ip = components.get("ip_evidence_composite", {}).get("score")
    excel = components.get("excel_quantified_evidence", {}).get("score")
    phrases = [
        f"{company}의 개인투자자용 Tech 최종 점수는 {final_score:.2f}/100이며, 판정은 {grade.get('label')}입니다.",
        f"최종 판단은 단순 특허 수보다 Tech-to-Value Bridge({bridge})와 IP Evidence({ip}) 및 Excel 기반 정량 근거({excel})를 함께 반영했습니다.",
        f"투자자가 확인할 핵심 근거는 {len(evidence)}개로 정리했으며, 중복 뉴스·중복 항목은 제외했습니다.",
    ]
    return phrases


def build_investor_tech_scorecard(company_dir: str, company_name: str | None = None, *, summary_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    slug = company_slug(company_dir)
    company = company_name or canonical_company_name(slug)
    tech_dir = _tech_dir(slug)
    paths = _artifact_paths(slug, tech_dir)

    summary, summary_path = _read_json_any(paths["summary"])
    if summary_payload:
        summary = summary_payload
    if not isinstance(summary, dict):
        summary = {}

    agent_packet, agent_packet_path = _read_json_any(paths["agent_packet"])
    if not isinstance(agent_packet, dict):
        agent_packet = {}

    bridge_doc, bridge_path = _read_json_any(paths["bridge"])
    if not isinstance(bridge_doc, dict):
        bridge_doc = {}

    excel_frame, excel_path = _read_json_any(paths["excel_frame"])
    if not isinstance(excel_frame, dict):
        excel_frame = {}
    metric_rows, metric_path = _read_csv_rows(paths["quantified"])

    ip_comp, ip_comp_path = _read_json_any(paths["ip_composite"])
    if not isinstance(ip_comp, dict):
        ip_comp = {}

    feature_docs: dict[str, dict[str, Any]] = {}
    feature_paths: dict[str, str | None] = {}
    for key in ("legal", "claim", "citation", "family"):
        doc, path = _read_json_any(paths[key])
        feature_docs[key] = doc if isinstance(doc, dict) else {}
        feature_paths[key] = rel_project_path(path) if path else None

    patent_doc, patent_path = _read_json_any(paths["patent"])
    if not isinstance(patent_doc, dict):
        patent_doc = {}

    bridge_score, bridge_meta = _extract_final_bridge(summary, bridge_doc)
    ip_score, ip_meta = _extract_ip_composite(ip_comp, feature_docs)
    excel_score, excel_meta = _score_excel_quantified(excel_frame, metric_rows)
    evidence_score, evidence_meta = _extract_evidence_confidence(summary, agent_packet, patent_doc, excel_meta)
    commercialization_score, commercialization_meta = _score_commercialization_and_funding_signal(
        summary,
        metric_rows,
        feature_docs,
        patent_doc,
        bridge_meta,
    )

    # 결측값이 있어도 전체 파이프라인이 멈추지 않도록 보수 기본값을 둔다.
    bridge_score = bridge_score if bridge_score is not None else 50.0
    ip_score = ip_score if ip_score is not None else 45.0
    evidence_score = evidence_score if evidence_score is not None else 45.0
    commercialization_score = commercialization_score if commercialization_score is not None else 45.0

    components = {
        "tech_to_value_bridge": {
            "label": "Tech-to-Value Bridge",
            "score": round(float(bridge_score), 2),
            "weight": FINAL_SCORE_WEIGHTS.get("tech_to_value_bridge", 0.45),
            "meaning": "기술이 고객 채택·양산·매출 전환으로 이어질 가능성",
            "meta": bridge_meta,
        },
        "ip_evidence_composite": {
            "label": "IP Evidence Composite",
            "score": round(float(ip_score), 2),
            "weight": FINAL_SCORE_WEIGHTS.get("ip_evidence_composite", 0.20),
            "meaning": "권리 안정성·청구항·인용·패밀리 기반 특허 품질",
            "meta": ip_meta,
        },
        "excel_quantified_evidence": {
            "label": "Excel 기반 정량 근거",
            "score": round(float(excel_score), 2),
            "weight": FINAL_SCORE_WEIGHTS.get("excel_quantified_evidence", 0.20),
            "meaning": "템플릿/수식 기준에 맞춰 실제 기업별 근거가 얼마나 채워졌는지",
            "meta": excel_meta,
        },
        "evidence_confidence": {
            "label": "근거 직접성·충분성",
            "score": round(float(evidence_score), 2),
            "weight": FINAL_SCORE_WEIGHTS.get("evidence_confidence", 0.15),
            "meaning": "Chair가 개인투자자에게 설명할 수 있는 근거의 직접성",
            "meta": evidence_meta,
        },
    }
    if "commercialization_and_funding_signal" in FINAL_SCORE_WEIGHTS:
        components["commercialization_and_funding_signal"] = {
            "label": "사업화·성장자금 지속성",
            "score": round(float(commercialization_score), 2),
            "weight": FINAL_SCORE_WEIGHTS.get("commercialization_and_funding_signal", 0.0),
            "meaning": "R&D·특허·정부과제·기술이전·CAPEX/희석성 자금조달이 사업화와 연결되는 정도",
            "meta": commercialization_meta,
        }

    final_score = round(sum(item["score"] * item["weight"] for item in components.values()), 2)
    grade = _grade(final_score)

    evidence = _build_evidence_pool(
        company=company,
        summary=summary,
        metric_rows=metric_rows,
        excel_frame=excel_frame,
        feature_docs=feature_docs,
        patent_doc=patent_doc,
        bridge_meta=bridge_meta,
        ip_meta=ip_meta,
    )
    takeaways = _build_takeaways(company, final_score, grade, evidence, components)

    source_paths = {
        "summary_json": rel_project_path(summary_path) if summary_path else None,
        "agent_packet_json": rel_project_path(agent_packet_path) if agent_packet_path else None,
        "bridge_json": rel_project_path(bridge_path) if bridge_path else None,
        "excel_frame_json": rel_project_path(excel_path) if excel_path else None,
        "quantified_metrics_csv": rel_project_path(metric_path) if metric_path else None,
        "ip_composite_json": rel_project_path(ip_comp_path) if ip_comp_path else None,
        "patent_json": rel_project_path(patent_path) if patent_path else None,
        **{f"{k}_feature_json": v for k, v in feature_paths.items()},
    }

    return {
        "version": INVESTOR_VIEW_VERSION,
        "generated_at": _now(),
        "company_slug": slug,
        "company_name": company,
        "final_tech_investor_score": final_score,
        "final_tech_investor_grade": grade,
        "score_policy": {
            "description": FINAL_TECH_SCORE_POLICY.get("description") if isinstance(FINAL_TECH_SCORE_POLICY, dict) else "개인투자자 관점에서는 여러 점수를 하나의 최종 Tech 점수로 합성한다.",
            "weights": FINAL_SCORE_WEIGHTS,
            "grade_thresholds": FINAL_TECH_SCORE_POLICY.get("grade_thresholds") if isinstance(FINAL_TECH_SCORE_POLICY, dict) else {},
            "score_caps": FINAL_TECH_SCORE_POLICY.get("score_caps") if isinstance(FINAL_TECH_SCORE_POLICY, dict) else {},
        },
        "prompt_policy_alignment": _prompt_policy_snapshot(),
        "score_components": components,
        "score_component_rows": _component_rows(components),
        "key_takeaways": takeaways,
        "investor_evidence": evidence,
        "limitations": [
            "이 점수는 투자수익률 예측값이 아니라 기술-사업화 근거의 설명 가능성 점수입니다.",
            "KIPRIS Plus 유료 endpoint 접근 권한 또는 호출 제한으로 일부 청구항·패밀리·인용 데이터가 부족하면 보수적으로 반영합니다.",
            "Excel 템플릿 값은 복사 근거가 아니라 정량화 프레임이며, 실제 기업별 자료가 채워진 항목만 점수화합니다.",
            "CB/BW·유상증자·정부과제·기술이전 신호는 성장자금과 희석/오버행 리스크를 분리해 보조 레이어로만 해석합니다.",
            "R&D 비용은 effort, 특허/IP는 intermediate output, 고객 채택·양산·매출·마진은 commercial outcome으로 구분합니다.",
        ],
        "source_paths": source_paths,
    }


def render_investor_tech_scorecard_md(scorecard: dict[str, Any]) -> str:
    company = scorecard.get("company_name") or scorecard.get("company_slug") or "기업"
    score = _to_float(scorecard.get("final_tech_investor_score"))
    grade = scorecard.get("final_tech_investor_grade") or {}
    grade_label = grade.get("label") if isinstance(grade, dict) else str(grade)
    grade_code = grade.get("code") if isinstance(grade, dict) else ""

    lines = [
        MARKER_START,
        "## 개인투자자용 Tech 최종 점수판",
        "",
        f"- **대상 기업:** {company}",
        f"- **최종 Tech 점수:** {score:.2f}/100" if score is not None else "- **최종 Tech 점수:** 확인 제한",
        f"- **최종 판정:** {grade_label} `{grade_code}`" if grade_code else f"- **최종 판정:** {grade_label}",
        "- **해석 원칙:** 특허 수, 기술 키워드 수, 뉴스 수를 각각 따로 과장하지 않고, 사업화 연결 가능성과 근거 직접성을 하나의 최종 점수로 통합했습니다.",
        "",
        "### 1) 최종 점수 구성",
        "| 구성요소 | 점수 | 가중치 | 가중 반영 | 의미 |",
        "|---|---:|---:|---:|---|",
    ]
    for row in scorecard.get("score_component_rows") or []:
        sc = _to_float(row.get("score"))
        wt = _to_float(row.get("weight"))
        ws = _to_float(row.get("weighted_score"))
        lines.append(
            f"| {_clean(row.get('label'), 80)} | {sc:.2f} | {wt:.2f} | {ws:.2f} | {_clean(row.get('meaning'), 140)} |"
            if sc is not None and wt is not None and ws is not None
            else f"| {_clean(row.get('label'), 80)} | 확인 제한 | 확인 제한 | 확인 제한 | {_clean(row.get('meaning'), 140)} |"
        )

    lines.extend(["", "### 2) 핵심 해석"])
    for item in _dedupe_list(scorecard.get("key_takeaways") or [], limit=5):
        lines.append(f"- {item}")

    lines.extend(["", "### 3) 개인투자자가 확인할 근거"])
    evidences = scorecard.get("investor_evidence") or []
    if not evidences:
        lines.append("- 확인 가능한 정량·정성 근거가 부족합니다. Tech Intake와 KIPRIS 수집을 먼저 실행하세요.")
    else:
        lines.append("| ID | 출처 | 근거 | 값 | 강도 |")
        lines.append("|---|---|---|---:|---|")
        for ev in evidences[:14]:
            value = _clean(ev.get("value"), 60, none="-")
            unit = _clean(ev.get("unit"), 20, none="")
            val_text = f"{value}{unit}" if value != "-" else "-"
            lines.append(
                f"| {ev.get('evidence_id')} | {_clean(ev.get('source'), 60)} | **{_clean(ev.get('title'), 90)}**: {_clean(ev.get('detail'), 220)} | {val_text} | {_clean(ev.get('strength'), 20)} |"
            )

    lines.extend(["", "### 4) 한계와 보완 필요사항"])
    for item in _dedupe_list(scorecard.get("limitations") or [], limit=5):
        lines.append(f"- {item}")
    lines.append(MARKER_END)
    return "\n".join(lines).strip() + "\n"




def render_investor_tech_view_markdown(scorecard: dict[str, Any]) -> str:
    """Backward-compatible alias used by tech_full_report.py."""
    return render_investor_tech_scorecard_md(scorecard)


def _replace_or_append_marked_block(text: str, block: str) -> str:
    text = text or ""
    if MARKER_START in text and MARKER_END in text:
        pattern = re.compile(re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END), re.S)
        return pattern.sub(block.strip(), text).rstrip() + "\n"
    return text.rstrip() + "\n\n" + block.strip() + "\n"


def merge_investor_scorecard_into_summary(summary: dict[str, Any], scorecard: dict[str, Any]) -> dict[str, Any]:
    summary = dict(summary or {})
    selected = dict(summary.get("selected_ml") or {})
    tv = dict(summary.get("tech_to_value") or {})

    selected["investor_final_tech_score"] = scorecard.get("final_tech_investor_score")
    selected["investor_final_tech_grade"] = scorecard.get("final_tech_investor_grade")
    selected["investor_evidence_count"] = len(scorecard.get("investor_evidence") or [])
    selected["excel_quantified_evidence_score"] = ((scorecard.get("score_components") or {}).get("excel_quantified_evidence") or {}).get("score")
    selected["commercialization_and_funding_signal_score"] = ((scorecard.get("score_components") or {}).get("commercialization_and_funding_signal") or {}).get("score")

    tv["investor_final_tech_score"] = scorecard.get("final_tech_investor_score")
    tv["investor_final_tech_grade"] = scorecard.get("final_tech_investor_grade")

    summary["selected_ml"] = selected
    summary["tech_to_value"] = tv
    summary["tech_investor_view"] = scorecard

    merged_takeaways = _dedupe_list((scorecard.get("key_takeaways") or []) + (summary.get("key_takeaways") or summary.get("takeaways") or []), limit=8)
    summary["key_takeaways"] = merged_takeaways

    return summary


def apply_investor_tech_view_saved_files(
    company_dir: str,
    company_name: str | None = None,
    *,
    summary_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    slug = company_slug(company_dir)
    company = company_name or canonical_company_name(slug)
    tech_dir = _tech_dir(slug)
    paths = _artifact_paths(slug, tech_dir)

    scorecard = build_investor_tech_scorecard(slug, company, summary_payload=summary_payload)
    scorecard_md = render_investor_tech_scorecard_md(scorecard)

    scorecard_json_path = tech_dir / "tech_investor_scorecard.json"
    scorecard_md_path = tech_dir / f"{slug}_tech_investor_scorecard.md"
    write_json(scorecard_json_path, scorecard)
    write_text(scorecard_md_path, scorecard_md)

    summary, summary_path = _read_json_any(paths["summary"])
    if summary_payload:
        summary = summary_payload
    if not isinstance(summary, dict):
        summary = {}
    merged_summary = merge_investor_scorecard_into_summary(summary, scorecard)
    merged_summary.setdefault("summary_files", {})["tech_investor_scorecard_json"] = rel_project_path(scorecard_json_path)
    merged_summary.setdefault("summary_files", {})["tech_investor_scorecard_md"] = rel_project_path(scorecard_md_path)

    canonical_summary_path = tech_dir / "tech_chair_summary.json"
    write_json(canonical_summary_path, merged_summary)
    if summary_path and summary_path != canonical_summary_path:
        write_json(summary_path, merged_summary)

    md_path = None
    for candidate in paths["summary_md"]:
        if candidate.exists():
            md_path = candidate
            break
    md_path = md_path or (tech_dir / f"{slug}_tech_chair_summary.md")
    try:
        existing_md = md_path.read_text(encoding="utf-8") if md_path.exists() else f"# {company} Tech Chair Summary\n"
    except Exception:
        existing_md = f"# {company} Tech Chair Summary\n"
    write_text(md_path, _replace_or_append_marked_block(existing_md, scorecard_md))

    return {
        "status": "OK",
        "company_slug": slug,
        "company_name": company,
        "scorecard": scorecard,
        "summary": merged_summary,
        "output_files": {
            "tech_investor_scorecard_json": rel_project_path(scorecard_json_path),
            "tech_investor_scorecard_md": rel_project_path(scorecard_md_path),
            "tech_chair_summary_json": rel_project_path(canonical_summary_path),
            "tech_chair_summary_md": rel_project_path(md_path),
        },
    }
