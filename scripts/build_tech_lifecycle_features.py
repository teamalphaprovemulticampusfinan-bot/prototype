from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_intake.tech_intake.technology_lifecycle import build_technology_lifecycle_features


def main() -> int:
    parser = argparse.ArgumentParser(description="Build technology lifecycle features from KIPRIS patent trends and optional external lifecycle CSVs.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-dir", "--company-slug", dest="company_dir", default="nepes")
    parser.add_argument("--company", "--company-name", dest="company", default=None)
    parser.add_argument("--keywords", default=None, help="Optional comma-separated technology keywords. If omitted, semiconductor default dictionary is used.")
    parser.add_argument("--recent-window", type=int, default=3)
    parser.add_argument("--baseline-window", type=int, default=5)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    feature = build_technology_lifecycle_features(
        company_dir=args.company_dir,
        company=args.company,
        field=args.field,
        keywords=args.keywords,
        recent_window=max(1, args.recent_window),
        baseline_window=max(1, args.baseline_window),
        write=not args.no_write,
    )
    print(json.dumps({
        "status": feature.get("status"),
        "company": feature.get("company"),
        "overall_lifecycle_stage": feature.get("overall_lifecycle_stage"),
        "overall_lifecycle_score": feature.get("overall_lifecycle_score"),
        "source_patent_csv": feature.get("source_patent_csv"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
