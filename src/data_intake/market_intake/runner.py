from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from pprint import pprint
from typing import Any

from common.data_paths import company_agent_dir, rel_project_path

from .data_loader import load_workbook
from .exporter import save_csv
from .preprocess import build_company_row
from .sector_semiconductor import build_market_semiconductor_daily
from .sources import fetch_dart_subsidy, fetch_market_news, fetch_oecd, fetch_stock


def run_collection(companies: list[str]) -> Path:
    """Build legacy market_dataset.csv while preferring data/market_excel sources.

    The previous implementation loaded one Market_통합.xlsx before the loop.
    After market_issues.db/exporter creates per-company market_final_<company>.xlsx
    files under data/market_excel, we need to resolve the workbook per company so
    the intake does not fall back to data/반도체/_sector_common/source_data.
    """

    news_data = fetch_market_news()
    rows: list[dict[str, Any]] = []

    for company in companies:
        workbook = load_workbook(company=company)
        oecd_data = fetch_oecd(workbook)
        stock_data = fetch_stock(company)
        dart_data = fetch_dart_subsidy(company)

        row = build_company_row(
            company,
            stock_data,
            oecd_data,
            dart_data,
            news_data,
            workbook,
        )
        rows.append(row)

    return save_csv(rows)


# ---------------------------------------------------------------------
# AlphaProve unified data_intake wrapper
# ---------------------------------------------------------------------
def run_market_intake(
    company_dir: str,
    company: str | None = None,
    field: str = "반도체",
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    network_update: bool | None = None,
    **_: object,
) -> dict[str, Any]:
    """Run Market Intake and save a visible manifest.

    This wrapper does two things:
    1. Builds the new sector-level daily file
       data/market_excel/market_semiconductor_daily.csv from the four local
       market source groups requested by the user.
    2. Keeps the existing workbook/company collection path alive so the old
       Market_통합.xlsx logic and market_dataset.csv are not broken.

    The wrapper is intentionally fail-soft. If an external API call fails, the
    manifest records the error and market_agent can still read the local
    market_semiconductor_daily.csv and existing Excel/database sources.
    """

    started = datetime.now()
    start_date = start_date or os.getenv("MARKET_START_DATE") or "2021-01-01"
    end_date = end_date or os.getenv("MARKET_END_DATE") or os.getenv("MARKET_AS_OF_DATE") or os.getenv("ALPHAPROVE_DATA_CUTOFF_DATE")
    company_name = company or company_dir
    out_dir = company_agent_dir(company_dir, "market", create=True) / "intake"
    out_dir.mkdir(parents=True, exist_ok=True)

    status = "OK"
    errors: list[str] = []
    sector_daily: dict[str, Any] = {}
    collection_csv = ""

    try:
        sector_daily = build_market_semiconductor_daily(
            field=field,
            start_date=start_date,
            end_date=end_date,
            network_update=network_update,
        )
    except Exception as exc:
        status = "PARTIAL"
        errors.append(f"market_semiconductor_daily build failed: {exc}")

    try:
        collection_path = run_collection([company_name])
        collection_csv = rel_project_path(collection_path)
    except Exception as exc:
        status = "PARTIAL"
        errors.append(f"legacy market workbook collection failed: {exc}")

    manifest = {
        "agent": "market",
        "status": status,
        "started_at": started.isoformat(timespec="seconds"),
        "ended_at": datetime.now().isoformat(timespec="seconds"),
        "company_dir": company_dir,
        "company": company_name,
        "field": field,
        "start_date": start_date,
        "end_date": end_date,
        "market_semiconductor_daily": sector_daily,
        "legacy_collection_csv": collection_csv,
        "errors": errors,
        "principle": (
            "market_intake now runs before market_agent, mirrors sector market "
            "sources to data/market_excel, and builds market_semiconductor_daily.csv."
        ),
    }

    manifest_path = out_dir / "market_intake_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Market Intake] manifest 저장: {manifest_path}")
    if errors:
        for err in errors:
            print(f"[Market Intake] WARN: {err}")
    return manifest


def run_intake(company_dir: str, company: str | None = None, **kwargs: object) -> dict[str, Any]:
    return run_market_intake(company_dir=company_dir, company=company, **kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Market Intake")
    parser.add_argument("--company-dir", required=False)
    parser.add_argument("--company", required=False)
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--network-update", action="store_true", help="Enable best-effort yfinance refresh for external market indices")
    parser.add_argument("companies", nargs="*", help="Legacy positional companies")
    args = parser.parse_args(argv)

    if args.company_dir or args.company:
        result = run_market_intake(
            company_dir=args.company_dir or args.company or "market",
            company=args.company,
            field=args.field,
            start_date=args.start_date,
            end_date=args.end_date,
            network_update=args.network_update,
        )
        pprint(result)
        return 0

    if args.companies:
        output = run_collection(args.companies)
        print(f"[Market Intake] legacy collection csv: {output}")
        return 0

    result = build_market_semiconductor_daily(
        field=args.field,
        start_date=args.start_date,
        end_date=args.end_date,
        network_update=args.network_update,
    )
    pprint(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
