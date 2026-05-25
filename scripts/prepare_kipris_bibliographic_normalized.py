from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from common.data_paths import company_agent_dir, normalize_field_name
except Exception:  # pragma: no cover
    company_agent_dir = None  # type: ignore
    normalize_field_name = lambda value=None, default="반도체": str(value or default).strip() or default  # type: ignore


PATENT_SOURCE_EXTS = {".csv", ".tsv", ".xlsx", ".xlsm"}
PATENT_NAME_HINTS = [
    "kipris",
    "patent",
    "patents",
    "특허",
    "산업재산권",
    "bibliographic",
    "biblio",
]
GENERATED_SKIP_HINTS = [
    "claims_normalized",
    "citations_normalized",
    "family_normalized",
    "plus_claim",
    "plus_family",
    "plus_citation",
    "tech_ip_",
    "evidence_composite",
    "tech_ml_enriched",
    "excel_quantified",
    "template",
    "inventory",
    "summary",
    "similarity",
    "top_pairs",
    "peer",
]
NEGATIVE_STATUS_HINTS = ["거절", "취하", "소멸", "포기", "무효", "말소", "소멸예정"]
REGISTERED_HINTS = ["등록", "registered", "grant", "granted"]

COLUMN_ALIASES: dict[str, list[str]] = {
    "application_number": [
        "application_number",
        "applicationNumber",
        "application_no",
        "applicationNo",
        "app_no",
        "appNo",
        "appl_no",
        "출원번호",
        "출원 번호",
        "출원번호정보",
    ],
    "open_number": [
        "open_number",
        "openNumber",
        "publication_number",
        "publicationNumber",
        "publication_no",
        "공개번호",
        "공개 번호",
    ],
    "register_number": [
        "register_number",
        "registerNumber",
        "registration_number",
        "registrationNumber",
        "registration_no",
        "reg_no",
        "등록번호",
        "등록 번호",
    ],
    "register_status": [
        "register_status",
        "registerStatus",
        "registration_status",
        "registrationStatus",
        "등록상태",
        "등록 상태",
        "상태",
        "법적상태",
        "legal_status",
        "legalStatus",
        "status",
    ],
    "final_disposal": [
        "final_disposal",
        "finalDisposal",
        "final_status",
        "finalStatus",
        "disposal",
        "처분상태",
        "최종처분",
        "최종상태",
        "권리상태",
    ],
    "invention_title": [
        "invention_title",
        "inventionTitle",
        "title",
        "patent_title",
        "발명의명칭",
        "발명의 명칭",
        "명칭",
        "제목",
    ],
    "right_holder": [
        "right_holder",
        "rightHolder",
        "applicant_name",
        "applicantName",
        "applicant",
        "assignee",
        "owner",
        "출원인",
        "출원인명",
        "권리자",
        "권리자명",
    ],
    "inventor": ["inventor", "inventorName", "inventor_name", "발명자", "발명자명"],
    "application_date": [
        "application_date",
        "applicationDate",
        "filing_date",
        "filingDate",
        "출원일",
        "출원일자",
    ],
    "open_date": [
        "open_date",
        "openDate",
        "publication_date",
        "publicationDate",
        "공개일",
        "공개일자",
    ],
    "register_date": [
        "register_date",
        "registerDate",
        "registration_date",
        "registrationDate",
        "등록일",
        "등록일자",
    ],
    "ipc_number": [
        "ipc_number",
        "ipcNumber",
        "ipc",
        "IPC",
        "ipc_code",
        "IPC분류",
        "국제특허분류",
        "분류코드",
    ],
    "cpc_number": ["cpc_number", "cpcNumber", "cpc", "CPC", "CPC분류", "cpc_code"],
    "abstract": ["abstract", "astrtCont", "summary", "초록", "요약", "기술요약"],
    "claim_text": ["claim_text", "claims", "claim", "청구항", "청구범위", "대표청구항"],
    "url": ["url", "link", "detail_url", "kipris_url", "링크", "상세URL"],
    "drawing": ["drawing", "bigDrawing", "대표도", "도면"],
}

