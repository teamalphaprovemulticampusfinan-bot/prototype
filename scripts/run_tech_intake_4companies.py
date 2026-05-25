from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COMPANIES = [
    ("hanmi", "한미반도체"),
    ("hansol", "한솔케미칼"),
    ("duksan", "덕산테코피아"),
    ("ltc", "엘티씨"),
]


def run(cmd: list[str], continue_on_error: bool) -> int:
    print("\n" + "=" * 88)
    print(" ".join(cmd))
    print("=" * 88)
    proc = subprocess.run(cmd, cwd=str(ROOT), text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0 and not continue_on_error:
        raise SystemExit(proc.returncode)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Tech Intake for 4 companies")
    parser.add_argument("--max-patents", type=int, default=0)
    parser.add_argument("--sleep-sec", type=float, default=0.6)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--force-fetch", action="store_true")
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("--skip-agent", action="store_true")
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--only", action="append", default=[])
    args = parser.parse_args()

    targets = COMPANIES
    if args.only:
        only = set(args.only)
        targets = [x for x in COMPANIES if x[0] in only]

    rc = 0
    for slug, name in targets:
        cmd = [
            sys.executable,
            "main.py",
            "intake",
            "--company-dir",
            slug,
            "--company",
            name,
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
        code = run(cmd, continue_on_error=not args.stop_on_error)
        rc = rc or code
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
