from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


START_MARKER = "<!-- IP_EVIDENCE_COMPOSITE_START -->"
END_MARKER = "<!-- IP_EVIDENCE_COMPOSITE_END -->"


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve_tech_dir(
    field: str | None = None,
    company_name: str | None = None,
    company_slug: str | None = None,
    tech_dir: str | Path | None = None,
) -> Path | None:
    if tech_dir:
        p = Path(tech_dir)
        return p if p.exists() else p

    if field and company_name:
        p = Path("data") / field / company_name / "tech"
        if p.exists():
            return p

    if company_slug:
        data_root = Path("data")
        if data_root.exists():
            for p in data_root.glob("*/*/tech"):
                if (p / "tech_ip_evidence_composite.json").exists():
                    return p
                if (p / f"{company_slug}_tech_ip_evidence_composite.json").exists():
                    return p

    return None


def load_ip_evidence_composite(
    tech_dir: str | Path,
    company_slug: str | None = None,
) -> dict[str, Any] | None:
    tech_path = Path(tech_dir)

    candidates: list[Path] = [
        tech_path / "tech_ip_evidence_composite.json",
    ]

    if company_slug:
        candidates.append(tech_path / f"{company_slug}_tech_ip_evidence_composite.json")

    for path in candidates:
        if path.exists():
            try:
                return _read_json(path)
            except Exception:
                continue

    return None


def _build_compact_ip_evidence(feature: dict[str, Any]) -> dict[str, Any]:
    components = feature.get("components", {}) or {}

    compact_components: dict[str, Any] = {}
    for key, item in components.items():
        if not isinstance(item, dict):
            continue
        compact_components[key] = {
            "label_ko": item.get("label_ko"),
            "status": item.get("status"),
            "score_estimated": item.get("score_estimated"),
            "weight": item.get("weight"),
            "weighted_contribution_points": item.get("weighted_contribution_points"),
            "bridge_signal": item.get("bridge_signal"),
            "bridge_adjustment_points": item.get("bridge_adjustment_points"),
        }

    return {
        "status": feature.get("status"),
        "ip_evidence_composite_score": feature.get("ip_evidence_composite_score"),
        "ip_evidence_data_coverage_rate": feature.get("ip_evidence_data_coverage_rate"),
        "bridge_adjustment_points": feature.get("bridge_adjustment_points"),
        "bridge_signal": feature.get("bridge_signal"),
        "components": compact_components,
        "strengths": feature.get("strengths", []),
        "cautions": feature.get("cautions", []),
        "usage_rule": (feature.get("tech_to_value_bridge", {}) or {}).get("usage_rule")
            or feature.get("usage_rule", ""),
    }


