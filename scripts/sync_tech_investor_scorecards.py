from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.data_paths import KNOWN_COMPANY_DIR_TO_NAME, company_slug
from tech_agent.investor_tech_view import apply_investor_tech_view_saved_files

DEFAULT_COMPANIES = [
    ("nepes", "네패스"),
    ("hanmi", "한미반도체"),
    ("hansol", "한솔케미칼"),
    ("duksan", "덕산테코피아"),
    ("ltc", "엘티씨"),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sync investor Tech scorecards into tech_chair_summary.json/md")
    p.add_argument("--all", action="store_true", help="Run for all semiconductor MVP companies")
    p.add_argument("--company-dir", default=None, help="Company slug, e.g. nepes")
    p.add_argument("--company", default=None, help="Company display name, e.g. 네패스")
    p.add_argument("--json", action="store_true", help="Print JSON result")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    targets = []
    if args.all:
        targets = DEFAULT_COMPANIES
    else:
        if not args.company_dir and not args.company:
            raise SystemExit("--all 또는 --company-dir/--company 중 하나를 지정하세요.")
        slug = company_slug(args.company_dir or args.company)
        company = args.company or KNOWN_COMPANY_DIR_TO_NAME.get(slug, slug)
        targets = [(slug, company)]

    results = []
    for slug, company in targets:
        print("=" * 80)
        print(f"[SYNC] Tech investor scorecard: {company} / {slug}")
        try:
            result = apply_investor_tech_view_saved_files(slug, company)
            score = ((result.get("scorecard") or {}).get("final_tech_investor_score"))
            grade = (((result.get("scorecard") or {}).get("final_tech_investor_grade") or {}).get("code"))
            print(f"[OK] score={score}, grade={grade}")
            for k, v in (result.get("output_files") or {}).items():
                print(f"  - {k}: {v}")
            results.append(result)
        except Exception as exc:
            print(f"[ERROR] {company}/{slug}: {exc}")
            results.append({"status": "ERROR", "company_slug": slug, "company_name": company, "error": str(exc)})

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))

    has_error = any(r.get("status") != "OK" for r in results)
    return 1 if has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
