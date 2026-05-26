from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evaluation.cutoff_data_auditor import write_cutoff_audit
from evaluation.cutoff_env import month_windows


def _read_universe(path: Path, field: str) -> list[dict[str, str]]:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                rows = [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]
            break
        except UnicodeDecodeError:
            continue
    else:
        rows = []
    out = []
    for row in rows:
        company = row.get("company") or row.get("회사명") or row.get("name") or row.get("기업명")
        company_dir = row.get("company_dir") or row.get("slug") or row.get("company_slug")
        stock_code = row.get("stock_code") or row.get("ticker") or row.get("종목코드")
        row_field = row.get("field") or row.get("sector") or field
        if company and company_dir:
            out.append({"company": company, "company_dir": company_dir, "stock_code": stock_code, "field": row_field})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate monthly no-look-ahead source files before/after backtest.")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--universe-csv", default="data/반도체/_sector_common/universe/universe_30_semiconductor_20260514.csv")
    ap.add_argument("--only-company-dir", default="")
    ap.add_argument("--out-dir", default="data/반도체/_sector_common/history_sheets_exports/monthly/cutoff_source_audits")
    ns = ap.parse_args(argv)

    universe = _read_universe(ROOT / ns.universe_csv, ns.field)
    only = {x.strip().lower() for x in ns.only_company_dir.replace(";", ",").split(",") if x.strip()}
    if only:
        universe = [r for r in universe if r["company_dir"].lower() in only]

    windows = month_windows(ns.start, ns.end)
    out_root = ROOT / ns.out_dir
    out_root.mkdir(parents=True, exist_ok=True)
    failures = []
    for as_of in windows:
        window = as_of[:7]
        for target in universe:
            audit_path = write_cutoff_audit(
                root=ROOT,
                field=ns.field,
                company=target["company"],
                company_dir=target["company_dir"],
                as_of_date=as_of,
                output_dir=out_root / window / target["company_dir"],
            )
            payload = json.loads(audit_path.read_text(encoding="utf-8"))
            bad = [agent for agent, item in payload["summary"].items() if item["status"] != "PASS"]
            if bad:
                failures.append({"window": window, "company_dir": target["company_dir"], "bad": bad, "audit": str(audit_path)})
            print(f"[cutoff-audit] {window} {target['company_dir']} {'PASS' if not bad else 'FAIL'} -> {audit_path}")

    summary = {"status": "PASS" if not failures else "FAIL", "failures": failures}
    summary_path = out_root / "cutoff_source_audit_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
