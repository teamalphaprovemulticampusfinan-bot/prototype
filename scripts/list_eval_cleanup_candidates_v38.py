from __future__ import annotations

import argparse
from pathlib import Path

LEGACY_PREFIXES = (
    "eval_monthly_2025_2026_v26",
    "eval_monthly_smoke_2025_01_v27",
    "eval_monthly_2025_2026_v27",
    "eval_monthly_2025_2026_v28",
    "eval_monthly_real_smoke_2025_01_v29",
    "eval_monthly_real_smoke_2025_01_v30",
    "eval_market_v32_nepes_2025_01",
    "eval_issue_v33_smoke_2025_01",
    "eval_tech_v34_smoke_2025_01",
    "eval_valuation_v35_nepes_2025_01",
    "eval_macro_v36_nepes_2025_01",
)

LEGACY_SCRIPT_NAMES = (
    "run_eval_history_real_pipeline_v30.py",
    "run_eval_history_range.py",
    "run_eval_history_range.ps1",
)


def main() -> int:
    ap = argparse.ArgumentParser(description="List old eval-history folders/scripts that can be archived after v38 works.")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--delete", action="store_true", help="Actually delete listed legacy output folders. Scripts are never deleted by this tool.")
    ns = ap.parse_args()
    root = Path.cwd().resolve()
    monthly_root = root / "data" / ns.field / "_sector_common" / "history_sheets_exports" / "monthly"
    print("[cleanup-v38] legacy monthly output candidates:")
    candidates = []
    for name in LEGACY_PREFIXES:
        p = monthly_root / name
        if p.exists():
            candidates.append(p)
            print(" -", p)
    if not candidates:
        print(" - none found")
    print("\n[cleanup-v38] keep the new structure under:")
    print(" -", monthly_root / "backtest")
    print("\n[cleanup-v38] old scripts you may archive after confirming v38 output:")
    for name in LEGACY_SCRIPT_NAMES:
        p = root / "scripts" / name
        print((" - EXISTS " if p.exists() else " - missing ") + str(p))
    if ns.delete:
        import shutil
        for p in candidates:
            shutil.rmtree(p)
            print("[deleted]", p)
    else:
        print("\nRun again with --delete only after opening the v38 Excel and confirming results.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
