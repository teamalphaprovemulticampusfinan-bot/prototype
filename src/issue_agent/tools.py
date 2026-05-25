from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import feedparser
import pandas as pd
import requests

from .config import (
    COMPANY_RSS_KEYWORDS,
    DEFAULT_RSS_KEYWORDS,
    RSS_SOURCES,
    SETTINGS,
)


def _safe_get(url: str, **kwargs) -> requests.Response:
    """
    requests.get 공통 래퍼입니다.
    REQUEST_TIMEOUT 환경변수를 기본 timeout으로 사용합니다.
    """
    timeout = kwargs.pop("timeout", SETTINGS.request_timeout)

    headers = kwargs.pop("headers", {}) or {}
    headers.setdefault("User-Agent", "Mozilla/5.0")

    return requests.get(url, timeout=timeout, headers=headers, **kwargs)


def _strip_html(text: Any) -> str:
    """
    네이버 뉴스 title/description에 포함되는 HTML 태그와 엔티티를 제거합니다.
    """
    if text is None:
        return ""

    cleaned = re.sub(r"<[^>]+>", " ", str(text))
    cleaned = html.unescape(cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def _contains_any(text: str, keywords: list[str]) -> bool:
    lower = str(text or "").lower()
    return any(str(keyword).lower() in lower for keyword in keywords if keyword)


def _safe_date(value: Any) -> str:
    if not value:
        return ""
    return str(value)[:60]


def get_company_rss_keywords(company_name: str) -> list[str]:
    """
    회사명 + 회사별 커스텀 키워드 + 기본 반도체 키워드를 병합합니다.
    runner.py의 filter_rss_for_company()에서 사용합니다.
    """
    custom = COMPANY_RSS_KEYWORDS.get(company_name, [])
    merged = [company_name, *custom, *DEFAULT_RSS_KEYWORDS]

    seen: set[str] = set()
    result: list[str] = []

    for keyword in merged:
        lowered = str(keyword).lower().strip()
        if lowered and lowered not in seen:
            seen.add(lowered)
            result.append(str(keyword))

    return result


def download_excel_if_needed() -> Path:
    """
    이슈 키워드 엑셀 파일이 없으면 다운로드합니다.
    현재 runner.py는 excel_loader.py를 사용하지만,
    기존 호환성을 위해 유지합니다.
    """
    path = Path(SETTINGS.excel_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and path.stat().st_size > 0:
        return path

    try:
        response = _safe_get(SETTINGS.excel_url)
        response.raise_for_status()
        path.write_bytes(response.content)
    except Exception as exc:
        print(f"  엑셀 다운로드 오류: {exc}")

    return path


def load_issue_keywords() -> pd.DataFrame:
    """
    기존 코드 호환용 함수입니다.
    """
    path = download_excel_if_needed()

    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()

    try:
        return pd.read_excel(path)
    except Exception as exc:
        print(f"  엑셀 로드 오류: {exc}")
        return pd.DataFrame()


def filter_company_keywords(df: pd.DataFrame, company_name: str) -> list[dict[str, Any]]:
    """
    기존 코드 호환용 함수입니다.
    """
    if df.empty:
        return []

    company_col = None
    for col in df.columns:
        col_text = str(col)
        if "기업" in col_text or "company" in col_text.lower():
            company_col = col
            break

    if company_col is None:
        return []

    filtered = df[df[company_col].astype(str).str.contains(company_name, case=False, na=False)]
    if filtered.empty:
        return []

    return filtered.fillna("").to_dict("records")


def _naver_news_search(
    query: str,
    *,
    display: int = 10,
    sort: str = "date",
) -> list[dict[str, Any]]:
    """
    News_Realtime.ipynb에서 쓰던 네이버 뉴스 검색 방식을 로컬 코드로 옮긴 함수입니다.

    필요 환경변수:
    - ISSUE_ENABLE_NAVER_NEWS=1
    - NAVER_CLIENT_ID=...
    - NAVER_CLIENT_SECRET=...

    네이버 API 키가 없거나 호출에 실패하면 빈 리스트를 반환합니다.
    이렇게 해야 RSS/엑셀 기반 분석이 계속 진행됩니다.
    """
    if not SETTINGS.enable_naver_news:
        return []

    if not SETTINGS.naver_client_id or not SETTINGS.naver_client_secret:
        print("  [Naver News 안내] NAVER_CLIENT_ID/NAVER_CLIENT_SECRET이 없어 네이버 뉴스 호출을 건너뜁니다.")
        return []

    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": SETTINGS.naver_client_id,
        "X-Naver-Client-Secret": SETTINGS.naver_client_secret,
    }
    params = {
        "query": query,
        "display": max(1, min(int(display), 100)),
        "start": 1,
        "sort": sort,
    }

    try:
        response = _safe_get(url, headers=headers, params=params)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(f"  네이버 뉴스 오류: {exc}")
        return []

    rows: list[dict[str, Any]] = []

    for item in payload.get("items", []) or []:
        title = _strip_html(item.get("title"))
        description = _strip_html(item.get("description"))
        link = item.get("originallink") or item.get("link") or ""

        rows.append(
            {
                "source": "Naver News",
                "title": title,
                "summary": description,
                "description": description,
                "content": description,
                "url": link,
                "link": link,
                "published": _safe_date(item.get("pubDate")),
                "published_at": _safe_date(item.get("pubDate")),
            }
        )

    return rows


def _newsapi_search(
    query: str,
    *,
    page_size: int = 10,
) -> list[dict[str, Any]]:
    """
    NewsAPI 예비 코드입니다.

    현재는 429 Too Many Requests가 자주 발생하므로 ISSUE_ENABLE_NEWS_API=0을 권장합니다.
    나중에 NewsAPI 키가 정상화되면 .env에서 ISSUE_ENABLE_NEWS_API=1로 바꿔 다시 사용할 수 있습니다.
    """
    if not SETTINGS.enable_news_api:
        return []

    if not SETTINGS.news_api_key:
        print("  [NewsAPI 안내] NEWS_API_KEY가 없어 NewsAPI 호출을 건너뜁니다.")
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": max(1, min(int(page_size), 100)),
        "apiKey": SETTINGS.news_api_key,
    }

    try:
        response = _safe_get(url, params=params)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 429:
            print("  [NewsAPI 경고] 호출 한도 초과(429)로 NewsAPI 결과를 생략합니다.")
            return []
        print(f"  [NewsAPI 경고] HTTP 오류로 NewsAPI 결과를 생략합니다: {exc}")
        return []
    except requests.exceptions.RequestException as exc:
        print(f"  [NewsAPI 경고] 요청 실패로 NewsAPI 결과를 생략합니다: {exc}")
        return []
    except Exception as exc:
        print(f"  [NewsAPI 경고] JSON 파싱 실패 또는 기타 오류로 NewsAPI 결과를 생략합니다: {exc}")
        return []

    rows: list[dict[str, Any]] = []

    for item in payload.get("articles", []) or []:
        source = item.get("source") or {}
        source_name = source.get("name") if isinstance(source, dict) else "NewsAPI"

        title = _strip_html(item.get("title"))
        description = _strip_html(item.get("description"))

        rows.append(
            {
                "source": source_name or "NewsAPI",
                "title": title,
                "summary": description,
                "description": description,
                "content": description,
                "url": item.get("url") or "",
                "link": item.get("url") or "",
                "published": _safe_date(item.get("publishedAt")),
                "published_at": _safe_date(item.get("publishedAt")),
            }
        )

    return rows


