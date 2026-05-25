from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from data_intake.market_intake.sector_semiconductor import build_market_semiconductor_daily, load_latest_market_semiconductor_row


def _load_market_snapshot_function():
    module_path = SRC / "market_agent" / "sector_semiconductor.py"
    spec = importlib.util.spec_from_file_location("market_sector_semiconductor_direct", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load_market_semiconductor_snapshot


def main() -> int:
    result = build_market_semiconductor_daily(field="반도체", start_date="2021-01-01")
    latest = load_latest_market_semiconductor_row(field="반도체")
    load_market_semiconductor_snapshot = _load_market_snapshot_function()
    snapshot = load_market_semiconductor_snapshot(field="반도체")

    print("[Market semiconductor intake safe check]")
    print(json.dumps({
        "build": result,
        "latest_row_keys": list(latest.keys())[:30],
        "latest_row_date": latest.get("date"),
        "snapshot": snapshot,
    }, ensure_ascii=False, indent=2, default=str))
    print("No API key, token, or raw secret was printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
