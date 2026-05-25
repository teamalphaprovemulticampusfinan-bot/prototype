from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
SRC = ROOT_FOR_IMPORT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_intake.tech_intake.excel_frame import build_sector_quantified_metrics

ROOT = ROOT_FOR_IMPORT
PYTHON = sys.executable

COMPANIES = [
    ("nepes", "네패스"),
    ("hanmi", "한미반도체"),
    ("hansol", "한솔케미칼"),
    ("duksan", "덕산테코피아"),
    ("ltc", "엘티씨"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Tech Intake for 5 semiconductor companies.")
    parser.add_argument("--max-patents", type=int, default=0)
    parser.add_argument("--sleep-sec", type=float, default=0.6)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--force-fetch", action="store_true")
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("--skip-agent", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true")
    args = parser.parse_args()

    targets = COMPANIES
    if args.only:
        only = {x.strip() for x in args.only if x.strip()}
        targets = [x for x in COMPANIES if x[0] in only or x[1] in only]

    failed = []
    for slug, company in targets:
        print("=" * 100)
        print(f"[RUN] Tech Intake: {company} / {slug}")
        print("=" * 100)
        cmd = [
            PYTHON,
            str(ROOT / "main.py"),
            "intake",
            "--company-dir",
            slug,
            "--company",
            company,
            "--agents",
            "tech",
            "--tech-max-patents",
            str(args.max_patents),
            "--tech-sleep-sec",
            str(args.sleep_sec),
            "--tech-timeout",
            str(args.timeout),
        ]
        if args.force_fetch:
            cmd.append("--tech-force-fetch")
        if args.skip_network:
            cmd.append("--tech-skip-network")
        if args.skip_agent:
            cmd.append("--tech-skip-agent")
        if args.stop_on_error:
            cmd.append("--stop-on-error")

        proc = subprocess.run(cmd, cwd=str(ROOT))
        if proc.returncode != 0:
            failed.append((slug, proc.returncode))
            if args.stop_on_error:
                break

    print("=" * 100)
    print("[SUMMARY]")
    try:
        agg = build_sector_quantified_metrics(
            field="반도체",
            companies=[slug for slug, _ in targets],
        )
        print(f"[AGGREGATE] quantified metrics: {agg.get('status')} rows={agg.get('row_count')} -> {agg.get('output_csv')}")
    except Exception as exc:
        print(f"[AGGREGATE] WARN failed to merge quantified metrics: {exc}")

    if failed:
        print("FAILED:", failed)
        return 1
    print("ALL DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
