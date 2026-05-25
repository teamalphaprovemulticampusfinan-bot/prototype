from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

def main() -> int:
    root = Path.cwd()
    checks = [
        root / "src" / "eval",
        root / "src" / "eval" / "finance_agent",
        root / "src" / "eval" / "valuation_agent",
        root / "src" / "eval" / "tech_agent",
        root / "src" / "eval" / "market_agent",
        root / "src" / "eval" / "issue_agent",
        root / "src" / "eval" / "macro_agent",
        root / "src" / "eval" / "chair_agent",
        root / "src" / "eval" / "auditor_agent",
        root / "src" / "eval" / "evaluation" / "history_runner.py",
    ]
    print("[sys.path first 5]")
    for p in sys.path[:5]:
        print(" -", p)
    ok = True
    print("\n[path checks]")
    for p in checks:
        exists = p.exists()
        print(f" - {exists!s:5} {p}")
        ok = ok and exists

    print("\n[import checks]")
    for mod in [
        "evaluation.history_runner",
        "evaluation.features_tech",
        "evaluation.features_valuation",
        "evaluation.features_macro",
        "evaluation.dma",
    ]:
        try:
            m = importlib.import_module(mod)
            print(f" - OK {mod}: {Path(m.__file__).resolve()}")
        except Exception as e:
            ok = False
            print(f" - FAIL {mod}: {e}")

    manifest = root / "src" / "eval" / "_eval_clone_manifest_v22.json"
    if manifest.exists():
        print("\n[manifest]")
        print(manifest.read_text(encoding="utf-8")[:1500])

    if ok:
        print("\n[OK] v22 evaluation clone is installed.")
        return 0
    print("\n[FAIL] v22 install check failed.")
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
