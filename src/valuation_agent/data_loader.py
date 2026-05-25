from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
import os
import re

from common.data_paths import company_agent_dir

from .schemas import ValuationContext
from .utils import read_csv, read_json, to_float


PRICE_CANONICAL = "valuation_price_history.csv"
EVAL_PRICE_HISTORY = "eval_price_history_v45.csv"

COMPANY_INTAKE_FILE_NAMES = (
    EVAL_PRICE_HISTORY,
    "valuation_market_snapshot.csv",
    PRICE_CANONICAL,
    "valuation_raw_dart_accounts.csv",
    "valuation_share_count.csv",
)

SECTOR_COMMON_FILE_NAMES = (
    "sector_growth_assumptions.csv",
    "semiconductor_peer_multiples.csv",
    "wacc_assumptions.csv",
)

# Valuation data cutoff env order.
# Explicit function argument has first priority, then valuation-specific envs,
# then the global AlphaProve cutoff used by daily/backtest runs.
_CUTOFF_ENV_KEYS = (
    "VALUATION_AS_OF_DATE",
    "VALUATION_END_DATE",
    "ALPHAPROVE_DATA_CUTOFF_DATE",
    "EVAL_AS_OF_DATE",
    "AS_OF_DATE",
    "DATA_CUTOFF_DATE",
)

_DATE_COLUMN_CANDIDATES = (
    "date",
    "Date",
    "날짜",
    "일자",
    "기준일",
    "공시일",
    "trading_date",
    "as_of_date",
    "base_date",
    "period_end",
    "price_end",
    "latest_date",
    "timestamp",
)

_YEAR_COLUMN_CANDIDATES = (
    "year",
    "Year",
    "사업연도",
    "연도",
    "fiscal_year",
    "bsns_year",
    "회계연도",
)


def valuation_dir(company_dir: str) -> Path:
    return company_agent_dir(company_dir, "valuation", create=True)


def intake_dir(company_dir: str) -> Path:
    path = valuation_dir(company_dir) / "intake"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sector_valuation_dir(company_dir: str) -> Path:
    path = valuation_dir(company_dir).parents[1] / "_sector_common" / "valuation"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _project_root() -> Path:
    # src/valuation_agent/data_loader.py -> project root is parents[2]
    return Path(__file__).resolve().parents[2]


def _resolve_rel_path(value: Any) -> Path | None:
    if not value:
        return None
    text = str(value).strip().strip('"').strip("'")
    if not text:
        return None
    p = Path(text)
    if p.is_absolute():
        return p
    return _project_root() / p


def _read_csv_first_existing(paths: list[Path | None]) -> tuple[list[dict[str, Any]], Path | None]:
    for p in paths:
        if p is None:
            continue
        try:
            if p.exists() and p.is_file():
                rows = read_csv(p)
                if rows:
                    return rows, p
        except Exception:
            continue
    return [], None


def _read_csv_last_existing(paths: list[Path | None]) -> tuple[dict[str, Any], Path | None]:
    rows, used = _read_csv_first_existing(paths)
    if not rows:
        return {}, used
    return dict(rows[-1]), used


def _find_price_csv(i: Path, source_map: dict[str, Any]) -> tuple[list[dict[str, Any]], Path | None]:

    files = source_map.get("files") if isinstance(source_map, dict) else {}
    candidates: list[Path | None] = [
        i / PRICE_CANONICAL,
        _resolve_rel_path(files.get("price_history_csv") if isinstance(files, dict) else None),
        i / EVAL_PRICE_HISTORY,
        _resolve_rel_path(files.get("eval_price_history_v45_csv") if isinstance(files, dict) else None),
        i / "valuation_stock_prices.csv",
        i / "price_history.csv",
    ]
    # Last-resort scan inside valuation/intake only.  Do not scan finance_agent folders.
    for pattern in ["*price*history*.csv", "*price*.csv", "*주가*.csv"]:
        try:
            candidates.extend(sorted(i.glob(pattern)))
        except Exception:
            pass
    rows, used = _read_csv_first_existing(candidates)
    if not rows:
        return [], used
    return _normalize_price_rows(rows), used


