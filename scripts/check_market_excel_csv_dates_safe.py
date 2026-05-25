from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
for p in (str(PROJECT_ROOT), str(SRC_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from market_agent.data_loader import summarize_market_excel_csv_dates


def main() -> int:
    as_of = sys.argv[1] if len(sys.argv) > 1 else os.getenv("MARKET_AS_OF_DATE", "")
    rows = summarize_market_excel_csv_dates(as_of_date=as_of)
    result = {
        "market_excel_dir": str(PROJECT_ROOT / "data" / "market_excel"),
        "as_of_date": as_of or None,
        "csv_count": len(rows),
        "date_detected_count": sum(1 for r in rows if r.get("date_column")),
        "no_date_column_count": sum(1 for r in rows if r.get("status") == "NO_DATE_COLUMN"),
        "files": rows,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("No API key, token, or raw secret was printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
