from __future__ import annotations

"""Run only the macro material collectors.

Usage from project root:
    python .\scripts\run_macro_material_probe.py

This is faster than full data intake and helps debug:
- FRED IP28 timeout
- SMM login/public-price availability
- USGS rare-earth / helium PDF parsing
- BLM helium page
- Helium news fallback
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_intake.macro_intake.material_collectors import run_material_probe  # noqa: E402


if __name__ == "__main__":
    result = run_material_probe()
    print("\n[MATERIAL PROBE DONE]")
    print(json.dumps(result, ensure_ascii=False, indent=2))
