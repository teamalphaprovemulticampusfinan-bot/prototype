from __future__ import annotations

from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
required = [
    "finance_agent", "valuation_agent", "tech_agent", "market_agent", "issue_agent", "macro_agent",
    "chair_agent", "auditor_agent", "data_intake", "common", "evaluation",
]
missing = []
for name in required:
    p = ROOT / "src_eval" / name
    print(("[OK] " if p.exists() else "[MISSING] ") + str(p))
    if not p.exists():
        missing.append(name)

sys.path.insert(0, str(ROOT / "src_eval"))
sys.path.insert(1, str(ROOT / "src"))

from evaluation.output_schema import TEAM_OUTPUT_COLUMNS
print("[team_schema_last_column]", TEAM_OUTPUT_COLUMNS[-1])
if TEAM_OUTPUT_COLUMNS[-1] != "macro_weight":
    raise SystemExit("team schema must end at macro_weight")
if missing:
    raise SystemExit("missing src_eval folders: " + ", ".join(missing))
print("[OK] src_eval sibling layout is ready")
