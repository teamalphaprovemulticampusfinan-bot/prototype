from __future__ import annotations

from pathlib import Path

from .utils import clean_text
from .workbook_schema import CANONICAL_SECTION_ORDER, SECTION_FIELD_GUIDE


def _find_section(categories: list[dict], section_name: str) -> dict:
    for row in categories or []:
        if clean_text(row.get("category", "")) == section_name:
            return row
    return {
        "category": section_name,
        "result": "공개 자료 기준 직접 확인이 제한되어 보수적으로 정리함.",
        "items": [],
    }


def _render_items(section_name: str, section: dict) -> list[str]:
    lines = []

    lines.append(f"추출 항목: ① {SECTION_FIELD_GUIDE[section_name][0]} ② {SECTION_FIELD_GUIDE[section_name][1]} ③ {SECTION_FIELD_GUIDE[section_name][2]}")
    lines.append(f"결과: {clean_text(section.get('result', '공개 자료 기준 직접 확인이 제한되어 보수적으로 정리함.'))}")
    lines.append("")

    items = section.get("items", []) or []
    if not items:
        for label in SECTION_FIELD_GUIDE[section_name]:
            lines.append(f"- {label}: 공개 자료 기준 직접 확인 제한")
            lines.append("  - 근거: 관련 근거 문구를 직접 확인하지 못해 보수적으로 정리함.")
        return lines

    used_names = set()
    for item in items[:6]:
        name = clean_text(item.get("name", ""))
        value = clean_text(item.get("value", ""))
        evidence = item.get("evidence", []) or []

        if not name:
            continue
        if name in used_names:
            continue
        used_names.add(name)

        lines.append(f"- {name}: {value or '공개 자료 기준 직접 확인 제한'}")
        if evidence:
            for ev in evidence[:2]:
                lines.append(f"  - 근거: {clean_text(ev)}")
        else:
            lines.append("  - 근거: 공개 자료 기준 직접 확인 제한")

    # template에 있는 필드가 빠졌으면 placeholder 보충
    for label in SECTION_FIELD_GUIDE[section_name]:
        if label not in used_names:
            lines.append(f"- {label}: 공개 자료 기준 직접 확인 제한")
            lines.append("  - 근거: 관련 근거 문구를 직접 확인하지 못해 보수적으로 정리함.")

    return lines


def write_markdown_report(
    company: dict,
    categories: list[dict],
    score_payload: dict,
    output_path,
    radar_image_name: str | None = None,
):
    output_path = Path(output_path)

    company_name = clean_text(company.get("corp_name", "기업"))
    total_score = score_payload.get("total_score", 0)
    max_score = score_payload.get("max_score", 35)
    strengths = score_payload.get("strengths", []) or []
    weaknesses = score_payload.get("weaknesses", []) or []
    judgment = clean_text(score_payload.get("judgment", "보수 검토형"))

    lines = []
    lines.append(f"### [기업명: {company_name}] 기술 분석 보고서")
    lines.append("")
    lines.append(f"- 총점: {total_score}/{max_score}")
    lines.append(f"- 강점: {', '.join(strengths) if strengths else '상대적 강점 축 제한적'}")
    lines.append(f"- 약점: {', '.join(weaknesses) if weaknesses else '상대적 약점 축 제한적'}")
    lines.append(
        f"- 종합 판단: 기술 경쟁력 종합 점수는 {total_score}/{max_score}점이며, "
        f"강점 축은 {', '.join(strengths) if strengths else '상대적 강점 축 제한적'}, "
        f"보완 축은 {', '.join(weaknesses) if weaknesses else '상대적 약점 축 제한적'}이다. "
        f"종합적으로 이 기업은 {judgment}으로 판단된다."
    )
    lines.append("")

    if radar_image_name:
        lines.append(f"![radar]({radar_image_name})")
        lines.append("")

    for idx, section_name in enumerate(CANONICAL_SECTION_ORDER, start=1):
        section = _find_section(categories, section_name)
        lines.append(f"## {idx}. {section_name}")
        lines.extend(_render_items(section_name, section))
        lines.append("")

    lines.append("## 기술 경쟁력 종합 판단")
    axis_rows = score_payload.get("axes", []) or []
    for row in axis_rows:
        axis = clean_text(row.get("axis", ""))
        score = row.get("score", 0)
        reason = clean_text(row.get("reason", ""))
        lines.append(f"- {axis}: {score}/5 ({reason})")

    lines.append("")
    lines.append(
        f"결과: 기술 경쟁력 종합 점수는 {total_score}/{max_score}점이며, "
        f"강점 축은 {', '.join(strengths) if strengths else '상대적 강점 축 제한적'}, "
        f"보완 축은 {', '.join(weaknesses) if weaknesses else '상대적 약점 축 제한적'}이다. "
        f"종합적으로 이 기업은 {judgment}으로 판단된다."
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def write_report_markdown(
    output_path=None,
    company: dict | None = None,
    categories: list[dict] | None = None,
    score_payload: dict | None = None,
    radar_image_name: str | None = None,
    **kwargs,
):
    if output_path is None:
        output_path = kwargs.get("out_path")
    if score_payload is None:
        score_payload = kwargs.get("score_result")
    if radar_image_name is None:
        radar_image_name = kwargs.get("radar_img")

    return write_markdown_report(
        company=company or {},
        categories=categories or [],
        score_payload=score_payload or {},
        output_path=output_path,
        radar_image_name=radar_image_name,
    )