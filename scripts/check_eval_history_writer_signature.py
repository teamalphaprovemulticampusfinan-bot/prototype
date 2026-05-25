from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in [ROOT / "src_eval", ROOT / "src"]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

print("[sys.path first 5]")
for p in sys.path[:5]:
    print(" -", p)

for mod_name in ["common.agent_history", "common.google_sheets_history", "evaluation.sheets_writer"]:
    try:
        mod = __import__(mod_name, fromlist=["*"])
        print(f"\n[{mod_name}] file={getattr(mod, '__file__', '')}")
        if hasattr(mod, "save_run_result"):
            print("save_run_result signature:", inspect.signature(mod.save_run_result))
        if hasattr(mod, "save_eval_run_result"):
            print("save_eval_run_result signature:", inspect.signature(mod.save_eval_run_result))
    except Exception as exc:
        print(f"\n[{mod_name}] ERROR: {exc!r}")
