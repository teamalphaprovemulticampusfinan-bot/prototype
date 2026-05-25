from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.data_paths import normalize_field_name


WEIGHTS = {
    "legal_stability": 0.25,
    "claim_defense": 0.30,
    "citation_influence": 0.25,
    "global_extension": 0.20,
}

COMPONENTS = {
    "legal_stability": {
        "label_ko": "등록·존속 안정성",
        "filename": "tech_ip_legal_features.json",
        "score_aliases": [
            "legal_stability_score_estimated",
            "legal_stability_score",
            "ip_legal_stability_score",
        ],
    },
    "claim_defense": {
        "label_ko": "청구항 방어 범위",
        "filename": "tech_ip_claim_features.json",
        "score_aliases": [
            "claim_defense_score_estimated",
            "claim_scope_score_estimated",
            "ip_claim_scope_score",
            "claim_score_estimated",
        ],
    },
    "citation_influence": {
        "label_ko": "인용 기반 기술 영향력",
        "filename": "tech_ip_citation_features.json",
        "score_aliases": [
            "citation_influence_score_estimated",
            "citation_impact_score_estimated",
            "ip_citation_influence_score",
            "technology_influence_score_estimated",
            "citation_score_estimated",
            "citation_power_score_estimated",
        ],
    },
    "global_extension": {
        "label_ko": "해외 패밀리 기반 글로벌 확장성",
        "filename": "tech_ip_family_features.json",
        "score_aliases": [
            "global_extension_score",
            "global_extension_score_estimated",
            "ip_global_extension_score",
            "family_global_extension_score",
        ],
    },
}


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def _norm_key(value: Any) -> str:
    text = _clean_text(value).lower()
    return re.sub(r"[\s_\-./()\[\]{}:]+", "", text)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    text = _clean_text(value)
    if not text:
        return None
    text = text.replace(",", "")
    try:
        return float(text)
    except Exception:
        return None


def _round2(value: float) -> float:
    return round(float(value), 2)


def _round4(value: float) -> float:
    return round(float(value), 4)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _json_candidates(tech_dir: Path, company_slug: str, filename: str) -> list[Path]:
    candidates = [
        tech_dir / filename,
        tech_dir / f"{company_slug}_{filename}",
    ]

    deduped: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        sig = str(path.resolve())
        if sig not in seen:
            deduped.append(path)
            seen.add(sig)
    return deduped


def _find_json(tech_dir: Path, company_slug: str, filename: str) -> Path | None:
    for path in _json_candidates(tech_dir, company_slug, filename):
        if path.exists():
            return path
    return None


def _iter_key_values(obj: Any) -> list[tuple[str, Any]]:
    pairs: list[tuple[str, Any]] = []

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                pairs.append((str(k), v))
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(x, list):
            for item in x:
                if isinstance(item, (dict, list)):
                    walk(item)

    walk(obj)
    return pairs


def _pick_value(data: dict[str, Any], aliases: list[str]) -> Any:
    pairs = _iter_key_values(data)
    alias_norms = [_norm_key(a) for a in aliases]

    for k, v in pairs:
        nk = _norm_key(k)
        for alias in alias_norms:
            if nk == alias:
                return v

    for k, v in pairs:
        nk = _norm_key(k)
        for alias in alias_norms:
            if len(alias) >= 10 and (alias in nk or nk in alias):
                return v

    return None


def _pick_number(data: dict[str, Any], aliases: list[str]) -> float | None:
    value = _pick_value(data, aliases)
    score = _safe_float(value)
    if score is None:
        return None

    if score < 0:
        score = 0.0
    if score > 100:
        score = 100.0
    return _round2(score)


def _pick_bridge_signal(data: dict[str, Any]) -> str:
    value = _pick_value(data, ["bridge_signal", "ip_bridge_signal", "signal"])
    return _clean_text(value)


def _pick_bridge_points(data: dict[str, Any]) -> float | None:
    return _safe_float(_pick_value(data, ["bridge_adjustment_points", "bridge_points", "adjustment_points"]))


def _pick_status(data: dict[str, Any]) -> str:
    value = _pick_value(data, ["status"])
    return _clean_text(value)


def _bridge_from_composite(score: float | None, coverage: float) -> tuple[float, str]:
    if score is None or coverage <= 0:
        return -1.0, "IP_EVIDENCE_DATA_NOT_AVAILABLE"

    if coverage < 0.50:
        return 0.0, "IP_EVIDENCE_PARTIAL_DATA_NEEDS_REVIEW"

    if score >= 80 and coverage >= 0.75:
        return 2.0, "IP_EVIDENCE_STRONG_POSITIVE"

    if score >= 65:
        return 1.0, "IP_EVIDENCE_POSITIVE"

    if score >= 45:
        return 0.0, "IP_EVIDENCE_NEUTRAL"

    return -1.0, "IP_EVIDENCE_WEAK"


