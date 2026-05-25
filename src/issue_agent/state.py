from __future__ import annotations

from typing import Any, TypedDict


class IssueAgentState(TypedDict, total=False):
    company_name: str
    related_rows: list[dict[str, Any]]
    news_items: list[dict[str, Any]]
    rss_items: list[dict[str, Any]]
    company_context: str
    news_context: str
    analysis_text: str
    markdown_report: str