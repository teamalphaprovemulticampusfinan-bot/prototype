# collector.py

import os
import time
import random
import re
from datetime import datetime
from io import StringIO

import requests
import pandas as pd
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================
# 환경 변수 / API 설정
# ============================================================

load_dotenv()

ECOS_API_KEY = os.getenv("ECOS_API_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")

ECOS_BASE_URL = "https://ecos.bok.or.kr/api"

if not ECOS_API_KEY:
    raise ValueError("ECOS_API_KEY가 .env 파일에 없습니다.")

# FRED_API_KEY가 없어도 fredapi는 일부 환경에서 동작할 수 있으나,
# 공식 금리 데이터를 안정적으로 쓰려면 .env에 FRED_API_KEY를 두는 것을 권장.
fred = Fred(api_key=FRED_API_KEY) if FRED_API_KEY else Fred()


# ============================================================
# 공통 세션 설정
# ============================================================

session = requests.Session()

retry = Retry(
    total=int(os.getenv("MACRO_HTTP_RETRY_TOTAL", "1")),
    backoff_factor=float(os.getenv("MACRO_HTTP_BACKOFF_FACTOR", "0.3")),
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True,
)

session.mount("https://", HTTPAdapter(max_retries=retry))
session.mount("http://", HTTPAdapter(max_retries=retry))


# ============================================================
# 공통 함수
# ============================================================

def merge_dfs(dfs):
    """
    여러 DataFrame을 date 기준으로 병합
    """
    result = None

    for df in dfs:
        if df is None or df.empty:
            continue

        result = df if result is None else pd.merge(result, df, on="date", how="outer")

    if result is None:
        return None

    return result.sort_values("date").reset_index(drop=True)


def to_daily_df(series, label):
    """
    yfinance/FRED Series를 일별 DataFrame으로 변환
    """
    if series is None:
        return pd.DataFrame()

    raw = series.dropna()

    if raw.empty:
        print(f"⚠️ [{label}] 데이터 없음")
        return pd.DataFrame()

    df = raw.reset_index()
    df.columns = ["date", label]

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.tz_localize(None)
    df[label] = pd.to_numeric(df[label], errors="coerce")

    df = df.dropna(subset=["date"])
    df = df.groupby("date", as_index=False)[label].mean()
    df = df.sort_values("date").reset_index(drop=True)

    print(f"  ✅ [{label}] {len(df)}행 수집")
    return df


def to_monthly_df(series, label):
    """
    FRED Series를 월별 DataFrame으로 변환
    """
    if series is None:
        return pd.DataFrame()

    raw = series.dropna()

    if raw.empty:
        print(f"⚠️ [{label}] 데이터 없음")
        return pd.DataFrame()

    df = raw.reset_index()
    df.columns = ["date", label]

    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.tz_localize(None)
    df[label] = pd.to_numeric(df[label], errors="coerce")

    df = df.dropna(subset=["date"])
    df = df.groupby("date", as_index=False)[label].mean()
    df = df.sort_values("date").reset_index(drop=True)

    print(f"  ✅ [{label}] {len(df)}행 수집")
    return df


def is_english(text):
    """
    영어 제목 필터링
    """
    if not text:
        return False

    ascii_count = sum(1 for c in text if ord(c) < 128)
    return (ascii_count / len(text)) > 0.7


# ============================================================
# ECOS
# ============================================================

def show_item_codes(stat_code):
    """
    ECOS 통계표 코드의 항목코드 목록 조회
    예) show_item_codes("817Y002")
    """
    url = f"{ECOS_BASE_URL}/StatisticItemList/{ECOS_API_KEY}/json/kr/1/200/{stat_code}"

    try:
        response = session.get(url, timeout=float(os.getenv("MACRO_HTTP_TIMEOUT_SEC", "5")))
        response.raise_for_status()

        rows = response.json().get("StatisticItemList", {}).get("row", [])

        if not rows:
            print(f"⚠️ [{stat_code}] 항목 없음 또는 코드 오류")
            return pd.DataFrame()

        return pd.DataFrame(rows)

    except Exception as e:
        print(f"❌ [{stat_code}] 항목 조회 오류: {e}")
        return pd.DataFrame()


