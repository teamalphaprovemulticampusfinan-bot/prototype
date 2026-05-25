from __future__ import annotations

import html
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = text.replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", text).strip()


class NewsItem(BaseModel):
    source: str = ""
    title: str = Field(default="")
    summary: str = ""
    url: str = ""
    published: str = ""

    @field_validator("source", "title", "summary", "url", "published", mode="before")
    @classmethod
    def clean_fields(cls, value: Any) -> str:
        return clean_text(value)


class RSSItem(BaseModel):
    source: str = ""
    title: str = Field(default="")
    summary: str = ""
    url: str = ""
    published: str = ""

    @field_validator("source", "title", "summary", "url", "published", mode="before")
    @classmethod
    def clean_fields(cls, value: Any) -> str:
        return clean_text(value)


class KeywordRow(BaseModel):
    기업명: str = ""
    키워드: str = ""
    카테고리: str = ""
    설명: str = ""

    @field_validator("*", mode="before")
    @classmethod
    def clean_fields(cls, value: Any) -> str:
        return clean_text(value)


class RawStats(BaseModel):
    keyword_rows: int = 0
    news_count: int = 0
    rss_count: int = 0
    df_news_rows: int = 0


class PipelineOutput(BaseModel):
    company_name: str
    related_rows: list[KeywordRow]
    news_items: list[NewsItem]
    rss_items: list[RSSItem]
    company_context: str
    news_context: str
    raw: RawStats