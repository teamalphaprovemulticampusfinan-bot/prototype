from __future__ import annotations

import os
import re
from typing import Any, Callable
from urllib.parse import unquote

import requests


PUBLIC_DATA_PORTAL_API_KEY = os.getenv("PUBLIC_DATA_PORTAL_API_KEY", "").strip()
FMP_API_KEY = os.getenv("FMP_API_KEY", "").strip()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "").strip()
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()

MARKET_STOCK_PROVIDER_ORDER = os.getenv(
    "MARKET_STOCK_PROVIDER_ORDER",
    "public_data,fmp,finnhub,alpha_vantage",
).strip()


def _safe_get(url: str, *, timeout: int = 15, **kwargs: Any) -> requests.Response:
    return requests.get(url, timeout=timeout, **kwargs)


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default

    text = str(value).strip()
    if not text:
        return default

    text = text.replace(",", "")

    try:
        return float(text)
    except ValueError:
        return default


def _to_int_if_possible(value: float) -> int | float:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _extract_krx_code(ticker: str) -> str:
    """
    예:
    - 042700.KQ -> 042700
    - 005930.KS -> 005930
    - 042700 -> 042700
    """
    if not ticker:
        return ""

    match = re.search(r"(\d{6})", str(ticker))
    return match.group(1) if match else ""


def _normalize_yahoo_ticker(ticker: str, krx_code: str = "") -> str:
    """
    yfinance/Yahoo chart API용 ticker 보정.

    이미 042700.KQ, 005930.KS처럼 들어오면 그대로 사용.
    6자리 코드만 있으면 우선 KQ가 아니라 판단이 어렵기 때문에 그대로 반환하지 않고,
    호출부에서 원래 ticker를 쓰도록 둔다.
    """
    ticker = (ticker or "").strip()

    if ticker:
        return ticker

    if krx_code:
        return f"{krx_code}.KS"

    return ""


def _provider_order() -> list[str]:
    raw = MARKET_STOCK_PROVIDER_ORDER or "public_data,fmp,finnhub,alpha_vantage"

    providers = [
        item.strip().lower()
        for item in raw.split(",")
        if item.strip()
    ]

    # yfinance는 명시하지 않아도 마지막 fallback으로 붙입니다.
    if "yfinance" not in providers:
        providers.append("yfinance")

    return providers


def _base_quote(
    *,
    provider: str,
    company: str,
    ticker: str,
    krx_code: str,
    current_price: float,
    currency: str = "KRW",
    as_of: str = "",
    change: float | None = None,
    change_rate: float | None = None,
    warning_stock: str = "",
    raw: Any | None = None,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "company": company,
        "ticker": ticker,
        "krx_code": krx_code,
        "current_price": _to_int_if_possible(current_price),
        "currency": currency,
        "as_of": as_of,
        "change": None if change is None else _to_int_if_possible(change),
        "change_rate": change_rate,
        "warning_stock": warning_stock,
        "raw": raw,
    }


def _get_public_data_service_key() -> str:
    """
    공공데이터포털 인증키는 Decoding 키 사용을 권장합니다.

    Encoding 키를 넣어도 일부 환경에서 동작하도록 unquote를 적용합니다.
    """
    key = PUBLIC_DATA_PORTAL_API_KEY.strip()
    if not key:
        return ""

    return unquote(key)


def fetch_public_data_quote(
    company: str,
    ticker: str,
    *,
    timeout: int = 15,
) -> dict[str, Any]:
    krx_code = _extract_krx_code(ticker)
    service_key = _get_public_data_service_key()

    if not service_key:
        raise RuntimeError("PUBLIC_DATA_PORTAL_API_KEY가 비어 있습니다.")

    if not krx_code:
        raise RuntimeError(f"KRX 6자리 종목코드를 추출할 수 없습니다. ticker={ticker!r}")

    url = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"

    params = {
        "serviceKey": service_key,
        "resultType": "json",
        "numOfRows": 10,
        "pageNo": 1,
        "likeSrtnCd": krx_code,
    }

    response = _safe_get(url, params=params, timeout=timeout)
    response.raise_for_status()

    data = response.json()
    body = (data.get("response") or {}).get("body") or {}
    items = (body.get("items") or {}).get("item") or []

    if isinstance(items, dict):
        items = [items]

    if not items:
        raise RuntimeError(f"공공데이터포털에서 종목 시세를 찾지 못했습니다. krx_code={krx_code}")

    # 동일 코드가 여러 개 올 가능성은 낮지만, 정확히 srtnCd가 같은 항목을 우선 선택
    selected = None
    for item in items:
        if str(item.get("srtnCd", "")).strip() == krx_code:
            selected = item
            break

    if selected is None:
        selected = items[0]

    price = _to_float(selected.get("clpr"))
    if price <= 0:
        raise RuntimeError(f"공공데이터포털 종가(clpr)가 비어 있습니다. krx_code={krx_code}")

    return _base_quote(
        provider="public_data",
        company=company,
        ticker=ticker,
        krx_code=krx_code,
        current_price=price,
        currency="KRW",
        as_of=str(selected.get("basDt", "")),
        change=_to_float(selected.get("vs")) if selected.get("vs") is not None else None,
        change_rate=_to_float(selected.get("fltRt")) if selected.get("fltRt") is not None else None,
        raw=selected,
    )