def merge_ip_evidence_composite_into_summary(
    summary: dict[str, Any],
    field: str | None = None,
    company_name: str | None = None,
    company_slug: str | None = None,
    tech_dir: str | Path | None = None,
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return summary

    field = field or _clean_text(summary.get("field")) or "반도체"
    company_name = company_name or _clean_text(summary.get("company_name"))
    company_slug = company_slug or _clean_text(summary.get("company_slug")) or _clean_text(summary.get("slug"))

    resolved_tech_dir = _resolve_tech_dir(
        field=field,
        company_name=company_name,
        company_slug=company_slug,
        tech_dir=tech_dir,
    )

    if resolved_tech_dir is None:
        summary["ip_evidence_composite_merge_status"] = "TECH_DIR_NOT_FOUND"
        return summary

    feature = load_ip_evidence_composite(resolved_tech_dir, company_slug=company_slug)
    if not feature:
        summary["ip_evidence_composite_merge_status"] = "FEATURE_FILE_NOT_FOUND"
        return summary

    compact = _build_compact_ip_evidence(feature)

    summary["ip_evidence_composite_merge_status"] = "MERGED"
    summary["ip_evidence_composite"] = feature

    selected_ml = summary.setdefault("selected_ml", {})
    if isinstance(selected_ml, dict):
        selected_ml["ip_evidence_composite"] = compact
        selected_ml["ip_evidence_composite_score"] = feature.get("ip_evidence_composite_score")
        selected_ml["ip_evidence_bridge_signal"] = feature.get("bridge_signal")
        selected_ml["ip_evidence_bridge_adjustment_points"] = feature.get("bridge_adjustment_points")

    bridge = summary.setdefault("tech_to_value_bridge", {})
    if isinstance(bridge, dict):
        bridge["ip_evidence_composite_score"] = feature.get("ip_evidence_composite_score")
        bridge["ip_evidence_bridge_signal"] = feature.get("bridge_signal")
        bridge["ip_evidence_bridge_adjustment_points"] = feature.get("bridge_adjustment_points")
        bridge["ip_evidence_data_coverage_rate"] = feature.get("ip_evidence_data_coverage_rate")

    return summary


def _component_rows(feature: dict[str, Any]) -> list[str]:
    components = feature.get("components", {}) or {}
    rows: list[str] = []

    label_map = {
        "legal_stability": "등록·존속 안정성",
        "claim_defense": "청구항 방어 범위",
        "citation_influence": "인용 기반 기술 영향력",
        "global_extension": "해외 패밀리 기반 글로벌 확장성",
    }

    for key in ["legal_stability", "claim_defense", "citation_influence", "global_extension"]:
        item = components.get(key, {}) or {}
        rows.append(
            "| "
            + key
            + " | "
            + str(item.get("label_ko") or label_map.get(key, ""))
            + " | "
            + str(item.get("weight", ""))
            + " | "
            + str(item.get("score_estimated", ""))
            + " | "
            + str(item.get("weighted_contribution_points", ""))
            + " | "
            + str(item.get("status", ""))
            + " |"
        )

    return rows


def build_ip_evidence_composite_md_block(feature: dict[str, Any] | None) -> str:
    if not feature:
        return ""

    score = feature.get("ip_evidence_composite_score")
    coverage = feature.get("ip_evidence_data_coverage_rate")
    bridge_signal = feature.get("bridge_signal")
    bridge_points = feature.get("bridge_adjustment_points")

    lines: list[str] = []
    lines.append(START_MARKER)
    lines.append("")
    lines.append("#### IP Evidence Composite Score")
    lines.append("")
    lines.append(
        "KIPRIS 기반 IP Feature 4종을 통합해 특허 포트폴리오의 질적 근거를 평가했습니다. "
        "이 점수는 특허 수량이 아니라 등록·존속 안정성, 청구항 방어 범위, 인용 기반 기술 영향력, "
        "해외 패밀리 확장성을 종합한 Tech-to-Value Bridge 보조 지표입니다."
    )
    lines.append("")
    lines.append(f"- IP Evidence Composite Score: **{score} / 100**")
    lines.append(f"- Data Coverage Rate: **{coverage}**")
    lines.append(f"- Bridge Signal: **{bridge_signal}**")
    lines.append(f"- Bridge Adjustment Points: **{bridge_points}**")
    lines.append("")
    lines.append("| Component | 의미 | Weight | Score | Contribution | Status |")
    lines.append("|---|---|---:|---:|---:|---|")
    lines.extend(_component_rows(feature))
    lines.append("")
    lines.append("해석:")
    lines.append("- 법적 안정성과 청구항 방어력은 IP 포트폴리오의 방어력을 보여줍니다.")
    lines.append("- 인용 영향력과 글로벌 패밀리 확장성은 시장 내 참조 가치와 해외 권리 확장성을 보여줍니다.")
    lines.append("- 본 지표는 직접적인 매출·수주 증거가 아니므로, 사업화·고객 채택·양산·FCF 개선 근거와 함께 해석해야 합니다.")
    lines.append("")
    lines.append(END_MARKER)
    lines.append("")
    return "\n".join(lines)


def append_ip_evidence_composite_to_markdown(
    markdown_text: str,
    feature: dict[str, Any] | None,
) -> str:
    if not feature:
        return markdown_text

    block = build_ip_evidence_composite_md_block(feature)
    if not block:
        return markdown_text

    text = markdown_text or ""

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER) + r"\s*",
        flags=re.DOTALL,
    )
    text = pattern.sub("", text).rstrip()

    return text + "\n\n" + block


def merge_ip_evidence_composite_saved_files(
    field: str = "반도체",
    company_name: str = "",
    company_slug: str = "",
    tech_dir: str | Path | None = None,
) -> dict[str, Any]:
    resolved_tech_dir = _resolve_tech_dir(
        field=field,
        company_name=company_name,
        company_slug=company_slug,
        tech_dir=tech_dir,
    )

    result: dict[str, Any] = {
        "status": "INIT",
        "json_updated": [],
        "md_updated": [],
        "tech_dir": str(resolved_tech_dir) if resolved_tech_dir else "",
    }

    if resolved_tech_dir is None:
        result["status"] = "TECH_DIR_NOT_FOUND"
        return result

    feature = load_ip_evidence_composite(resolved_tech_dir, company_slug=company_slug)
    if not feature:
        result["status"] = "FEATURE_FILE_NOT_FOUND"
        return result

    json_candidates = [
        resolved_tech_dir / "tech_chair_summary.json",
    ]
    if company_slug:
        json_candidates.append(resolved_tech_dir / f"{company_slug}_tech_chair_summary.json")

    for path in json_candidates:
        if not path.exists():
            continue

        try:
            data = _read_json(path)
            data = merge_ip_evidence_composite_into_summary(
                data,
                field=field,
                company_name=company_name,
                company_slug=company_slug,
                tech_dir=resolved_tech_dir,
            )
            _write_json(path, data)
            result["json_updated"].append(str(path))
        except Exception as exc:
            result.setdefault("json_errors", []).append({"path": str(path), "error": repr(exc)})

    md_candidates = []
    if company_slug:
        md_candidates.append(resolved_tech_dir / f"{company_slug}_tech_chair_summary.md")
    md_candidates.append(resolved_tech_dir / "tech_chair_summary.md")

    for path in md_candidates:
        if not path.exists():
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            text = append_ip_evidence_composite_to_markdown(text, feature)
            _write_text(path, text)
            result["md_updated"].append(str(path))
        except Exception as exc:
            result.setdefault("md_errors", []).append({"path": str(path), "error": repr(exc)})

    result["status"] = "MERGED"
    result["ip_evidence_composite_score"] = feature.get("ip_evidence_composite_score")
    result["bridge_signal"] = feature.get("bridge_signal")
    result["bridge_adjustment_points"] = feature.get("bridge_adjustment_points")

    return result