OUTPUT_COLUMNS = [
    "application_number",
    "application_no",
    "open_number",
    "publication_no",
    "register_number",
    "registration_no",
    "register_status",
    "final_disposal",
    "legal_status",
    "invention_title",
    "title",
    "right_holder",
    "applicant",
    "inventor",
    "application_date",
    "application_year",
    "open_date",
    "publication_date",
    "register_date",
    "registration_date",
    "ipc_number",
    "ipc",
    "cpc_number",
    "cpc",
    "abstract",
    "claim_text",
    "claims",
    "url",
    "drawing",
    "is_registered",
    "is_alive_estimated",
    "has_negative_disposal_estimated",
    "tech_keyword_match_count",
    "source_file",
    "source_sheet",
    "source_row",
]

TECH_KEYWORDS = [
    "반도체",
    "패키지",
    "패키징",
    "웨이퍼",
    "wafer",
    "wlp",
    "fowlp",
    "fo-wlp",
    "fan-out",
    "fanout",
    "범프",
    "bump",
    "테스트",
    "test",
    "소자",
    "chip",
    "칩",
    "기판",
    "substrate",
    "interposer",
    "인터포저",
    "probe",
    "프로브",
    "전구체",
    "precursor",
    "ald",
    "cvd",
    "소재",
]


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ").strip()
    if text.lower() in {"nan", "none", "null", "nat"}:
        return ""
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return re.sub(r"\s+", " ", text).strip()


def _norm_key(value: Any) -> str:
    text = _clean_text(value).lower()
    return re.sub(r"[\s_\-./()\[\]{}:：]+", "", text)


def _digits(value: Any) -> str:
    return re.sub(r"\D+", "", _clean_text(value))


def _normalize_application_number(value: Any) -> str:
    d = _digits(value)
    if not d:
        return ""
    if d.startswith("10") and len(d) >= 11:
        return d
    if len(d) >= 10 and d[:4].isdigit():
        try:
            year = int(d[:4])
        except Exception:
            year = 0
        if 1990 <= year <= datetime.now().year + 1:
            return "10" + d
    return d


def _year(value: Any) -> int | None:
    text = _clean_text(value)
    match = re.search(r"(19\d{2}|20\d{2})", text)
    if not match:
        return None
    year = int(match.group(1))
    if 1980 <= year <= datetime.now().year + 1:
        return year
    return None


def _find_col(df: pd.DataFrame, aliases: list[str]) -> str:
    norm_map = {_norm_key(col): str(col) for col in df.columns}
    for alias in aliases:
        key = _norm_key(alias)
        if key in norm_map:
            return norm_map[key]
    for alias in aliases:
        key = _norm_key(alias)
        if not key:
            continue
        for nk, col in norm_map.items():
            if key in nk or nk in key:
                return col
    return ""


def _read_csv_like(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            sep = "\t" if path.suffix.lower() == ".tsv" else None
            return pd.read_csv(path, encoding=enc, dtype=str, sep=sep, engine="python").fillna("")
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"CSV/TSV 읽기 실패: {path} / {last_error}")


def _read_excel_like(path: Path) -> pd.DataFrame:
    sheets = pd.read_excel(path, sheet_name=None, dtype=str).items()
    frames: list[pd.DataFrame] = []
    for sheet_name, df in sheets:
        df = df.fillna("")
        if df.empty:
            continue
        df["__source_sheet"] = str(sheet_name)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False).fillna("")


