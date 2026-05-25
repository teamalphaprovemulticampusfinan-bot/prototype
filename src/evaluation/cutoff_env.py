from __future__ import annotations

import os
import re
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any


def _parse_date_like(value: str | date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}", text):
        y, m = map(int, text.split("-"))
        return date(y, m, monthrange(y, m)[1])
    if re.fullmatch(r"\d{6}", text):
        y, m = int(text[:4]), int(text[4:6])
        return date(y, m, monthrange(y, m)[1])
    if re.fullmatch(r"\d{8}", text):
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    return datetime.strptime(text[:10], "%Y-%m-%d").date()


def _exclusive_next_day(d: date) -> str:
    return (d + timedelta(days=1)).strftime("%Y%m%d")


def _previous_available_financial_year(as_of: date) -> int:
    """Return a conservative accounting-year cutoff for backtests.

    Agent price/news/macro rows can be cut at the exact as-of date.  Annual
    financial statement rows usually only carry a fiscal year, not a filing
    timestamp.  To avoid look-ahead leakage, monthly backtests use the previous
    fiscal year as the default financial cutoff.  Example: an as-of date in
    2025 uses financial rows through 2024; an as-of date in 2026 uses rows
    through 2025.
    """
    return int(as_of.year - 1)


def build_cutoff_env(
    as_of_date: str | date | datetime,
    *,
    start_date: str = "2021-01-01",
    include_tech: bool = False,
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build no-look-ahead environment variables for a monthly pipeline run.

    For a 2025-01 window, dated market/issue/macro/stock/valuation-price inputs
    are limited to <= 2025-01-31.  Annual financial inputs are limited to the
    previous available fiscal year by default because year-only CSV rows do not
    encode exact disclosure dates.
    """
    env = dict(base_env or os.environ)
    asof = _parse_date_like(as_of_date)
    asof_iso = asof.isoformat()
    cutoff_exclusive = _exclusive_next_day(asof)
    fin_year = _previous_available_financial_year(asof)

    # Global coordination key used by several agents.
    env["ALPHAPROVE_DATA_CUTOFF_DATE"] = asof_iso
    env["ALPHAPROVE_AS_OF_DATE"] = asof_iso

    # Market Agent and Market Intake.
    env["MARKET_START_DATE"] = start_date
    env["MARKET_AS_OF_DATE"] = asof_iso
    env["MARKET_END_DATE"] = asof_iso

    # Issue Agent and Issue Intake.
    env["ISSUE_START_DATE"] = start_date
    env["ISSUE_AS_OF_DATE"] = asof_iso
    env["ISSUE_END_DATE"] = asof_iso

    # Macro Agent.  macro_agent.loader keeps date < cutoff, so use next day.
    env["MACRO_START_DATE"] = start_date
    env["MACRO_AS_OF_DATE"] = asof_iso
    env["MACRO_END_DATE"] = asof_iso
    env["MACRO_CUTOFF_DATE"] = cutoff_exclusive
    env["MACRO_CUTOFF_EXCLUSIVE_DATE"] = cutoff_exclusive

    # Finance Agent and Finance Intake.
    env["FINANCE_START_DATE"] = start_date
    env["FINANCE_AS_OF_DATE"] = asof_iso
    env["FINANCE_END_DATE"] = asof_iso
    env["FINANCE_CUTOFF_YEAR"] = str(fin_year)
    env["FINANCE_FINANCIAL_START_YEAR"] = start_date[:4]
    env["FINANCE_FINANCIAL_END_YEAR"] = str(fin_year)
    env["FINANCE_STOCK_START_DATE"] = start_date
    env["FINANCE_STOCK_CUTOFF_DATE"] = asof_iso
    env["FINANCE_PRICE_CUTOFF_DATE"] = asof_iso

    # Valuation Agent and Valuation Intake.
    env["VALUATION_START_DATE"] = start_date
    env["VALUATION_AS_OF_DATE"] = asof_iso
    env["VALUATION_END_DATE"] = asof_iso
    env["VALUATION_CUTOFF_YEAR"] = str(fin_year)
    env["VALUATION_PRICE_CUTOFF_DATE"] = asof_iso
    env["VALUATION_PRICE_END_DATE"] = asof_iso

    # Tech intentionally has no cutoff by default, per the project policy.
    if include_tech:
        env["TECH_AS_OF_DATE"] = asof_iso
        env["TECH_END_DATE"] = asof_iso
    else:
        for key in ("TECH_AS_OF_DATE", "TECH_END_DATE"):
            env.pop(key, None)

    return env


def cutoff_audit_payload(
    as_of_date: str | date | datetime,
    *,
    start_date: str = "2021-01-01",
    include_tech: bool = False,
) -> dict[str, str]:
    env = build_cutoff_env(as_of_date, start_date=start_date, include_tech=include_tech, base_env={})
    keys = [
        "ALPHAPROVE_DATA_CUTOFF_DATE",
        "MARKET_START_DATE",
        "MARKET_AS_OF_DATE",
        "MARKET_END_DATE",
        "ISSUE_START_DATE",
        "ISSUE_AS_OF_DATE",
        "ISSUE_END_DATE",
        "MACRO_START_DATE",
        "MACRO_AS_OF_DATE",
        "MACRO_END_DATE",
        "MACRO_CUTOFF_DATE",
        "FINANCE_START_DATE",
        "FINANCE_AS_OF_DATE",
        "FINANCE_CUTOFF_YEAR",
        "FINANCE_STOCK_START_DATE",
        "FINANCE_STOCK_CUTOFF_DATE",
        "VALUATION_START_DATE",
        "VALUATION_AS_OF_DATE",
        "VALUATION_CUTOFF_YEAR",
        "VALUATION_PRICE_CUTOFF_DATE",
    ]
    if include_tech:
        keys.extend(["TECH_AS_OF_DATE", "TECH_END_DATE"])
    return {k: env[k] for k in keys if k in env}


def month_windows(start: str, end: str | None = None) -> list[str]:
    start_d = _parse_date_like(start)
    end_d = _parse_date_like(end or datetime.now().strftime("%Y-%m-%d"))

    y, m = start_d.year, start_d.month
    out: list[str] = []
    while True:
        last = date(y, m, monthrange(y, m)[1])
        if last >= start_d and last <= end_d:
            out.append(last.isoformat())
        if (y, m) >= (end_d.year, end_d.month):
            break
        m += 1
        if m == 13:
            y += 1
            m = 1
    return out
