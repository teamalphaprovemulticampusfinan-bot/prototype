from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from common.company_metadata import get_company_metadata  # noqa: E402

CSV_PATH = ROOT / "data" / "반도체" / "_sector_common" / "universe" / "universe_30_semiconductor_20260514.csv"


def read_rows() -> list[dict[str, str]]:
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f) if str(r.get("include_in_evaluation", "1")).strip() == "1"]


def main() -> int:
    rows = read_rows()
    failures: list[dict[str, str]] = []

    for row in rows:
        slug = str(row["company_dir"]).strip()
        name = str(row["company_name"]).strip()
        code = str(row["stock_code"]).strip().zfill(6)

        meta = get_company_metadata(slug, name)
        ok = bool(meta and meta.slug == slug and meta.stock_code == code)

        print(json.dumps(
            {
                "query_slug": slug,
                "query_name": name,
                "expected_code": code,
                "resolved": None if meta is None else {
                    "slug": meta.slug,
                    "name": meta.name,
                    "stock_code": meta.stock_code,
                    "market": meta.market,
                    "yf_ticker": meta.yf_ticker,
                },
                "ok": ok,
            },
            ensure_ascii=False,
        ))

        if not ok:
            failures.append({
                "company_dir": slug,
                "company_name": name,
                "expected_code": code,
                "resolved": "" if meta is None else f"{meta.slug}/{meta.name}/{meta.stock_code}",
            })

    if failures:
        print("\n[FAILURES]", json.dumps(failures, ensure_ascii=False, indent=2))
        return 1

    print("\n[OK] all companies resolved exactly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
