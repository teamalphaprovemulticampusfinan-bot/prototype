from __future__ import annotations
import pandas as pd
import requests
import yfinance as yf
import logging

from .config import (
    TICKERS,
    CORP_CODES,
    DART_API_KEY,
    NEWS_API_KEY,
    OECD_REGIONS,
    NEWS_KEYWORD,
    resolve_company_key,
)
from .data_loader import WorkbookData, fallback_oecd_from_excel
from .schemas import StockData, OecdData, DartData, NewsItem

logger = logging.getLogger(__name__)


# -----------------------------
# 📈 주가 데이터
# -----------------------------
def fetch_stock(company: str) -> StockData:
    company_key = resolve_company_key(company)
    ticker = TICKERS.get(company) or TICKERS.get(company_key, "")

    try:
        t = yf.Ticker(ticker)
        info = t.info
        hist = t.history(period="5d")

        beta = info.get("beta")

        if beta is None:
            market_ticker = "^KQ11" if ticker.endswith(".KQ") else "^KS11"
            beta = calculate_beta(ticker, market_ticker)

        return {
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "week52_high": info.get("fiftyTwoWeekHigh"),
            "week52_low": info.get("fiftyTwoWeekLow"),
            "beta": beta,
            "volume": int(hist["Volume"].iloc[-1]) if not hist.empty else 0,
            "price_change_5d": _calc_change(hist),
        }

    except Exception as e:
        logger.warning(f"[{company}] stock fetch 실패: {e}")
        return {}


def _calc_change(hist):
    if len(hist) < 2:
        return 0
    return round(
        (hist["Close"].iloc[-1] - hist["Close"].iloc[0]) /
        hist["Close"].iloc[0] * 100, 2
    )


# -----------------------------
# 🌍 OECD
# -----------------------------
def fetch_oecd(workbook: WorkbookData) -> OecdData:
    try:
        result = {}

        for name, code in OECD_REGIONS.items():
            url = f"https://stats.oecd.org/sdmx-json/data/MEI_CLI/LOLITOAA.{code}.M/all?lastNObservations=3"
            r = requests.get(url, timeout=10)
            r.raise_for_status()

            data = r.json()
            obs = data["dataSets"][0]["series"]["0:0:0"]["observations"]
            latest = sorted(obs.items())[-1]

            result[name] = round(latest[1][0], 2)

        return result

    except Exception as e:
        logger.warning(f"OECD API 실패 → fallback 사용: {e}")
        return fallback_oecd_from_excel(workbook)


# -----------------------------
# 🏢 DART
# -----------------------------
def fetch_dart_subsidy(company: str) -> DartData:
    try:
        company_key = resolve_company_key(company)
        code = CORP_CODES.get(company) or CORP_CODES.get(company_key, "")

        r = requests.get(
            "https://opendart.fss.or.kr/api/list.json",
            params={
                "crtfc_key": DART_API_KEY,
                "corp_code": code,
                "bgn_de": "20240101",
                "page_count": 10,
                "sort": "date",        # ✅ 추가
                "sort_mth": "desc",    # ✅ 최신순 정렬
            },
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()

        status = data.get("status")
        message = data.get("message", "")

        print(f"[{company}] corp_code={code}, status={status}, message={message}")

        # ✅ status 분기 추가
        if status == "013":  # 조회된 데이터 없음
            print(f"[{company}] DART 공시 없음 (013)")
            return {"latest_report": "", "date": ""}
        
        if status != "000":
            print(f"[{company}] DART 오류: {status} - {message}")
            return {"latest_report": "", "date": ""}

        items = data.get("list", [])
        if not items:
            return {"latest_report": "", "date": ""}

        return {
            "latest_report": items[0].get("report_nm"),
            "date": items[0].get("rcept_dt"),
        }

    except Exception as e:
        print(f"[{company}] DART 오류:", e)
        return {}


# -----------------------------
# 📰 뉴스
# -----------------------------
def fetch_market_news(keyword: str | None = None) -> list[NewsItem]:
    keyword = keyword or NEWS_KEYWORD

    try:
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": keyword,
                "language": "ko",
                "sortBy": "publishedAt",
                "pageSize": 10,
                "apiKey": NEWS_API_KEY,
            },
            timeout=15,
        )
        r.raise_for_status()

        articles = r.json().get("articles", [])

        return [
            {"title": a["title"], "date": a["publishedAt"][:10]}
            for a in articles
        ]

    except Exception as e:
        logger.warning(f"뉴스 수집 실패: {e}")
        return []

# beta함수 계산
def calculate_beta(company_ticker: str, market_ticker: str = "^KS11"):
    try:
        stock = yf.download(company_ticker, period="6mo", progress=False)["Close"]
        market = yf.download(market_ticker, period="6mo", progress=False)["Close"]

        df = pd.concat([stock, market], axis=1).dropna()
        df.columns = ["stock", "market"]

        returns = df.pct_change().dropna()

        if returns.empty or returns["market"].var() == 0:
            return None

        beta = returns["stock"].cov(returns["market"]) / returns["market"].var()
        return round(float(beta), 2)

    except Exception as e:
        logger.warning(f"beta 계산 실패: {company_ticker}, {e}")
        return None