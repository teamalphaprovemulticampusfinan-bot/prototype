from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return data
    return {"value": data}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def find_first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None or value == "":
            return default
        return int(float(value))
    except Exception:
        return default


def deep_get(data: Any, key: str, default: Any = None) -> Any:
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for value in data.values():
            found = deep_get(value, key, default=None)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = deep_get(item, key, default=None)
            if found is not None:
                return found
    return default


def build_selected_claim_features(feature: dict[str, Any], source_path: Path) -> dict[str, Any]:
    selected = {
        "status": deep_get(feature, "status", "UNKNOWN"),
        "target_patent_count": safe_int(deep_get(feature, "target_patent_count")),
        "patents_with_claims": safe_int(deep_get(feature, "patents_with_claims")),
        "claim_collection_coverage": safe_float(deep_get(feature, "claim_collection_coverage")),
        "claim_count": safe_int(deep_get(feature, "claim_count")),
        "independent_claim_count_estimated": safe_int(deep_get(feature, "independent_claim_count_estimated")),
        "claim_defense_score_estimated": safe_float(deep_get(feature, "claim_defense_score_estimated")),
        "bridge_adjustment_points": safe_float(deep_get(feature, "bridge_adjustment_points"), 0.0),
        "bridge_signal": deep_get(feature, "bridge_signal", "IP_CLAIM_DATA_NOT_AVAILABLE"),
        "parse_error_count": safe_int(deep_get(feature, "parse_error_count"), 0),
        "source_file": str(source_path.as_posix()),
        "usage_rule": (
            "Use this KIPRIS Plus claim-scope feature as a conservative IP defensibility signal. "
            "It supports Tech-to-Value Bridge adjustment, but it is not direct commercialization evidence."
        ),
    }

    coverage = selected["claim_collection_coverage"] or 0.0
    parse_error_count = selected["parse_error_count"] or 0
    target_count = selected["target_patent_count"] or 0

    if selected["status"] == "OK" and coverage >= 0.95 and parse_error_count == 0:
        selected["collection_quality"] = "HIGH"
    elif selected["status"] == "OK" and coverage >= 0.80:
        selected["collection_quality"] = "MEDIUM"
    else:
        selected["collection_quality"] = "LOW"

    if target_count > 0:
        selected["parse_error_rate"] = round(parse_error_count / target_count, 4)
    else:
        selected["parse_error_rate"] = None

    return selected


def merge_into_json(path: Path, selected: dict[str, Any]) -> None:
    if not path.exists():
        return

    data = read_json(path)

    data["ip_claim_feature_merge_status"] = "MERGED"
    data["ip_claim_features"] = selected

    feature_merge_status = data.get("feature_merge_status")
    if not isinstance(feature_merge_status, dict):
        feature_merge_status = {}
    feature_merge_status["ip_claim_feature_merge_status"] = "MERGED"
    data["feature_merge_status"] = feature_merge_status

    selected_ml = data.get("selected_ml")
    if not isinstance(selected_ml, dict):
        selected_ml = {}
    selected_ml["ip_claim_scope"] = selected
    data["selected_ml"] = selected_ml

    # Chair/Tech에서 바로 꺼내 쓰기 쉽게 top-level 요약도 둔다.
    data["claim_defense_score_estimated"] = selected.get("claim_defense_score_estimated")
    data["claim_count"] = selected.get("claim_count")
    data["independent_claim_count_estimated"] = selected.get("independent_claim_count_estimated")
    data["ip_claim_bridge_adjustment_points"] = selected.get("bridge_adjustment_points")
    data["ip_claim_bridge_signal"] = selected.get("bridge_signal")

    write_json(path, data)


def remove_existing_marked_section(text: str) -> str:
    pattern = re.compile(
        r"\n?<!-- IP_CLAIM_FEATURES_START -->.*?<!-- IP_CLAIM_FEATURES_END -->\n?",
        flags=re.DOTALL,
    )
    return pattern.sub("\n", text).rstrip() + "\n"


