from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evaluation.cutoff_env import cutoff_audit_payload, month_windows


def main() -> int:
    ap = argparse.ArgumentParser(description="Print non-secret cutoff env preview for one/monthly range.")
    ap.add_argument("--as-of-date", default=None)
    ap.add_argument("--start", default="2025-01")
    ap.add_argument("--end", default="2026-05")
    ap.add_argument("--start-date", default="2021-01-01")
    ap.add_argument("--include-tech", action="store_true")
    ns = ap.parse_args()

    if ns.as_of_date:
        windows = [ns.as_of_date]
    else:
        windows = month_windows(ns.start, ns.end)
    payload = {
        "status": "OK",
        "windows": windows,
        "count": len(windows),
        "first": cutoff_audit_payload(windows[0], start_date=ns.start_date, include_tech=ns.include_tech) if windows else {},
        "last": cutoff_audit_payload(windows[-1], start_date=ns.start_date, include_tech=ns.include_tech) if windows else {},
        "note": "No API key, token, raw URL, or secret is printed.",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
