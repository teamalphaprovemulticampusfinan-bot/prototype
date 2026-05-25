from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

try:
    from openpyxl import load_workbook
except Exception:  # pragma: no cover
    load_workbook = None  # type: ignore

from common.data_paths import (
    KNOWN_COMPANY_DIR_TO_NAME,
    company_agent_dir,
    company_slug,
    field_common_dir,
    templates_dir,
    tech_source_dir,
)

NUMBER_RE = re.compile(
    r"(?P<value>[-+]?\d{1,3}(?:,\d{3})*(?:\.\d+)?|[-+]?\d+(?:\.\d+)?)\s*"
    r"(?P<unit>%|회|건|개사|개|곳|명|종|년|개월|원|억원|백만원|천원|배|℃|도|μm|um|㎛|nm|㎚|g/mL|단|라인|세대)?"
)

TECH_KEYWORDS = [
    "반도체", "패키징", "후공정", "HBM", "TC", "본더", "Bonder", "WLP", "FOWLP", "FOPLP",
    "Bumping", "Test", "Precursor", "프리커서", "전구체", "과산화수소", "고순도", "증착", "박막",
    "ALD", "CVD", "OLED", "QD", "이차전지", "배터리", "리드탭", "EMI", "식각", "세정", "박리",
    "CMP", "Glass", "Carrier", "유리기판", "소재", "공정", "양산", "고객", "특허", "청구항",
]

COMPANY_SHEET_BY_SLUG = {
    "nepes": "네패스",
    "hanmi": "한미",
    "hansol": "한솔",
    "duksan": "덕산",
    "ltc": "엘티씨",
}

COMPANY_ALIASES = {
    "네패스": "nepes",
    "한미": "hanmi",
    "한미반도체": "hanmi",
    "한솔": "hansol",
    "한솔케미칼": "hansol",
    "덕산": "duksan",
    "덕산테코피아": "duksan",
    "엘티씨": "ltc",
    "LTC": "ltc",
}

ITEM_COLUMN_CANDIDATES = {
    "company": ["기업명", "company"],
    "category": ["대분류", "category", "분류"],
    "major_source": ["대 출처", "대출처", "major"],
    "middle_source": ["중 출처", "중출처", "middle", "sub"],
    "quantifiable": ["정량화가능한 부분", "정량화", "quant"],
    "item_name": ["항목명", "항목", "item"],
    "content": ["내용", "실제", "content", "description"],
}


def _clean(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _candidate_template_paths(field: str = "반도체") -> list[Path]:
    base = templates_dir(field=field, create=True)
    candidates = [
        base / "tech_template.xlsx",
        base / "tech_template_base.xlsx",
        field_common_dir("templates", field=field, create=True) / "tech_template.xlsx",
        field_common_dir("templates", field=field, create=True) / "tech_template_base.xlsx",
    ]
    out: list[Path] = []
    for p in candidates:
        if p.exists() and p not in out:
            out.append(p)
    # last-resort scan under templates directory
    for p in base.glob("*.xlsx"):
        if p not in out:
            out.append(p)
    return out


def _header_index(headers: list[str], keys: list[str], default: int) -> int:
    for i, h in enumerate(headers):
        low = h.lower()
        if any(k.lower() in low for k in keys):
            return i
    return default


def _detect_header(rows: list[tuple[Any, ...]]) -> tuple[int, list[str]]:
    for idx, row in enumerate(rows[:20]):
        vals = [_clean(x) for x in row]
        joined = " ".join(vals)
        if "대분류" in joined and ("항목명" in joined or "내용" in joined):
            return idx, vals
    return 0, [_clean(x) for x in rows[0]] if rows else []


def _idx_map(headers: list[str]) -> dict[str, int]:
    return {
        name: _header_index(headers, candidates, default)
        for default, (name, candidates) in enumerate(ITEM_COLUMN_CANDIDATES.items())
    }


def _get(vals: list[str], idx: int) -> str:
    return vals[idx] if 0 <= idx < len(vals) else ""


def _extract_numbers(text: str, limit: int = 80) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in NUMBER_RE.finditer(text or ""):
        raw = m.group("value")
        unit = _clean(m.group("unit"))
        start = max(0, m.start() - 45)
        end = min(len(text), m.end() + 55)
        try:
            value = float(raw.replace(",", ""))
        except Exception:
            value = None
        # Ignore isolated years unless the context explicitly looks like a tech claim.
        if unit in {"", "년"} and value is not None and 1900 <= value <= 2100:
            ctx = text[start:end]
            if not any(k in ctx for k in ["대응", "개발", "공정", "특허", "매출", "성장", "가동률", "고객"]):
                continue
        out.append(
            {
                "raw": raw,
                "value": value,
                "unit": unit,
                "context": _clean(text[start:end]),
            }
        )
        if len(out) >= limit:
            break
    return out


def _keyword_counts(text: str) -> dict[str, int]:
    low = (text or "").lower()
    counts: dict[str, int] = {}
    for kw in TECH_KEYWORDS:
        c = low.count(kw.lower())
        if c:
            counts[kw] = c
    return dict(sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:30])


