from __future__ import annotations

import feedparser
import requests

from .config import RSS_SOURCES, SETTINGS
from .schema import NewsItem, RSSItem


def _safe_get(url: str, **kwargs) -> requests.Response:
    timeout = kwargs.pop("timeout", SETTINGS.request_timeout)

    headers = kwargs.pop("headers", {}) or {}
    headers.setdefault("User-Agent", "Mozilla/5.0")

    return requests.get(url, timeout=timeout, headers=headers, **kwargs)


def _naver_news_search(company_name: str, display: int = 10) -> list[NewsItem]:
    if not SETTINGS.enable_naver_news:
        return []

    if not SETTINGS.naver_client_id or not SETTINGS.naver_client_secret:
        print("[Naver News] NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 없습니다.")
        return []

    display = max(1, min(display, 100))

    url = "https://openapi.naver.com/v1/search/news.json"

    headers = {
        "X-Naver-Client-Id": SETTINGS.naver_client_id,
        "X-Naver-Client-Secret": SETTINGS.naver_client_secret,
    }

    params = {
        "query": company_name,
        "display": display,
        "start": 1,
        "sort": "date",
    }

    try:
        response = _safe_get(url, headers=headers, params=params)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        print(f"[Naver News] 수집 실패: {exc}")
        return []

    results: list[NewsItem] = []

    for item in payload.get("items", []):
        results.append(
            NewsItem(
                source="Naver News",
                title=item.get("title", ""),
                summary=item.get("description", ""),
                url=item.get("originallink") or item.get("link", ""),
                published=item.get("pubDate", ""),
            )
        )

    return results


def fetch_news_for_company(company_name: str, limit: int = 10) -> list[NewsItem]:
    return _naver_news_search(company_name, display=limit)[:limit]


def fetch_rss_articles(max_entries_per_feed: int = 15) -> list[RSSItem]:
    articles: list[RSSItem] = []

    for source_name, url in RSS_SOURCES.items():
        try:
            response = _safe_get(url)
            response.raise_for_status()
            feed = feedparser.parse(response.text)
        except Exception as exc:
            print(f"[RSS] {source_name} 수집 실패: {exc}")
            continue

        for entry in feed.entries[:max_entries_per_feed]:
            articles.append(
                RSSItem(
                    source=source_name,
                    title=entry.get("title", ""),
                    summary=entry.get("summary", ""),
                    url=entry.get("link", ""),
                    published=entry.get("published") or entry.get("updated", ""),
                )
            )

    return articles