def fetch_ecos(
    stat_code,
    cycle,
    start,
    end,
    item_code1="?",
    item_code2="?",
    item_code3="?",
    item_code4="?",
    label=None,
):
    """
    ECOS API에서 통계 데이터를 수집.

    예:
    - 한국은행 기준금리:
      fetch_ecos("722Y001", "M", M_START, M_END, "0101000", label="한국은행_기준금리")

    - 국고채 10년:
      fetch_ecos("817Y002", "D", D_START, D_END, "010210000", label="국고채_10년")
    """
    url = (
        f"{ECOS_BASE_URL}/StatisticSearch/{ECOS_API_KEY}/json/kr/1/10000"
        f"/{stat_code}/{cycle}/{start}/{end}"
        f"/{item_code1}/{item_code2}/{item_code3}/{item_code4}"
    )

    try:
        response = session.get(url, timeout=float(os.getenv("MACRO_HTTP_TIMEOUT_SEC", "5")))
        response.raise_for_status()

        rows = response.json().get("StatisticSearch", {}).get("row", [])

        if not rows:
            print(f"⚠️ [{label or stat_code}] 데이터 없음")
            return pd.DataFrame()

        col = label or rows[0].get("ITEM_NAME1", stat_code)

        df = pd.DataFrame(rows)[["TIME", "DATA_VALUE"]].copy()
        df.columns = ["date", col]

        df[col] = pd.to_numeric(df[col], errors="coerce")

        print(f"  ✅ [{col}] {len(df)}행 수집")
        return df

    except Exception as e:
        print(f"❌ [{label or stat_code}] ECOS 수집 오류: {e}")
        return pd.DataFrame()


# ============================================================
# yfinance
# ============================================================

def fetch_yf(ticker, label, start, end):
    """
    yfinance에서 종가 데이터를 수집.

    주의:
    - 정책금리, 기준금리, 연방기금금리에는 사용하지 않는다.
    - 정책금리는 ECOS/FRED 공식 계열만 사용한다.
    """
    try:
        raw = yf.download(
            ticker,
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
            threads=False,
        )["Close"]

        if isinstance(raw, pd.DataFrame):
            raw = raw.squeeze()

        return to_daily_df(raw, label)

    except Exception as e:
        print(f"❌ [{label}] yfinance 오류: {e}")
        return pd.DataFrame()


# ============================================================
# FRED
# ============================================================

def fetch_fred(series_id, label, start, end):
    """
    FRED에서 월별 경제지표를 수집.

    기존 macro_intake에서 사용하던 함수.
    예:
    - FEDFUNDS: 월별 Federal Funds Rate
    - EFFR: Effective Federal Funds Rate 계열
    """
    try:
        raw = fred.get_series(
            series_id,
            observation_start=start,
            observation_end=end,
        ).dropna()

        return to_monthly_df(raw, label)

    except Exception as e:
        print(f"❌ [{label}] FRED 오류: {e}")
        return pd.DataFrame()


def fetch_fred_daily(series_id, label, start, end):
    """
    FRED에서 일별 공식 경제지표를 수집.

    정책금리/연방기금금리용 공식 계열:
    - DFF       : Federal Funds Effective Rate, 일별
    - DFEDTARU : Federal Funds Target Range - Upper Limit, 일별
    - DFEDTARL : Federal Funds Target Range - Lower Limit, 일별

    사용 예:
    fetch_fred_daily("DFF", "미국_연방기금금리_DFF", FRED_START, FRED_END)
    fetch_fred_daily("DFEDTARU", "미국_정책금리_상단", FRED_START, FRED_END)
    fetch_fred_daily("DFEDTARL", "미국_정책금리_하단", FRED_START, FRED_END)

    주의:
    - 정책금리/연방기금금리는 yfinance가 아니라 FRED 공식 계열만 사용한다.
    """
    try:
        raw = fred.get_series(
            series_id,
            observation_start=start,
            observation_end=end,
        ).dropna()

        return to_daily_df(raw, label)

    except Exception as e:
        print(f"❌ [{label}] FRED daily 오류: {e}")
        return pd.DataFrame()