def _first_number_for_quant(row: dict[str, Any], numbers: list[dict[str, Any]]) -> tuple[Any, str, str]:
    """Pick the most meaningful numeric value for a quantified_metrics row."""
    quant = _clean(row.get("quantifiable"))
    content = _clean(row.get("content"))
    if not numbers:
        return len(content), "chars", "엑셀 내용 글자 수"

    # Prefer metrics that are explicitly mentioned in the quantifiable template.
    preferred_units = []
    if "%" in quant:
        preferred_units.append("%")
    if "회" in quant or "빈도" in quant:
        preferred_units.append("회")
    if "개" in quant or "수" in quant:
        preferred_units.extend(["개", "건", "곳", "개사", "종"])
    if "매출" in quant:
        preferred_units.extend(["백만원", "억원", "천원", "원"])

    for unit in preferred_units:
        for n in numbers:
            if n.get("unit") == unit:
                return n.get("value"), unit, n.get("context") or "엑셀 내용 내 직접 수치"

    n = numbers[0]
    return n.get("value"), n.get("unit") or "number", n.get("context") or "엑셀 내용 내 직접 수치"


def _load_sheet_rows(wb_path: Path, sheet_name: str) -> list[dict[str, Any]]:
    if load_workbook is None:
        return []
    wb = load_workbook(wb_path, data_only=True, read_only=True)
    if sheet_name not in wb.sheetnames:
        return []
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    header_i, headers = _detect_header(rows)
    idx = _idx_map(headers)

    current = {
        "company": "",
        "category": "",
        "major_source": "",
        "middle_source": "",
        "quantifiable": "",
    }
    items: list[dict[str, Any]] = []
    for excel_row_number, row in enumerate(rows[header_i + 1 :], start=header_i + 2):
        vals = [_clean(x) for x in row]
        if not any(vals):
            continue
        company = _get(vals, idx["company"]) or current["company"]
        category = _get(vals, idx["category"]) or current["category"]
        major = _get(vals, idx["major_source"]) or current["major_source"]
        middle = _get(vals, idx["middle_source"]) or current["middle_source"]
        quant = _get(vals, idx["quantifiable"]) or current["quantifiable"]
        item_name = _get(vals, idx["item_name"])
        content = _get(vals, idx["content"])
        current.update({
            "company": company,
            "category": category,
            "major_source": major,
            "middle_source": middle,
            "quantifiable": quant,
        })
        if not category and not item_name and not content:
            continue
        numbers = _extract_numbers(content)
        counts = _keyword_counts(content)
        value, unit, value_source = _first_number_for_quant(
            {
                "category": category,
                "quantifiable": quant,
                "item_name": item_name,
                "content": content,
            },
            numbers,
        )
        items.append(
            {
                "excel_row": excel_row_number,
                "sheet": sheet_name,
                "company_name": company,
                "category": category,
                "major_source": major,
                "middle_source": middle,
                "quantifiable": quant,
                "item_name": item_name,
                "content": content,
                "content_present": bool(content),
                "content_char_count": len(content),
                "numeric_signal_count": len(numbers),
                "keyword_signal_count": sum(counts.values()),
                "keyword_counts": counts,
                "numbers": numbers,
                "metric_name": quant or item_name or category,
                "metric_value": value,
                "metric_unit": unit,
                "metric_value_source": value_source,
            }
        )
    return items


