from __future__ import annotations

"""Extract Excel-template technology evidence into per-company quantified metrics.

This version treats the template workbook as a schema/evidence map, not as a
literal final answer.  The most important fix is the visible workbook layout:

A 기업명 / B 대분류 / C 대 출처 / D 중 출처 / E 정량화가능한 부분 / F 항목명 / G 내용

Older logic mapped C("대 출처") to evidence_text, so the output was too broad
and missed row-level 항목명/내용.  This script now keeps source columns as source
hints and uses F/G as the actual item/evidence body.
"""

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common.data_paths import (
    KNOWN_COMPANY_DIRS,
    company_agent_dir,
    company_name,
    company_slug,
    templates_dir,
)

try:
    import openpyxl  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit("openpyxl이 필요합니다. pip install openpyxl 후 다시 실행하세요.") from exc


CANONICAL_COLUMNS = [
    "company_dir",
    "company_name",
    "source_workbook",
    "source_sheet",
    "source_row",
    "major_category",
    "source_big",
    "source_middle",
    "metric_name",
    "item_name",
    "middle_category",
    "evidence_text",
    "quantitative_values",
    "extracted_numbers_json",
    "evidence_score",
    "importance_grade",
    "investor_relevance",
    "data_origin",
    "created_at",
]

COMPANY_ALIASES = {
    "nepes": {"네패스", "nepes", "NEPES", "033640"},
    "hanmi": {"한미반도체", "hanmi", "Hanmi", "Hanmi Semiconductor", "HANMI", "042700"},
    "hansol": {"한솔케미칼", "한솔", "hansol", "Hansol", "Hansol Chemical", "HANSOL", "014680"},
    "duksan": {"덕산테코피아", "덕산", "duksan", "Duksan", "DS Techopia", "DUKSAN TECHOPIA", "317330"},
    "ltc": {"엘티씨", "LTC", "ltc", "170920"},
    "dbhitek": {"DB하이텍", "디비하이텍", "dbhitek", "DB HiTek", "000990"},
    "mico": {"미코", "mico", "MiCo", "059090"},
    "lxsemicon": {"LX세미콘", "엘엑스세미콘", "lxsemicon", "LX Semicon", "108320"},
    "jeju_semicon": {"제주반도체", "jeju_semicon", "jeju semicon", "Jeju Semiconductor", "080220"},
    "abov": {"어보브반도체", "abov", "ABOV", "ABOV Semiconductor", "102120"},
    "telechips": {"텔레칩스", "telechips", "Telechips", "054450"},
    "coasia": {"코아시아", "coasia", "CoAsia", "045970"},
    "gaochips": {"가온칩스", "gaochips", "gaonchips", "Gaonchips", "399720"},
    "wonik_ips": {"원익IPS", "원익아이피에스", "wonik_ips", "wonik ips", "Wonik IPS", "240810"},
    "eugene_tech": {"유진테크", "eugene_tech", "eugene tech", "Eugene Technology", "084370"},
    "psk": {"피에스케이", "psk", "PSK", "319660"},
    "tes": {"테스", "tes", "TES", "095610"},
    "gst": {"GST", "지에스티", "gst", "Global Standard Technology", "083450"},
    "sti": {"에스티아이", "sti", "STI", "039440"},
    "nextin": {"넥스틴", "nextin", "NEXTIN", "348210"},
    "soulbrain": {"솔브레인", "soulbrain", "Soulbrain", "357780"},
    "dongjin_semichem": {"동진쎄미켐", "dongjin_semichem", "dongjin semichem", "Dongjin Semichem", "005290"},
    "wonik_materials": {"원익머트리얼즈", "wonik_materials", "wonik materials", "Wonik Materials", "104830"},
    "enf_tech": {"이엔에프테크놀로지", "ENF테크놀로지", "enf", "enf_tech", "ENF Technology", "102710"},
    "tck": {"티씨케이", "TCK", "tck", "064760"},
    "woldex": {"월덱스", "woldex", "WONDEX", "Woldex", "101160"},
    "isc": {"ISC", "아이에스시", "isc", "095340"},
    "sfa_semicon": {"SFA반도체", "SFA 반도체", "에스에프에이반도체", "sfa", "sfa_semicon", "SFA Semicon", "036540"},
    "doosan_tesna": {"두산테스나", "doosan_tesna", "doosan tesna", "Doosan Tesna", "131970"},
    "leeno": {"리노공업", "leeno", "Leeno", "Leeno Industrial", "058470"},
}