def fetch_news_for_company(
    company_name: str,
    page_size: int = 10,
) -> list[dict[str, Any]]:
    """
    Issue Agent용 회사 뉴스 수집 함수입니다.

    우선순위:
    1. 네이버 뉴스 API
    2. NewsAPI 예비 코드

    NewsAPI는 현재 429 방지를 위해 기본 OFF입니다.
    .env에서 ISSUE_ENABLE_NEWS_API=1로 바꾸면 다시 사용할 수 있습니다.

    두 API 모두 실패해도 빈 리스트를 반환해서
    RSS/엑셀 기반 분석이 계속 진행되도록 합니다.
    """
    news_items: list[dict[str, Any]] = []

    # 1순위: 네이버 뉴스 API
    news_items.extend(
        _naver_news_search(
            f"{company_name} 주가 실적 투자 이슈",
            display=page_size,
            sort="date",
        )
    )

    # 2순위: NewsAPI 예비 코드
    # 현재는 ISSUE_ENABLE_NEWS_API=0이면 자동으로 실행되지 않습니다.
    if not news_items:
        news_items.extend(
            _newsapi_search(
                company_name,
                page_size=page_size,
            )
        )

    return news_items[:page_size]


def fetch_rss_articles(max_entries_per_feed: int = 15) -> list[dict[str, Any]]:
    """
    runner.py가 import하는 RSS 원문 수집 함수입니다.

    기존 patch에서 이 함수가 빠져 ImportError가 발생했습니다.
    따라서 반드시 tools.py 안에 있어야 합니다.
    """
    articles: list[dict[str, Any]] = []

    for source_name, url in RSS_SOURCES.items():
        try:
            response = _safe_get(url)
            feed = feedparser.parse(response.text)
        except Exception as exc:
            print(f"[RSS 경고] {source_name} 파싱 실패: {exc}")
            continue

        for entry in feed.entries[:max_entries_per_feed]:
            title = _strip_html(entry.get("title", ""))
            summary = _strip_html(entry.get("summary", ""))
            link = entry.get("link", "")
            published = (
                entry.get("published")
                or entry.get("updated")
                or entry.get("pubDate")
                or ""
            )

            articles.append(
                {
                    "source": source_name,
                    "title": title,
                    "summary": summary,
                    "description": summary,
                    "content": summary,
                    "link": link,
                    "url": link,
                    "published": _safe_date(published),
                    "published_at": _safe_date(published),
                }
            )

    return articles


