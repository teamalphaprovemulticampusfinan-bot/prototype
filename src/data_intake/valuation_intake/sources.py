from __future__ import annotations

import csv
import io
import json
import os
import re
import time
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

try:
    import yfinance as yf  # type: ignore
except Exception:  # pragma: no cover
    yf = None  # type: ignore

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore

from common.data_paths import ROOT_DIR, company_slug, company_agent_dir

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore


@dataclass(frozen=True)
class ListedCompany:
    slug: str
    name: str
    stock_code: str
    market: str
    yf_ticker: str


COMPANY_REGISTRY: dict[str, ListedCompany] = {
    "nepes": ListedCompany("nepes", "네패스", "033640", "KOSDAQ", "033640.KQ"),
    "hanmi": ListedCompany("hanmi", "한미반도체", "042700", "KOSPI", "042700.KS"),
    "hansol": ListedCompany("hansol", "한솔케미칼", "014680", "KOSPI", "014680.KS"),
    "duksan": ListedCompany("duksan", "덕산테코피아", "317330", "KOSDAQ", "317330.KQ"),
    "ltc": ListedCompany("ltc", "엘티씨", "170920", "KOSDAQ", "170920.KQ"),
}


def _market_to_yf_suffix(market: str) -> str:
    m = str(market or "").strip().upper()
    if m == "KOSPI":
        return ".KS"
    if m == "KOSDAQ":
        return ".KQ"
    return ""


def _make_yf_ticker(stock_code: str, market: str) -> str:
    code = str(stock_code or "").strip().zfill(6)
    if not code or not code.isdigit() or code == "000000":
        return ""
    return f"{code}{_market_to_yf_suffix(market)}" if _market_to_yf_suffix(market) else code


def resolve_company(company_dir: str, company: str | None = None) -> ListedCompany:
    """Resolve a company without hard-coding only the original 5-company set.

    Priority:
    1. common.company_metadata universe/company.yaml resolver
    2. existing 5-company registry
    3. valuation-specific environment variables

    This makes Valuation Intake work for 30-company universe names such as
    ``sfa`` + ``SFA 반도체`` as well as canonical slugs like ``sfa_semicon``.
    """
    raw_value = company_dir or company or ""
    slug = company_slug(raw_value)

    try:
        from common.company_metadata import get_company_metadata

        meta = get_company_metadata(raw_value, company) or get_company_metadata(slug, company)
        if meta and meta.stock_code:
            return ListedCompany(
                slug=meta.slug,
                name=meta.name,
                stock_code=str(meta.stock_code).zfill(6),
                market=meta.market or "KOSDAQ",
                yf_ticker=meta.yf_ticker or _make_yf_ticker(str(meta.stock_code), meta.market),
            )
    except Exception:
        pass

    if slug in COMPANY_REGISTRY:
        return COMPANY_REGISTRY[slug]

    name = company or company_dir or slug
    stock_code = os.getenv(f"VALUATION_STOCK_CODE_{slug.upper()}", "").strip().zfill(6)
    stock_code = stock_code if stock_code != "000000" else ""
    market = os.getenv(f"VALUATION_MARKET_{slug.upper()}", "KOSDAQ").strip() or "KOSDAQ"
    yf_ticker = os.getenv(f"VALUATION_YF_TICKER_{slug.upper()}", _make_yf_ticker(stock_code, market)).strip()
    return ListedCompany(slug=slug, name=name, stock_code=stock_code, market=market, yf_ticker=yf_ticker)


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if text in {"", "-", "nan", "None", "null"}:
        return None
    # DART may wrap negatives as (123)
    neg = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    try:
        num = float(text)
        return -num if neg else num
    except Exception:
        return None


def _today_kst() -> date:
    # KST 기준 날짜. 외부 의존성(pytz)을 추가하지 않기 위해 UTC+9로 처리한다.
    return (datetime.utcnow() + timedelta(hours=9)).date()