def fetch_fmp_quote(
    company: str,
    ticker: str,
    *,
    timeout: int = 15,
) -> dict[str, Any]:
    if not FMP_API_KEY:
        raise RuntimeError("FMP_API_KEY가 비어 있습니다.")

    if not ticker:
        raise RuntimeError("ticker가 비어 있어 FMP 조회를 건너뜁니다.")

    krx_code = _extract_krx_code(ticker)

    url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}"
    params = {
        "apikey": FMP_API_KEY,
    }

    response = _safe_get(url, params=params, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list) or not data:
        raise RuntimeError(f"FMP에서 종목 시세를 찾지 못했습니다. ticker={ticker}")

    item = data[0]
    price = _to_float(item.get("price"))

    if price <= 0:
        raise RuntimeError(f"FMP price가 비어 있습니다. ticker={ticker}")

    return _base_quote(
        provider="fmp",
        company=company,
        ticker=ticker,
        krx_code=krx_code,
        current_price=price,
        currency=str(item.get("currency", "") or ""),
        as_of=str(item.get("timestamp", "") or ""),
        change=_to_float(item.get("change")) if item.get("change") is not None else None,
        change_rate=_to_float(item.get("changesPercentage")) if item.get("changesPercentage") is not None else None,
        raw=item,
    )


