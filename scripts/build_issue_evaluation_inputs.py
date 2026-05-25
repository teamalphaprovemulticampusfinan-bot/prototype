from __future__ import annotations

"""Build date-aware Issue Agent input CSVs under data/<field>/_sector_common/issue.

This script is safe for evaluation mode: it writes only sector-common issue input
CSVs, not company-local agent outputs.  It converts existing Issue_Integration,
news, and RSS files into normalized daily/monthly/common issue tables with the
same column schema.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def _import_feature_module():
    import sys
    src_eval = ROOT / "src_eval"
    src = ROOT / "src"
    for p in [src_eval, src]:
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)
    from issue_agent.history_issue_features import (
        EXPOSURE_COLUMNS,
        ISSUE_COLUMNS,
        issue_input_paths,
        normalize_issue_events,
        write_issue_feature_templates,
    )
    return EXPOSURE_COLUMNS, ISSUE_COLUMNS, issue_input_paths, normalize_issue_events, write_issue_feature_templates


def _read_csv_any(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return pd.read_csv(path, encoding=enc, dtype=str)
        except Exception:
            pass
    return pd.DataFrame()


def _read_excel_any(path: Path) -> pd.DataFrame:
    frames = []
    try:
        xls = pd.ExcelFile(path)
        for sheet in xls.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet, dtype=str)
            if not df.empty:
                df["_source_sheet"] = sheet
                frames.append(df)
    except Exception:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _read_any(path: Path) -> pd.DataFrame:
    return _read_excel_any(path) if path.suffix.lower() in {".xlsx", ".xls", ".xlsm"} else _read_csv_any(path)


def _discover_source_files(root: Path, field: str) -> list[Path]:
    sector = root / "data" / field / "_sector_common"
    candidates = [sector / "data" / "Issue_Integration.xlsx", sector / "data" / "issue_integration.xlsx"]
    for base in [sector / "issue", sector / "data"]:
        if not base.exists():
            continue
        for pat in ["*Issue*.xlsx", "*issue*.xlsx", "*Issue*.csv", "*issue*.csv", "*news*.csv", "*뉴스*.csv", "*rss*.csv"]:
            candidates.extend(sorted(base.glob(pat)))
    seen, out = set(), []
    generated_names = {
        "issue_events_daily.csv", "issue_events_monthly.csv", "issue_events_common.csv",
        "issue_events_daily_template.csv", "issue_events_monthly_template.csv", "issue_events_common_template.csv",
        "company_issue_exposure.csv", "company_issue_exposure_template.csv", "issue_feature_manifest.csv",
    }
    for p in candidates:
        if p.exists() and p.is_file() and p.name not in generated_names:
            key = str(p.resolve())
            if key not in seen:
                seen.add(key)
                out.append(p)
    return out


def _normalize_code(x: Any) -> str:
    text = str(x or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits.zfill(6) if digits and len(digits) <= 6 else text


def _read_universe(path: Path) -> pd.DataFrame:
    if not path or not path.exists():
        return pd.DataFrame()
    return _read_csv_any(path)


def _build_exposure_from_universe(universe: pd.DataFrame, field: str, exposure_cols: list[str]) -> pd.DataFrame:
    if universe.empty:
        return pd.DataFrame(columns=exposure_cols)
    rows = []
    for _, r in universe.iterrows():
        d = {str(k): ("" if pd.isna(v) else str(v)) for k, v in r.to_dict().items()}
        company = d.get("company") or d.get("company_name") or d.get("name") or ""
        ticker = _normalize_code(d.get("ticker") or d.get("stock_code") or d.get("code") or "")
        vc_role = d.get("vc_role") or d.get("peer_group") or d.get("sector") or ""
        role_low = vc_role.lower()
        base = {c: "" for c in exposure_cols}
        base.update({"field": field, "company": company, "ticker": ticker, "stock_code": ticker, "company_dir": d.get("company_dir") or d.get("slug") or "", "vc_role": vc_role, "default_exposure": 0.70, "evidence_note": "auto template; edit manually when company-specific issue sensitivity is available"})
        # Magnitude-only exposure; sign still comes from issue sentiment/category.
        for c in ["earnings", "capital_structure", "financing_dilution", "credit_rating"]:
            base[c] = 0.90
        if any(k in role_low for k in ["후공정", "패키징", "테스트", "osat", "test"]):
            for c in ["order_contract", "customer_adoption", "technology_validation", "capacity_expansion"]:
                base[c] = 1.15
        elif any(k in role_low for k in ["소재", "material", "chemical"]):
            for c in ["supply_chain", "customer_adoption", "order_contract", "regulation"]:
                base[c] = 1.15
        elif any(k in role_low for k in ["장비", "equipment"]):
            for c in ["order_contract", "capacity_expansion", "customer_adoption", "technology_validation"]:
                base[c] = 1.15
        rows.append(base)
    return pd.DataFrame(rows, columns=exposure_cols)


def _aggregate_monthly(events: pd.DataFrame, issue_cols: list[str]) -> pd.DataFrame:
    if events.empty:
        return pd.DataFrame(columns=issue_cols)
    x = events.copy()
    dt = pd.to_datetime(x["published_at"].fillna(x["date"]), errors="coerce")
    x = x[dt.notna()].copy()
    if x.empty:
        return pd.DataFrame(columns=issue_cols)
    x["_month_end"] = dt[dt.notna()].dt.to_period("M").dt.to_timestamp(how="end").dt.strftime("%Y-%m-%d")
    keys = ["_month_end", "field", "company", "ticker", "stock_code", "issue_category", "sentiment_label"]
    rows = []
    for key, g in x.groupby(keys, dropna=False):
        row = {c: "" for c in issue_cols}
        month_end, field, company, ticker, stock_code, category, label = key
        row.update({"date": month_end, "published_at": month_end, "as_of_date": month_end, "field": field, "company": company, "ticker": ticker, "stock_code": stock_code, "frequency": "monthly", "source_kind": "monthly_aggregate", "source": "issue_events_daily", "source_type": "aggregate", "issue_category": category, "sentiment_label": label, "title": f"{company} {month_end[:7]} {category} issue aggregate"})
        row["issue_count"] = int(g["issue_count"].fillna(1).astype(float).sum())
        row["positive_issue_count"] = int(g["positive_issue_count"].fillna(0).astype(float).sum())
        row["negative_issue_count"] = int(g["negative_issue_count"].fillna(0).astype(float).sum())
        row["material_issue_count"] = int(g["material_issue_count"].fillna(0).astype(float).sum())
        row["sentiment_score"] = float(g["sentiment_score"].fillna(0).astype(float).mean())
        row["materiality_weight"] = float(g["materiality_weight"].fillna(0.55).astype(float).mean())
        row["source_weight"] = float(g["source_weight"].fillna(0.65).astype(float).mean())
        row["evidence_note"] = "monthly aggregate from dated issue rows"
        rows.append(row)
    return pd.DataFrame(rows, columns=issue_cols)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build src_eval Issue Agent daily/monthly input CSVs")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--universe-csv", default="data/반도체/_sector_common/universe/universe_30_semiconductor_20260514.csv")
    parser.add_argument("--force", action="store_true", help="overwrite existing generated issue_events_daily/monthly files")
    args = parser.parse_args()

    exposure_cols, issue_cols, issue_input_paths, normalize_issue_events, write_issue_feature_templates = _import_feature_module()
    paths = issue_input_paths(ROOT, args.field)
    write_issue_feature_templates(ROOT, args.field)

    source_files = _discover_source_files(ROOT, args.field)
    frames = []
    for path in source_files:
        df = _read_any(path)
        if df.empty:
            continue
        norm = normalize_issue_events(df, field=args.field, source_file=str(path), default_frequency="daily")
        if not norm.empty:
            frames.append(norm)
    events = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=issue_cols)
    if not events.empty:
        events = events.drop_duplicates(subset=["company", "ticker", "stock_code", "published_at", "title", "summary", "url"], keep="first")

    dated = events[pd.to_datetime(events["published_at"].fillna(events["date"]), errors="coerce").notna()].copy() if not events.empty else pd.DataFrame(columns=issue_cols)
    undated = events[pd.to_datetime(events["published_at"].fillna(events["date"]), errors="coerce").isna()].copy() if not events.empty else pd.DataFrame(columns=issue_cols)

    if args.force or not paths["daily"].exists() or paths["daily"].stat().st_size < 10:
        dated.to_csv(paths["daily"], index=False, encoding="utf-8-sig")
    monthly = _aggregate_monthly(dated, issue_cols)
    if args.force or not paths["monthly"].exists() or paths["monthly"].stat().st_size < 10:
        monthly.to_csv(paths["monthly"], index=False, encoding="utf-8-sig")
    if args.force or not paths["common"].exists() or paths["common"].stat().st_size < 10:
        undated.to_csv(paths["common"], index=False, encoding="utf-8-sig")

    universe_path = ROOT / args.universe_csv
    universe = _read_universe(universe_path)
    exposure = _build_exposure_from_universe(universe, args.field, exposure_cols)
    if args.force or not paths["exposure"].exists() or paths["exposure"].stat().st_size < 10:
        exposure.to_csv(paths["exposure"], index=False, encoding="utf-8-sig")

    manifest = {
        "field": args.field,
        "source_files": [str(p) for p in source_files],
        "issue_events_daily": str(paths["daily"]),
        "issue_events_monthly": str(paths["monthly"]),
        "issue_events_common": str(paths["common"]),
        "company_issue_exposure": str(paths["exposure"]),
        "daily_rows": int(len(dated)),
        "monthly_rows": int(len(monthly)),
        "common_undated_rows": int(len(undated)),
        "policy": "Only dated rows are used for monthly/daily history signals. Undated rows are kept as common reference and do not affect past signal unless dated by the user.",
    }
    paths["manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