def _build_component_result(
    component_key: str,
    tech_dir: Path,
    company_slug: str,
) -> dict[str, Any]:
    spec = COMPONENTS[component_key]
    filename = spec["filename"]
    weight = WEIGHTS[component_key]

    path = _find_json(tech_dir, company_slug, filename)
    if path is None:
        return {
            "component": component_key,
            "label_ko": spec["label_ko"],
            "status": "MISSING_FILE",
            "source_file": "",
            "weight": weight,
            "score_estimated": None,
            "weighted_contribution_points": 0.0,
            "bridge_signal": "",
            "bridge_adjustment_points": None,
        }

    try:
        data = _read_json(path)
    except Exception as exc:
        return {
            "component": component_key,
            "label_ko": spec["label_ko"],
            "status": "READ_ERROR",
            "source_file": str(path),
            "error": repr(exc),
            "weight": weight,
            "score_estimated": None,
            "weighted_contribution_points": 0.0,
            "bridge_signal": "",
            "bridge_adjustment_points": None,
        }

    score = _pick_number(data, spec["score_aliases"])
    feature_status = _pick_status(data)
    bridge_signal = _pick_bridge_signal(data)
    bridge_points = _pick_bridge_points(data)

    if score is None:
        status = "MISSING_SCORE"
        contribution = 0.0
    else:
        status = "OK"
        contribution = _round2(score * weight)

    return {
        "component": component_key,
        "label_ko": spec["label_ko"],
        "status": status,
        "feature_status": feature_status,
        "source_file": str(path),
        "weight": weight,
        "score_estimated": score,
        "weighted_contribution_points": contribution,
        "bridge_signal": bridge_signal,
        "bridge_adjustment_points": bridge_points,
    }


def _build_composite(
    field: str,
    company_name: str,
    company_slug: str,
) -> dict[str, Any]:
    tech_dir = Path("data") / field / company_name / "tech"

    components: dict[str, Any] = {}
    available_weight = 0.0
    weighted_sum = 0.0

    for key in COMPONENTS:
        result = _build_component_result(key, tech_dir, company_slug)
        components[key] = result

        score = result.get("score_estimated")
        weight = float(result.get("weight") or 0.0)
        if score is not None:
            available_weight += weight
            weighted_sum += float(score) * weight

    if available_weight > 0:
        composite_score = _round2(weighted_sum / available_weight)
    else:
        composite_score = None

    data_coverage_rate = _round4(available_weight / sum(WEIGHTS.values()))
    bridge_points, bridge_signal = _bridge_from_composite(composite_score, data_coverage_rate)

    if available_weight >= 0.999:
        status = "OK"
    elif available_weight > 0:
        status = "PARTIAL_OK"
    else:
        status = "NO_FEATURE_DATA"

    missing_components = [
        key for key, value in components.items()
        if value.get("status") != "OK"
    ]

    strengths: list[str] = []
    cautions: list[str] = []

    if composite_score is not None:
        if composite_score >= 80:
            strengths.append("IP 증거의 종합 강도가 높아 Tech-to-Value Bridge에서 기술 방어력과 사업화 근거를 강하게 보강할 수 있습니다.")
        elif composite_score >= 65:
            strengths.append("IP 증거의 종합 강도가 양호하여 특허 포트폴리오의 질적 근거로 활용할 수 있습니다.")
        elif composite_score >= 45:
            cautions.append("IP 증거는 중립 수준으로, 특허 수량만으로 강한 가치평가 가산을 부여하기에는 제한이 있습니다.")
        else:
            cautions.append("IP 증거 강도가 낮아 Tech-to-Value Bridge에서 보수적 해석이 필요합니다.")

    if missing_components:
        cautions.append(f"일부 컴포넌트가 누락되었거나 점수 필드가 없습니다: {', '.join(missing_components)}")

    feature = {
        "company_slug": company_slug,
        "company_name": company_name,
        "field": field,
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "weights": WEIGHTS,
        "components": components,
        "score_calculation": {
            "weighted_sum_on_full_100_scale": _round2(weighted_sum),
            "available_weight": _round4(available_weight),
            "data_coverage_rate": data_coverage_rate,
            "composite_score_estimated": composite_score,
            "formula": (
                "IP Evidence Composite Score = "
                "legal_stability*0.25 + claim_defense*0.30 + "
                "citation_influence*0.25 + global_extension*0.20. "
                "If a component score is missing, the score is normalized by available weight."
            ),
        },
        "tech_to_value_bridge": {
            "bridge_adjustment_points": bridge_points,
            "bridge_signal": bridge_signal,
            "usage_rule": (
                "Use this composite IP evidence score as the integrated IP-quality layer in Tech-to-Value Bridge. "
                "It summarizes legal stability, claim scope defense, citation influence, and global family expansion. "
                "It is not direct revenue evidence and should be combined with finance, market, and commercialization signals."
            ),
        },
        "bridge_adjustment_points": bridge_points,
        "bridge_signal": bridge_signal,
        "ip_evidence_composite_score": composite_score,
        "ip_evidence_data_coverage_rate": data_coverage_rate,
        "strengths": strengths,
        "cautions": cautions,
        "missing_components": missing_components,
    }

    return feature


