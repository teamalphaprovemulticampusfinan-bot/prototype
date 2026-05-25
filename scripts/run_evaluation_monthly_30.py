from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = project_root()
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from evaluation.monthly_eval import run_monthly_evaluation

    parser = argparse.ArgumentParser(
        description="월별 과거 평가용 objective local-file snapshots -> Google Sheets history -> Chair replay -> signal_df CSV 1개 생성"
    )
    parser.add_argument("--month", required=True, help="YYYY-MM, 예: 2025-01")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--universe-csv", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--run-id", default="", help="기존 run_id를 재사용하거나 직접 지정")
    parser.add_argument("--skip-chair", action="store_true", help="snapshot 저장과 source audit만 확인하고 Chair replay는 생략")
    parser.add_argument("--strict", action="store_true", help="Chair 실패 시 즉시 중단")

    args = parser.parse_args()

    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("ALPHAPROVE_HISTORY_BACKEND", "sheets")

    output_dir = args.output_dir or None
    out = run_monthly_evaluation(
        month=args.month,
        field=args.field,
        universe_csv=args.universe_csv,
        limit=args.limit or None,
        output_dir=output_dir,
        run_id=args.run_id or None,
        fail_open=not args.strict,
        skip_chair=args.skip_chair,
    )
    print(f"[DONE] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
