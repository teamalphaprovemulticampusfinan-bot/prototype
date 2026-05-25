from __future__ import annotations

import html
import re
from typing import Any

import requests
from .config import (
    CORP_CODES,
    DART_API_KEY,
    MARKET_ENABLE_NAVER_NEWS,
    MARKET_ENABLE_NEWS_API,
    NAVER_CLIENT_ID,
    NAVER_CLIENT_SECRET,
    NEWS_API_KEY,
    OECD_REGIONS,
    REQUEST_TIMEOUT,
    resolve_company_key,
    TICKERS,
)
from .data_loader import WorkbookData, fallback_oecd_from_excel
from .stock_quote_providers import fetch_stock_quote


def _safe_get(url: str, **kwargs) -> requests.Response:
    timeout = kwargs.pop("timeout", REQUEST_TIMEOUT)
    return requests.get(url, timeout=timeout, **kwargs)


def _strip_html(text: Any) -> str:
    if text is None:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", str(text))
    cleaned = html.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def fetch_stock(company: str) -> dict:
    company_key = resolve_company_key(company)
    ticker = TICKERS.get(company) or TICKERS.get(company_key, "")
    try:
        quote = fetch_stock_quote(company, ticker, timeout=REQUEST_TIMEOUT)
        provider = quote.get("provider", "unknown")
        price = quote.get("current_price", 0)
        print(f"  [{company}] 주가 provider={provider}, current_price={price}")
        return quote
    except Exception as e:
        print(f"  [{company}] 주가 오류: {e}")
        return {
            "provider": "none",
            "ticker": ticker,
            "current_price": 0,
            "warning_stock": str(e),
        }


def _get_oecd_fallback(workbook: WorkbookData) -> dict:
    try:
        data = fallback_oecd_from_excel(workbook)
        if isinstance(data, dict) and data:
            return data
    except Exception:
        pass
    return {"G20": 0, "한국": 0, "미국": 0, "중국": 0}


def _extract_latest_oecd_value(data: dict) -> float:
    # 신규 구조: data.dataSets 또는 data.data
    datasets = data.get("dataSets") or data.get("data", {}).get("dataSets") or []

    # 그래도 없으면 data 키 직접 탐색
    if not datasets:
        data_block = data.get("data") or {}
        datasets = data_block.get("dataSets") or []

    if not datasets:
        raise KeyError("dataSets")

    series = datasets[0].get("series") or {}
    if not series:
        raise KeyError("series")

    if "0:0:0" in series:
        observations = series["0:0:0"].get("observations") or {}
    else:
        first_key = next(iter(series))
        observations = series[first_key].get("observations") or {}

    if not observations:
        raise KeyError("observations")

    latest_key = sorted(observations.keys())[-1]
    latest_row = observations[latest_key]
    if not latest_row:
        raise ValueError("empty observation row")
    return round(float(latest_row[0]), 2)


def fetch_oecd(workbook: WorkbookData) -> dict:
    result: dict[str, float] = {}
    fallback = _get_oecd_fallback(workbook)

    for name, code in OECD_REGIONS.items():
        url = (
            "https://stats.oecd.org/sdmx-json/data/"
            f"MEI_CLI/LOLITOAA.{code}.M/all?lastNObservations=3"
        )
        try:
            r = _safe_get(url, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            result[name] = _extract_latest_oecd_value(data)
        except Exception as e:
            print(f"  [OECD:{name}] 오류: {e} -> fallback 사용")
            result[name] = fallback.get(name, 0)

    return result


def fetch_dart_subsidy(company: str) -> dict:
    try:
        company_key = resolve_company_key(company)
        code = CORP_CODES.get(company) or CORP_CODES.get(company_key, "")
        r = _safe_get(
            "https://opendart.fss.or.kr/api/list.json",
            params={
                "crtfc_key": DART_API_KEY,
                "corp_code": code,
                "pblntf_ty": "A",
                "last_reprt_at": "Y",
            },
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        items = r.json().get("list", [])
        if items:
            return {
                "latest_report": items[0].get("report_nm", ""),
                "date": items[0].get("rcept_dt", ""),
            }
        return {}
    except Exception as e:
        print(f"  [{company}] DART 오류: {e}")
        return {}


def _fetch_naver_market_news(keyword: str, *, limit: int = 10) -> list[dict]:
    if not MARKET_ENABLE_NAVER_NEWS:
        return []

    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("  [Market Naver News 안내] NAVER_CLIENT_ID/NAVER_CLIENT_SECRET이 없어 네이버 뉴스 호출을 건너뜁니다.")
        return []

    try:
        r = _safe_get(
            "https://openapi.naver.com/v1/search/news.json",
            headers={
                "X-Naver-Client-Id": NAVER_CLIENT_ID,
                "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
            },
            params={
                "query": keyword,
                "display": max(1, min(int(limit), 100)),
                "start": 1,
                "sort": "date",
            },
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        items = r.json().get("items", []) or []
    except Exception as e:
        print(f"  네이버 뉴스 오류: {e}")
        return []

    return [
        {
            "title": _strip_html(item.get("title")),
            "date": str(item.get("pubDate", ""))[:16],
            "source": "Naver News",
            "url": item.get("originallink") or item.get("link") or "",
            "description": _strip_html(item.get("description")),
        }
        for item in items
    ]


def _fetch_newsapi_market_news(keyword: str, *, limit: int = 10) -> list[dict]:
    """
    NewsAPI 예비 코드입니다.

    현재는 429 Too Many Requests가 자주 발생하므로 MARKET_ENABLE_NEWS_API=0을 권장합니다.
    나중에 NewsAPI 키가 정상화되면 .env에서 MARKET_ENABLE_NEWS_API=1로 바꿔 다시 사용할 수 있습니다.
    """
    if not MARKET_ENABLE_NEWS_API:
        return []

    if not NEWS_API_KEY:
        print("  [Market NewsAPI 안내] NEWS_API_KEY가 없어 NewsAPI 호출을 건너뜁니다.")
        return []

    try:
        r = _safe_get(
            "https://newsapi.org/v2/everything",
            params={
                "q": keyword,
                "language": "ko",
                "sortBy": "publishedAt",
                "pageSize": max(1, min(int(limit), 100)),
                "apiKey": NEWS_API_KEY,
            },
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        articles = r.json().get("articles", []) or []
    except Exception as e:
        print(f"  뉴스 오류: {e}")
        return []

    return [
        {
            "title": _strip_html(a.get("title")),
            "date": str(a.get("publishedAt", ""))[:10],
            "source": (a.get("source") or {}).get("name") or "NewsAPI",
            "url": a.get("url") or "",
            "description": _strip_html(a.get("description")),
        }
        for a in articles
    ]


def fetch_market_news(keyword: str = "반도체 업황") -> list[dict]:
    """
    Market Agent 뉴스 수집.

    우선순위:
    1. 네이버 뉴스 API
    2. NewsAPI 예비 코드(기본 OFF)

    뉴스 수집이 실패해도 []를 반환하므로 주가/OECD/DART/엑셀 기반 분석은 계속 진행됩니다.
    """
    naver_items = _fetch_naver_market_news(keyword, limit=10)
    if naver_items:
        return naver_items[:10]

    # NewsAPI는 429 방지를 위해 기본 비활성화되어 있습니다.
    # 필요 시 .env에서 MARKET_ENABLE_NEWS_API=1로 바꾸면 아래 예비 코드가 동작합니다.
    newsapi_items = _fetch_newsapi_market_news(keyword, limit=10)
    return newsapi_items[:10]