def _normalize_price_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aliases = {
        "일자": "date", "날짜": "date", "Date": "date",
        "시가": "open", "Open": "open",
        "고가": "high", "High": "high",
        "저가": "low", "Low": "low",
        "종가": "close", "Close": "close",
        "수정종가": "adj_close", "Adj Close": "adj_close", "Adj_Close": "adj_close",
        "거래량": "volume", "Volume": "volume",
        "일수익률": "daily_return", "Daily Return": "daily_return",
        "드로다운": "drawdown", "MDD": "drawdown",
        "20일선": "ma20", "60일선": "ma60", "120일선": "ma120",
        "출처": "source", "티커": "ticker",
    }
    out: list[dict[str, Any]] = []
    for r in rows:
        nr: dict[str, Any] = {}
        for k, v in r.items():
            key = aliases.get(k, k)
            nr[key] = v
        if nr.get("date") is None and nr.get("index") is not None:
            nr["date"] = nr.get("index")
        # Coerce numeric columns. Keep strings for source/ticker.
        for key in [
            "open", "high", "low", "close", "adj_close", "volume", "daily_return", "drawdown",
            "ma20", "ma60", "ma120", "rolling_vol_20", "rolling_vol_60", "return_20d", "return_60d",
            "return_120d", "distance_to_ma20", "distance_to_ma60", "distance_to_ma120", "price_to_52w_high",
            "price_to_52w_low", "rolling_high_52w", "rolling_low_52w", "shares_outstanding", "market_cap",
            "trading_value", "trading_value_ma20", "turnover_ratio",
        ]:
            if key in nr:
                nr[key] = to_float(nr.get(key))
        if nr.get("close") is not None or nr.get("date") is not None:
            out.append(nr)
    out.sort(key=lambda x: str(x.get("date") or ""))
    return out


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip().lower() in {"", "none", "nan", "null", "na", "n/a"}


def _read_market_snapshot(i: Path, source_map: dict[str, Any], cutoff: date | None) -> tuple[dict[str, Any], dict[str, str]]:
    files = source_map.get("files") if isinstance(source_map, dict) else {}
    json_candidates = [
        i / "valuation_market_snapshot.json",
        _resolve_rel_path(files.get("market_snapshot_json") if isinstance(files, dict) else None),
    ]
    csv_candidates = [
        i / "valuation_market_snapshot.csv",
        _resolve_rel_path(files.get("market_snapshot_csv") if isinstance(files, dict) else None),
    ]
    snapshot: dict[str, Any] = {}
    loaded: dict[str, str] = {}
    for p in json_candidates:
        if p is None:
            continue
        obj = read_json(p, {}) or {}
        if isinstance(obj, dict) and obj:
            date_key = _find_existing_key(obj, _DATE_COLUMN_CANDIDATES)
            row_date = _parse_row_date(obj.get(date_key)) if date_key else None
            if row_date is None or cutoff is None or row_date <= cutoff:
                snapshot.update(obj)
                loaded["market_snapshot_json"] = str(p)
            break
    csv_rows, csv_path = _read_csv_first_existing(csv_candidates)
    csv_rows = _filter_rows_by_cutoff(csv_rows, cutoff)
    csv_row = dict(csv_rows[-1]) if csv_rows else {}
    if csv_row:
        for key, value in csv_row.items():
            if key not in snapshot or _is_blank(snapshot.get(key)):
                snapshot[key] = value
        if csv_path:
            loaded["market_snapshot_csv"] = str(csv_path)
    return snapshot, loaded