def _parse_date_like(value: Any) -> date | None:
    text = str(value or "").strip().strip('"').strip("'")
    if not text:
        return None
    text = text.replace(".", "-").replace("/", "-")
    if "T" in text:
        text = text.split("T", 1)[0]
    if " " in text:
        text = text.split(" ", 1)[0]
    try:
        if re.fullmatch(r"\d{8}", text):
            return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
        if re.fullmatch(r"\d{6}", text):
            y, m = int(text[:4]), int(text[4:6])
            return date(y + (m // 12), (m % 12) + 1, 1) - timedelta(days=1)
        if re.fullmatch(r"\d{4}", text):
            return date(int(text), 12, 31)
        if re.fullmatch(r"\d{4}-\d{1,2}", text):
            y, m = [int(x) for x in text.split("-")]
            return date(y + (m // 12), (m % 12) + 1, 1) - timedelta(days=1)
        return datetime.fromisoformat(text).date()
    except Exception:
        return None


def valuation_date_range(
    *,
    years: int = 5,
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
) -> tuple[date, date]:
    """Return valuation collection range.

    Default is 2021-01-01 through today so Valuation Intake can rebuild the
    historical panel used by evaluation/backtest/dashboard runs. Environment
    variables are supported for scheduled runs:
    - VALUATION_START_DATE
    - VALUATION_END_DATE / VALUATION_AS_OF_DATE / ALPHAPROVE_DATA_CUTOFF_DATE
    """
    end = (
        _parse_date_like(end_date)
        or _parse_date_like(os.getenv("VALUATION_END_DATE"))
        or _parse_date_like(os.getenv("VALUATION_AS_OF_DATE"))
        or _parse_date_like(os.getenv("ALPHAPROVE_DATA_CUTOFF_DATE"))
        or _today_kst()
    )
    start = (
        _parse_date_like(start_date)
        or _parse_date_like(os.getenv("VALUATION_START_DATE"))
        or date(2021, 1, 1)
    )
    if start > end:
        start, end = end, start
    return start, end


def _year_range_from_dates(start: date, end: date) -> list[int]:
    return list(range(start.year, end.year + 1))


def _date_in_range(row_date: Any, start: date, end: date) -> bool:
    parsed = _parse_date_like(row_date)
    return bool(parsed and start <= parsed <= end)


def _load_project_dotenv_once() -> None:
    """Load .env for standalone `python main.py valuation-intake ...` runs.

    기존 Chair는 graph.py에서 dotenv를 로드하지만, valuation-intake는 독립
    명령으로 실행되므로 여기서도 안전하게 .env를 로드한다. 이미 PowerShell
    환경변수로 값이 들어간 경우에는 override하지 않는다.
    """
    if load_dotenv is None:
        return
    for candidate in (ROOT_DIR / ".env", Path.cwd() / ".env"):
        try:
            if candidate.exists():
                load_dotenv(dotenv_path=candidate, override=False)
        except Exception:
            continue


def _get_api_key() -> str:
    _load_project_dotenv_once()
    for key in ("DART_API_KEY", "OPEN_DART_API_KEY", "OPENDART_API_KEY"):
        value = os.getenv(key)
        if value and value.strip():
            return value.strip()
    return ""


def _load_cached_corp_code_map() -> dict[str, dict[str, str]]:
    candidates = [
        ROOT_DIR / ".cache" / "dart" / "corp_code_map.json",
        ROOT_DIR / "data" / "_global_common" / "dart" / "corp_code_map.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def _download_corp_code_map(api_key: str, cache_path: Path) -> dict[str, dict[str, str]]:
    if not api_key or requests is None:
        return {}
    url = "https://opendart.fss.or.kr/api/corpCode.xml"
    resp = requests.get(url, params={"crtfc_key": api_key}, timeout=30)
    resp.raise_for_status()
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    xml_name = zf.namelist()[0]
    root = ET.fromstring(zf.read(xml_name))
    mapping: dict[str, dict[str, str]] = {}
    for item in root.findall("list"):
        corp_code = (item.findtext("corp_code") or "").strip()
        corp_name = (item.findtext("corp_name") or "").strip()
        stock_code = (item.findtext("stock_code") or "").strip()
        if not corp_code:
            continue
        row = {"corp_code": corp_code, "corp_name": corp_name, "stock_code": stock_code}
        if stock_code:
            mapping[stock_code] = row
        if corp_name:
            mapping[corp_name] = row
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    return mapping


def resolve_dart_corp_code(company: ListedCompany, diagnostics: list[str]) -> str:
    _load_project_dotenv_once()
    env_key = os.getenv(f"DART_CORP_CODE_{company.slug.upper()}", "").strip()
    if env_key:
        diagnostics.append(f"DART corp_code resolved from env for {company.slug}.")
        return env_key

    mapping = _load_cached_corp_code_map()
    row = mapping.get(company.stock_code) or mapping.get(company.name)
    if isinstance(row, dict) and row.get("corp_code"):
        diagnostics.append(f"DART corp_code resolved from cache for {company.name}/{company.stock_code}.")
        return str(row["corp_code"])

    api_key = _get_api_key()
    if not api_key:
        diagnostics.append("DART API key not found: set DART_API_KEY or OPEN_DART_API_KEY for live financial-statement intake.")
        return ""

    try:
        mapping = _download_corp_code_map(api_key, ROOT_DIR / ".cache" / "dart" / "corp_code_map.json")
        row = mapping.get(company.stock_code) or mapping.get(company.name)
        if isinstance(row, dict) and row.get("corp_code"):
            diagnostics.append(f"DART corp_code resolved from OpenDART corpCode.xml for {company.name}/{company.stock_code}.")
            return str(row["corp_code"])
    except Exception as exc:
        diagnostics.append(f"DART corp-code download failed: {exc}")
    return ""


def _append_dart_row(
    output: list[dict[str, Any]],
    *,
    company: ListedCompany,
    corp_code: str,
    year: int,
    fs_div: str,
    endpoint_name: str,
    row: dict[str, Any],
) -> None:
    output.append({
        "source": endpoint_name,
        "corp_code": corp_code,
        "company": company.name,
        "company_dir": company.slug,
        "stock_code": company.stock_code,
        "year": year,
        "fs_div": fs_div,
        "sj_div": row.get("sj_div"),
        "sj_nm": row.get("sj_nm"),
        "account_id": row.get("account_id"),
        "account_nm": row.get("account_nm"),
        "account_detail": row.get("account_detail"),
        "thstrm_nm": row.get("thstrm_nm"),
        "amount": _to_float(row.get("thstrm_amount")),
        "frmtrm_amount": _to_float(row.get("frmtrm_amount")),
        "currency": row.get("currency") or "KRW",
        "ord": row.get("ord"),
    })


def _fetch_dart_all_accounts(
    *,
    api_key: str,
    company: ListedCompany,
    corp_code: str,
    year: int,
    fs_div: str,
    diagnostics: list[str],
) -> list[dict[str, Any]]:
    endpoint = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": "11011",
        "fs_div": fs_div,
    }
    try:
        resp = requests.get(endpoint, params=params, timeout=30)  # type: ignore[union-attr]
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        diagnostics.append(f"DART all-account fetch failed year={year} fs_div={fs_div}: {exc}")
        return []
    status = str(data.get("status", ""))
    if status != "000":
        msg = data.get("message") or data.get("msg") or status
        if status not in {"013", "014"}:
            diagnostics.append(f"DART all-account status={status} year={year} fs_div={fs_div}: {msg}")
        return []
    rows = data.get("list") or []
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for r in rows:
        if isinstance(r, dict):
            _append_dart_row(out, company=company, corp_code=corp_code, year=year, fs_div=fs_div, endpoint_name="OpenDART_fnlttSinglAcntAll", row=r)
    return out


def _fetch_dart_major_accounts(
    *,
    api_key: str,
    company: ListedCompany,
    corp_code: str,
    year: int,
    fs_div: str,
    diagnostics: list[str],
) -> list[dict[str, Any]]:
    """Fallback to OpenDART single-account endpoint.

    일부 기업/연도는 `fnlttSinglAcntAll`에서 013(데이터 없음)을 반환하지만
    주요계정 API(`fnlttSinglAcnt`)에는 매출액/영업이익/자산/자본 등이
    존재한다. DCF/WACC workbook의 최소 입력값을 확보하기 위한 보조 경로다.
    """
    endpoint = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": "11011",
    }
    try:
        resp = requests.get(endpoint, params=params, timeout=30)  # type: ignore[union-attr]
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        diagnostics.append(f"DART major-account fetch failed year={year}: {exc}")
        return []
    status = str(data.get("status", ""))
    if status != "000":
        msg = data.get("message") or data.get("msg") or status
        if status not in {"013", "014"}:
            diagnostics.append(f"DART major-account status={status} year={year}: {msg}")
        return []
    rows = data.get("list") or []
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        row_fs_div = str(r.get("fs_div") or fs_div or "CFS")
        # Consolidated rows are preferred; if caller asks CFS, skip OFS where CFS exists later by normalizer ordering.
        if fs_div and row_fs_div not in {fs_div, ""}:
            continue
        _append_dart_row(out, company=company, corp_code=corp_code, year=year, fs_div=row_fs_div, endpoint_name="OpenDART_fnlttSinglAcnt_fallback", row=r)
    return out


def fetch_dart_financial_accounts(company: ListedCompany, years: int, diagnostics: list[str], start_date: str | date | datetime | None = None, end_date: str | date | datetime | None = None) -> list[dict[str, Any]]:
    api_key = _get_api_key()
    if not api_key or requests is None:
        diagnostics.append("DART financial statements skipped: missing API key or requests package. `.env` is now auto-loaded; check DART_API_KEY if this persists.")
        return []

    diagnostics.append("DART API key detected for valuation intake.")
    corp_code = resolve_dart_corp_code(company, diagnostics)
    if not corp_code:
        diagnostics.append(f"DART corp_code not resolved for {company.name} ({company.stock_code}).")
        return []

    start, end = valuation_date_range(years=years, start_date=start_date, end_date=end_date)
    candidate_years = _year_range_from_dates(start, end)
    output: list[dict[str, Any]] = []
    yearly_counts: dict[int, int] = {}

    for y in candidate_years:
        year_rows: list[dict[str, Any]] = []
        for fs_div in ("CFS", "OFS"):
            rows = _fetch_dart_all_accounts(api_key=api_key, company=company, corp_code=corp_code, year=y, fs_div=fs_div, diagnostics=diagnostics)
            if not rows:
                rows = _fetch_dart_major_accounts(api_key=api_key, company=company, corp_code=corp_code, year=y, fs_div=fs_div, diagnostics=diagnostics)
            if rows:
                year_rows.extend(rows)
                # Prefer consolidated statements when available.
                if fs_div == "CFS":
                    break
            time.sleep(0.08)
        if year_rows:
            output.extend(year_rows)
            yearly_counts[y] = len(year_rows)

    if yearly_counts:
        diagnostics.append("DART financial rows collected: " + ", ".join(f"{y}={c}" for y, c in sorted(yearly_counts.items())))
    else:
        diagnostics.append(
            f"DART returned zero usable annual financial rows for {company.name}. "
            "Check corp_code, report availability, and DART API daily limits."
        )
    return output

def _normalize_account_name(name: Any) -> str:
    text = str(name or "").strip().replace(" ", "")
    text = re.sub(r"[()\[\]{}]", "", text)
    return text


def normalize_dart_accounts(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_year: dict[int, dict[str, Any]] = {}
    source_counts: dict[int, int] = {}

    def put(year: int, key: str, amount: float | None, account_nm: str) -> None:
        if amount is None:
            return
        row = by_year.setdefault(year, {"year": year})
        # Keep first non-null value. DART can have subtotal/duplicate accounts.
        if row.get(key) in (None, ""):
            row[key] = amount
            row[f"{key}_source_account"] = account_nm

    for r in raw_rows:
        try:
            year = int(r.get("year"))
        except Exception:
            continue
        amount = _to_float(r.get("amount"))
        name = _normalize_account_name(r.get("account_nm"))
        if not name:
            continue
        source_counts[year] = source_counts.get(year, 0) + 1
        # Income statement
        if name in {"매출액", "수익매출액", "영업수익", "매출"} or name.endswith("매출액"):
            put(year, "revenue", amount, str(r.get("account_nm")))
        elif name == "영업이익" or name.endswith("영업이익손실") or name == "영업손익":
            put(year, "operating_profit", amount, str(r.get("account_nm")))
        elif "당기순이익" in name and "지배" not in name:
            put(year, "net_income", amount, str(r.get("account_nm")))
        # Balance sheet
        elif name == "자산총계":
            put(year, "assets", amount, str(r.get("account_nm")))
        elif name == "부채총계":
            put(year, "liabilities", amount, str(r.get("account_nm")))
        elif name == "자본총계":
            put(year, "equity", amount, str(r.get("account_nm")))
        elif name in {"현금및현금성자산", "현금및현금성자산의증가감소"}:
            put(year, "cash", amount, str(r.get("account_nm")))
        # Cash flow
        elif "영업활동" in name and "현금흐름" in name:
            put(year, "cfo", amount, str(r.get("account_nm")))
        elif ("유형자산" in name or "무형자산" in name) and ("취득" in name or "구입" in name):
            # DART often records capex as negative cash flow.
            put(year, "capex", abs(amount) if amount is not None else None, str(r.get("account_nm")))
        elif "투자활동" in name and "현금흐름" in name:
            put(year, "investing_cf", amount, str(r.get("account_nm")))

    records: list[dict[str, Any]] = []
    for year in sorted(by_year):
        row = by_year[year]
        cfo = _to_float(row.get("cfo"))
        capex = _to_float(row.get("capex"))
        if capex is None:
            inv_cf = _to_float(row.get("investing_cf"))
            # Conservative fallback: do not treat all investing cash flow as capex;
            # use only as low-confidence proxy and mark it.
            if inv_cf is not None and inv_cf < 0:
                capex = abs(inv_cf) * 0.50
                row["capex_source_account"] = "투자활동현금흐름 50% proxy"
        if cfo is not None and capex is not None:
            row["fcf"] = cfo - capex
        row["source_account_count"] = source_counts.get(year, 0)
        records.append(row)
    return records



def _coerce_date_text(value: Any) -> str:
    """Convert common date representations to YYYY-MM-DD text."""
    if value is None:
        return ""
    if hasattr(value, "date"):
        try:
            return value.date().isoformat()
        except Exception:
            pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat"}:
        return ""
    # Naver often returns 20260511 without dashes.
    digits = re.sub(r"[^0-9]", "", text)
    if len(digits) >= 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return text[:10]


def _scalar(value: Any) -> Any:
    """Return a scalar from pandas Series/NumPy scalar/list-like values."""
    if value is None:
        return None
    try:
        if hasattr(value, "iloc"):
            if len(value) == 0:
                return None
            return value.iloc[0]
    except Exception:
        pass
    try:
        if isinstance(value, (list, tuple)):
            return value[0] if value else None
    except Exception:
        pass
    return value


def _row_value(row: Any, *names: str) -> Any:
    """Read a row value from flat or MultiIndex yfinance rows."""
    for name in names:
        try:
            if name in row:
                return _scalar(row.get(name))
        except Exception:
            pass
    # pandas Series from MultiIndex columns can have tuple keys.
    try:
        keys = list(getattr(row, "index", []))
        for key in keys:
            if isinstance(key, tuple):
                joined = "|".join(str(x) for x in key)
                if any(n in joined for n in names):
                    return _scalar(row.get(key))
    except Exception:
        pass
    return None


def _dedupe_price_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date: dict[str, dict[str, Any]] = {}
    for r in rows:
        date_text = _coerce_date_text(r.get("date"))
        close = _to_float(r.get("close"))
        if not date_text or close is None:
            continue
        nr = dict(r)
        nr["date"] = date_text
        nr["close"] = close
        for k in ("open", "high", "low", "adj_close", "volume"):
            if k in nr:
                nr[k] = _to_float(nr.get(k))
        by_date[date_text] = nr
    return [by_date[k] for k in sorted(by_date)]


def fetch_yfinance_prices(company: ListedCompany, years: int, diagnostics: list[str], start_date: str | date | datetime | None = None, end_date: str | date | datetime | None = None) -> list[dict[str, Any]]:
    if yf is None or not company.yf_ticker:
        diagnostics.append("yfinance price fetch skipped: yfinance not installed or ticker missing.")
        return []
    try:
        start, end = valuation_date_range(years=years, start_date=start_date, end_date=end_date)
        df = yf.download(company.yf_ticker, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(), interval="1d", progress=False, auto_adjust=False, threads=False)
        if df is None or getattr(df, "empty", True):
            diagnostics.append(f"yfinance returned empty data for {company.yf_ticker}.")
            return []
        # yfinance can return MultiIndex columns even for one ticker depending on version.
        try:
            if getattr(df.columns, "nlevels", 1) > 1:
                flat = []
                for c in df.columns.to_flat_index():
                    # Usually ('Close', '033640.KQ'); keep first level if it is a field name.
                    field = str(c[0]) if str(c[0]) in {"Open", "High", "Low", "Close", "Adj Close", "Volume", "Date"} else str(c[-1])
                    flat.append(field)
                df = df.copy()
                df.columns = flat
        except Exception:
            pass
        rows: list[dict[str, Any]] = []
        for _, row in df.reset_index().iterrows():
            dt = _row_value(row, "Date", "Datetime", "index")
            rows.append({
                "date": _coerce_date_text(dt),
                "open": _to_float(_row_value(row, "Open")),
                "high": _to_float(_row_value(row, "High")),
                "low": _to_float(_row_value(row, "Low")),
                "close": _to_float(_row_value(row, "Close")),
                "adj_close": _to_float(_row_value(row, "Adj Close", "Adj_Close")),
                "volume": _to_float(_row_value(row, "Volume")),
                "source": "yfinance_download",
                "ticker": company.yf_ticker,
            })
        rows = _dedupe_price_rows(rows)
        diagnostics.append(f"yfinance price rows for {company.yf_ticker}: {len(rows)}")
        return rows
    except Exception as exc:
        diagnostics.append(f"yfinance price fetch failed for {company.yf_ticker}: {exc}")
        return []


def fetch_yahoo_chart_prices(company: ListedCompany, years: int, diagnostics: list[str], start_date: str | date | datetime | None = None, end_date: str | date | datetime | None = None) -> list[dict[str, Any]]:
    """Fetch Yahoo chart JSON directly as a fallback when yfinance wrapper fails."""
    if requests is None or not company.yf_ticker:
        diagnostics.append("Yahoo chart price fetch skipped: requests not installed or ticker missing.")
        return []
    try:
        start, end = valuation_date_range(years=years, start_date=start_date, end_date=end_date)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{company.yf_ticker}"
        params = {"period1": int(datetime.combine(start, datetime.min.time()).timestamp()), "period2": int(datetime.combine(end + timedelta(days=1), datetime.min.time()).timestamp()), "interval": "1d", "events": "history"}
        resp = requests.get(url, params=params, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        data = resp.json()
        result = (((data.get("chart") or {}).get("result") or []) or [None])[0]
        if not result:
            diagnostics.append(f"Yahoo chart returned no result for {company.yf_ticker}.")
            return []
        timestamps = result.get("timestamp") or []
        quote = (((result.get("indicators") or {}).get("quote") or []) or [{}])[0]
        adj = (((result.get("indicators") or {}).get("adjclose") or []) or [{}])[0].get("adjclose") or []
        rows: list[dict[str, Any]] = []
        for i, ts in enumerate(timestamps):
            dt = datetime.utcfromtimestamp(int(ts)).date().isoformat()
            def pick(key: str) -> Any:
                vals = quote.get(key) or []
                return vals[i] if i < len(vals) else None
            rows.append({
                "date": dt,
                "open": _to_float(pick("open")),
                "high": _to_float(pick("high")),
                "low": _to_float(pick("low")),
                "close": _to_float(pick("close")),
                "adj_close": _to_float(adj[i] if i < len(adj) else pick("close")),
                "volume": _to_float(pick("volume")),
                "source": "yahoo_chart_api",
                "ticker": company.yf_ticker,
            })
        rows = _dedupe_price_rows(rows)
        diagnostics.append(f"Yahoo chart price rows for {company.yf_ticker}: {len(rows)}")
        return rows
    except Exception as exc:
        diagnostics.append(f"Yahoo chart price fetch failed for {company.yf_ticker}: {exc}")
        return []


def fetch_naver_prices(company: ListedCompany, years: int, diagnostics: list[str], start_date: str | date | datetime | None = None, end_date: str | date | datetime | None = None) -> list[dict[str, Any]]:
    if requests is None or not company.stock_code:
        diagnostics.append("Naver price fetch skipped: requests not installed or stock code missing.")
        return []
    start, end = valuation_date_range(years=years, start_date=start_date, end_date=end_date)
    params = {
        "symbol": company.stock_code,
        "requestType": "1",
        "startTime": start.strftime("%Y%m%d"),
        "endTime": end.strftime("%Y%m%d"),
        "timeframe": "day",
    }
    url = "https://api.finance.naver.com/siseJson.naver?" + urlencode(params)
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0", "Referer": f"https://finance.naver.com/item/sise.naver?code={company.stock_code}"})
        resp.raise_for_status()
        # Naver endpoint may be decoded incorrectly by requests depending on headers.
        text = resp.text.strip()
        if "날짜" not in text:
            try:
                text = resp.content.decode("euc-kr", errors="ignore").strip()
            except Exception:
                pass
        text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ").strip().rstrip(";")
        import ast
        data = ast.literal_eval(text)
        if not data or len(data) < 2:
            diagnostics.append(f"Naver siseJson returned no rows for {company.stock_code}.")
            return []
        header = [str(x).strip() for x in data[0]]
        rows: list[dict[str, Any]] = []
        for item in data[1:]:
            if not isinstance(item, (list, tuple)) or len(item) < len(header):
                continue
            d = dict(zip(header, item))
            rows.append({
                "date": _coerce_date_text(d.get("날짜")),
                "open": _to_float(d.get("시가")),
                "high": _to_float(d.get("고가")),
                "low": _to_float(d.get("저가")),
                "close": _to_float(d.get("종가")),
                "adj_close": _to_float(d.get("종가")),
                "volume": _to_float(d.get("거래량")),
                "source": "naver_finance_siseJson",
                "ticker": company.stock_code,
            })
        rows = _dedupe_price_rows(rows)
        diagnostics.append(f"Naver siseJson price rows for {company.stock_code}: {len(rows)}")
        return rows
    except Exception as exc:
        diagnostics.append(f"Naver siseJson price fetch failed for {company.stock_code}: {exc}")
        return []


def fetch_naver_day_table_prices(company: ListedCompany, years: int, diagnostics: list[str], start_date: str | date | datetime | None = None, end_date: str | date | datetime | None = None) -> list[dict[str, Any]]:
  
    if requests is None or not company.stock_code:
        diagnostics.append("Naver day-table fetch skipped: requests not installed or stock code missing.")
        return []
    start, end = valuation_date_range(years=years, start_date=start_date, end_date=end_date)
    max_rows = max(260, int(((end - start).days + 1) / 365.25 * 260) + 80)
    max_pages = min(260, (max_rows // 10) + 12)
    rows: list[dict[str, Any]] = []
    base_url = "https://finance.naver.com/item/sise_day.naver"
    for page in range(1, max_pages + 1):
        try:
            resp = requests.get(base_url, params={"code": company.stock_code, "page": page}, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            html = resp.content.decode("euc-kr", errors="ignore")
            parsed_rows: list[dict[str, Any]] = []
            if pd is not None:
                try:
                    tables = pd.read_html(html)
                    for tbl in tables:
                        cols = [str(c).strip() for c in getattr(tbl, "columns", [])]
                        if "날짜" not in cols or "종가" not in cols:
                            continue
                        for _, r in tbl.dropna(how="all").iterrows():
                            parsed_rows.append({
                                "date": _coerce_date_text(r.get("날짜")),
                                "open": _to_float(r.get("시가")),
                                "high": _to_float(r.get("고가")),
                                "low": _to_float(r.get("저가")),
                                "close": _to_float(r.get("종가")),
                                "adj_close": _to_float(r.get("종가")),
                                "volume": _to_float(r.get("거래량")),
                                "source": "naver_finance_sise_day_table",
                                "ticker": company.stock_code,
                            })
                except Exception as exc:
                    diagnostics.append(f"Naver day-table pandas parse failed page={page}: {exc}")
            if not parsed_rows:
                # Regex fallback for the simple table shape.
                trs = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S | re.I)
                for tr in trs:
                    cells = [re.sub(r"<.*?>", "", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S | re.I)]
                    cells = [c.replace("\xa0", "").strip() for c in cells]
                    if len(cells) >= 7 and re.search(r"\d{4}\.\d{2}\.\d{2}", cells[0]):
                        parsed_rows.append({
                            "date": _coerce_date_text(cells[0]),
                            "close": _to_float(cells[1]),
                            "open": _to_float(cells[3]),
                            "high": _to_float(cells[4]),
                            "low": _to_float(cells[5]),
                            "volume": _to_float(cells[6]),
                            "adj_close": _to_float(cells[1]),
                            "source": "naver_finance_sise_day_regex",
                            "ticker": company.stock_code,
                        })
            if not parsed_rows:
                if page <= 2:
                    diagnostics.append(f"Naver day-table page={page} parsed zero rows for {company.stock_code}.")
                break
            rows.extend(parsed_rows)
            if len(_dedupe_price_rows(rows)) >= max_rows:
                break
            time.sleep(0.03)
        except Exception as exc:
            diagnostics.append(f"Naver day-table fetch failed page={page} for {company.stock_code}: {exc}")
            break
    rows = _dedupe_price_rows(rows)
    rows = [r for r in rows if _date_in_range(r.get("date"), start, end)]
    if len(rows) > max_rows:
        rows = rows[-max_rows:]
    diagnostics.append(f"Naver day-table price rows for {company.stock_code}: {len(rows)}")
    return rows


def fetch_price_history(company: ListedCompany, years: int, diagnostics: list[str], start_date: str | date | datetime | None = None, end_date: str | date | datetime | None = None) -> list[dict[str, Any]]:
    providers = [
        ("yfinance", fetch_yfinance_prices),
        ("yahoo_chart", fetch_yahoo_chart_prices),
        ("naver_siseJson", fetch_naver_prices),
        ("naver_day_table", fetch_naver_day_table_prices),
    ]
    for provider_name, provider in providers:
        rows = provider(company, years, diagnostics, start_date=start_date, end_date=end_date)
        if rows:
            diagnostics.append(f"price provider selected: {provider_name}, rows={len(rows)}")
            return rows
    diagnostics.append(f"All valuation price providers returned 0 rows for {company.name} ({company.stock_code}/{company.yf_ticker}).")
    return []

def _rolling_average(values: list[float | None], window: int) -> list[float | None]:

    out: list[float | None] = []
    for i in range(len(values)):
        start = max(0, i + 1 - window)
        chunk = [v for v in values[start:i + 1] if v is not None]
        out.append(sum(chunk) / len(chunk) if chunk else None)
    return out


def _rolling_volatility(returns: list[float | None], window: int) -> list[float | None]:
  
    out: list[float | None] = []
    for i in range(len(returns)):
        start = max(0, i + 1 - window)
        chunk = [v for v in returns[start:i + 1] if v is not None]
        if len(chunk) < 2:
            out.append(0.0)
            continue
        mean = sum(chunk) / len(chunk)
        var = sum((x - mean) ** 2 for x in chunk) / (len(chunk) - 1)
        out.append((var ** 0.5) * (252 ** 0.5))
    return out


def _period_return(values: list[float | None], window: int, idx: int) -> float | None:
    # For early rows, compare against the first available close rather than
    # leaving 20/60/120-day return columns blank.
    base_idx = max(0, idx - window)
    cur = values[idx]
    prev = values[base_idx]
    if cur is None or prev in (None, 0):
        return None
    return cur / prev - 1.0


def enrich_price_history(price_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add return, drawdown, rolling-volatility, moving averages and technical ratios.

    This remains Valuation-Agent-only data. It is used by the workbook and dashboard
    so investors can download a richer valuation pack instead of only one DCF tab.
    """
    clean = [dict(r) for r in price_rows if _to_float(r.get("close")) is not None]
    clean.sort(key=lambda r: str(r.get("date") or ""))
    closes = [_to_float(r.get("close")) for r in clean]
    ma20 = _rolling_average(closes, 20)
    ma60 = _rolling_average(closes, 60)
    ma120 = _rolling_average(closes, 120)

    daily_returns: list[float | None] = []
    prev = None
    for close in closes:
        daily_returns.append((close / prev - 1.0) if close is not None and prev not in (None, 0) else 0.0)
        prev = close
    rolling_vol_20 = _rolling_volatility(daily_returns, 20)
    rolling_vol_60 = _rolling_volatility(daily_returns, 60)

    max_close = None
    min_close = None
    for i, row in enumerate(clean):
        close = closes[i]
        if close is not None:
            max_close = close if max_close is None else max(max_close, close)
            min_close = close if min_close is None else min(min_close, close)
        drawdown = (close / max_close - 1.0) if close is not None and max_close not in (None, 0) else None
        row["daily_return"] = daily_returns[i]
        row["drawdown"] = drawdown
        row["ma20"] = ma20[i]
        row["ma60"] = ma60[i]
        row["ma120"] = ma120[i]
        row["rolling_vol_20"] = rolling_vol_20[i]
        row["rolling_vol_60"] = rolling_vol_60[i]
        row["return_20d"] = _period_return(closes, 20, i)
        row["return_60d"] = _period_return(closes, 60, i)
        row["return_120d"] = _period_return(closes, 120, i)
        row["distance_to_ma20"] = (close / ma20[i] - 1.0) if close is not None and ma20[i] not in (None, 0) else None
        row["distance_to_ma60"] = (close / ma60[i] - 1.0) if close is not None and ma60[i] not in (None, 0) else None
        row["distance_to_ma120"] = (close / ma120[i] - 1.0) if close is not None and ma120[i] not in (None, 0) else None
        window_52 = [c for c in closes[max(0, i - 251):i + 1] if c is not None]
        high_52 = max(window_52) if window_52 else None
        low_52 = min(window_52) if window_52 else None
        row["rolling_high_52w"] = high_52
        row["rolling_low_52w"] = low_52
        row["price_to_52w_high"] = (close / high_52 - 1.0) if close is not None and high_52 not in (None, 0) else None
        row["price_to_52w_low"] = (close / low_52 - 1.0) if close is not None and low_52 not in (None, 0) else None
        volume = _to_float(row.get("volume"))
        row["trading_value"] = close * volume if close is not None and volume is not None else None
        value_window = [_to_float(x.get("trading_value")) for x in clean[max(0, i - 19):i + 1]]
        value_window = [x for x in value_window if x is not None]
        row["trading_value_ma20"] = sum(value_window) / len(value_window) if value_window else None
    return clean


def fetch_dart_share_counts(company: ListedCompany, years: int, diagnostics: list[str], start_date: str | date | datetime | None = None, end_date: str | date | datetime | None = None) -> list[dict[str, Any]]:
    """Collect share-count data from OpenDART stockTotqySttus endpoint.

    The endpoint can vary by year/company. The parser keeps both raw row fields
    and a normalized `shares_outstanding` candidate so the valuation model can
    compute market-cap and implied-price gaps when available.
    """
    api_key = _get_api_key()
    if not api_key or requests is None:
        diagnostics.append("DART share-count intake skipped: missing API key or requests package.")
        return []
    corp_code = resolve_dart_corp_code(company, diagnostics)
    if not corp_code:
        diagnostics.append(f"DART share-count corp_code not resolved for {company.name} ({company.stock_code}).")
        return []
    start, end = valuation_date_range(years=years, start_date=start_date, end_date=end_date)
    candidate_years = _year_range_from_dates(start, end)
    rows_out: list[dict[str, Any]] = []
    endpoint = "https://opendart.fss.or.kr/api/stockTotqySttus.json"
    for y in candidate_years:
        params = {"crtfc_key": api_key, "corp_code": corp_code, "bsns_year": str(y), "reprt_code": "11011"}
        try:
            resp = requests.get(endpoint, params=params, timeout=30)  # type: ignore[union-attr]
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            diagnostics.append(f"DART share-count fetch failed year={y}: {exc}")
            continue
        status = str(data.get("status", ""))
        if status != "000":
            msg = data.get("message") or data.get("msg") or status
            if status not in {"013", "014"}:
                diagnostics.append(f"DART share-count status={status} year={y}: {msg}")
            continue
        rows = data.get("list") or []
        if not isinstance(rows, list):
            continue
        for r in rows:
            if not isinstance(r, dict):
                continue
            label = str(r.get("se") or r.get("stock_knd") or r.get("stk_knd") or "").strip()
            # Prefer listed/common shares, but keep other rows too.
            candidates = [
                r.get("istc_totqy"),
                r.get("isu_stock_totqy"),
                r.get("now_to_isu_stock_totqy"),
                r.get("distb_stock_totqy"),
                r.get("stk_totqy"),
            ]
            shares = None
            for cand in candidates:
                shares = _to_float(cand)
                if shares is not None:
                    break
            rows_out.append({
                "source": "OpenDART_stockTotqySttus",
                "corp_code": corp_code,
                "company": company.name,
                "company_dir": company.slug,
                "stock_code": company.stock_code,
                "year": y,
                "share_class": label,
                "shares_outstanding": shares,
                "raw": json.dumps(r, ensure_ascii=False),
            })
            time.sleep(0.05)
    return rows_out


def latest_share_count(share_rows: list[dict[str, Any]]) -> dict[str, Any]:
    clean = [r for r in share_rows if _to_float(r.get("shares_outstanding")) is not None]
    if not clean:
        return {"shares_outstanding": None, "share_count_year": None, "share_count_source": None}
    def score(row: dict[str, Any]) -> tuple[int, int]:
        label = str(row.get("share_class") or "")
        common_bonus = 1 if ("보통" in label or "합계" in label or label == "") else 0
        try:
            year = int(row.get("year") or 0)
        except Exception:
            year = 0
        return (year, common_bonus)
    row = sorted(clean, key=score)[-1]
    return {
        "shares_outstanding": _to_float(row.get("shares_outstanding")),
        "share_count_year": row.get("year"),
        "share_count_class": row.get("share_class"),
        "share_count_source": row.get("source"),
    }


def compute_price_summary(price_rows: list[dict[str, Any]], shares_outstanding: float | None = None) -> dict[str, Any]:
    shares_outstanding = _to_float(shares_outstanding)
    clean = [r for r in price_rows if _to_float(r.get("close")) is not None]
    clean.sort(key=lambda r: str(r.get("date") or ""))
    if not clean:
        return {"latest_close": None, "return_1y": None, "volatility_annualized": None, "mdd": None, "price_rows": 0, "market_cap": None}
    latest = _to_float(clean[-1].get("close"))
    first = _to_float(clean[0].get("close"))
    ret_total = (latest / first - 1.0) if latest is not None and first not in (None, 0) else None
    one_year_cut = datetime.fromisoformat(str(clean[-1]["date"])).date() - timedelta(days=370)
    one_year_rows = [r for r in clean if str(r.get("date")) >= one_year_cut.isoformat()]
    first_1y = _to_float(one_year_rows[0].get("close")) if one_year_rows else first
    ret_1y = (latest / first_1y - 1.0) if latest is not None and first_1y not in (None, 0) else ret_total
    returns: list[float] = []
    max_close = None
    mdd = 0.0
    prev = None
    closes: list[float] = []
    for r in clean:
        c = _to_float(r.get("close"))
        if c is None or c <= 0:
            continue
        closes.append(c)
        if prev not in (None, 0):
            returns.append(c / prev - 1.0)
        prev = c
        max_close = c if max_close is None else max(max_close, c)
        if max_close:
            mdd = min(mdd, c / max_close - 1.0)
    vol = None
    if len(returns) >= 2:
        mean = sum(returns) / len(returns)
        var = sum((x - mean) ** 2 for x in returns) / (len(returns) - 1)
        vol = (var ** 0.5) * (252 ** 0.5)
    high_52w = max(closes[-252:]) if closes else None
    low_52w = min(closes[-252:]) if closes else None
    market_cap = latest * shares_outstanding if latest is not None and shares_outstanding is not None else None
    latest_volume = _to_float(clean[-1].get("volume"))
    latest_trading_value = latest * latest_volume if latest is not None and latest_volume is not None else None
    trading_values = [_to_float(r.get("trading_value")) for r in clean[-20:]]
    trading_values = [x for x in trading_values if x is not None]
    avg_trading_value_20d = sum(trading_values) / len(trading_values) if trading_values else None
    avg_volume_20d_rows = [_to_float(r.get("volume")) for r in clean[-20:]]
    avg_volume_20d_rows = [x for x in avg_volume_20d_rows if x is not None]
    avg_volume_20d = sum(avg_volume_20d_rows) / len(avg_volume_20d_rows) if avg_volume_20d_rows else None
    turnover_latest = latest_volume / shares_outstanding if latest_volume is not None and shares_outstanding not in (None, 0) else None
    turnover_20d = avg_volume_20d / shares_outstanding if avg_volume_20d is not None and shares_outstanding not in (None, 0) else None
    return {
        "latest_close": latest,
        "first_close": first,
        "return_total": ret_total,
        "return_1y": ret_1y,
        "volatility_annualized": vol,
        "mdd": mdd,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "shares_outstanding": shares_outstanding,
        "market_cap": market_cap,
        "latest_volume": latest_volume,
        "latest_trading_value": latest_trading_value,
        "avg_trading_value_20d": avg_trading_value_20d,
        "avg_volume_20d": avg_volume_20d,
        "turnover_latest": turnover_latest,
        "turnover_20d": turnover_20d,
        "price_rows": len(clean),
        "price_start": clean[0].get("date"),
        "price_end": clean[-1].get("date"),
    }


def _read_csv_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return []
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return [dict(r) for r in csv.DictReader(f)]
        except Exception:
            continue
    return []


def _first_existing_csv(paths: list[Path]) -> tuple[list[dict[str, Any]], Path | None]:
    for path in paths:
        rows = _read_csv_file(path)
        if rows:
            return rows, path
    return [], None


def _local_finance_dir(company: ListedCompany) -> Path:
    return company_agent_dir(company.slug, "finance", create=True)


def _local_valuation_intake_dir(company: ListedCompany) -> Path:
    return company_agent_dir(company.slug, "valuation", create=True) / "intake"


def load_local_financial_fallback(
    company: ListedCompany,
    *,
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
    diagnostics: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Load already-existing local finance CSVs and normalize them for Valuation.

    This does not replace live DART collection; it fills missing annual rows when
    OpenDART has no rows, rate-limits, or a company has not been mapped yet.
    """
    diagnostics = diagnostics if diagnostics is not None else []
    start, end = valuation_date_range(start_date=start_date, end_date=end_date)
    fdir = _local_finance_dir(company)
    candidates = [
        fdir / f"{company.name}_재무데이터.csv",
        fdir / f"{company.name}_재무.csv",
    ]
    candidates.extend(sorted(fdir.glob("*재무데이터*.csv")))
    candidates.extend(sorted(fdir.glob("*재무*.csv")))
    rows, used = _first_existing_csv(candidates)
    if not rows:
        diagnostics.append(f"local financial fallback skipped: no finance CSV for {company.name}.")
        return []

    out: list[dict[str, Any]] = []
    for r in rows:
        year_raw = r.get("year") or r.get("Year") or r.get("연도") or r.get("사업연도")
        try:
            year = int(float(str(year_raw).replace(",", "")))
        except Exception:
            continue
        if year < start.year or year > end.year:
            continue
        revenue = _to_float(r.get("revenue") or r.get("sales") or r.get("매출액") or r.get("수익(매출액)"))
        op = _to_float(r.get("operating_profit") or r.get("operating_income") or r.get("영업이익") or r.get("영업손익"))
        ni = _to_float(r.get("net_income") or r.get("당기순이익") or r.get("순이익"))
        assets = _to_float(r.get("assets") or r.get("total_assets") or r.get("자산총계"))
        liabilities = _to_float(r.get("liabilities") or r.get("total_liabilities") or r.get("부채총계"))
        equity = _to_float(r.get("equity") or r.get("total_equity") or r.get("자본총계"))
        cfo = _to_float(r.get("cfo") or r.get("ocf") or r.get("영업활동현금흐름"))
        capex = _to_float(r.get("capex") or r.get("CAPEX"))
        fcf = _to_float(r.get("fcf") or r.get("FCF"))
        if fcf is None and cfo is not None and capex is not None:
            fcf = cfo - abs(capex)
        cash = _to_float(r.get("cash") or r.get("현금및현금성자산"))
        out.append({
            "year": year,
            "revenue": revenue,
            "operating_profit": op,
            "net_income": ni,
            "assets": assets,
            "liabilities": liabilities,
            "equity": equity,
            "cash": cash,
            "cfo": cfo,
            "capex": abs(capex) if capex is not None else None,
            "fcf": fcf,
            "investing_cf": _to_float(r.get("investing_cf") or r.get("투자활동현금흐름")),
            "source_account_count": r.get("source_account_count") or "local_finance_csv",
            "revenue_source_account": "local_finance_csv",
            "operating_profit_source_account": "local_finance_csv",
            "net_income_source_account": "local_finance_csv",
            "assets_source_account": "local_finance_csv",
            "liabilities_source_account": "local_finance_csv",
            "equity_source_account": "local_finance_csv",
            "cfo_source_account": "local_finance_csv",
            "capex_source_account": "local_finance_csv",
            "cash_source_account": "local_finance_csv",
        })
    if out:
        diagnostics.append(f"local financial fallback loaded rows={len(out)} from {used}.")
    return out


def merge_financial_rows(primary: list[dict[str, Any]], fallback: list[dict[str, Any]], diagnostics: list[str] | None = None) -> list[dict[str, Any]]:
    diagnostics = diagnostics if diagnostics is not None else []
    by_year: dict[int, dict[str, Any]] = {}
    for row in fallback:
        try:
            year = int(row.get("year"))
        except Exception:
            continue
        by_year[year] = dict(row)
    for row in primary:
        try:
            year = int(row.get("year"))
        except Exception:
            continue
        base = by_year.setdefault(year, {})
        base["year"] = year
        for key, value in row.items():
            if value not in (None, "", "nan"):
                base[key] = value
    merged = [by_year[y] for y in sorted(by_year)]
    if fallback and len(merged) > len(primary):
        diagnostics.append(f"financial rows merged with local fallback: primary={len(primary)}, fallback={len(fallback)}, merged={len(merged)}.")
    return merged


def load_local_price_fallback(
    company: ListedCompany,
    *,
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
    diagnostics: list[str] | None = None,
) -> list[dict[str, Any]]:
    diagnostics = diagnostics if diagnostics is not None else []
    start, end = valuation_date_range(start_date=start_date, end_date=end_date)
    fdir = _local_finance_dir(company)
    idir = _local_valuation_intake_dir(company)
    candidates = [
        idir / "valuation_price_history.csv",
        fdir / f"{company.name}_stock.csv",
        fdir / f"{company.name}_주식.csv",
    ]
    candidates.extend(sorted(fdir.glob("*stock*.csv")))
    candidates.extend(sorted(fdir.glob("*주식*.csv")))
    candidates.extend(sorted(fdir.glob("*주가*.csv")))
    rows, used = _first_existing_csv(candidates)
    if not rows:
        diagnostics.append(f"local price fallback skipped: no local stock/price CSV for {company.name}.")
        return []
    normalized: list[dict[str, Any]] = []
    for r in rows:
        dt = r.get("date") or r.get("Date") or r.get("날짜") or r.get("일자")
        if not _date_in_range(dt, start, end):
            continue
        normalized.append({
            "date": _coerce_date_text(dt),
            "open": _to_float(r.get("open") or r.get("Open") or r.get("시가")),
            "high": _to_float(r.get("high") or r.get("High") or r.get("고가")),
            "low": _to_float(r.get("low") or r.get("Low") or r.get("저가")),
            "close": _to_float(r.get("close") or r.get("Close") or r.get("종가") or r.get("현재가")),
            "adj_close": _to_float(r.get("adj_close") or r.get("Adj Close") or r.get("수정종가") or r.get("close") or r.get("종가")),
            "volume": _to_float(r.get("volume") or r.get("Volume") or r.get("거래량")),
            "source": "local_price_csv_fallback",
            "ticker": company.yf_ticker or company.stock_code,
        })
    normalized = _dedupe_price_rows(normalized)
    if normalized:
        diagnostics.append(f"local price fallback loaded rows={len(normalized)} from {used}.")
    return normalized


def merge_price_rows(primary: list[dict[str, Any]], fallback: list[dict[str, Any]], diagnostics: list[str] | None = None) -> list[dict[str, Any]]:
    diagnostics = diagnostics if diagnostics is not None else []
    by_date: dict[str, dict[str, Any]] = {}
    for row in fallback:
        d = str(row.get("date") or "").strip()
        if d:
            by_date[d] = dict(row)
    for row in primary:
        d = str(row.get("date") or "").strip()
        if d:
            base = by_date.setdefault(d, {})
            for key, value in row.items():
                if value not in (None, "", "nan"):
                    base[key] = value
    merged = _dedupe_price_rows(list(by_date.values()))
    if fallback and len(merged) > len(primary):
        diagnostics.append(f"price rows merged with local fallback: primary={len(primary)}, fallback={len(fallback)}, merged={len(merged)}.")
    return merged


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for r in rows:
            for k in r.keys():
                if k not in fieldnames:
                    fieldnames.append(k)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return path


def fetch_naver_market_snapshot(company: ListedCompany, diagnostics: list[str]) -> dict[str, Any]:

    if requests is None or not company.stock_code:
        diagnostics.append("Naver market snapshot skipped: requests not installed or stock code missing.")
        return {}
    url = f"https://finance.naver.com/item/main.naver?code={company.stock_code}"
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        html = resp.content.decode("euc-kr", errors="ignore")
    except Exception as exc:
        diagnostics.append(f"Naver market snapshot fetch failed for {company.stock_code}: {exc}")
        return {}

    def clean_num(text: Any) -> float | None:
        return _to_float(str(text or "").replace("%", ""))

    snapshot: dict[str, Any] = {
        "source": "naver_finance_item_main",
        "company": company.name,
        "company_dir": company.slug,
        "stock_code": company.stock_code,
        "fetched_at_kst": _today_kst().isoformat(),
    }
    # Representative fields often appear as <em id="_per">, <em id="_pbr">, etc.
    id_map = {
        "per_naver": "_per",
        "pbr_naver": "_pbr",
        "eps_naver": "_eps",
        "bps_naver": "_bps",
        "dividend_yield_pct_naver": "_dvr",
    }
    for key, html_id in id_map.items():
        m = re.search(rf'id=["\\\']{re.escape(html_id)}["\\\'][^>]*>(.*?)<', html, flags=re.I | re.S)
        if m:
            snapshot[key] = clean_num(re.sub(r"<.*?>", "", m.group(1)).strip())
    # Fallback regex by Korean label nearby. This is deliberately conservative.
    label_patterns = {
        "per_naver": r"PER[^0-9\-]*([\-0-9,.]+)",
        "pbr_naver": r"PBR[^0-9\-]*([\-0-9,.]+)",
        "eps_naver": r"EPS[^0-9\-]*([\-0-9,.]+)",
        "bps_naver": r"BPS[^0-9\-]*([\-0-9,.]+)",
        "dividend_yield_pct_naver": r"배당수익률[^0-9\-]*([\-0-9,.]+)",
    }
    text = re.sub(r"<.*?>", " ", html)
    text = re.sub(r"\s+", " ", text)
    for key, pat in label_patterns.items():
        if snapshot.get(key) is not None:
            continue
        m = re.search(pat, text, flags=re.I)
        if m:
            snapshot[key] = clean_num(m.group(1))
    available = [k for k, v in snapshot.items() if k.endswith("_naver") and v is not None]
    snapshot["available_metric_count"] = len(available)
    snapshot["available_metrics"] = available
    if available:
        diagnostics.append(f"Naver market snapshot collected: {', '.join(available)}")
    else:
        diagnostics.append("Naver market snapshot collected no usable PER/PBR/EPS/BPS fields; continuing with DART-derived metrics.")
    return snapshot


def enrich_market_snapshot_with_derived_metrics(
    company: ListedCompany,
    latest_financial: dict[str, Any] | None,
    price_summary: dict[str, Any] | None,
    market_snapshot: dict[str, Any] | None,
    diagnostics: list[str],
) -> dict[str, Any]:
  
    latest = latest_financial or {}
    price = price_summary or {}
    snap = dict(market_snapshot or {})
    snap.setdefault("source", "naver_finance_item_main + valuation_derived_fallback")
    snap.setdefault("company", company.name)
    snap.setdefault("company_dir", company.slug)
    snap.setdefault("stock_code", company.stock_code)
    snap.setdefault("fetched_at_kst", _today_kst().isoformat())

    market_cap = _to_float(price.get("market_cap"))
    close = _to_float(price.get("latest_close"))
    shares = _to_float(price.get("shares_outstanding"))
    revenue = _to_float(latest.get("revenue"))
    equity = _to_float(latest.get("equity"))
    net_income = _to_float(latest.get("net_income"))
    operating_profit = _to_float(latest.get("operating_profit"))
    fcf = _to_float(latest.get("fcf"))
    cash = _to_float(latest.get("cash")) or 0.0
    liabilities = _to_float(latest.get("liabilities")) or 0.0
    enterprise_value = market_cap + liabilities - cash if market_cap is not None else None

    def div(a: Any, b: Any) -> float | None:
        x = _to_float(a)
        y = _to_float(b)
        if x is None or y in (None, 0):
            return None
        return x / y

    derived = {
        "latest_close_auto": close,
        "shares_outstanding_auto": shares,
        "market_cap_auto": market_cap,
        "enterprise_value_auto": enterprise_value,
        "eps_auto": div(net_income, shares),
        "bps_auto": div(equity, shares),
        "per_auto": div(market_cap, net_income) if net_income and net_income > 0 else None,
        "pbr_auto": div(market_cap, equity),
        "psr_auto": div(market_cap, revenue),
        "p_fcf_auto": div(market_cap, fcf) if fcf and fcf > 0 else None,
        "ev_sales_auto": div(enterprise_value, revenue),
        "ev_ebit_auto": div(enterprise_value, operating_profit) if operating_profit and operating_profit > 0 else None,
        "fcf_yield_auto": div(fcf, market_cap),
        "sales_yield_auto": div(revenue, market_cap),
    }
    for k, v in derived.items():
        if v is not None:
            snap[k] = v

    # Keep live Naver metrics when available, otherwise mirror the derived values
    # into display-friendly aliases and explicitly state the provenance.
    alias_pairs = {
        "per_naver": "per_auto",
        "pbr_naver": "pbr_auto",
        "eps_naver": "eps_auto",
        "bps_naver": "bps_auto",
    }
    for naver_key, auto_key in alias_pairs.items():
        if snap.get(naver_key) is None and snap.get(auto_key) is not None:
            snap[naver_key] = snap.get(auto_key)
            snap[f"{naver_key}_source"] = "DART/price derived fallback"
        elif snap.get(naver_key) is not None:
            snap[f"{naver_key}_source"] = "Naver Finance live display"

    available = [
        k for k, v in snap.items()
        if (k.endswith("_naver") or k.endswith("_auto")) and v is not None
    ]
    snap["available_metric_count"] = len(available)
    snap["available_metrics"] = available
    snap["snapshot_status_kr"] = "실시간/보조 산출 혼합 확보" if available else "보조 산출값 없음"
    snap["derivation_note_kr"] = "Naver 원천값이 없으면 DART 재무제표와 Valuation 주가/발행주식 수로 PER/PBR/EPS/BPS/PSR 등을 자동 산출합니다."
    if available:
        diagnostics.append(f"Market snapshot enriched with live/derived metrics count={len(available)}.")
    else:
        diagnostics.append("Market snapshot enrichment produced no usable metrics; check DART/price/share-count intake.")
    return snap

# === ALPHAPROVE_UNIVERSE30_DYNAMIC_METADATA_START ===
# Added by scripts/patch_universe30_dynamic_metadata.py
# Purpose: keep Valuation Agent code generic. New companies are resolved from
# data/반도체/_sector_common/universe/*.csv or data/반도체/<회사>/_company_common/company.yaml.
try:
    from common.company_metadata import get_company_metadata

    _alphaprove_static_resolve_company = resolve_company

    def resolve_company(company_dir: str, company: str | None = None) -> ListedCompany:  # type: ignore[no-redef]
        meta = get_company_metadata(company_dir or company or "", company)
        if meta and meta.stock_code:
            return ListedCompany(
                slug=meta.slug,
                name=meta.name,
                stock_code=meta.stock_code,
                market=meta.market or "KOSDAQ",
                yf_ticker=meta.yf_ticker,
            )
        return _alphaprove_static_resolve_company(company_dir, company)

except Exception:
    pass
# === ALPHAPROVE_UNIVERSE30_DYNAMIC_METADATA_END ===
