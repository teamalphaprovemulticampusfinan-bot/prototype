from __future__ import annotations

from .normalizer import CANONICAL_ITEM_MAP
from .utils import clean_text


def validate_section_payload(section: dict) -> dict:
    category = clean_text(section.get("category", ""))
    item_map = section.get("item_map", {}) or {}
    canonical_items = CANONICAL_ITEM_MAP.get(category, [])

    issues: list[str] = []

    if not category:
        issues.append("category_missing")

    if canonical_items:
        for item in canonical_items:
            row = item_map.get(item)
            if not row:
                issues.append(f"missing_item:{item}")
                continue
            value = clean_text(row.get("value", ""))
            if not value:
                issues.append(f"empty_item:{item}")

    result_text = clean_text(section.get("result_text", ""))
    if not result_text:
        issues.append("result_text_missing")

    evidence_pool = section.get("evidence_pool", []) or []
    if not evidence_pool:
        issues.append("evidence_missing")

    section["validation_issues"] = issues
    section["validation_ok"] = len(issues) == 0
    return section


def validate_full_report(report: dict) -> dict:
    sections = report.get("sections", []) or []
    validated = []
    issue_count = 0

    for section in sections:
        checked = validate_section_payload(section)
        validated.append(checked)
        issue_count += len(checked.get("validation_issues", []))

    report["sections"] = validated
    report["validation_issue_count"] = issue_count
    report["validation_ok"] = issue_count == 0
    return report