def _synthetic_price_row_from_summary(price_summary: dict[str, Any]) -> list[dict[str, Any]]:

    if not isinstance(price_summary, dict):
        return []
    latest_close = to_float(price_summary.get("latest_close"))
    if latest_close is None:
        return []
    return [{
        "date": price_summary.get("price_end") or price_summary.get("latest_date") or "summary_only",
        "open": None,
        "high": price_summary.get("high_52w"),
        "low": price_summary.get("low_52w"),
        "close": latest_close,
        "adj_close": latest_close,
        "volume": None,
        "daily_return": None,
        "drawdown": price_summary.get("mdd"),
        "ma20": None,
        "ma60": None,
        "ma120": None,
        "source": "valuation_price_summary_json_only",
        "ticker": None,
        "data_quality_note": "원천 주가 CSV가 없어 summary JSON의 최신가만 표시",
    }]


def _strip_text(value: Any) -> str:
    return str(value or "").strip().strip('"').strip("'")


def _infer_company_name_from_path(path: str | Path) -> str:
    p = Path(path)
    if p.parent.name == "intake" and p.parent.parent.parent.name:
        return p.parent.parent.parent.name
    if p.parent.parent.name:
        return p.parent.parent.name
    if p.parent.name:
        return p.parent.name
    return p.stem or "unknown_company"


def _last_day_of_month(year: int, month: int) -> date:
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def _parse_cutoff_date(value: Any) -> date | None:
    """Parse an as-of/cutoff value.

    Supported examples:
    - 2025        -> 2025-12-31
    - 2025-06     -> 2025-06-30
    - 2025-06-15  -> 2025-06-15
    - 20250615    -> 2025-06-15
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = _strip_text(value)
    if not text:
        return None

    # Keep only date part when ISO datetime is supplied.
    text = text.replace(".", "-").replace("/", "-")
    if "T" in text:
        text = text.split("T", 1)[0]
    if " " in text:
        text = text.split(" ", 1)[0]

    if re.fullmatch(r"\d{4}", text):
        return date(int(text), 12, 31)
    if re.fullmatch(r"\d{6}", text):
        return _last_day_of_month(int(text[:4]), int(text[4:6]))
    if re.fullmatch(r"\d{8}", text):
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))

    ym = re.fullmatch(r"(\d{4})-(\d{1,2})", text)
    if ym:
        return _last_day_of_month(int(ym.group(1)), int(ym.group(2)))

    ymd = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if ymd:
        return date(int(ymd.group(1)), int(ymd.group(2)), int(ymd.group(3)))

    try:
        return datetime.fromisoformat(text).date()
    except Exception:
        return None


def _parse_row_date(value: Any) -> date | None:
    """Parse row-level date values. Invalid or summary-only dates return None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = _strip_text(value)
    if not text or text.lower() in {"nan", "none", "null", "summary_only"}:
        return None

    text = text.replace(".", "-").replace("/", "-")
    if "T" in text:
        text = text.split("T", 1)[0]
    if " " in text:
        text = text.split(" ", 1)[0]

    if re.fullmatch(r"\d{8}", text):
        try:
            return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
        except Exception:
            return None
    if re.fullmatch(r"\d{6}", text):
        try:
            return _last_day_of_month(int(text[:4]), int(text[4:6]))
        except Exception:
            return None
    if re.fullmatch(r"\d{4}", text):
        try:
            return date(int(text), 12, 31)
        except Exception:
            return None

    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            parsed = datetime.strptime(text, fmt).date()
            if fmt == "%Y-%m":
                return _last_day_of_month(parsed.year, parsed.month)
            if fmt == "%Y":
                return date(parsed.year, 12, 31)
            return parsed
        except Exception:
            continue

    try:
        return datetime.fromisoformat(text).date()
    except Exception:
        return None


def _resolve_cutoff_date(as_of_date: str | date | datetime | None = None) -> date | None:
    explicit = _parse_cutoff_date(as_of_date)
    if explicit:
        return explicit

    for key in _CUTOFF_ENV_KEYS:
        parsed = _parse_cutoff_date(os.getenv(key, ""))
        if parsed:
            return parsed
    return None


def _find_existing_key(row: dict[str, Any], candidates: tuple[str, ...]) -> str | None:
    if not isinstance(row, dict):
        return None
    keys = set(row.keys())
    for c in candidates:
        if c in keys:
            return c
    lowered = {str(k).strip().lower(): k for k in row.keys()}
    for c in candidates:
        hit = lowered.get(c.lower())
        if hit is not None:
            return str(hit)
    return None


