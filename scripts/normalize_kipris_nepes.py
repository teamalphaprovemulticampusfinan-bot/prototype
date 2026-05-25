from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


FIELD = "반도체"
COMPANY_DIR = "네패스"
COMPANY_SLUG = "nepes"

SOURCE_FILE = Path("data") / FIELD / COMPANY_DIR / "tech" / "source" / "kipris_nepes_patents.csv"
OUT_DIR = Path("data") / FIELD / COMPANY_DIR / "tech"
OUT_DIR.mkdir(parents=True, exist_ok=True)

NORMALIZED_CSV = OUT_DIR / f"{COMPANY_SLUG}_kipris_patents_normalized.csv"
SUMMARY_JSON = OUT_DIR / f"{COMPANY_SLUG}_kipris_patents_normalized_summary.json"
SUMMARY_MD = OUT_DIR / f"{COMPANY_SLUG}_kipris_patents_normalized_summary.md"


TECH_KEYWORDS = [
    "반도체",
    "패키지",
    "패키징",
    "웨이퍼",
    "wafer",
    "wlp",
    "fowlp",
    "fan-out",
    "fanout",
    "테스트",
    "test",
    "소자",
    "chip",
    "칩",
    "substrate",
    "기판",
    "bump",
    "범프",
    "interposer",
    "인터포저",
    "probe",
    "프로브",
    "module",
    "모듈",
]

SEMICONDUCTOR_IPC_PREFIXES = [
    "H01L",  # semiconductor devices
    "H05K",  # printed circuits / electronic assemblies
    "G01R",  # electrical testing
    "B81B",  # micro-structural devices
    "B81C",  # manufacture/treatment of micro-structural devices
]


def read_csv_safely(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"CSV 읽기 실패: {path} / {last_error}")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def parse_date(value: Any) -> pd.Timestamp | pd.NaT:
    text = clean_text(value)
    if not text:
        return pd.NaT

    text = text.replace(".", "-").replace("/", "-")

    # 20250103, 2025-01-03 모두 대응
    if re.fullmatch(r"\d{8}", text):
        text = f"{text[:4]}-{text[4:6]}-{text[6:8]}"

    try:
        return pd.to_datetime(text, errors="coerce")
    except Exception:
        return pd.NaT


def year_from_date(value: Any) -> int | None:
    dt = parse_date(value)
    if pd.isna(dt):
        return None
    return int(dt.year)


def normalize_ipc(value: Any) -> str:
    text = clean_text(value).upper()
    text = text.replace(";", ",")
    text = re.sub(r"\s+", " ", text)
    return text


def first_ipc(value: Any) -> str:
    text = normalize_ipc(value)
    if not text:
        return ""

    parts = re.split(r"[,|/;]", text)
    for part in parts:
        part = part.strip()
        if part:
            return part
    return ""


def ipc_section(value: Any) -> str:
    ipc = first_ipc(value)
    if not ipc:
        return ""
    return ipc[0]


def has_semiconductor_ipc(value: Any) -> bool:
    text = normalize_ipc(value)
    return any(prefix in text for prefix in SEMICONDUCTOR_IPC_PREFIXES)


def has_h01l(value: Any) -> bool:
    text = normalize_ipc(value)
    return "H01L" in text


def keyword_match_count(row: dict[str, Any]) -> int:
    joined = " ".join(
        [
            clean_text(row.get("invention_title")),
            clean_text(row.get("abstract")),
            clean_text(row.get("ipc_number")),
        ]
    ).lower()

    count = 0
    for kw in TECH_KEYWORDS:
        if kw.lower() in joined:
            count += 1
    return count


def derive_final_disposal(register_status: Any, register_number: Any, register_date: Any) -> str:
    """
    원천 CSV에 final_disposal 컬럼이 없으므로 register_status 기반으로 보수적으로 추정한다.
    이 값은 법적 최종처분 원문이 아니라 'derived' 값이다.
    """
    status = clean_text(register_status)
    reg_no = clean_text(register_number)
    reg_date = clean_text(register_date)

    if "거절" in status:
        return "거절_추정"
    if "취하" in status:
        return "취하_추정"
    if "소멸" in status:
        return "소멸_추정"
    if "포기" in status:
        return "포기_추정"
    if "등록" in status or reg_no or reg_date:
        return "등록_추정"
    if "공개" in status:
        return "공개_추정"
    if status:
        return f"상태확인필요_{status}"
    return "확인제한"


