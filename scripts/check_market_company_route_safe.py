from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for p in (str(ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

from data_intake.market_intake.config import TICKERS, CORP_CODES, resolve_company_key  # noqa: E402
from data_intake.market_intake.data_loader import (  # noqa: E402
    market_excel_dir,
    resolve_workbook_path,
    _decode_escaped_unicode,
    _normalize_company_token,
)


def main() -> int:
    company = sys.argv[1] if len(sys.argv) > 1 else "SFA 반도체"
    key = resolve_company_key(company)
    root = market_excel_dir()
    resolved = resolve_workbook_path(company=company)
    company_token = _normalize_company_token(company)

    candidates = []
    if root.exists():
        for p in sorted(root.glob("market_final_*.xlsx")):
            decoded_name = _decode_escaped_unicode(p.name)
            stem = _decode_escaped_unicode(p.stem)
            suffix = stem[len("market_final_"):] if stem.startswith("market_final_") else stem
            candidates.append({
                "file": str(p.relative_to(root)),
                "decoded_name": decoded_name,
                "company_suffix": suffix,
                "is_requested_company": _normalize_company_token(suffix) == company_token,
            })

    result = {
        "company_input": company,
        "resolved_company_key": key,
        "ticker_present": bool(TICKERS.get(company) or TICKERS.get(key)),
        "ticker_value_masked": "present" if (TICKERS.get(company) or TICKERS.get(key)) else "missing",
        "corp_code_present": bool(CORP_CODES.get(company) or CORP_CODES.get(key)),
        "corp_code_value_masked": "present" if (CORP_CODES.get(company) or CORP_CODES.get(key)) else "missing",
        "market_excel_dir": str(root),
        "resolved_workbook_path": str(resolved),
        "resolved_workbook_decoded_name": _decode_escaped_unicode(resolved.name),
        "wrong_nepes_workbook_guard": "OK" if "네패스" not in _decode_escaped_unicode(resolved.name) or _normalize_company_token(company) == _normalize_company_token("네패스") else "CHECK",
        "market_final_candidates": candidates[:50],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("No API key, token, or raw secret was printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