def _load_formula_rows(wb_path: Path) -> list[dict[str, str]]:
    if load_workbook is None or not wb_path.exists():
        return []
    try:
        wb = load_workbook(wb_path, data_only=True, read_only=True)
    except Exception:
        return []
    formula_sheets = [s for s in wb.sheetnames if "수식" in s or "formula" in s.lower() or "정량" in s]
    out: list[dict[str, str]] = []
    for sname in formula_sheets:
        ws = wb[sname]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        header_i, headers = _detect_header(rows)
        # Formula sheet often does not have 항목명/내용, so re-detect.
        if header_i == 0 and headers:
            joined = " ".join(headers)
            if not ("계산" in joined or "수식" in joined):
                header_i = 0
        h = [_clean(x) for x in rows[header_i]] if rows else []
        ci = _header_index(h, ["대분류", "category"], 0)
        mi = _header_index(h, ["정량화", "지표", "metric"], 1)
        fi = _header_index(h, ["계산식", "수식", "formula"], 2)
        current_cat = ""
        for excel_row_number, row in enumerate(rows[header_i + 1 :], start=header_i + 2):
            vals = [_clean(x) for x in row]
            if not any(vals):
                continue
            cat = _get(vals, ci) or current_cat
            metric = _get(vals, mi)
            formula = _get(vals, fi)
            current_cat = cat or current_cat
            if not metric and not formula:
                continue
            out.append(
                {
                    "sheet": sname,
                    "excel_row": str(excel_row_number),
                    "category": cat,
                    "metric_name": metric,
                    "formula": formula,
                }
            )
    return out




def _load_base_rows(wb_path: Path) -> list[dict[str, Any]]:
    """Load the common Excel-frame base sheet so company extraction keeps the original schema."""
    if load_workbook is None or not wb_path.exists():
        return []
    try:
        wb = load_workbook(wb_path, data_only=True, read_only=True)
    except Exception:
        return []
    base_sheets = [s for s in wb.sheetnames if s in {"베이스", "base", "Base"} or "base" in s.lower()]
    if not base_sheets:
        base_sheets = [wb.sheetnames[0]] if wb.sheetnames else []
    out: list[dict[str, Any]] = []
    for sname in base_sheets[:2]:
        ws = wb[sname]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        header_i, headers = _detect_header(rows)
        idx = _idx_map(headers)
        current = {"category": "", "major_source": "", "middle_source": "", "quantifiable": ""}
        for excel_row_number, row in enumerate(rows[header_i + 1 :], start=header_i + 2):
            vals = [_clean(x) for x in row]
            if not any(vals):
                continue
            category = _get(vals, idx["category"]) or current["category"]
            major = _get(vals, idx["major_source"]) or current["major_source"]
            middle = _get(vals, idx["middle_source"]) or current["middle_source"]
            quant = _get(vals, idx["quantifiable"]) or current["quantifiable"]
            item_name = _get(vals, idx["item_name"])
            content = _get(vals, idx["content"])
            current.update({"category": category, "major_source": major, "middle_source": middle, "quantifiable": quant})
            if not category and not item_name and not quant and not content:
                continue
            out.append(
                {
                    "sheet": sname,
                    "excel_row": excel_row_number,
                    "category": category,
                    "major_source": major,
                    "middle_source": middle,
                    "quantifiable": quant,
                    "item_name": item_name,
                    "content": content,
                }
            )
    return out


def _company_sheet_candidates(slug: str, company: str | None) -> list[str]:
    names = []
    for x in [COMPANY_SHEET_BY_SLUG.get(slug), company, KNOWN_COMPANY_DIR_TO_NAME.get(slug), slug]:
        x = _clean(x)
        if x and x not in names:
            names.append(x)
    if company and company in COMPANY_ALIASES:
        alias = COMPANY_SHEET_BY_SLUG.get(COMPANY_ALIASES[company])
        if alias and alias not in names:
            names.append(alias)
    return names


def _resolve_company_sheet(wb_path: Path, slug: str, company: str | None) -> str | None:
    if load_workbook is None or not wb_path.exists():
        return None
    try:
        wb = load_workbook(wb_path, read_only=True)
    except Exception:
        return None
    sheet_names = wb.sheetnames
    candidates = _company_sheet_candidates(slug, company)
    for cand in candidates:
        if cand in sheet_names:
            return cand
    for cand in candidates:
        for s in sheet_names:
            if cand and (cand in s or s in cand):
                return s
    return None


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            safe = dict(row)
            for k, v in list(safe.items()):
                if isinstance(v, (dict, list)):
                    safe[k] = json.dumps(v, ensure_ascii=False)
            w.writerow(safe)


