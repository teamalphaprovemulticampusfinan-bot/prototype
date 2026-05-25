from typing import Any, TypedDict


class StockData(TypedDict, total=False):
    current_price: float
    week52_high: float
    week52_low: float
    beta: float
    volume: int
    price_change_5d: float


class OecdData(TypedDict, total=False):
    G20: float
    한국: float
    미국: float
    중국: float


class DartData(TypedDict, total=False):
    latest_report: str
    date: str


class NewsItem(TypedDict, total=False):
    title: str
    date: str


class StaticData(TypedDict, total=False):
    chain: dict[str, Any]
    base: dict[str, Any]
    competitors: list[dict[str, Any]]
    policy: dict[str, Any]
    growth: dict[str, Any]


class CompanyDatasetRow(TypedDict, total=False):
    company: str

    current_price: float
    week52_high: float
    week52_low: float
    beta: float
    volume: int
    price_change_5d: float

    oecd_g20: float
    oecd_korea: float
    oecd_usa: float
    oecd_china: float

    latest_report: str
    dart_date: str

    value_chain_position: str
    products: str
    process: str

    news_titles: str
    news_dates: str