from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore


DATE_COL_CANDIDATES = [
    "date", "일자", "기준일", "거래일", "날짜", "datetime", "timestamp",
    "published_at", "pubDate", "공시일", "보도일", "작성일",
    "fiscal_date", "period_end", "결산일", "year", "년도",
]


def _safe_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _read_table(path: Path):
    if pd is None or not path.exists() or not path.is_file():
        return None
    try:
        if path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
            return pd.read_excel(path)
        for enc in ("utf-8-sig", "utf-8", "cp949"):
            try:
                return pd.read_csv(path, encoding=enc)
            except UnicodeDecodeError:
                continue
        return pd.read_csv(path, encoding="utf-8", encoding_errors="replace")
    except Exception:
        return None


def _detect_date_col(df) -> str:
    cols = list(getattr(df, "columns", []))
    lower = {str(c).lower(): c for c in cols}
    for c in DATE_COL_CANDIDATES:
        if c.lower() in lower:
            return lower[c.lower()]
    for c in cols:
        name = str(c).lower()
        if "date" in name or "일자" in name or "날짜" in name or "기준" in name:
            return c
    return ""


def _date_series(df, col: str):
    if pd is None or not col:
        return None
    s = df[col]
    # Year-only columns are interpreted as year-end. This is conservative for
    # annual finance/valuation financial tables.
    if str(col).lower() in {"year", "년도"}:
        s = s.astype(str).str.extract(r"(\d{4})", expand=False).fillna("")
        return pd.to_datetime(s + "-12-31", errors="coerce")
    return pd.to_datetime(s, errors="coerce")


def _scan_file(path: Path, as_of_date: str, root: Path) -> dict[str, Any]:
    result = {
        "file": str(path.relative_to(root)) if path.exists() and path.is_relative_to(root) else str(path),
        "exists": path.exists(),
        "rows": 0,
        "date_column": "",
        "min_date": "",
        "max_date": "",
        "rows_after_cutoff": 0,
        "cutoff_ok": True,
        "note": "",
    }
    df = _read_table(path)
    if df is None:
        result["cutoff_ok"] = path.exists()
        result["note"] = "not_readable_or_not_tabular" if path.exists() else "missing"
        return result
    result["rows"] = int(len(df))
    col = _detect_date_col(df)
    result["date_column"] = _safe_text(col)
    if not col:
        result["note"] = "no_date_column_detected"
        return result
    dates = _date_series(df, col)
    if dates is None:
        result["note"] = "date_parse_unavailable"
        return result
    valid = dates.dropna()
    if len(valid):
        result["min_date"] = valid.min().strftime("%Y-%m-%d")
        result["max_date"] = valid.max().strftime("%Y-%m-%d")
    cutoff = pd.to_datetime(as_of_date, errors="coerce")
    after = dates.notna() & (dates > cutoff)
    result["rows_after_cutoff"] = int(after.sum())
    result["cutoff_ok"] = result["rows_after_cutoff"] == 0
    return result


def _glob_limited(root: Path, patterns: list[str], limit: int = 200) -> list[Path]:
    out: list[Path] = []
    for pattern in patterns:
        out.extend([p for p in root.glob(pattern) if p.is_file()])
        if len(out) >= limit:
            break
    return list(dict.fromkeys(out))[:limit]


def validate_monthly_cutoff_sources(
    *,
    root: str | Path,
    field: str,
    company: str,
    company_dir: str,
    as_of_date: str,
) -> dict[str, Any]:
    root = Path(root)
    company_data_candidates = [
        root / "data" / field / company,
        root / "data" / field / company_dir,
    ]
    company_data = next((p for p in company_data_candidates if p.exists()), company_data_candidates[0])

    market_dir = Path(os.getenv("MARKET_EXCEL_DIR", "")) if os.getenv("MARKET_EXCEL_DIR") else root / "data" / "market_excel"
    valuation_intake = company_data / "valuation" / "intake"
    finance_intake = company_data / "finance" / "intake"
    issue_intake = company_data / "issue" / "intake"
    macro_dir = root / "data" / "_global_common" / "macro"

    checks: dict[str, list[dict[str, Any]]] = {
        "market": [],
        "valuation": [],
        "finance": [],
        "issue": [],
        "macro": [],
    }

    market_files = _glob_limited(market_dir, ["*.csv", "*.xlsx", f"*{company}*.xlsx", f"*{company_dir}*.xlsx"], limit=200)
    # Also check legacy sector workbook if present.
    legacy_market = root / "data" / field / "_sector_common" / "data" / "Market_통합.xlsx"
    if legacy_market.exists():
        market_files.append(legacy_market)
    checks["market"] = [_scan_file(p, as_of_date, root) for p in list(dict.fromkeys(market_files))]

    valuation_files = _glob_limited(valuation_intake, ["*.csv", "*.json"], limit=100)
    checks["valuation"] = [_scan_file(p, as_of_date, root) for p in valuation_files if p.suffix.lower() == ".csv"]
    if not valuation_intake.exists():
        checks["valuation"].append({"file": str(valuation_intake), "exists": False, "cutoff_ok": False, "note": "valuation_intake_dir_missing"})

    finance_files = _glob_limited(finance_intake, ["*.csv", "*.xlsx"], limit=100)
    if not finance_files:
        finance_files = _glob_limited(company_data / "finance", ["*.csv", "*.xlsx"], limit=100)
    checks["finance"] = [_scan_file(p, as_of_date, root) for p in finance_files]

    issue_files = _glob_limited(issue_intake, ["*.csv", "*.xlsx"], limit=100)
    legacy_issue = root / "data" / field / "_sector_common" / "data" / "Issue_Integration.xlsx"
    if legacy_issue.exists():
        issue_files.append(legacy_issue)
    checks["issue"] = [_scan_file(p, as_of_date, root) for p in list(dict.fromkeys(issue_files))]

    macro_files = _glob_limited(macro_dir, ["*.csv", "*.xlsx"], limit=100)
    checks["macro"] = [_scan_file(p, as_of_date, root) for p in macro_files]

    summary: dict[str, Any] = {}
    for agent, rows in checks.items():
        readable = [r for r in rows if r.get("exists")]
        violations = [r for r in rows if r.get("exists") and r.get("cutoff_ok") is False]
        summary[agent] = {
            "files_checked": len(rows),
            "files_existing": len(readable),
            "cutoff_violations": len(violations),
            "status": "PASS" if not violations else "FAIL",
        }

    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "field": field,
        "company": company,
        "company_dir": company_dir,
        "as_of_date": as_of_date,
        "policy": "tech excluded by project policy; finance/market/valuation/issue/macro checked against monthly cutoff",
        "summary": summary,
        "checks": checks,
    }


def write_cutoff_audit(
    *,
    root: str | Path,
    field: str,
    company: str,
    company_dir: str,
    as_of_date: str,
    output_dir: str | Path,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = validate_monthly_cutoff_sources(
        root=root,
        field=field,
        company=company,
        company_dir=company_dir,
        as_of_date=as_of_date,
    )
    path = output_dir / "cutoff_source_audit.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