HEADER_ALIASES = {
    "company": {"기업", "기업명", "회사", "회사명", "company", "corp", "name"},
    "major_category": {"대분류", "major", "category", "tech_category", "구분"},
    "source_big": {"대출처", "대 출처", "상위출처", "source_big", "primary_source"},
    "source_middle": {"중출처", "중 출처", "중간출처", "source_middle", "secondary_source"},
    "metric_name": {"정량화가능한부분", "정량화 가능한 부분", "정량화가능한 부분", "정량화", "지표", "metric", "quantified_metric"},
    "item_name": {"항목명", "항목", "세부항목", "item", "item_name", "middle", "sub_category"},
    "evidence_text": {"내용", "근거", "설명", "evidence", "source_text", "description", "text"},
    "importance_grade": {"중요도", "강도", "등급", "grade", "importance"},
}

KEYWORD_SCORE_BOOSTS = {
    "양산": 8,
    "상용": 8,
    "고객": 7,
    "공급": 6,
    "매출": 7,
    "패키징": 5,
    "HBM": 6,
    "AI": 4,
    "반도체": 4,
    "특허": 5,
    "등록": 4,
    "청구항": 4,
    "수율": 5,
    "원가": 4,
    "공정": 4,
    "FCF": 5,
    "현금흐름": 5,
}


def _norm(value: Any) -> str:
    return re.sub(r"[\s_\-./()\[\]{}:：]+", "", str(value or "").strip().lower())


def _canonical_company_slug(value: Any) -> str:
    slug = company_slug(value)
    if slug in KNOWN_COMPANY_DIRS:
        return slug

    value_norm = _norm(value)
    for canonical, aliases in COMPANY_ALIASES.items():
        alias_norms = {_norm(canonical), *{_norm(alias) for alias in aliases}}
        if value_norm in alias_norms:
            return canonical
    return slug


def _clean(value: Any, limit: int = 700) -> str:
    text = re.sub(r"\s+", " ", str(value or "").replace("\u3000", " ")).strip()
    if text.lower() in {"nan", "none", "null"}:
        text = ""
    return text[:limit] + ("..." if len(text) > limit else "")


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return not text or text.lower() in {"nan", "none", "null"}


def _extract_numbers(text: str) -> list[dict[str, Any]]:
    numbers: list[dict[str, Any]] = []
    pattern = r"(?P<num>-?\d+(?:,\d{3})*(?:\.\d+)?)(?P<unit>\s*(?:%|건|개|명|원|억원|조원|배|년|개월|회|nm|㎚|mm|㎜|μm|um|℃|달러|USD|KRW)?)"
    for m in re.finditer(pattern, text):
        raw = m.group("num")
        unit = (m.group("unit") or "").strip()
        try:
            value = float(raw.replace(",", ""))
        except Exception:
            continue
        numbers.append({"raw": raw + (unit or ""), "value": value, "unit": unit})
    return numbers