def is_registered(register_status: Any, register_number: Any, register_date: Any) -> bool:
    status = clean_text(register_status)
    return bool("등록" in status or clean_text(register_number) or clean_text(register_date))


def estimated_expiry_year(application_date: Any) -> int | None:
    """
    특허권 존속기간은 일반적으로 출원일 기준 20년을 쓰는 보수적 추정값.
    단, 실제 존속 여부는 연차료 납부/소멸/무효/권리변동 정보가 있어야 확정 가능.
    """
    year = year_from_date(application_date)
    if year is None:
        return None
    return year + 20


def is_alive_estimated(application_date: Any, registered: bool) -> bool | None:
    if not registered:
        return False

    expiry_year = estimated_expiry_year(application_date)
    if expiry_year is None:
        return None

    current_year = datetime.now().year
    return expiry_year >= current_year


def build_normalized(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        raw = row.to_dict()

        app_date = raw.get("application_date")
        open_date = raw.get("open_date")
        pub_date = raw.get("publication_date")
        reg_date = raw.get("register_date")
        reg_status = raw.get("register_status")
        reg_no = raw.get("register_number")

        registered = is_registered(reg_status, reg_no, reg_date)
        alive_est = is_alive_estimated(app_date, registered)
        expiry_year = estimated_expiry_year(app_date)

        out = {
            "company_slug": COMPANY_SLUG,
            "company_name": COMPANY_DIR,
            "source_file": SOURCE_FILE.name,

            "query_applicant": clean_text(raw.get("query_applicant")),
            "index_no": clean_text(raw.get("index_no")),

            "invention_title": clean_text(raw.get("invention_title")),
            "applicant_name": clean_text(raw.get("applicant_name")),

            "application_number": clean_text(raw.get("application_number")),
            "application_date": clean_text(app_date),
            "application_year": year_from_date(app_date),

            "open_number": clean_text(raw.get("open_number")),
            "open_date": clean_text(open_date),
            "open_year": year_from_date(open_date),

            "publication_number": clean_text(raw.get("publication_number")),
            "publication_date": clean_text(pub_date),
            "publication_year": year_from_date(pub_date),

            "register_number": clean_text(reg_no),
            "register_date": clean_text(reg_date),
            "register_year": year_from_date(reg_date),
            "register_status": clean_text(reg_status),

            "final_disposal": derive_final_disposal(reg_status, reg_no, reg_date),
            "final_disposal_source": "derived_from_register_status_because_source_csv_missing_final_disposal",

            "abstract": clean_text(raw.get("abstract")),
            "drawing": clean_text(raw.get("drawing")),
            "big_drawing": clean_text(raw.get("big_drawing")),

            "ipc_number": normalize_ipc(raw.get("ipc_number")),
            "ipc_main": first_ipc(raw.get("ipc_number")),
            "ipc_section": ipc_section(raw.get("ipc_number")),
            "has_semiconductor_ipc": has_semiconductor_ipc(raw.get("ipc_number")),
            "has_h01l": has_h01l(raw.get("ipc_number")),

            "is_registered": registered,
            "estimated_expiry_year": expiry_year,
            "is_alive_estimated": alive_est,

            "tech_keyword_match_count": keyword_match_count(raw),
        }

        rows.append(out)

    return pd.DataFrame(rows)


def build_summary(norm_df: pd.DataFrame) -> dict[str, Any]:
    total = len(norm_df)
    registered = int(norm_df["is_registered"].fillna(False).sum()) if total else 0
    alive = int(norm_df["is_alive_estimated"].fillna(False).sum()) if total else 0
    h01l = int(norm_df["has_h01l"].fillna(False).sum()) if total else 0
    semi_ipc = int(norm_df["has_semiconductor_ipc"].fillna(False).sum()) if total else 0

    app_years = sorted([int(x) for x in norm_df["application_year"].dropna().unique().tolist()])
    reg_years = sorted([int(x) for x in norm_df["register_year"].dropna().unique().tolist()])

    recent_5y_threshold = datetime.now().year - 5
    recent_5y = int((norm_df["application_year"].fillna(0) >= recent_5y_threshold).sum()) if total else 0

    top_ipc = (
        norm_df["ipc_main"]
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .head(15)
        .to_dict()
    )

    top_applicants = (
        norm_df["applicant_name"]
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .head(10)
        .to_dict()
    )

    return {
        "company_slug": COMPANY_SLUG,
        "company_name": COMPANY_DIR,
        "source_file": str(SOURCE_FILE),
        "normalized_csv": str(NORMALIZED_CSV),
        "total_patents": total,
        "registered_patents_estimated": registered,
        "alive_patents_estimated": alive,
        "registration_rate_estimated": round(registered / total, 4) if total else None,
        "alive_rate_among_registered_estimated": round(alive / registered, 4) if registered else None,
        "recent_5y_application_patents": recent_5y,
        "application_year_min": min(app_years) if app_years else None,
        "application_year_max": max(app_years) if app_years else None,
        "register_year_min": min(reg_years) if reg_years else None,
        "register_year_max": max(reg_years) if reg_years else None,
        "semiconductor_ipc_patents": semi_ipc,
        "h01l_patents": h01l,
        "top_ipc_main": top_ipc,
        "top_applicants": top_applicants,
        "final_disposal_note": "source CSV has no final_disposal column; final_disposal was conservatively derived from register_status/register_number/register_date.",
    }


def write_summary_md(summary: dict[str, Any]) -> None:
    lines = []
    lines.append(f"# {summary['company_name']} KIPRIS normalized summary")
    lines.append("")
    lines.append("## 1. Source")
    lines.append(f"- source_file: `{summary['source_file']}`")
    lines.append(f"- normalized_csv: `{summary['normalized_csv']}`")
    lines.append("")
    lines.append("## 2. Core Counts")
    lines.append(f"- total_patents: {summary['total_patents']}")
    lines.append(f"- registered_patents_estimated: {summary['registered_patents_estimated']}")
    lines.append(f"- alive_patents_estimated: {summary['alive_patents_estimated']}")
    lines.append(f"- registration_rate_estimated: {summary['registration_rate_estimated']}")
    lines.append(f"- alive_rate_among_registered_estimated: {summary['alive_rate_among_registered_estimated']}")
    lines.append(f"- recent_5y_application_patents: {summary['recent_5y_application_patents']}")
    lines.append("")
    lines.append("## 3. Year Range")
    lines.append(f"- application_year_range: {summary['application_year_min']} ~ {summary['application_year_max']}")
    lines.append(f"- register_year_range: {summary['register_year_min']} ~ {summary['register_year_max']}")
    lines.append("")
    lines.append("## 4. Tech/IP Signals")
    lines.append(f"- semiconductor_ipc_patents: {summary['semiconductor_ipc_patents']}")
    lines.append(f"- h01l_patents: {summary['h01l_patents']}")
    lines.append("")
    lines.append("## 5. Top IPC")
    for k, v in summary["top_ipc_main"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## 6. Note")
    lines.append(f"- {summary['final_disposal_note']}")
    lines.append("")

    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if not SOURCE_FILE.exists():
        print(f"[ERROR] KIPRIS source file not found: {SOURCE_FILE}")
        return 1

    df = read_csv_safely(SOURCE_FILE)
    norm_df = build_normalized(df)

    norm_df.to_csv(NORMALIZED_CSV, index=False, encoding="utf-8-sig")

    summary = build_summary(norm_df)
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_summary_md(summary)

    print("[DONE] KIPRIS normalized CSV created")
    print(f"- source rows: {len(df):,}")
    print(f"- normalized rows: {len(norm_df):,}")
    print(f"- normalized csv: {NORMALIZED_CSV}")
    print(f"- summary json: {SUMMARY_JSON}")
    print(f"- summary md: {SUMMARY_MD}")
    print()
    print("[SUMMARY]")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
