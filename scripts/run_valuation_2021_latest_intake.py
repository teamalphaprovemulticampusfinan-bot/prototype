from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.company_metadata import iter_company_metadata  # noqa: E402
from data_intake.valuation_intake.runner import run_valuation_intake  # noqa: E402


def today_kst() -> str:
    return (datetime.utcnow() + timedelta(hours=9)).date().isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Valuation Intake from 2021-01-01 to latest/cutoff date.")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-dir", default="")
    parser.add_argument("--company", default="")
    parser.add_argument("--all", action="store_true", help="Run all companies in universe/company.yaml metadata.")
    parser.add_argument("--start", default="2021-01-01")
    parser.add_argument("--end", default=today_kst())
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true")
    args = parser.parse_args()

    if args.all:
        metas = iter_company_metadata()
        if not metas:
            print("[valuation-auto] no company metadata found.")
            return 1
        failed: list[str] = []
        for idx, meta in enumerate(metas, start=1):
            print(f"\n[valuation-auto] {idx}/{len(metas)} {meta.name} ({meta.slug})")
            try:
                run_valuation_intake(
                    company_dir=meta.slug,
                    company=meta.name,
                    field=args.field,
                    years=args.years,
                    skip_network=args.skip_network,
                    continue_on_error=not args.stop_on_error,
                    start_date=args.start,
                    end_date=args.end,
                )
            except Exception as exc:
                failed.append(f"{meta.slug}: {exc}")
                print(f"[valuation-auto] FAILED {meta.slug}: {exc}")
                if args.stop_on_error:
                    raise
        if failed:
            print("\n[valuation-auto] completed with failures:")
            for msg in failed:
                print("  -", msg)
            return 2
        print("\n[valuation-auto] all companies completed.")
        return 0

    if not args.company_dir or not args.company:
        parser.error("single-company run requires --company-dir and --company, or use --all")

    run_valuation_intake(
        company_dir=args.company_dir,
        company=args.company,
        field=args.field,
        years=args.years,
        skip_network=args.skip_network,
        continue_on_error=not args.stop_on_error,
        start_date=args.start,
        end_date=args.end,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