def fetch_finnhub_quote(
    company: str,
    ticker: str,
    *,
    timeout: int = 15,
) -> dict[str, Any]:
    if not FINNHUB_API_KEY:
        raise RuntimeError("FINNHUB_API_KEY가 비어 있습니다.")

    if not ticker:
        raise RuntimeError("ticker가 비어 있어 Finnhub 조회를 건너뜁니다.")

    krx_code = _extract_krx_code(ticker)

    url = "https://finnhub.io/api/v1/quote"
    params = {
        "symbol": ticker,
        "token": FINNHUB_API_KEY,
    }

    response = _safe_get(url, params=params, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    price = _to_float(data.get("c"))
    if price <= 0:
        raise RuntimeError(f"Finnhub 현재가(c)가 비어 있습니다. ticker={ticker}")

    previous_close = _to_float(data.get("pc"))
    change = price - previous_close if previous_close > 0 else None
    change_rate = (change / previous_close * 100) if previous_close > 0 and change is not None else None

    return _base_quote(
        provider="finnhub",
        company=company,
        ticker=ticker,
        krx_code=krx_code,
        current_price=price,
        currency="",
        as_of=str(data.get("t", "") or ""),
        change=change,
        change_rate=change_rate,
        raw=data,
    )


def fetch_alpha_vantage_quote(
    company: str,
    ticker: str,
    *,
    timeout: int = 15,
) -> dict[str, Any]:
    if not ALPHA_VANTAGE_API_KEY:
        raise RuntimeError("ALPHA_VANTAGE_API_KEY가 비어 있습니다.")

    if not ticker:
        raise RuntimeError("ticker가 비어 있어 Alpha Vantage 조회를 건너뜁니다.")

    krx_code = _extract_krx_code(ticker)

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": ticker,
        "apikey": ALPHA_VANTAGE_API_KEY,
    }

    response = _safe_get(url, params=params, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    if "Note" in data:
        raise RuntimeError(f"Alpha Vantage 호출 제한 또는 안내 메시지: {data.get('Note')}")

    if "Information" in data:
        raise RuntimeError(f"Alpha Vantage 안내 메시지: {data.get('Information')}")

    quote = data.get("Global Quote") or {}
    price = _to_float(quote.get("05. price"))

    if price <= 0:
        raise RuntimeError(f"Alpha Vantage price가 비어 있습니다. ticker={ticker}")

    return _base_quote(
        provider="alpha_vantage",
        company=company,
        ticker=ticker,
        krx_code=krx_code,
        current_price=price,
        currency="",
        as_of=str(quote.get("07. latest trading day", "") or ""),
        change=_to_float(quote.get("09. change")) if quote.get("09. change") is not None else None,
        change_rate=_to_float(str(quote.get("10. change percent", "")).replace("%", ""))
        if quote.get("10. change percent") is not None
        else None,
        raw=quote,
    )


def fetch_yfinance_quote(
    company: str,
    ticker: str,
    *,
    timeout: int = 15,
) -> dict[str, Any]:
    """
    yfinance 패키지를 설치하지 않고 Yahoo Finance chart API를 직접 호출하는 fallback입니다.
    """
    krx_code = _extract_krx_code(ticker)
    yahoo_ticker = _normalize_yahoo_ticker(ticker, krx_code)

    if not yahoo_ticker:
        raise RuntimeError("ticker가 비어 있어 yfinance fallback 조회를 건너뜁니다.")

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_ticker}"
    params = {
        "range": "5d",
        "interval": "1d",
    }

    response = _safe_get(url, params=params, timeout=timeout)
    response.raise_for_status()

    data = response.json()
    result = ((data.get("chart") or {}).get("result") or [])

    if not result:
        error = (data.get("chart") or {}).get("error")
        raise RuntimeError(f"Yahoo Finance 결과가 비어 있습니다. ticker={yahoo_ticker}, error={error}")

    item = result[0]
    meta = item.get("meta") or {}

    price = _to_float(meta.get("regularMarketPrice"))

    timestamps = item.get("timestamp") or []
    indicators = item.get("indicators") or {}
    quote_items = indicators.get("quote") or []
    close_values = []

    if quote_items:
        close_values = quote_items[0].get("close") or []

    if price <= 0 and close_values:
        valid_closes = [
            _to_float(value)
            for value in close_values
            if value is not None and _to_float(value) > 0
        ]
        if valid_closes:
            price = valid_closes[-1]

    if price <= 0:
        raise RuntimeError(f"Yahoo Finance 현재가를 찾지 못했습니다. ticker={yahoo_ticker}")

    as_of = ""
    if timestamps:
        as_of = str(timestamps[-1])

    return _base_quote(
        provider="yfinance",
        company=company,
        ticker=ticker,
        krx_code=krx_code,
        current_price=price,
        currency=str(meta.get("currency", "") or ""),
        as_of=as_of,
        raw={
            "symbol": yahoo_ticker,
            "meta": meta,
        },
    )


_PROVIDER_FUNCTIONS: dict[str, Callable[..., dict[str, Any]]] = {
    "public_data": fetch_public_data_quote,
    "fmp": fetch_fmp_quote,
    "finnhub": fetch_finnhub_quote,
    "alpha_vantage": fetch_alpha_vantage_quote,
    "yfinance": fetch_yfinance_quote,
}


def fetch_stock_quote(
    company: str,
    ticker: str,
    *,
    timeout: int = 15,
) -> dict[str, Any]:
    """
    sources.py에서 호출하는 메인 함수입니다.

    provider 순서:
    .env의 MARKET_STOCK_PROVIDER_ORDER 값을 따름.
    기본값:
    public_data -> fmp -> finnhub -> alpha_vantage -> yfinance

    모든 provider가 실패하면 RuntimeError를 발생시킵니다.
    sources.py의 fetch_stock()에서 이 오류를 잡아 warning_stock으로 반환합니다.
    """
    errors: list[str] = []

    for provider in _provider_order():
        fetcher = _PROVIDER_FUNCTIONS.get(provider)

        if fetcher is None:
            errors.append(f"{provider}: 알 수 없는 provider")
            continue

        try:
            quote = fetcher(company, ticker, timeout=timeout)

            if quote.get("current_price", 0):
                if errors:
                    quote["provider_errors"] = errors
                return quote

            errors.append(f"{provider}: current_price가 비어 있음")

        except Exception as exc:
            errors.append(f"{provider}: {exc}")

    joined_errors = " | ".join(errors)
    raise RuntimeError(f"모든 주가 provider 조회 실패: {joined_errors}")