def render_md_section(selected: dict[str, Any]) -> str:
    return f"""
<!-- IP_CLAIM_FEATURES_START -->
## KIPRIS Plus 청구항 기반 IP Claim Scope Feature

- status: {selected.get("status")}
- collection_quality: {selected.get("collection_quality")}
- target_patent_count: {selected.get("target_patent_count")}
- patents_with_claims: {selected.get("patents_with_claims")}
- claim_collection_coverage: {selected.get("claim_collection_coverage")}
- claim_count: {selected.get("claim_count")}
- independent_claim_count_estimated: {selected.get("independent_claim_count_estimated")}
- claim_defense_score_estimated: {selected.get("claim_defense_score_estimated")}
- bridge_adjustment_points: {selected.get("bridge_adjustment_points")}
- bridge_signal: {selected.get("bridge_signal")}
- parse_error_count: {selected.get("parse_error_count")}
- parse_error_rate: {selected.get("parse_error_rate")}

### 해석

KIPRIS Plus 청구항 전문 기준으로 수집된 청구항 범위와 독립항 수를 활용해 특허 포트폴리오의 방어력과 권리 범위 신호를 보수적으로 평가한다.  
이 지표는 Tech-to-Value Bridge에서 기술 방어력 보조 가산 요인으로 사용하되, 고객 채택·양산·매출 전환·FCF 개선을 직접 입증하는 사업화 근거로 해석하지 않는다.
<!-- IP_CLAIM_FEATURES_END -->
""".strip()


def merge_into_md(path: Path, selected: dict[str, Any]) -> None:
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8", errors="replace")
    text = remove_existing_marked_section(text)
    section = render_md_section(selected)

    path.write_text(text.rstrip() + "\n\n" + section + "\n", encoding="utf-8")


def merge_ip_claim_features_to_outputs(
    field: str,
    company_name: str,
    company_slug: str,
) -> dict[str, Any]:
    tech_dir = ROOT_DIR / "data" / field / company_name / "tech"

    feature_path = find_first_existing(
        [
            tech_dir / f"{company_slug}_tech_ip_claim_features.json",
            tech_dir / "tech_ip_claim_features.json",
        ]
    )

    if feature_path is None:
        raise FileNotFoundError(
            "청구항 feature json을 찾지 못했습니다. "
            f"확인 위치: {tech_dir / f'{company_slug}_tech_ip_claim_features.json'} 또는 {tech_dir / 'tech_ip_claim_features.json'}"
        )

    feature = read_json(feature_path)
    selected = build_selected_claim_features(feature, feature_path)

    json_targets = [
        tech_dir / "tech_chair_summary.json",
        tech_dir / f"{company_slug}_tech.json",
        tech_dir / f"{company_slug}_tech_agent_packet.json",
        tech_dir / "tech.json",
    ]

    md_targets = [
        tech_dir / f"{company_slug}_tech_chair_summary.md",
        tech_dir / f"{company_slug}_tech_full_appendix.md",
        tech_dir / f"{company_slug}_tech_high_quality_report.md",
    ]

    changed_json = []
    changed_md = []

    for path in json_targets:
        if path.exists():
            merge_into_json(path, selected)
            changed_json.append(str(path))

    for path in md_targets:
        if path.exists():
            merge_into_md(path, selected)
            changed_md.append(str(path))

    return {
        "status": "DONE",
        "tech_dir": str(tech_dir),
        "feature_path": str(feature_path),
        "selected": selected,
        "changed_json": changed_json,
        "changed_md": changed_md,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-name", default="네패스")
    parser.add_argument("--company-slug", default="nepes")
    args = parser.parse_args()

    result = merge_ip_claim_features_to_outputs(
        field=args.field,
        company_name=args.company_name,
        company_slug=args.company_slug,
    )

    print("[DONE] IP Claim Scope feature merged into Tech outputs")
    print(f"- tech_dir: {result['tech_dir']}")
    print(f"- feature_path: {result['feature_path']}")
    print(f"- claim_defense_score_estimated: {result['selected'].get('claim_defense_score_estimated')}")
    print(f"- bridge_adjustment_points: {result['selected'].get('bridge_adjustment_points')}")
    print(f"- bridge_signal: {result['selected'].get('bridge_signal')}")
    print()
    print("[CHANGED JSON]")
    for path in result["changed_json"]:
        print(f"- {path}")
    print()
    print("[CHANGED MD]")
    for path in result["changed_md"]:
        print(f"- {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())