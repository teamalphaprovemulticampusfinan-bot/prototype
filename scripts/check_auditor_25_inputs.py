from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "data" / "반도체" / "_sector_common" / "universe" / "universe_30_semiconductor_20260514.csv"
ORIGINAL_5 = {"nepes", "hanmi", "hansol", "duksan", "ltc"}

AGENT_PATTERNS = {
    "finance": ["*_finance_agent_packet.json", "finance.json"],
    "market": ["*_market_agent_packet.json", "market.json"],
    "issue": ["*_issue_agent_packet.json", "issue.json"],
    "macro": ["*_macro_agent_packet.json", "macro.json"],
    "tech": ["*_tech_agent_packet.json", "tech.json", "tech_chair_summary.json"],
    "valuation": ["*_valuation_agent_packet.json", "valuation.json", "*_valuation_metrics.json", "*_valuation_validation.json"],
}


def truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def read_rows(path: Path, *, include_original5: bool, only_company_dir: str = "") -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = [dict(r) for r in csv.DictReader(f) if truthy(r.get("include_in_evaluation", "1"))]

    if not include_original5:
        rows = [r for r in rows if str(r.get("company_dir", "")).strip() not in ORIGINAL_5]

    if only_company_dir:
        rows = [r for r in rows if str(r.get("company_dir", "")).strip() == only_company_dir]

    return rows


def find_company_dir(company_name: str) -> Path:
    return ROOT / "data" / "반도체" / company_name


def glob_any(base: Path, patterns: list[str]) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        out.extend(base.rglob(pat))
    return sorted(set(out))


def main() -> int:
    p = argparse.ArgumentParser(description="Check specialist agent outputs before Auditor.")
    p.add_argument("--csv", default=str(DEFAULT_CSV))
    p.add_argument("--include-original5", action="store_true")
    p.add_argument("--only-company-dir", default="")
    p.add_argument("--require-all", action="store_true")
    args = p.parse_args()

    rows = read_rows(Path(args.csv), include_original5=args.include_original5, only_company_dir=args.only_company_dir)

    results: list[dict[str, Any]] = []
    failed = False

    for row in rows:
        name = str(row["company_name"]).strip()
        slug = str(row["company_dir"]).strip()
        company_root = find_company_dir(name)

        agent_status: dict[str, Any] = {}

        for agent, patterns in AGENT_PATTERNS.items():
            agent_dir = company_root / agent
            matches = glob_any(agent_dir, patterns) if agent_dir.exists() else []
            agent_status[agent] = {
                "exists": bool(matches),
                "count": len(matches),
                "examples": [str(p.relative_to(ROOT)) for p in matches[:3]],
            }

        missing = [a for a, s in agent_status.items() if not s["exists"]]
        ok = not missing

        if args.require_all and missing:
            failed = True

        results.append({
            "company_name": name,
            "company_dir": slug,
            "ok": ok,
            "missing": missing,
            "agents": agent_status,
        })

    print(json.dumps({
        "count": len(results),
        "require_all": args.require_all,
        "results": results,
    }, ensure_ascii=False, indent=2))

    if failed:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
