from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _bootstrap_paths() -> Path:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    for p in (root, src):
        sp = str(p)
        if sp not in sys.path:
            sys.path.insert(0, sp)
    os.environ["PYTHONPATH"] = str(src)
    return root


def main(argv: list[str] | None = None) -> int:
    root = _bootstrap_paths()

    from evaluation.daily_eval import run_daily_evaluation

    parser = argparse.ArgumentParser(description="AlphaProve 일별 historical evaluation 실행")
    parser.add_argument("--start-date", required=True, help="시작일. 예: 2025-01-01")
    parser.add_argument("--end-date", required=True, help="종료일. 예: 2025-01-31")
    parser.add_argument("--field", default="반도체")
    parser.add_argument(
        "--universe-csv",
        default=str(root / "data" / "반도체" / "_sector_common" / "universe" / "universe_30_semiconductor_20260514.csv"),
    )
    parser.add_argument("--limit", type=int, default=0, help="테스트용 기업 수 제한")
    parser.add_argument("--date-limit", type=int, default=0, help="테스트용 날짜 수 제한")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--strict-auditor", action="store_true")
    parser.add_argument("--skip-chair", action="store_true")

    args = parser.parse_args(argv)

    out = run_daily_evaluation(
        start_date=args.start_date,
        end_date=args.end_date,
        universe_csv=args.universe_csv,
        field=args.field,
        limit=args.limit or None,
        date_limit=args.date_limit or None,
        run_id=args.run_id or None,
        output_dir=args.output_dir or None,
        fail_open=not args.strict_auditor,
        skip_chair=args.skip_chair,
    )
    print(f"\n[DONE] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
