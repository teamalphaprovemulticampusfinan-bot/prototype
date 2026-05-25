from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from market_agent.data_loader import (  # noqa: E402
    filter_by_cutoff,
    load_market_excel_csvs,
    load_workbook,
    market_excel_dir,
    resolve_workbook_path,
    summarize_market_excel_csv_dates,
)


def main() -> int:
    company = sys.argv[1] if len(sys.argv) >= 2 else "네패스"
    as_of_date = sys.argv[2] if len(sys.argv) >= 3 else ""

    workbook_path = resolve_workbook_path(company=company)
    workbook = load_workbook(company=company)
    csvs = load_market_excel_csvs(as_of_date=as_of_date)
    summary = summarize_market_excel_csv_dates(as_of_date=as_of_date)

    result = {
        "company": company,
        "market_excel_dir": str(market_excel_dir()),
        "resolved_workbook_path": str(workbook_path),
        "workbook_source_format": workbook.source_format,
        "csv_count": len(csvs),
        "csv_date_summary_first_20": summary[:20],
        "filter_by_cutoff_available": callable(filter_by_cutoff),
        "safe_note": "No API key, token, raw secret, or environment value was printed.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
