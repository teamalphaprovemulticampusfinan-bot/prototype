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
    parser = argparse.ArgumentParser(
        description="기존 Google Sheets run_id 결과를 다시 읽어서 월별 signal_df CSV만 재생성합니다. Chair/Auditor를 재실행하지 않습니다."
    )
    parser.add_argument("--month", required=True, help="평가 월. 예: 2025-01")
    parser.add_argument("--run-id", required=True, help="기존 실행 run_id. 예: eval_month_2025-01_20260518_174543")
    parser.add_argument("--field", default="반도체")
    parser.add_argument(
        "--universe-csv",
        default=str(root / "data" / "반도체" / "_sector_common" / "universe" / "universe_30_semiconductor_20260514.csv"),
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output-dir", default="")
    args = parser.parse_args(argv)

    from evaluation.monthly_eval import export_monthly_signal_csv, parse_month, read_universe

    window = parse_month(args.month)
    targets = read_universe(args.universe_csv, field=args.field)
    if args.limit:
        targets = targets[: args.limit]
    if not targets:
        raise RuntimeError(f"universe CSV에서 대상을 찾지 못했습니다: {args.universe_csv}")

    out = export_monthly_signal_csv(
        targets=targets,
        window=window,
        run_id=args.run_id,
        output_dir=args.output_dir or None,
    )
    print(f"[DONE] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
