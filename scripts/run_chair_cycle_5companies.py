from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    slug: str
    name: str


COMPANIES = [
    Company("nepes", "네패스"),
    Company("hanmi", "한미반도체"),
    Company("hansol", "한솔케미칼"),
    Company("duksan", "덕산테코피아"),
    Company("ltc", "엘티씨"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Chair full cycle for 5 semiconductor companies.")
    parser.add_argument("--only", action="append", default=[], help="Run only selected company-dir. Can repeat.")
    parser.add_argument("--no-intake", action="store_true", help="Pass --no-intake to chair.")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue even if one company fails.")
    args = parser.parse_args()

    selected = set(args.only or [])
    targets = [c for c in COMPANIES if not selected or c.slug in selected]

    if not targets:
        print(f"[ERROR] No matching companies for --only={sorted(selected)}")
        return 2

    failures: list[tuple[str, int]] = []

    for company in targets:
        cmd = [
            sys.executable,
            "main.py",
            "chair",
            "--company-dir",
            company.slug,
            "--company",
            company.name,
        ]
        if args.no_intake:
            cmd.append("--no-intake")

        print("=" * 100)
        print(f"[Chair Cycle] {company.name} / {company.slug}")
        print(" ".join(cmd))
        print("=" * 100)

        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            failures.append((company.slug, proc.returncode))
            print(f"[FAIL] {company.slug}: returncode={proc.returncode}")
            if not args.continue_on_error:
                return proc.returncode

    if failures:
        print("[DONE WITH FAILURES]")
        for slug, code in failures:
            print(f"  - {slug}: {code}")
        return 1

    print("[ALL DONE] Chair full cycle completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
