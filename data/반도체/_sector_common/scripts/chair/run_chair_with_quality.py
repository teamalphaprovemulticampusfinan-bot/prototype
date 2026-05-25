# -*- coding: utf-8 -*-
"""
Run Chair Agent and then evaluate final report quality.

Example:
  python scripts\run_chair_with_quality.py --company-dir nepes --company "네패스"
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
import sys
ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_FOR_IMPORT / "src"))
from common.data_paths import chair_quality_dir


def _ensure_src_on_path() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Chair and Chair report quality evaluation.")
    parser.add_argument("--company-dir", required=True, help="Company slug directory, e.g. nepes")
    parser.add_argument("--company", required=True, help="Display company name, e.g. 네패스")
    parser.add_argument("--skip-chair", action="store_true", help="Only evaluate existing Chair report")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    _ensure_src_on_path()
    from common.output_paths import agent_output_path

    report_path = agent_output_path(args.company_dir, "chair", f"{args.company_dir}_chair_report.md", root=root)

    if not args.skip_chair:
        cmd = [
            sys.executable,
            "main.py",
            "chair",
            "--company-dir",
            args.company_dir,
            "--company",
            args.company,
        ]
        print("[Chair+Quality] Chair 실행:", " ".join(cmd))
        proc = subprocess.run(cmd, cwd=str(root), env=os.environ.copy())
        if proc.returncode != 0:
            print(f"[Chair+Quality] Chair 실행 실패: returncode={proc.returncode}")
            return proc.returncode

    _ensure_src_on_path()
    from chair_agent.report_quality import evaluate_chair_report

    result = evaluate_chair_report(
        report_path=report_path,
        company_dir=args.company_dir,
        company_name=args.company,
        output_root=root / "data",
        save=True,
    )
    print(f"[Chair+Quality] Quality status={result.status} score={result.total_score:.2f}/100")
    print(f"[Chair+Quality] Report: {report_path}")
    print(f"[Chair+Quality] Quality MD: {chair_quality_dir(args.company_dir) / 'chair_report_quality.md'}")
    return 0 if result.status in {"PASS", "REVIEW"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
