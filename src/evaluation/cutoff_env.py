from __future__ import annotations

import os
import re
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any


def parse_date_like(value: Any, *, end_of_month: bool = True) -> date:
    """Parse YYYY-MM, YYYY-MM-DD, YYYYMMDD, or YYYY into a date."""
    text = str(value or "").strip()
    if not text:
        raise ValueError("empty date value")
    text = text.replace(".", "-").replace("/", "-")
    if "T" in text:
        text = text.split("T", 1)[0]
    if " " in text:
        text = text.split(" ", 1)[0]

    if re.fullmatch(r"\d{8}", text):
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    if re.fullmatch(r"\d{6}", text):
        y, m = int(text[:4]), int(text[4:6])
        return date(y, m, monthrange(y, m)[1] if end_of_month else 1)
    if re.fullmatch(r"\d{4}", text):
        y = int(text)
        return date(y, 12, 31) if end_of_month else date(y, 1, 1)
    if re.fullmatch(r"\d{4}-\d{1,2}", text):
        y, m = map(int, text.split("-"))
        return date(y, m, monthrange(y, m)[1] if end_of_month else 1)
    return datetime.strptime(text[:10], "%Y-%m-%d").date()


def month_windows(start: str, end: str, *, cap_last_to_end: bool = True) -> list[str]:
    """Return monthly as-of dates.

    For completed months this returns month-end.  When the final end date is
    inside the current month, the final window is capped to that end date so a
    run like end=2026-05-25 does not fabricate 2026-05-31.
    """
    start_d = parse_date_like(start, end_of_month=False)
    end_d = parse_date_like(end, end_of_month=True)
    y, m = start_d.year, start_d.month
    out: list[str] = []
    while True:
        last = date(y, m, monthrange(y, m)[1])
        as_of = min(last, end_d) if cap_last_to_end and (y, m) == (end_d.year, end_d.month) else last
        if as_of >= start_d and as_of <= end_d:
            out.append(as_of.isoformat())
        if (y, m) >= (end_d.year, end_d.month):
            break
        m += 1
        if m == 13:
            y += 1
            m = 1
    return out


def next_month_yyyy_mm(as_of_date: str | date) -> str:
    d = parse_date_like(as_of_date) if not isinstance(as_of_date, date) else as_of_date
    if d.month == 12:
        return f"{d.year + 1:04d}-01"
    return f"{d.year:04d}-{d.month + 1:02d}"


def next_day_yyyymmdd(as_of_date: str | date) -> str:
    d = parse_date_like(as_of_date) if not isinstance(as_of_date, date) else as_of_date
    return (d + timedelta(days=1)).strftime("%Y%m%d")


def build_cutoff_env(
    as_of_date: str,
    *,
    start_date: str = "2021-01-01",
    include_tech: bool = False,
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build environment variables for one no-look-ahead backtest window.

    as_of_date is inclusive.  For example, 2025-01-31 keeps data up to
    2025-01-31 and removes 2025-02-01 onward.
    """
    d = parse_date_like(as_of_date)
    asof = d.isoformat()
    exclusive_month = next_month_yyyy_mm(d)
    macro_exclusive = next_day_yyyymmdd(d)

    env = dict(base_env or os.environ)
    env.update({
        "ALPHAPROVE_DATA_CUTOFF_DATE": asof,
        "BACKTEST_AS_OF_DATE": asof,
        "EVAL_AS_OF_DATE": asof,
        "ALPHAPROVE_EVAL_HISTORY": "1",
        "ALPHAPROVE_HISTORY_BACKEND": "local",
        "ALPHAPROVE_DISABLE_GOOGLE_SHEETS": "1",
        "CHAIR_FORCE_LOCAL_OUTPUT": "1",
        "ALPHAPROVE_CHAIR_OUTPUT_BACKEND": "local",

        "MARKET_START_DATE": start_date,
        "MARKET_AS_OF_DATE": asof,
        "MARKET_END_DATE": asof,

        "ISSUE_START_DATE": start_date,
        "ISSUE_AS_OF_DATE": asof,
        "ISSUE_END_DATE": asof,

        "MACRO_START_DATE": start_date,
        "MACRO_AS_OF_DATE": asof,
        "MACRO_END_DATE": asof,
        # macro loader uses date < cutoff, so use next day.
        "MACRO_CUTOFF_DATE": macro_exclusive,
        "MACRO_CUTOFF_EXCLUSIVE_DATE": macro_exclusive,

        "FINANCE_START_DATE": start_date,
        "FINANCE_STOCK_START_DATE": start_date,
        "FINANCE_AS_OF_DATE": asof,
        "FINANCE_END_DATE": asof,
        "FINANCE_CUTOFF_YEAR": str(d.year),
        "FINANCE_STOCK_CUTOFF_DATE": asof,
        "FINANCE_STOCK_EXCLUSIVE_MONTH": exclusive_month,

        "VALUATION_START_DATE": start_date,
        "VALUATION_AS_OF_DATE": asof,
        "VALUATION_END_DATE": asof,
        "VALUATION_CUTOFF_YEAR": str(d.year),
        "VALUATION_PRICE_CUTOFF_DATE": asof,
        "VALUATION_PRICE_EXCLUSIVE_MONTH": exclusive_month,
    })

    # Tech is intentionally not cut off by default because the current project
    # keeps Tech/IP evidence outside this monthly look-ahead automation.
    if include_tech:
        env.update({
            "TECH_START_DATE": start_date,
            "TECH_AS_OF_DATE": asof,
            "TECH_END_DATE": asof,
        })
    else:
        for key in ("TECH_START_DATE", "TECH_AS_OF_DATE", "TECH_END_DATE"):
            env.pop(key, None)

    return env


def cutoff_audit_payload(as_of_date: str, *, start_date: str = "2021-01-01", include_tech: bool = False) -> dict[str, str]:
    env = build_cutoff_env(as_of_date, start_date=start_date, include_tech=include_tech, base_env={})
    keys = [
        "ALPHAPROVE_DATA_CUTOFF_DATE",
        "MARKET_AS_OF_DATE",
        "ISSUE_AS_OF_DATE",
        "MACRO_AS_OF_DATE",
        "MACRO_CUTOFF_DATE",
        "FINANCE_AS_OF_DATE",
        "FINANCE_CUTOFF_YEAR",
        "FINANCE_STOCK_CUTOFF_DATE",
        "VALUATION_AS_OF_DATE",
        "VALUATION_CUTOFF_YEAR",
        "VALUATION_PRICE_CUTOFF_DATE",
    ]
    if include_tech:
        keys.extend(["TECH_AS_OF_DATE", "TECH_END_DATE"])
    return {k: env[k] for k in keys if k in env}
