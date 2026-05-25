from __future__ import annotations

import json
from pathlib import Path

REQUIRED = [
    "valuation_credit_ml_overlay_candidate.csv",
    "valuation_credit_ml_overlay.json",
    "ml_quality_summary.csv",
]
OPTIONAL = ["valuation_credit_ml_outputs.xlsx"]

ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIRS = [
    ROOT / "data" / "반도체" / "_sector_common" / "ml_universe",
    ROOT / "src" / "auditor_agent" / "resources",
    ROOT / "workspace" / "ml_universe",
    ROOT / "workspace" / "outputs",
]


def find_file(name: str) -> Path | None:
    for d in SEARCH_DIRS:
        p = d / name
        if p.exists():
            return p
    return None


def main() -> int:
    print("[ML Assets] checking valuation/credit/tech universe artifacts")
    ok = True
    for name in REQUIRED:
        p = find_file(name)
        if p:
            print(f"[OK] {name}: {p}")
            if name.endswith(".json"):
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    print(f"     row_count={data.get('row_count')}, records={len(data.get('records', []))}")
                except Exception as exc:
                    print(f"[WARN] JSON read failed: {exc}")
        else:
            ok = False
            print(f"[MISSING] {name}")
    for name in OPTIONAL:
        p = find_file(name)
        print(f"[OPTIONAL {'OK' if p else 'MISSING'}] {name}: {p or ''}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
