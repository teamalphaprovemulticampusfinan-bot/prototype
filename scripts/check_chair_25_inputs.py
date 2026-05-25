from __future__ import annotations
import argparse, csv, json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "반도체" / "_sector_common" / "universe" / "universe_30_semiconductor_20260514.csv"
ORIGINAL_5 = {"nepes","hanmi","hansol","duksan","ltc"}

HELPFUL = {
    "auditor_chair_packet": ["auditor/first_auditor/compact_agent_packets/auditor_chair_packet.json"],
    "finance": ["finance/*_finance_agent_packet.json", "finance/finance.json"],
    "market": ["market/*_market_agent_packet.json", "market/market.json"],
    "issue": ["issue/*_issue_agent_packet.json", "issue/issue.json"],
    "macro": ["macro/*_macro_agent_packet.json", "macro/macro.json"],
    "tech": ["tech/*_tech_agent_packet.json", "tech/tech.json", "tech/tech_chair_summary.json"],
    "valuation": ["valuation/*_valuation_metrics.json", "valuation/*_valuation_validation.json", "valuation/*_valuation_workbook.xlsx"],
}

def truthy(v: Any) -> bool:
    return str(v or "").strip().lower() in {"1","true","yes","y"}

def rows(path: Path, include_original5: bool, only: str) -> list[dict[str,str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        out = [dict(r) for r in csv.DictReader(f) if truthy(r.get("include_in_evaluation","1"))]
    if not include_original5:
        out = [r for r in out if str(r.get("company_dir","")).strip() not in ORIGINAL_5]
    if only:
        out = [r for r in out if str(r.get("company_dir","")).strip() == only]
    return out

def glob_any(base: Path, patterns: list[str]) -> list[Path]:
    found = []
    for pat in patterns:
        found.extend(base.glob(pat))
    return sorted(set(found))

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default=str(DEFAULT_CSV))
    p.add_argument("--include-original5", action="store_true")
    p.add_argument("--only-company-dir", default="")
    p.add_argument("--require-auditor-packet", action="store_true")
    args = p.parse_args()
    result = []
    failed = False
    for r in rows(Path(args.csv), args.include_original5, args.only_company_dir):
        name, slug = str(r["company_name"]).strip(), str(r["company_dir"]).strip()
        root = ROOT / "data" / "반도체" / name
        status = {}
        for k, pats in HELPFUL.items():
            m = glob_any(root, pats) if root.exists() else []
            status[k] = {"exists": bool(m), "count": len(m), "examples": [str(p.relative_to(ROOT)) for p in m[:3]]}
        missing = [k for k, v in status.items() if not v["exists"]]
        if args.require_auditor_packet and not status["auditor_chair_packet"]["exists"]:
            failed = True
        result.append({"company_name": name, "company_dir": slug, "ok_for_nepes_style": status["auditor_chair_packet"]["exists"], "missing": missing, "inputs": status})
    print(json.dumps({"count": len(result), "require_auditor_packet": args.require_auditor_packet, "results": result}, ensure_ascii=False, indent=2))
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