def _fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    return str(value)


def _build_markdown(feature: dict[str, Any]) -> str:
    lines: list[str] = []

    company_name = feature.get("company_name", "")
    lines.append(f"# {company_name} IP Evidence Composite Score")
    lines.append("")
    lines.append("## 1. Summary")
    lines.append(f"- status: {feature.get('status')}")
    lines.append(f"- ip_evidence_composite_score: {feature.get('ip_evidence_composite_score')}")
    lines.append(f"- ip_evidence_data_coverage_rate: {feature.get('ip_evidence_data_coverage_rate')}")
    lines.append(f"- bridge_adjustment_points: {feature.get('bridge_adjustment_points')}")
    lines.append(f"- bridge_signal: {feature.get('bridge_signal')}")
    lines.append("")

    lines.append("## 2. Component Scores")
    lines.append("")
    lines.append("| Component | Korean Label | Weight | Score | Contribution | Source Status | Bridge Signal |")
    lines.append("|---|---:|---:|---:|---:|---|---|")

    components = feature.get("components", {}) or {}
    for key, item in components.items():
        lines.append(
            "| "
            + str(key)
            + " | "
            + str(item.get("label_ko", ""))
            + " | "
            + _fmt(item.get("weight"))
            + " | "
            + _fmt(item.get("score_estimated"))
            + " | "
            + _fmt(item.get("weighted_contribution_points"))
            + " | "
            + _fmt(item.get("status"))
            + " | "
            + _fmt(item.get("bridge_signal"))
            + " |"
        )

    lines.append("")
    lines.append("## 3. Formula")
    lines.append("")
    lines.append(str(feature.get("score_calculation", {}).get("formula", "")))
    lines.append("")

    lines.append("## 4. Tech-to-Value Bridge")
    lines.append("")
    bridge = feature.get("tech_to_value_bridge", {}) or {}
    lines.append(f"- bridge_adjustment_points: {bridge.get('bridge_adjustment_points')}")
    lines.append(f"- bridge_signal: {bridge.get('bridge_signal')}")
    lines.append(f"- usage_rule: {bridge.get('usage_rule')}")
    lines.append("")

    lines.append("## 5. Strengths")
    strengths = feature.get("strengths", []) or []
    if strengths:
        for item in strengths:
            lines.append(f"- {item}")
    else:
        lines.append("- 별도 강점 문구 없음")
    lines.append("")

    lines.append("## 6. Cautions")
    cautions = feature.get("cautions", []) or []
    if cautions:
        for item in cautions:
            lines.append(f"- {item}")
    else:
        lines.append("- 별도 유의사항 없음")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build integrated IP Evidence Composite Score from KIPRIS IP features.")
    parser.add_argument("--field", required=True, help="예: 반도체")
    parser.add_argument("--company-name", required=True, help="예: 네패스")
    parser.add_argument("--company-slug", required=True, help="예: nepes")
    args = parser.parse_args()
    field = normalize_field_name(args.field)

    tech_dir = Path("data") / field / args.company_name / "tech"
    if not tech_dir.exists():
        raise FileNotFoundError(f"tech directory not found: {tech_dir}")

    feature = _build_composite(
        field=field,
        company_name=args.company_name,
        company_slug=args.company_slug,
    )

    common_json = tech_dir / "tech_ip_evidence_composite.json"
    slug_json = tech_dir / f"{args.company_slug}_tech_ip_evidence_composite.json"
    slug_md = tech_dir / f"{args.company_slug}_tech_ip_evidence_composite.md"

    _write_json(common_json, feature)
    _write_json(slug_json, feature)
    _write_text(slug_md, _build_markdown(feature))

    print("[DONE] IP Evidence Composite created")
    print(f"- common json: {common_json.resolve()}")
    print(f"- slug json: {slug_json.resolve()}")
    print(f"- md: {slug_md.resolve()}")
    print()
    print("[FEATURE SUMMARY]")
    print(json.dumps({
        "status": feature.get("status"),
        "ip_evidence_composite_score": feature.get("ip_evidence_composite_score"),
        "ip_evidence_data_coverage_rate": feature.get("ip_evidence_data_coverage_rate"),
        "bridge_adjustment_points": feature.get("bridge_adjustment_points"),
        "bridge_signal": feature.get("bridge_signal"),
        "missing_components": feature.get("missing_components"),
        "components": {
            k: {
                "status": v.get("status"),
                "score_estimated": v.get("score_estimated"),
                "weight": v.get("weight"),
                "weighted_contribution_points": v.get("weighted_contribution_points"),
            }
            for k, v in (feature.get("components", {}) or {}).items()
        },
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