# ============================================================
# OECD CLI
# ============================================================

FRED_CLI_FALLBACK_SERIES = {
    # OECD/FRED: Leading Indicators OECD: CLI, Amplitude adjusted
    "KOR": "LOLITOAAKRM659S",
    "USA": "LOLITOAAUSM659S",
}


def _to_oecd_month_period(value):
    """
    OECD SDMX startPeriod/endPeriod를 YYYY-MM으로 정규화.

    기존 코드에서 20210501[:7] -> 2021050처럼 잘리는 문제가 있어
    YYYYMM, YYYYMMDD, YYYY-MM, YYYY-MM-DD, datetime-like 값을 모두 YYYY-MM으로 맞춘다.
    """
    if value is None:
        return ""

    raw = str(value).strip()

    if not raw:
        return ""

    digits = re.sub(r"\D", "", raw)

    if len(digits) >= 6:
        return f"{digits[:4]}-{digits[4:6]}"

    parsed = pd.to_datetime(raw, errors="coerce")

    if pd.notna(parsed):
        return parsed.strftime("%Y-%m")

    return datetime.today().strftime("%Y-%m")


def _parse_oecd_cli_csv(text, label):
    if not text or not text.strip():
        return pd.DataFrame()

    df = pd.read_csv(StringIO(text))

    if df.empty:
        return pd.DataFrame()

    date_candidates = [
        "TIME_PERIOD",
        "TIME_PERIOD:Time period",
        "Time period",
        "TIME",
    ]

    value_candidates = [
        "OBS_VALUE",
        "OBS_VALUE:Observation value",
        "Observation value",
        "Value",
    ]

    date_col = next((c for c in date_candidates if c in df.columns), None)
    value_col = next((c for c in value_candidates if c in df.columns), None)

    if date_col is None or value_col is None:
        date_col = next(
            (c for c in df.columns if "TIME_PERIOD" in c or "Time period" in c),
            None,
        )
        value_col = next(
            (c for c in df.columns if "OBS_VALUE" in c or "Observation value" in c),
            None,
        )

    if date_col is None or value_col is None:
        return pd.DataFrame()

    out = df[[date_col, value_col]].copy()
    out.columns = ["date", label]

    out["date"] = pd.to_datetime(
        out["date"].astype(str).str[:7] + "-01",
        errors="coerce",
    )
    out[label] = pd.to_numeric(out[label], errors="coerce")

    out = out.dropna(subset=["date"])
    out = out.groupby("date", as_index=False)[label].mean()
    out = out.sort_values("date").reset_index(drop=True)

    return out


def _fetch_fred_cli_fallback(country_code, label, start_m, end_m):
    series_id = FRED_CLI_FALLBACK_SERIES.get(str(country_code).upper())

    if not series_id:
        print(f"  ⚠️ [{label}] OECD 실패 후 FRED fallback 없음 → skip")
        return pd.DataFrame()

    start_date = f"{start_m}-01"
    end_date = f"{end_m}-01"

    try:
        raw = fred.get_series(
            series_id,
            observation_start=start_date,
            observation_end=end_date,
        ).dropna()

        df = to_monthly_df(raw, label)

        if not df.empty:
            print(f"  ✅ [{label}] FRED fallback {series_id} 사용")

        return df

    except Exception as e:
        print(f"  ⚠️ [{label}] FRED fallback 오류: {e}")
        return pd.DataFrame()