def _find_header(row_values: list[Any]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    normalized = [_norm(v) for v in row_values]
    for canonical, aliases in HEADER_ALIASES.items():
        alias_norms = {_norm(a) for a in aliases}
        for idx, cell in enumerate(normalized):
            if cell and cell in alias_norms:
                mapping[canonical] = idx
                break

    # Explicitly recognize the known template layout.  This prevents C/D source
    # columns from being mistaken for the final evidence body.
    if all(k in mapping for k in ["company", "major_category", "source_big", "source_middle", "metric_name", "item_name", "evidence_text"]):
        return mapping

    if len(row_values) >= 7:
        first_seven = [_norm(v) for v in row_values[:7]]
        known_layout = ["기업명", "대분류", "대출처", "중출처", "정량화가능한부분", "항목명", "내용"]
        if all(known_layout[i] in first_seven[i] or first_seven[i] in known_layout[i] for i in range(7)):
            return {
                "company": 0,
                "major_category": 1,
                "source_big": 2,
                "source_middle": 3,
                "metric_name": 4,
                "item_name": 5,
                "evidence_text": 6,
            }
    return mapping


def _iter_sheet_rows(ws: Any) -> list[tuple[int, dict[str, Any]]]:
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    best_header_idx = 0
    best_mapping: dict[str, int] = {}
    for idx, values in enumerate(rows[:25]):
        mapping = _find_header(list(values or []))
        if len(mapping) > len(best_mapping):
            best_header_idx = idx
            best_mapping = mapping

    if len(best_mapping) < 2:
        best_mapping = {
            "company": 0,
            "major_category": 1,
            "source_big": 2,
            "source_middle": 3,
            "metric_name": 4,
            "item_name": 5,
            "evidence_text": 6,
        }
        best_header_idx = 0

    parsed: list[tuple[int, dict[str, Any]]] = []
    fill_down_keys = {"company", "major_category", "source_big", "source_middle", "metric_name"}
    last_values: dict[str, Any] = {}
    for excel_row_idx, values in enumerate(rows[best_header_idx + 1 :], start=best_header_idx + 2):
        if values is None:
            continue
        row: dict[str, Any] = {}
        for key, col_idx in best_mapping.items():
            value = values[col_idx] if col_idx < len(values) else None
            if _is_empty(value) and key in fill_down_keys:
                value = last_values.get(key)
            if not _is_empty(value) and key in fill_down_keys:
                last_values[key] = value
            row[key] = value
        text_pool = " ".join(str(v or "") for v in row.values())
        if len(text_pool.strip()) < 3:
            continue
        parsed.append((excel_row_idx, row))
    return parsed


def _matches_company(row: dict[str, Any], slug: str, sheet_title: str) -> bool:
    aliases = {company_name(slug), slug, *COMPANY_ALIASES.get(slug, set())}
    target_norms = {_norm(x) for x in aliases if x}
    sheet_norm = _norm(sheet_title)
    company_cell = _norm(row.get("company"))
    text_pool = _norm(" ".join(str(v or "") for v in row.values()))

    if sheet_norm in target_norms or any(t in sheet_norm for t in target_norms if len(t) >= 3):
        return True
    if company_cell and (company_cell in target_norms or any(t in company_cell for t in target_norms if len(t) >= 3)):
        return True
    return bool(company_cell and any(t in text_pool for t in target_norms if len(t) >= 3))


def _evidence_score(text: str, numbers: list[dict[str, Any]], grade: str) -> tuple[float, str]:
    score = 52.0
    if numbers:
        score += min(20.0, 4.0 * len(numbers))
    grade_clean = str(grade or "").strip()
    if grade_clean in {"강", "상", "high", "High"}:
        score += 12
    elif grade_clean in {"중", "medium", "Medium"}:
        score += 6
    elif grade_clean in {"약", "하", "보강", "low", "Low"}:
        score -= 4
    for kw, boost in KEYWORD_SCORE_BOOSTS.items():
        if kw.lower() in text.lower():
            score += boost
    score = max(35.0, min(95.0, score))
    if score >= 75:
        imp = "강"
    elif score >= 60:
        imp = "중"
    else:
        imp = "보강"
    return round(score, 2), imp


def _record_from_row(slug: str, workbook: Path, sheet: str, row_idx: int, row: dict[str, Any]) -> dict[str, Any] | None:
    major = _clean(row.get("major_category") or "Excel-frame", 120)
    source_big = _clean(row.get("source_big"), 350)
    source_middle = _clean(row.get("source_middle"), 350)
    metric = _clean(row.get("metric_name"), 260)
    item = _clean(row.get("item_name") or row.get("middle_category") or metric, 220)
    evidence = _clean(row.get("evidence_text"), 900)

    # The base/template sheet often contains source guidance but not company-level evidence.
    # Keep only rows that have an actual item or evidence body.
    if not any([item, evidence, metric]):
        return None
    if not evidence and sheet in {"베이스", "base", "Base"}:
        return None

    evidence_hint = " / ".join(x for x in [source_big, source_middle] if x)
    text_pool = f"{major} {item} {metric} {evidence} {evidence_hint}"
    numbers = _extract_numbers(text_pool)
    score, inferred_grade = _evidence_score(text_pool, numbers, str(row.get("importance_grade") or ""))
    quantitative_values = ", ".join(n["raw"] for n in numbers[:10]) if numbers else "정성 근거 중심"
    return {
        "company_dir": slug,
        "company_name": company_name(slug),
        "source_workbook": str(workbook).replace("\\", "/"),
        "source_sheet": sheet,
        "source_row": row_idx,
        "major_category": major,
        "source_big": source_big,
        "source_middle": source_middle,
        "metric_name": metric,
        "item_name": item,
        "middle_category": item,
        "evidence_text": evidence or evidence_hint,
        "quantitative_values": quantitative_values,
        "extracted_numbers_json": json.dumps(numbers, ensure_ascii=False),
        "evidence_score": score,
        "importance_grade": str(row.get("importance_grade") or inferred_grade).strip() or inferred_grade,
        "investor_relevance": "Excel-frame 항목명·정량화 가능 지표·근거 본문을 연결한 개인투자자 설명 가능 Tech 근거",
        "data_origin": "sector_template_excel_row_level",
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


def _find_template_workbooks(template_dir: Path | None = None) -> list[Path]:
    dirs: list[Path] = []
    if template_dir is not None:
        dirs.append(template_dir)
    try:
        dirs.append(templates_dir(create=True))
    except Exception:
        pass
    dirs.extend(ROOT_DIR.glob("data/**/templates"))

    workbooks: list[Path] = []
    seen: set[Path] = set()
    for d in dirs:
        if not d.exists() or not d.is_dir():
            continue
        for p in d.glob("*.xlsx"):
            if p.name.startswith("~$"):
                continue
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            workbooks.append(p)
    return sorted(workbooks, key=lambda x: str(x))


def extract_company_rows(slug: str, template_dir: Path | None = None) -> list[dict[str, Any]]:
    slug = _canonical_company_slug(slug)
    tdir = template_dir or templates_dir(create=True)
    workbooks = _find_template_workbooks(tdir)
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for workbook in workbooks:
        try:
            wb = openpyxl.load_workbook(workbook, read_only=True, data_only=True)
        except Exception as exc:
            print(f"[Tech Excel Metrics] workbook skip: {workbook} / {exc}")
            continue
        for ws in wb.worksheets:
            for row_idx, row in _iter_sheet_rows(ws):
                if not _matches_company(row, slug, ws.title):
                    continue
                rec = _record_from_row(slug, workbook, ws.title, row_idx, row)
                if not rec:
                    continue
                key = (
                    rec["major_category"],
                    rec["item_name"],
                    rec["metric_name"],
                    rec["evidence_text"][:120],
                )
                if key in seen:
                    continue
                seen.add(key)
                records.append(rec)
    return records


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in CANONICAL_COLUMNS})