def _build_quantified_metrics(slug: str, company: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        rows.append(
            {
                "company_slug": slug,
                "company_name": company,
                "source": "tech_template_company_sheet",
                "sheet": item.get("sheet"),
                "excel_row": item.get("excel_row"),
                "category": item.get("category"),
                "item_name": item.get("item_name"),
                "metric_name": item.get("metric_name"),
                "metric_value": item.get("metric_value"),
                "metric_unit": item.get("metric_unit"),
                "metric_value_source": item.get("metric_value_source"),
                "numeric_signal_count": item.get("numeric_signal_count"),
                "keyword_signal_count": item.get("keyword_signal_count"),
                "content_present": int(bool(item.get("content_present"))),
                "content_char_count": item.get("content_char_count"),
                "quantifiable_plan": item.get("quantifiable"),
                "major_source_plan": item.get("major_source"),
                "middle_source_plan": item.get("middle_source"),
            }
        )
    return rows


def _render_md(company: str, slug: str, payload: dict[str, Any]) -> str:
    lines = [
        f"# {company} Tech Excel-frame Intake",
        "",
        f"- company_slug: {slug}",
        f"- generated_at: {payload.get('generated_at')}",
        f"- template_path: {payload.get('template_path')}",
        f"- company_sheet: {payload.get('company_sheet')}",
        f"- base_item_count: {payload.get('base_item_count')}",
        f"- company_item_count: {payload.get('company_item_count')}",
        f"- content_filled_count: {payload.get('content_filled_count')}",
        f"- numeric_signal_count: {payload.get('numeric_signal_count')}",
        f"- formula_rule_count: {payload.get('formula_rule_count')}",
        "",
        "## 베이스 시트 원본 구조",
    ]
    for base in payload.get("base_items") or []:
        lines.append(
            f"- {base.get('category')} / {base.get('item_name')} / 정량화: {base.get('quantifiable')} / 출처: {base.get('major_source')} > {base.get('middle_source')}"
        )
    lines.append("")
    lines.append("## 엑셀 회사별 시트 전체 추출")
    current_cat = None
    for item in payload.get("company_items") or []:
        cat = item.get("category") or "미분류"
        if cat != current_cat:
            lines += ["", f"### {cat}"]
            current_cat = cat
        lines += [
            "",
            f"#### {item.get('item_name') or '항목명 없음'}",
            f"- 대 출처: {item.get('major_source')}",
            f"- 중 출처: {item.get('middle_source')}",
            f"- 정량화 가능 부분: {item.get('quantifiable')}",
            f"- 수치 신호 수: {item.get('numeric_signal_count')} / 키워드 신호 수: {item.get('keyword_signal_count')}",
            "- 내용:",
        ]
        content = item.get("content") or "내용 없음"
        for line in str(content).splitlines():
            lines.append(f"  {line}")
        nums = item.get("numbers") or []
        if nums:
            lines.append("- 추출 수치:")
            for n in nums[:12]:
                lines.append(f"  - {n.get('raw')}{n.get('unit') or ''}: {n.get('context')}")
    lines += ["", "## 수식 정리 시트"]
    for f in payload.get("formula_rules") or []:
        lines.append(f"- {f.get('category')} / {f.get('metric_name')}: {f.get('formula')}")
    return "\n".join(lines).rstrip() + "\n"


def prepare_excel_frame_artifacts(
    *,
    company_dir: str,
    company: str | None = None,
    field: str = "반도체",
    template_path: str | Path | None = None,
) -> dict[str, Any]:
    """Extract the Excel template/company sheet into company tech artifacts.

    This is intentionally deterministic and does not call any LLM or paid API.  It
    fills the gap where Tech Agent had the template workbook but did not preserve
    all company-specific Excel rows as actual local evidence.
    """

    slug = company_slug(company_dir)
    company_name = _clean(company) or KNOWN_COMPANY_DIR_TO_NAME.get(slug, slug)
    candidates = [Path(template_path)] if template_path else _candidate_template_paths(field)
    candidates = [p for p in candidates if p and p.exists()]
    if not candidates:
        return {
            "status": "NO_TEMPLATE_WORKBOOK",
            "company_slug": slug,
            "company_name": company_name,
            "searched": [str(p) for p in _candidate_template_paths(field)],
        }

    chosen = candidates[0]
    sheet = _resolve_company_sheet(chosen, slug, company_name)
    if not sheet:
        return {
            "status": "NO_COMPANY_SHEET",
            "company_slug": slug,
            "company_name": company_name,
            "template_path": str(chosen),
            "sheet_candidates": _company_sheet_candidates(slug, company_name),
        }

    base_items = _load_base_rows(chosen)
    items = _load_sheet_rows(chosen, sheet)
    formula_rules = _load_formula_rows(chosen)
    metrics = _build_quantified_metrics(slug, company_name, items)
    generated_at = datetime.now().isoformat(timespec="seconds")

    payload = {
        "status": "OK",
        "generated_at": generated_at,
        "company_slug": slug,
        "company_name": company_name,
        "field": field,
        "template_path": str(chosen),
        "company_sheet": sheet,
        "base_item_count": len(base_items),
        "company_item_count": len(items),
        "content_filled_count": sum(1 for x in items if x.get("content_present")),
        "numeric_signal_count": sum(int(x.get("numeric_signal_count") or 0) for x in items),
        "formula_rule_count": len(formula_rules),
        "base_items": base_items,
        "company_items": items,
        "formula_rules": formula_rules,
        "quantified_metrics": metrics,
    }

    tech_dir = company_agent_dir(slug, "tech", create=True)
    source_dir = tech_source_dir(slug, create=True)

    json_path = tech_dir / "tech_excel_frame_full.json"
    item_csv = tech_dir / "tech_excel_frame_items.csv"
    metric_csv = tech_dir / "tech_excel_frame_metrics.csv"
    quantified_csv = tech_dir / "quantified_metrics.csv"
    quantified_typo_csv = tech_dir / "quanified_metrix.csv"
    md_path = tech_dir / "tech_excel_frame_summary.md"
    source_md = source_dir / f"{slug}_tech_excel_frame_evidence.md"
    source_json = source_dir / f"{slug}_tech_excel_frame_evidence.json"

    json_text = json.dumps(payload, ensure_ascii=False, indent=2)
    json_path.write_text(json_text, encoding="utf-8")
    source_json.write_text(json_text, encoding="utf-8")

    item_fields = [
        "company_name", "sheet", "excel_row", "category", "major_source", "middle_source", "quantifiable",
        "item_name", "content", "content_present", "content_char_count", "numeric_signal_count", "keyword_signal_count",
        "metric_name", "metric_value", "metric_unit", "metric_value_source", "keyword_counts", "numbers",
    ]
    _write_csv(item_csv, items, item_fields)

    metric_fields = [
        "company_slug", "company_name", "source", "sheet", "excel_row", "category", "item_name",
        "metric_name", "metric_value", "metric_unit", "metric_value_source", "numeric_signal_count",
        "keyword_signal_count", "content_present", "content_char_count", "quantifiable_plan",
        "major_source_plan", "middle_source_plan",
    ]
    _write_csv(metric_csv, metrics, metric_fields)
    _write_csv(quantified_csv, metrics, metric_fields)
    # Compatibility for the common typo in earlier notes/logs.
    _write_csv(quantified_typo_csv, metrics, metric_fields)

    md = _render_md(company_name, slug, payload)
    md_path.write_text(md, encoding="utf-8")
    source_md.write_text(md, encoding="utf-8")

    payload["output_paths"] = {
        "json": str(json_path),
        "items_csv": str(item_csv),
        "metrics_csv": str(metric_csv),
        "quantified_metrics_csv": str(quantified_csv),
        "quanified_metrix_csv": str(quantified_typo_csv),
        "md": str(md_path),
        "source_md": str(source_md),
        "source_json": str(source_json),
    }
    # Re-write with output paths included.
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    source_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def build_sector_quantified_metrics(*, field: str = "반도체", companies: Iterable[str] | None = None) -> dict[str, Any]:
    """Merge per-company quantified_metrics.csv files into a sector-level table."""
    import pandas as pd

    slugs = list(companies or KNOWN_COMPANY_DIR_TO_NAME.keys())
    frames = []
    paths = []
    for slug in slugs:
        p = company_agent_dir(slug, "tech", create=True) / "quantified_metrics.csv"
        if p.exists():
            try:
                frames.append(pd.read_csv(p, encoding="utf-8-sig"))
                paths.append(str(p))
            except Exception:
                pass
    out_dir = field_common_dir("tech", field=field, create=True)
    out_csv = out_dir / "tech_intake_quantified_metrics_5companies.csv"
    out_json = out_dir / "tech_intake_quantified_metrics_5companies_manifest.json"
    if frames:
        df = pd.concat(frames, ignore_index=True)
        df.to_csv(out_csv, index=False, encoding="utf-8-sig")
        status = "OK"
        row_count = int(len(df))
    else:
        out_csv.write_text("company_slug,company_name,metric_name,metric_value\n", encoding="utf-8-sig")
        status = "NO_COMPANY_METRICS"
        row_count = 0
    manifest = {
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "field": field,
        "companies": slugs,
        "source_paths": paths,
        "output_csv": str(out_csv),
        "row_count": row_count,
    }
    out_json.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
