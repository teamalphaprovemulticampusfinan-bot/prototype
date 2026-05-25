from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tech_agent.ml_signal import build_tech_ml_signal


DEFAULT_COMPANIES = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "LTC",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Tech ML signal builder.")
    parser.add_argument("--company-dir", default="", help="company slug, e.g. nepes")
    parser.add_argument("--company", default="", help="display company name")
    parser.add_argument("--all", action="store_true", help="run all default companies")
    args = parser.parse_args()

    if args.all:
        for company_dir, company in DEFAULT_COMPANIES.items():
            print("=" * 80)
            print(f"[Tech ML] 실행: {company} ({company_dir})")
            print("=" * 80)
            build_tech_ml_signal(company_dir=company_dir, company=company)
        return 0

    if not args.company_dir:
        print("[오류] --company-dir 또는 --all 중 하나를 지정하세요.")
        return 1

    company = args.company or DEFAULT_COMPANIES.get(args.company_dir, args.company_dir)
    build_tech_ml_signal(company_dir=args.company_dir, company=company)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())