def _write_outputs(slug: str, rows: list[dict[str, Any]]) -> dict[str, str]:
    out_dir = company_agent_dir(slug, "tech", create=True)
    csv_path = out_dir / "tech_excel_quantified_metrics.csv"
    common_csv = out_dir / "quantified_metrics.csv"
    json_path = out_dir / "tech_excel_quantified_metrics.json"
    md_path = out_dir / f"{slug}_tech_excel_quantified_metrics.md"

    _write_csv(csv_path, rows)
    _write_csv(common_csv, rows)
    payload = {
        "company_dir": slug,
        "company_name": company_name(slug),
        "row_count": len(rows),
        "numeric_row_count": sum(1 for r in rows if r.get("quantitative_values") and r.get("quantitative_values") != "정성 근거 중심"),
        "rows": rows,
        "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "layout_rule": "A 기업명 / B 대분류 / C 대 출처 / D 중 출처 / E 정량화가능한 부분 / F 항목명 / G 내용",
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {company_name(slug)} Excel-frame 정량 근거 추출",
        "",
        f"- row_count: {payload['row_count']}",
        f"- numeric_row_count: {payload['numeric_row_count']}",
        "- parsing: 항목명(F열)과 내용(G열)을 실제 근거로 사용하고, 대/중 출처(C/D열)는 source hint로 보존",
        "",
        "| 대분류 | 항목명 | 정량화 가능 지표 | 값/숫자 | 근거 본문 | 출처 힌트 | 점수 |",
        "|---|---|---|---:|---|---|---:|",
    ]
    for row in rows[:60]:
        source_hint = " / ".join(x for x in [row.get("source_big", ""), row.get("source_middle", "")] if x)
        lines.append(
            f"| {row.get('major_category','')} | {row.get('item_name','')} | {row.get('metric_name','')} | {row.get('quantitative_values','')} | {row.get('evidence_text','')} | {source_hint} | {row.get('evidence_score','')} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"csv": str(csv_path), "common_csv": str(common_csv), "json": str(json_path), "md": str(md_path)}


def run(company_dirs: list[str] | None = None, field: str = "반도체") -> dict[str, Any]:
    targets = [_canonical_company_slug(x) for x in (company_dirs or KNOWN_COMPANY_DIRS)]
    results: dict[str, Any] = {}
    tdir = templates_dir(field=field, create=True)
    for slug in targets:
        rows = extract_company_rows(slug, tdir)
        files = _write_outputs(slug, rows)
        results[slug] = {"company_name": company_name(slug), "row_count": len(rows), "files": files}
        print(f"[Tech Excel Metrics] {company_name(slug)} / {slug}: {len(rows)} rows")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Tech Excel-frame quantified metrics for one or more companies.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-dir", action="append", default=[])
    parser.add_argument("--all", action="store_true", help="Build all known semiconductor companies.")
    args = parser.parse_args(argv)
    targets = KNOWN_COMPANY_DIRS if args.all or not args.company_dir else args.company_dir
    result = run(list(targets), field=args.field)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
