from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

COMPANIES = [
    ("nepes", "네패스"),
    ("hanmi", "한미반도체"),
    ("hansol", "한솔케미칼"),
    ("duksan", "덕산테코피아"),
    ("ltc", "엘티씨"),
]


def run(cmd: list[str]) -> int:
    print("\n$ " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=PROJECT_ROOT)
    return int(proc.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run Valuation Intake + Valuation Agent for focal semiconductor companies")
    ap.add_argument("--skip-network", action="store_true", help="Use cached intake where possible; do not call live APIs")
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--company-dir", action="append", help="Optional subset slug. Repeatable.")
    args = ap.parse_args()

    selected = [c for c in COMPANIES if not args.company_dir or c[0] in set(args.company_dir)]
    failed: list[str] = []

    for slug, name in selected:
        base = [sys.executable, "main.py"]
        intake = base + ["valuation-intake", "--company-dir", slug, "--company", name, "--years", str(args.years)]
        if args.skip_network:
            intake.append("--skip-network")
        agent = base + ["valuation", "--company-dir", slug, "--company", name]
        if args.skip_network:
            agent.append("--skip-network")
        check = [sys.executable, "scripts/check_valuation_outputs.py", "--company-dir", slug, "--company", name]

        rc1 = run(intake)
        rc2 = run(agent) if rc1 == 0 else rc1
        rc3 = run(check) if rc2 == 0 else rc2
        if rc1 or rc2 or rc3:
            failed.append(slug)

    if failed:
        print("\n[VALUATION COMPANIES] FAIL:", ", ".join(failed))
        return 1
    print("\n[VALUATION COMPANIES] ALL DONE / CHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