def _to_int_year(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            if value != value:  # NaN guard
                return None
            year = int(value)
            return year if 1900 <= year <= 2100 else None
        except Exception:
            return None

    text = _strip_text(value)
    if not text or text.lower() in {"nan", "none", "null"}:
        return None

    # DART-like business year often comes as "2024" or "2024.0".
    m = re.search(r"(19\d{2}|20\d{2}|21\d{2})", text)
    if not m:
        return None
    return int(m.group(1))


def _filter_rows_by_cutoff(
    rows: list[dict[str, Any]],
    cutoff: date | None,
    *,
    prefer_year: bool = False,
) -> list[dict[str, Any]]:
    """Keep only rows whose date/year is not after cutoff.

    This helper is intentionally conservative and local to valuation loading:
    - If there is a date column, date <= cutoff is used.
    - If no date column exists but a year column exists, year <= cutoff.year is used.
    - If neither exists, rows are returned unchanged to avoid breaking non-temporal inputs.
    """
    if not rows or cutoff is None:
        return rows

    first = rows[0]
    date_key = _find_existing_key(first, _DATE_COLUMN_CANDIDATES)
    year_key = _find_existing_key(first, _YEAR_COLUMN_CANDIDATES)

    if prefer_year and year_key:
        return [r for r in rows if (_to_int_year(r.get(year_key)) or 9999) <= cutoff.year]

    if date_key:
        filtered: list[dict[str, Any]] = []
        for r in rows:
            parsed = _parse_row_date(r.get(date_key))
            if parsed is not None and parsed <= cutoff:
                filtered.append(r)
        return filtered

    if year_key:
        return [r for r in rows if (_to_int_year(r.get(year_key)) or 9999) <= cutoff.year]

    return rows


def _month_start(year_month: str) -> date:
    parsed = _parse_cutoff_date(f"{_strip_text(year_month)}-01")
    if parsed is None:
        raise ValueError(f"invalid year_month: {year_month}")
    return date(parsed.year, parsed.month, 1)


# 데이터 입력 기간 로직 추가
# 기준 연도(year)까지만 valuation 재무 데이터를 사용
# 예: year=2024 -> 2024년 이하만 유지, 2025 이후 제거
def load_valuation_financials(path: str | Path, year: int = 2024) -> dict[str, Any]:
    rows = read_csv(Path(path))
    if not rows:
        raise ValueError(f"valuation financial csv is empty: {path}")

    year_key = _find_existing_key(rows[0], _YEAR_COLUMN_CANDIDATES)
    if year_key is None:
        raise KeyError(f"valuation financial csv has no year column: {path}")

    filtered: list[dict[str, Any]] = []
    for row in rows:
        row_year = _to_int_year(row.get(year_key))
        if row_year is None or row_year > year:
            continue
        item = dict(row)
        item[year_key] = int(row_year)
        filtered.append(item)

    if not filtered:
        raise ValueError(f"valuation financial csv has no usable rows up to {year}: {path}")

    meta = {
        "company_name": str(filtered[0].get("company") or _infer_company_name_from_path(path)),
        "source_file": str(path),
        "cutoff_year": int(year),
        "year_column": year_key,
    }
    return {
        "meta": meta,
        "financials": filtered,
    }


# 데이터 입력 기간 로직 추가
# 기준 월(year_month) 이전 valuation 가격 데이터만 사용
# 예: year_month="2025-07" -> 2025-06-30까지 유지, 2025-07-01 이후 제거
def load_valuation_price_data(path: str | Path, year_month: str = "2025-06") -> dict[str, Any]:
    rows = _normalize_price_rows(read_csv(Path(path)))
    if not rows:
        raise ValueError(f"valuation price csv is empty: {path}")

    month_start = _month_start(year_month)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        row_date = _parse_row_date(row.get("date"))
        if row_date is not None and row_date < month_start:
            filtered.append(row)

    if not filtered:
        raise ValueError(f"valuation price csv has no usable rows before {year_month}: {path}")

    latest_date = _parse_row_date(filtered[-1].get("date"))
    recent_start = latest_date - timedelta(days=30) if latest_date else None
    recent_1m = [
        dict(row) for row in filtered
        if recent_start is None or (_parse_row_date(row.get("date")) or date.min) >= recent_start
    ]

    meta = {
        "company_name": str(filtered[0].get("company") or _infer_company_name_from_path(path)),
        "ticker": str(filtered[0].get("ticker") or ""),
        "market": str(filtered[0].get("market") or ""),
        "source_file": str(path),
        "cutoff_exclusive_month": year_month,
    }
    return {
        "meta": meta,
        "price_history": filtered,
        "recent_1m": recent_1m,
    }


def _load_financial_rows_for_context(path: Path, cutoff: date | None) -> list[dict[str, Any]]:
    rows = read_csv(path)
    if cutoff is not None:
        return _filter_rows_by_cutoff(rows, cutoff, prefer_year=True)
    if not rows:
        return []
    try:
        return load_valuation_financials(path)["financials"]
    except Exception:
        return rows


def _load_price_rows_for_context(path: Path | None, rows: list[dict[str, Any]], cutoff: date | None) -> list[dict[str, Any]]:
    if cutoff is not None:
        return _filter_rows_by_cutoff(rows, cutoff)
    if path is not None:
        try:
            return load_valuation_price_data(path)["price_history"]
        except Exception:
            pass
    return rows


def _latest_price_row_at_cutoff(price_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    dated: list[tuple[date, dict[str, Any]]] = []
    for r in price_rows:
        parsed = _parse_row_date(r.get("date"))
        if parsed is not None:
            dated.append((parsed, r))
    if not dated:
        return None
    dated.sort(key=lambda x: x[0])
    return dated[-1][1]


def _cutoff_price_summary(
    price_summary: dict[str, Any],
    price_rows: list[dict[str, Any]],
    cutoff: date | None,
) -> dict[str, Any]:
    if not isinstance(price_summary, dict):
        return {}
    if cutoff is None:
        return price_summary

    out = dict(price_summary)
    out["data_cutoff_applied"] = cutoff.isoformat()

    latest_row = _latest_price_row_at_cutoff(price_rows)
    if latest_row:
        latest_date = latest_row.get("date")
        latest_close = to_float(latest_row.get("close") or latest_row.get("adj_close"))
        if latest_date:
            out["price_end"] = latest_date
            out["latest_date"] = latest_date
        if latest_close is not None:
            out["latest_close"] = latest_close
            out["current_price"] = latest_close
        out["price_summary_cutoff_source"] = "valuation_price_history.csv"
    else:
        # Do not fabricate a price if no row exists at or before cutoff.
        summary_date = _parse_row_date(out.get("price_end") or out.get("latest_date"))
        if summary_date and summary_date > cutoff:
            out["price_summary_cutoff_warning"] = (
                "price_summary latest date is after cutoff and no price-history row exists before cutoff"
            )
    return out


def _target_key_values(company_dir: str, company: str) -> set[str]:
    return {str(x).strip().lower() for x in (company_dir, company) if str(x).strip()}


def _mark_target_peer_rows(rows: list[dict[str, Any]], *, company_dir: str, company: str) -> list[dict[str, Any]]:
    keys = _target_key_values(company_dir, company)
    for row in rows:
        if str(row.get("is_target") or "").strip().lower() in {"true", "1", "yes", "y"}:
            row["is_target"] = True
            continue
        values = {
            str(row.get(k) or "").strip().lower()
            for k in ("company_dir", "company", "company_name", "peer_company", "ticker", "stock_code")
        }
        if keys & values:
            row["is_target"] = True
    return rows


def _load_peer_rows(
    i: Path,
    sector_dir: Path,
    cutoff: date | None,
    *,
    company_dir: str,
    company: str,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    local_rows, local_path = _read_csv_first_existing([i / "valuation_peer_input.csv", i / "peer_multiples.csv"])
    local_rows = _filter_rows_by_cutoff(local_rows, cutoff)
    sector_path = sector_dir / "semiconductor_peer_multiples.csv"
    sector_rows = _filter_rows_by_cutoff(read_csv(sector_path), cutoff)
    loaded: dict[str, str] = {}
    if local_path:
        loaded["company_peer_rows"] = str(local_path)
    if sector_rows:
        loaded["sector_peer_multiples"] = str(sector_path)

    rows = list(local_rows)
    seen = {
        (
            str(r.get("company_dir") or r.get("company") or r.get("peer_company") or "").strip().lower(),
            str(r.get("ticker") or r.get("stock_code") or "").strip(),
        )
        for r in rows
    }
    for row in sector_rows:
        key = (
            str(row.get("company_dir") or row.get("company") or row.get("peer_company") or "").strip().lower(),
            str(row.get("ticker") or row.get("stock_code") or "").strip(),
        )
        if key not in seen:
            rows.append(row)
            seen.add(key)
    return _mark_target_peer_rows(rows, company_dir=company_dir, company=company), loaded


def _latest_assumption_row(path: Path, cutoff: date | None) -> dict[str, Any]:
    rows = _filter_rows_by_cutoff(read_csv(path), cutoff)
    if not rows:
        return {}
    rows.sort(key=lambda r: str(r.get("as_of_date") or r.get("date") or r.get("year") or ""))
    return dict(rows[-1])


def _merge_wacc_row(assumptions: dict[str, Any], row: dict[str, Any]) -> None:
    alias = {
        "cost_of_debt": "pre_tax_cost_of_debt",
        "discount_period": "projection_years",
    }
    for key, value in row.items():
        if _is_blank(value):
            continue
        assumptions[key] = value
        if key in alias:
            assumptions[alias[key]] = value


def _merge_growth_row(assumptions: dict[str, Any], row: dict[str, Any]) -> None:
    mapping = {
        "revenue_growth": "forecast_revenue_growth",
        "op_margin": "forecast_op_margin",
        "capex_ratio": "forecast_capex_ratio",
    }
    for key, value in row.items():
        if _is_blank(value):
            continue
        assumptions[key] = value
        if key in mapping:
            assumptions[mapping[key]] = value


def _load_assumptions(i: Path, sector_dir: Path, cutoff: date | None) -> tuple[dict[str, Any], dict[str, str]]:
    assumptions = read_json(i / "valuation_assumptions.json", {}) or {}
    if not isinstance(assumptions, dict):
        assumptions = {}
    loaded: dict[str, str] = {}
    if (i / "valuation_assumptions.json").exists():
        loaded["company_assumptions_json"] = str(i / "valuation_assumptions.json")

    growth_path = sector_dir / "sector_growth_assumptions.csv"
    growth_row = _latest_assumption_row(growth_path, cutoff)
    if growth_row:
        _merge_growth_row(assumptions, growth_row)
        loaded["sector_growth_assumptions"] = str(growth_path)

    sector_wacc_path = sector_dir / "wacc_assumptions.csv"
    sector_wacc_row = _latest_assumption_row(sector_wacc_path, cutoff)
    if sector_wacc_row:
        _merge_wacc_row(assumptions, sector_wacc_row)
        loaded["sector_wacc_assumptions"] = str(sector_wacc_path)

    company_wacc_path = i / "valuation_assumptions.csv"
    company_wacc_row = _latest_assumption_row(company_wacc_path, cutoff)
    if company_wacc_row:
        _merge_wacc_row(assumptions, company_wacc_row)
        loaded["company_valuation_assumptions_csv"] = str(company_wacc_path)

    return assumptions, loaded


def has_required_intake(company_dir: str) -> bool:
    i = intake_dir(company_dir)
    manifest_or_requested_inputs = (i / "valuation_intake_manifest.json").exists() or any(
        (i / name).exists() for name in COMPANY_INTAKE_FILE_NAMES
    )
    return manifest_or_requested_inputs and (
        (i / "valuation_normalized_financials.csv").exists()
        or (i / PRICE_CANONICAL).exists()
        or (i / EVAL_PRICE_HISTORY).exists()
        or (i / "valuation_price_summary.json").exists()
    )


def intake_quality(company_dir: str, as_of_date: str | date | datetime | None = None) -> dict[str, Any]:
    i = intake_dir(company_dir)
    sector_dir = sector_valuation_dir(company_dir)
    cutoff = _resolve_cutoff_date(as_of_date)
    manifest = read_json(i / "valuation_intake_manifest.json", {}) or {}
    source_map = read_json(i / "valuation_source_map.json", {}) or {}
    if not isinstance(source_map, dict):
        source_map = {}
    price_summary = read_json(i / "valuation_price_summary.json", {}) or {}
    market_snapshot, market_sources = _read_market_snapshot(i, source_map, cutoff)
    price_rows, price_path = _find_price_csv(i, source_map)
    price_rows_before_cutoff = len(price_rows)
    price_rows = _load_price_rows_for_context(price_path, price_rows, cutoff)
    financials_raw = read_csv(i / "valuation_normalized_financials.csv")
    financials = _load_financial_rows_for_context(i / "valuation_normalized_financials.csv", cutoff)
    return {
        "has_manifest": bool(manifest),
        "financial_rows": len(financials),
        "financial_rows_before_cutoff": len(financials_raw),
        "price_rows_loaded": len(price_rows),
        "price_rows_before_cutoff": price_rows_before_cutoff,
        "price_rows_manifest": ((manifest.get("counts") or {}).get("price_rows") if isinstance(manifest, dict) else None),
        "price_rows_summary": price_summary.get("price_rows") if isinstance(price_summary, dict) else None,
        "price_path": str(price_path) if price_path else None,
        "data_cutoff_applied": cutoff.isoformat() if cutoff else None,
        "has_market_snapshot": bool(market_snapshot),
        "market_snapshot_sources": market_sources,
        "recognized_company_intake_files": {
            name: str(i / name) for name in COMPANY_INTAKE_FILE_NAMES if (i / name).exists()
        },
        "recognized_sector_common_files": {
            name: str(sector_dir / name) for name in SECTOR_COMMON_FILE_NAMES if (sector_dir / name).exists()
        },
    }


def load_context(
    company_dir: str,
    company: str,
    as_of_date: str | date | datetime | None = None,
) -> ValuationContext:
    i = intake_dir(company_dir)
    sector_dir = sector_valuation_dir(company_dir)
    cutoff = _resolve_cutoff_date(as_of_date)
    source_map = read_json(i / "valuation_source_map.json", {}) or {}
    if not isinstance(source_map, dict):
        source_map = {}
    price_summary = read_json(i / "valuation_price_summary.json", {}) or {}
    market_snapshot, market_sources = _read_market_snapshot(i, source_map, cutoff)
    price_rows, price_path = _find_price_csv(i, source_map)
    price_rows_before_cutoff = len(price_rows)
    price_rows = _load_price_rows_for_context(price_path, price_rows, cutoff)
    if not price_rows:
        price_rows = _synthetic_price_row_from_summary(price_summary)
        price_rows = _filter_rows_by_cutoff(price_rows, cutoff)
    price_summary = _cutoff_price_summary(price_summary, price_rows, cutoff)

    financials_raw = read_csv(i / "valuation_normalized_financials.csv")
    raw_accounts_raw = read_csv(i / "valuation_raw_dart_accounts.csv")
    share_count_raw = read_csv(i / "valuation_share_count.csv")

    financials = _load_financial_rows_for_context(i / "valuation_normalized_financials.csv", cutoff)
    raw_accounts = _load_financial_rows_for_context(i / "valuation_raw_dart_accounts.csv", cutoff)
    share_count = _filter_rows_by_cutoff(share_count_raw, cutoff)
    peers, peer_sources = _load_peer_rows(i, sector_dir, cutoff, company_dir=company_dir, company=company)
    assumptions, assumption_sources = _load_assumptions(i, sector_dir, cutoff)
    latest_price_row = _latest_price_row_at_cutoff(price_rows)
    if latest_price_row:
        latest_close = to_float(latest_price_row.get("close") or latest_price_row.get("adj_close"))
        market_cap = to_float(latest_price_row.get("market_cap"))
        if latest_close is not None:
            assumptions["latest_close"] = latest_close
        if market_cap is not None:
            assumptions["market_cap"] = market_cap

    if isinstance(source_map, dict):
        source_map.setdefault("loader_diagnostics", {})
        source_map["loader_diagnostics"].update({
            "price_history_loaded_rows": len(price_rows),
            "price_history_rows_before_cutoff": price_rows_before_cutoff,
            "price_history_loaded_from": str(price_path) if price_path else ("valuation_price_summary.json" if price_rows else None),
            "financial_rows_before_cutoff": len(financials_raw),
            "financial_rows_after_cutoff": len(financials),
            "raw_account_rows_before_cutoff": len(raw_accounts_raw),
            "raw_account_rows_after_cutoff": len(raw_accounts),
            "share_count_rows_before_cutoff": len(share_count_raw),
            "share_count_rows_after_cutoff": len(share_count),
            "data_cutoff_applied": cutoff.isoformat() if cutoff else None,
            "market_snapshot_sources": market_sources,
            "peer_sources": peer_sources,
            "assumption_sources": assumption_sources,
            "recognized_company_intake_files": {
                name: str(i / name) for name in COMPANY_INTAKE_FILE_NAMES if (i / name).exists()
            },
            "recognized_sector_common_files": {
                name: str(sector_dir / name) for name in SECTOR_COMMON_FILE_NAMES if (sector_dir / name).exists()
            },
        })

    return ValuationContext(
        company_dir=company_dir,
        company=company,
        financials=financials,
        raw_accounts=raw_accounts,
        price_history=price_rows,
        share_count=share_count,
        peers=peers,
        reference_universe=read_csv(i / "valuation_reference_universe_208.csv"),
        reference_focus=read_csv(i / "valuation_reference_universe_focus.csv"),
        reference_summary=read_json(i / "valuation_reference_universe_summary.json", {}) or {},
        assumptions=assumptions,
        price_summary=price_summary,
        market_snapshot=market_snapshot,
        template_catalog=read_json(i / "valuation_modeling_template_catalog.json", []) or [],
        source_map=source_map,
        intake_manifest=read_json(i / "valuation_intake_manifest.json", {}) or {},
    )


def get_valuation_data_range(path: str | Path, start_date: str, end_date: str) -> list[dict[str, Any]]:
    """Return raw valuation CSV rows inside a requested date/year range."""
    rows = read_csv(Path(path))
    if not rows:
        return []

    first = rows[0]
    date_key = _find_existing_key(first, _DATE_COLUMN_CANDIDATES)
    year_key = _find_existing_key(first, _YEAR_COLUMN_CANDIDATES)
    start = _parse_cutoff_date(start_date)
    end = _parse_cutoff_date(end_date)
    if start is None or end is None:
        raise ValueError(f"invalid valuation data range: {start_date} ~ {end_date}")

    if date_key:
        out: list[dict[str, Any]] = []
        for row in rows:
            parsed = _parse_row_date(row.get(date_key))
            if parsed is not None and start <= parsed <= end:
                item = dict(row)
                item[date_key] = parsed.isoformat()
                out.append(item)
        out.sort(key=lambda r: str(r.get(date_key) or ""))
        return out

    if year_key:
        start_year = start.year
        end_year = end.year
        out = [
            dict(row) for row in rows
            if (year := _to_int_year(row.get(year_key))) is not None and start_year <= year <= end_year
        ]
        out.sort(key=lambda r: _to_int_year(r.get(year_key)) or 0)
        return out

    raise KeyError(f"valuation csv has no date/year column: {path}")
