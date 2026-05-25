from typing import Any, TypedDict


class MarketState(TypedDict):
    company:     str
    stock_data:  dict[str, Any]
    oecd_data:   dict[str, Any]
    dart_data:   dict[str, Any]
    news_data:   list[dict[str, Any]]
    static_data: dict[str, Any]
    analysis:    dict[str, Any]