def fetch_oecd_cli(country_code, label, start, end):
    """
    OECD 경기선행지수 CLI 수집.

    Primary:
    - OECD SDMX REST CSV

    Fallback:
    - FRED OECD CLI series for KOR/USA
    """
    country_code = str(country_code).upper().strip()
    start_m = _to_oecd_month_period(start)
    end_m = _to_oecd_month_period(end)

    query_variants = [
        f"{country_code}.M.LI...AA...H",
        f"{country_code}.M.LI...AA...",
    ]

    for query in query_variants:
        url = (
            "https://sdmx.oecd.org/public/rest/data/"
            f"OECD.SDD.STES,DSD_STES@DF_CLI/{query}"
            f"?startPeriod={start_m}"
            f"&endPeriod={end_m}"
            f"&dimensionAtObservation=AllDimensions"
            f"&format=csvfilewithlabels"
        )

        try:
            response = session.get(url, timeout=float(os.getenv("MACRO_HTTP_TIMEOUT_SEC", "5")))

            if response.status_code == 422:
                print(
                    f"  ⚠️ [{label}] OECD 422: "
                    f"query={query}, start={start_m}, end={end_m}"
                )
                continue

            response.raise_for_status()

            df = _parse_oecd_cli_csv(response.text, label)

            if not df.empty:
                print(f"  ✅ [{label}] OECD {len(df)}행 수집")
                return df

            print(f"  ⚠️ [{label}] OECD 응답 파싱 실패: query={query}")

        except Exception as e:
            print(f"  ⚠️ [{label}] OECD 오류: {e}")

    return _fetch_fred_cli_fallback(country_code, label, start_m, end_m)


# ============================================================
# GDELT 뉴스
# ============================================================

def fetch_gdelt_news(keyword, label, max_results=3):
    """
    GDELT에서 외신 뉴스 수집.
    category 컬럼에 검색 키워드(label)를 기록.
    """
    url = "https://api.gdeltproject.org/api/v2/doc/doc"

    params = {
        "query": f"{keyword} sourcelang:english",
        "mode": "artlist",
        "maxrecords": max_results,
        "format": "json",
        "sort": "DateDesc",
    }

    for attempt in range(4):
        try:
            response = session.get(url, params=params, timeout=float(os.getenv("MACRO_HTTP_TIMEOUT_SEC", "5")))

            if response.status_code == 429:
                wait = min(int(response.headers.get("Retry-After", 3)), int(os.getenv("MACRO_GDELT_429_SLEEP_CAP_SEC", "3")))
                time.sleep(wait + random.uniform(0.1, 0.5))
                continue

            response.raise_for_status()

            articles = response.json().get("articles", [])

            rows = []

            for article in articles:
                title = article.get("title", "")

                if not is_english(title):
                    continue

                domain = article.get("domain", "")

                rows.append(
                    {
                        "category": label,
                        "date": article.get("seendate", "")[:8],
                        "title": title,
                        "url": article.get("url", ""),
                        "domain": domain,
                        "source": domain,
                    }
                )

            df = pd.DataFrame(rows)

            if not df.empty:
                df["date"] = pd.to_datetime(
                    df["date"],
                    format="%Y%m%d",
                    errors="coerce",
                )
                df = df.dropna(subset=["date"])
                df = df.sort_values("date", ascending=False).reset_index(drop=True)

            print(f"  ✅ [{label}] {len(df)}건 수집")
            return df

        except requests.exceptions.Timeout:
            if attempt < 3:
                time.sleep((attempt + 1) * 10)
                continue

            print(f"❌ [{label}] GDELT 오류: timeout")
            return pd.DataFrame()

        except Exception as e:
            print(f"❌ [{label}] GDELT 오류: {e}")
            return pd.DataFrame()

    print(f"❌ [{label}] GDELT 오류: rate limit 초과")
    return pd.DataFrame()