def _read_source_file(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        return _read_excel_like(path)
    return _read_csv_like(path)


def _looks_like_patent_input(path: Path) -> bool:
    name = path.name.lower()
    if path.suffix.lower() not in PATENT_SOURCE_EXTS:
        return False
    if path.name.startswith("~$"):
        return False
    if any(skip in name for skip in GENERATED_SKIP_HINTS):
        return False
    return any(hint.lower() in name for hint in PATENT_NAME_HINTS)


def _score_source_file(path: Path, slug: str) -> tuple[int, str]:
    name = path.name.lower()
    score = 0
    if path.parent.name.lower() == "source":
        score += 40
    if "kipris" in name:
        score += 30
    if slug.lower() in name:
        score += 25
    if "bibliographic" in name or "biblio" in name:
        score += 20
    if "patents_normalized" in name or "patent_normalized" in name:
        score += 15
    if "claims" in name or "family" in name or "citation" in name:
        score -= 80
    if path.suffix.lower() in {".csv", ".tsv"}:
        score += 5
    return score, str(path)


def _tech_dir(field: str, company_name: str, company_slug: str) -> Path:
    if company_agent_dir is not None:
        try:
            return Path(company_agent_dir(company_slug, "tech", create=True))
        except Exception:
            pass
    return ROOT / "data" / field / company_name / "tech"


def _find_input_files(tech_dir: Path, slug: str) -> list[Path]:
    # Prefer true manual/free KIPRIS exports under ./source.  Generated normalized
    # aliases are used only when no raw source file is available, which prevents
    # repeated self-ingestion and inflated rows_before_dedupe counts.
    source_explicit = [
        tech_dir / "source" / f"kipris_{slug}_patents.csv",
        tech_dir / "source" / f"{slug}_kipris_patents.csv",
        tech_dir / "source" / f"{slug}_kipris_bibliographic.csv",
        tech_dir / "source" / f"{slug}_kipris_bibliographic_normalized.csv",
        tech_dir / "source" / f"{slug}_kipris_patents_normalized.csv",
    ]
    source_found: list[Path] = [p for p in source_explicit if p.exists() and p.is_file()]
    source_root = tech_dir / "source"
    if source_root.exists():
        for path in source_root.rglob("*"):
            if path.is_file() and _looks_like_patent_input(path):
                source_found.append(path)

    if source_found:
        deduped = {str(p.resolve()): p for p in source_found}
        return sorted(deduped.values(), key=lambda p: _score_source_file(p, slug), reverse=True)

    generated_fallback = [
        tech_dir / f"{slug}_kipris_bibliographic_normalized.csv",
        tech_dir / f"{slug}_kipris_patents_normalized.csv",
        tech_dir / f"{slug}_tech_patent_normalized.csv",
    ]
    found: list[Path] = [p for p in generated_fallback if p.exists() and p.is_file()]
    for path in tech_dir.glob("*kipris*normalized*.csv"):
        if path.is_file() and _looks_like_patent_input(path):
            found.append(path)
    for path in tech_dir.glob("*patent*normalized*.csv"):
        if path.is_file() and _looks_like_patent_input(path):
            found.append(path)

    deduped = {str(p.resolve()): p for p in found}
    return sorted(deduped.values(), key=lambda p: _score_source_file(p, slug), reverse=True)


def _map_columns(df: pd.DataFrame) -> dict[str, str]:
    return {key: _find_col(df, aliases) for key, aliases in COLUMN_ALIASES.items()}


def _pick(row: pd.Series, col: str) -> str:
    if not col:
        return ""
    try:
        return _clean_text(row.get(col, ""))
    except Exception:
        return ""


def _status_flags(register_number: str, register_date: str, register_status: str, final_disposal: str) -> tuple[bool, bool, bool]:
    joined = " ".join([register_number, register_date, register_status, final_disposal]).lower()
    is_registered = bool(register_number or register_date) or any(h.lower() in joined for h in REGISTERED_HINTS)
    negative = any(h.lower() in joined for h in NEGATIVE_STATUS_HINTS)
    is_alive = bool(is_registered and not negative)
    return is_registered, is_alive, negative


def _tech_keyword_count(row: dict[str, Any]) -> int:
    joined = " ".join(
        [
            str(row.get("invention_title") or ""),
            str(row.get("abstract") or ""),
            str(row.get("claim_text") or ""),
            str(row.get("ipc_number") or ""),
            str(row.get("cpc_number") or ""),
        ]
    ).lower()
    return sum(1 for kw in TECH_KEYWORDS if kw.lower() in joined)


def _normalize_frame(df: pd.DataFrame, *, source_file: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if df.empty:
        return [], {}
    mapping = _map_columns(df)
    rows: list[dict[str, Any]] = []
    for idx, row in df.iterrows():
        app_no = _normalize_application_number(_pick(row, mapping.get("application_number", "")))
        title = _pick(row, mapping.get("invention_title", ""))
        right_holder = _pick(row, mapping.get("right_holder", ""))
        application_date = _pick(row, mapping.get("application_date", ""))
        register_number = _digits(_pick(row, mapping.get("register_number", "")))
        register_date = _pick(row, mapping.get("register_date", ""))
        register_status = _pick(row, mapping.get("register_status", ""))
        final_disposal = _pick(row, mapping.get("final_disposal", ""))
        ipc_number = _pick(row, mapping.get("ipc_number", ""))
        cpc_number = _pick(row, mapping.get("cpc_number", ""))
        abstract = _pick(row, mapping.get("abstract", ""))
        claim_text = _pick(row, mapping.get("claim_text", ""))
        open_number = _digits(_pick(row, mapping.get("open_number", "")))
        inventor = _pick(row, mapping.get("inventor", ""))
        url = _pick(row, mapping.get("url", ""))
        drawing = _pick(row, mapping.get("drawing", ""))
        open_date = _pick(row, mapping.get("open_date", ""))

        if not any([app_no, title, right_holder, abstract, claim_text, register_number, ipc_number, cpc_number]):
            continue

        if not app_no:
            # Claim/family endpoints need an application number, but keep the record only if it can still support local patent evidence.
            app_no = _normalize_application_number("|".join([title, right_holder, application_date]))

        is_registered, is_alive, negative = _status_flags(register_number, register_date, register_status, final_disposal)
        item: dict[str, Any] = {
            "application_number": app_no,
            "application_no": app_no,
            "open_number": open_number,
            "publication_no": open_number,
            "register_number": register_number,
            "registration_no": register_number,
            "register_status": register_status,
            "final_disposal": final_disposal or register_status,
            "legal_status": " ".join(x for x in [register_status, final_disposal] if x),
            "invention_title": title,
            "title": title,
            "right_holder": right_holder,
            "applicant": right_holder,
            "inventor": inventor,
            "application_date": application_date,
            "application_year": _year(application_date),
            "open_date": open_date,
            "publication_date": open_date,
            "register_date": register_date,
            "registration_date": register_date,
            "ipc_number": ipc_number,
            "ipc": ipc_number,
            "cpc_number": cpc_number,
            "cpc": cpc_number,
            "abstract": abstract,
            "claim_text": claim_text,
            "claims": claim_text,
            "url": url,
            "drawing": drawing,
            "is_registered": bool(is_registered),
            "is_alive_estimated": bool(is_alive),
            "has_negative_disposal_estimated": bool(negative),
            "source_file": str(source_file),
            "source_sheet": _clean_text(row.get("__source_sheet", "")),
            "source_row": int(idx) + 2,
        }
        item["tech_keyword_match_count"] = _tech_keyword_count(item)
        rows.append(item)
    return rows, {k: v for k, v in mapping.items() if v}


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = str(row.get("application_number") or "").strip()
        if not key:
            key = "|".join(
                [
                    str(row.get("invention_title") or "")[:120],
                    str(row.get("right_holder") or "")[:80],
                    str(row.get("application_date") or ""),
                ]
            )
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _write_outputs(tech_dir: Path, slug: str, rows: list[dict[str, Any]], summary: dict[str, Any], *, force: bool) -> dict[str, str]:
    tech_dir.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    df = df[OUTPUT_COLUMNS]

    outputs = {
        "bibliographic_csv": tech_dir / f"{slug}_kipris_bibliographic_normalized.csv",
        "patents_csv": tech_dir / f"{slug}_kipris_patents_normalized.csv",
        "tech_patent_csv": tech_dir / f"{slug}_tech_patent_normalized.csv",
        "request_targets_csv": tech_dir / f"{slug}_kipris_plus_request_targets.csv",
        "summary_json": tech_dir / f"{slug}_kipris_bibliographic_normalized_summary.json",
        "summary_md": tech_dir / f"{slug}_kipris_bibliographic_normalized_summary.md",
    }

    for key in ("bibliographic_csv", "patents_csv", "tech_patent_csv"):
        path = outputs[key]
        if path.exists() and not force and len(df) == 0:
            continue
        df.to_csv(path, index=False, encoding="utf-8-sig")

    req_cols = [
        "application_number",
        "open_number",
        "register_number",
        "register_status",
        "final_disposal",
        "invention_title",
        "right_holder",
    ]
    df[req_cols].to_csv(outputs["request_targets_csv"], index=False, encoding="utf-8-sig")

    summary["output_files"] = {k: str(v) for k, v in outputs.items()}
    outputs["summary_json"].write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        f"# KIPRIS Bibliographic Normalize Summary - {summary.get('company_name')} ({summary.get('company_slug')})",
        "",
        f"- status: {summary.get('status')}",
        f"- source_file_count: {summary.get('source_file_count')}",
        f"- rows_before_dedupe: {summary.get('rows_before_dedupe')}",
        f"- rows_after_dedupe: {summary.get('rows_after_dedupe')}",
        f"- registered_patents_estimated: {summary.get('registered_patents_estimated')}",
        f"- alive_patents_estimated: {summary.get('alive_patents_estimated')}",
        f"- recent_5y_patents: {summary.get('recent_5y_patents')}",
        "",
        "## Source Files",
        *[f"- {p}" for p in summary.get("source_files", [])],
        "",
        "## Output Files",
        *[f"- {k}: `{v}`" for k, v in summary.get("output_files", {}).items()],
    ]
    outputs["summary_md"].write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return {k: str(v) for k, v in outputs.items()}


def prepare_one(field: str, company_name: str, company_slug: str, *, force: bool = False) -> dict[str, Any]:
    field = normalize_field_name(field)
    tech_dir = _tech_dir(field, company_name, company_slug)
    tech_dir.mkdir(parents=True, exist_ok=True)
    (tech_dir / "source").mkdir(parents=True, exist_ok=True)

    input_files = _find_input_files(tech_dir, company_slug)
    all_rows: list[dict[str, Any]] = []
    column_mappings: dict[str, dict[str, str]] = {}
    read_errors: list[dict[str, str]] = []

    for path in input_files:
        try:
            df = _read_source_file(path)
            rows, mapping = _normalize_frame(df, source_file=path)
            if rows:
                all_rows.extend(rows)
                column_mappings[str(path)] = mapping
        except Exception as exc:
            read_errors.append({"source_file": str(path), "error": str(exc)})

    rows = _dedupe(all_rows)
    current_year = datetime.now().year
    registered = sum(1 for r in rows if r.get("is_registered"))
    alive = sum(1 for r in rows if r.get("is_alive_estimated"))
    recent = sum(1 for r in rows if isinstance(r.get("application_year"), int) and int(r.get("application_year")) >= current_year - 5)

    status = "OK" if rows else "INPUT_NOT_FOUND_OR_EMPTY"
    summary: dict[str, Any] = {
        "company_name": company_name,
        "company_slug": company_slug,
        "field": field,
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "tech_dir": str(tech_dir),
        "source_file_count": len(input_files),
        "source_files": [str(p) for p in input_files],
        "read_errors": read_errors,
        "column_mappings": column_mappings,
        "rows_before_dedupe": len(all_rows),
        "rows_after_dedupe": len(rows),
        "registered_patents_estimated": registered,
        "alive_patents_estimated": alive,
        "recent_5y_patents": recent,
        "offline_free_mode_ready": bool(rows),
        "kipris_plus_request_targets_ready": bool(rows),
        "usage_rule": (
            "This script normalizes free/manual KIPRIS CSV/XLSX exports and existing local patent files. "
            "KIPRIS Plus claim/citation/family collectors can use the generated request-target CSV after API approval."
        ),
    }

    _write_outputs(tech_dir, company_slug, rows, summary, force=force)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Normalize free/manual KIPRIS patent exports into Tech Intake-ready bibliographic CSV."
    )
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-name", required=True)
    parser.add_argument("--company-slug", required=True)
    parser.add_argument("--force", action="store_true", help="Overwrite normalized alias CSVs even if they already exist.")
    args = parser.parse_args(argv)

    result = prepare_one(
        field=normalize_field_name(args.field),
        company_name=args.company_name,
        company_slug=args.company_slug,
        force=args.force,
    )

    print("[PREPARE RESULT]")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