def _normalize_news_data(news_data: Any) -> list[Any]:
    """
    filter_rss_for_company() 입력값을 list 형태로 정규화합니다.
    """
    if news_data is None:
        return []

    if isinstance(news_data, pd.DataFrame):
        return news_data.to_dict(orient="records")

    if isinstance(news_data, dict):
        return [news_data]

    if isinstance(news_data, list):
        return news_data

    return [news_data]


def filter_rss_for_company(company_name: str, news_data: Any) -> list[dict[str, Any]]:
    """
    runner.py가 import하는 RSS 필터링 함수입니다.

    회사명 또는 회사별 키워드가 제목/요약/본문에 포함된 RSS 기사만 반환합니다.
    """
    company = str(company_name or "").strip().lower()
    keywords = [str(k).lower() for k in get_company_rss_keywords(company_name)]

    articles = _normalize_news_data(news_data)
    filtered: list[dict[str, Any]] = []

    for article in articles:
        if isinstance(article, str):
            item = {
                "title": article,
                "content": article,
                "summary": article,
            }
        elif isinstance(article, dict):
            item = article
        else:
            item = {
                "title": str(article),
                "content": str(article),
                "summary": str(article),
            }

        title = _strip_html(
            item.get("title")
            or item.get("headline")
            or item.get("news_title")
            or item.get("제목")
            or ""
        )

        content = _strip_html(
            item.get("content")
            or item.get("summary")
            or item.get("description")
            or item.get("본문")
            or ""
        )

        company_field = _strip_html(
            item.get("company")
            or item.get("corp_name")
            or item.get("기업명")
            or ""
        )

        source = str(item.get("source") or item.get("publisher") or "")
        url = str(item.get("url") or item.get("link") or "")
        link = str(item.get("link") or item.get("url") or "")

        published = str(
            item.get("published")
            or item.get("publishedAt")
            or item.get("published_at")
            or item.get("pubDate")
            or item.get("date")
            or ""
        )

        haystack = f"{title} {content} {company_field} {source}".lower()

        if company and company in haystack:
            matched = True
        else:
            matched = any(keyword in haystack for keyword in keywords if keyword)

        if matched:
            filtered.append(
                {
                    "title": title,
                    "content": content,
                    "summary": content,
                    "description": content,
                    "url": url,
                    "link": link,
                    "source": source,
                    "date": _safe_date(published),
                    "published": _safe_date(published),
                    "published_at": _safe_date(published),
                }
            )

    return filtered


def fetch_rss_items(company_name: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    기존 patch에서 사용하던 함수도 호환용으로 유지합니다.
    내부적으로 fetch_rss_articles() + filter_rss_for_company()를 사용합니다.
    """
    articles = fetch_rss_articles(max_entries_per_feed=50)
    filtered = filter_rss_for_company(company_name, articles)
    return filtered[:limit]