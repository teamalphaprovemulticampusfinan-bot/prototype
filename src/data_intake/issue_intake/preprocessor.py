from __future__ import annotations

from typing import Any

import pandas as pd

from .config import get_company_keywords
from .schema import KeywordRow, NewsItem, RSSItem, clean_text


def filter_company_keywords(
    df_keywords: pd.DataFrame,
    company_name: str,
) -> list[KeywordRow]:
    if df_keywords is None or df_keywords.empty:
        return []

    company_col = None

    if "기업명" in df_keywords.columns:
        company_col = "기업명"
    else:
        for col in df_keywords.columns:
            col_text = str(col).lower()
            if "기업" in str(col) or "company" in col_text:
                company_col = col
                break

    if company_col is None:
        return []

    company = str(company_name).strip()

    filtered = df_keywords[
        df_keywords[company_col].astype(str).str.strip() == company
    ]

    rows = filtered.fillna("").to_dict(orient="records")

    return [
        KeywordRow(
            기업명=row.get("기업명", row.get(company_col, "")),
            키워드=row.get("키워드", row.get("keyword", "")),
            카테고리=row.get("카테고리", row.get("category", "")),
            설명=row.get("설명", row.get("description", "")),
        )
        for row in rows
    ]


def _row_value(row: Any, *keys: str) -> str:
    if isinstance(row, KeywordRow):
        data = row.model_dump()
    elif isinstance(row, dict):
        data = row
    else:
        return ""

    for key in keys:
        value = clean_text(data.get(key, ""))
        if value:
            return value

    return ""


def build_company_context(related_rows: list[KeywordRow]) -> str:
    if not related_rows:
        return "관련 내부 키워드 정보가 없습니다."

    lines: list[str] = []

    for row in related_rows[:15]:
        keyword = _row_value(row, "키워드", "keyword", "이슈", "issue")
        category = _row_value(row, "카테고리", "category", "분류")
        description = _row_value(row, "설명", "description", "내용", "summary", "요약")

        line = f"- 키워드: {keyword}" if keyword else "- 키워드: 확인 제한"

        if category:
            line += f" / 카테고리: {category}"

        if description:
            line += f" / 설명: {description}"

        lines.append(line)

    return "\n".join(lines)


def filter_company_rss(
    company_name: str,
    rss_articles: list[RSSItem],
) -> list[RSSItem]:
    if not rss_articles:
        return []

    keywords = get_company_keywords(company_name)
    filtered: list[RSSItem] = []

    for item in rss_articles:
        haystack = " ".join(
            [
                item.title,
                item.summary,
                item.source,
            ]
        ).lower()

        matched = any(keyword in haystack for keyword in keywords)

        if matched:
            filtered.append(item)

    return filtered


def build_news_context(
    news_items: list[NewsItem],
    rss_items: list[RSSItem],
) -> str:
    merged: list[str] = []

    for item in news_items[:10]:
        title = item.title
        summary = item.summary
        published = item.published

        if title or summary:
            date_text = f" / 날짜: {published}" if published else ""
            merged.append(f"- 뉴스: {title} | {summary}{date_text}")

    for item in rss_items[:10]:
        title = item.title
        summary = item.summary
        published = item.published

        if title or summary:
            date_text = f" / 날짜: {published}" if published else ""
            merged.append(f"- RSS: {title} | {summary}{date_text}")

    if not merged:
        return "최근 수집된 뉴스/RSS 정보가 없습니다."

    return "\n".join(merged)