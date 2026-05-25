# runner.py

import io
import json
import os
import re
import time
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from .collector import (
    fetch_ecos, show_item_codes, merge_dfs,
    fetch_yf, fetch_fred, fetch_fred_daily, fetch_oecd_cli, fetch_gdelt_news,
)
from .normalizer import clean_text_frame, normalize, normalize_news, normalize_rare_earth, normalize_helium
from .validator import validate_dataset
from common.data_paths import macro_common_dir
from .worldmonitor_fallbacks import (
    fetch_semiconductor_worldmonitor_news,
    fetch_regulatory_worldmonitor_fallback,
    collect_semiconductor_supply_chain_risks,
)
from . import material_collectors
from .manual_macro_signals import build_bigtech_credit_macro_signals
from .market_indices import collect_market_index_benchmarks
from .schema_tools import prepare_official_macro_csv


# ============================================================
# 공통 유틸
# ============================================================

def is_english(text, threshold=0.7):
    if not text:
        return False
    ascii_count = sum(1 for c in text if ord(c) < 128)
    return (ascii_count / len(text)) > threshold


def clean(text, limit=250):
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", text).strip()[:limit]


def parse_date(raw):
    try:
        return pd.to_datetime(raw, utc=True).tz_localize(None)
    except Exception:
        return pd.NaT


def attach_monthly_policy_rate_to_daily(
    df_daily: pd.DataFrame,
    df_monthly_rate: pd.DataFrame,
    rate_col: str = "한국은행_기준금리",
) -> pd.DataFrame:
    """
    ECOS 월별 기준금리 공식값을 일별 df_daily 날짜축에 붙인다.

    이유:
    - 한국은행 기준금리는 정책 결정일 기준으로 변하지만,
      ECOS 테이블/주기 조합에 따라 D 조회가 빈 값으로 올 수 있다.
    - Macro Agent 일별 입력에는 일별 컬럼이 필요하므로,
      월별 공식값을 일별 날짜축에 forward-fill로 확장한다.
    """
    if df_daily is None or df_daily.empty:
        return df_daily

    if df_monthly_rate is None or df_monthly_rate.empty:
        print(f"⚠️ [{rate_col}] 월별 기준금리 데이터 없음 → 일별 부착 생략")
        return df_daily

    daily = df_daily.copy()
    monthly = df_monthly_rate.copy()

    daily["date"] = pd.to_datetime(daily["date"], errors="coerce")
    monthly["date"] = pd.to_datetime(monthly["date"], errors="coerce")

    if rate_col not in monthly.columns:
        alt_cols = [c for c in monthly.columns if "기준금리" in c and c != "date"]
        if alt_cols:
            monthly = monthly.rename(columns={alt_cols[0]: rate_col})
        else:
            print(f"⚠️ [{rate_col}] 월별 기준금리 컬럼 없음 → 일별 부착 생략")
            return df_daily

    monthly = monthly[["date", rate_col]].dropna()
    monthly = monthly.sort_values("date")
    monthly["date"] = monthly["date"].dt.to_period("M").dt.to_timestamp()

    rate_daily = pd.DataFrame({"date": daily["date"].dropna().sort_values().unique()})
    rate_daily["month"] = rate_daily["date"].dt.to_period("M").dt.to_timestamp()

    rate_monthly = monthly.rename(columns={"date": "month"})
    rate_daily = rate_daily.merge(rate_monthly, on="month", how="left")
    rate_daily[rate_col] = rate_daily[rate_col].ffill().bfill()
    rate_daily = rate_daily[["date", rate_col]]

    if rate_col in daily.columns:
        daily = daily.drop(columns=[rate_col])

    daily = daily.merge(rate_daily, on="date", how="left")

    print(f"✅ [{rate_col}] 월별 공식값을 일별 파일에 부착 완료")
    return daily


def make_reg_row(country, reg_type, date, title, url, source):
    return {
        "country": country, "type": reg_type,
        "date": date, "title": clean(title),
        "url": url, "source": source,
    }


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _merge_on_date(frames: list[pd.DataFrame | None]) -> pd.DataFrame | None:
    result = None
    for frame in frames:
        if frame is None or frame.empty:
            continue
        tmp = normalize(frame)
        if tmp is None or tmp.empty:
            continue
        result = tmp.copy() if result is None else pd.merge(result, tmp, on="date", how="outer", sort=True)
    if result is None:
        return None
    return normalize(result)


def _resample_to_monthly(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    if frame is None or frame.empty or "date" not in frame.columns:
        return None
    df = normalize(frame)
    if df is None or df.empty:
        return None
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date")
    if df.empty:
        return None
    df["date"] = df["date"].dt.to_period("M").dt.to_timestamp("M")
    numeric_cols = [c for c in df.columns if c != "date" and pd.api.types.is_numeric_dtype(df[c])]
    text_cols = [c for c in df.columns if c != "date" and c not in numeric_cols]
    agg: dict[str, object] = {c: "last" for c in numeric_cols}
    for col in text_cols:
        agg[col] = "last"
    return df.groupby("date", as_index=False).agg(agg).sort_values("date").reset_index(drop=True)


def _expand_to_daily(frame: pd.DataFrame | None, daily_dates: pd.Series | list[pd.Timestamp]) -> pd.DataFrame | None:
    if frame is None or frame.empty or "date" not in frame.columns:
        return None
    df = normalize(frame)
    if df is None or df.empty:
        return None
    dates = pd.to_datetime(pd.Series(list(daily_dates)), errors="coerce").dropna().drop_duplicates().sort_values()
    if dates.empty:
        dates = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    base = pd.DataFrame({"date": dates})
    src = df.copy().sort_values("date")
    return pd.merge_asof(base.sort_values("date"), src.sort_values("date"), on="date", direction="backward")


def _align_daily_monthly(
    daily_frames: list[pd.DataFrame | None],
    monthly_frames: list[pd.DataFrame | None],
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Make macro_일별 and macro_월별 carry the same indicator universe.

    - 일별: native daily values + native monthly/quarterly values forward-filled to the daily date axis.
    - 월별: daily values resampled to month-end + native monthly/quarterly values.
    """
    daily_native = _merge_on_date(daily_frames)
    monthly_native = _merge_on_date(monthly_frames)

    if daily_native is not None and not daily_native.empty:
        date_axis = daily_native["date"]
    elif monthly_native is not None and not monthly_native.empty:
        start, end = monthly_native["date"].min(), monthly_native["date"].max()
        date_axis = pd.Series(pd.date_range(start, end, freq="D"))
    else:
        return None, None

    monthly_as_daily = _expand_to_daily(monthly_native, date_axis)
    macro_daily = _merge_on_date([daily_native, monthly_as_daily])

    daily_as_monthly = _resample_to_monthly(daily_native)
    monthly_native_eom = _resample_to_monthly(monthly_native)
    macro_monthly = _merge_on_date([daily_as_monthly, monthly_native_eom])

    return macro_daily, macro_monthly


def _safe_write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write a macro CSV after official schema/outlier hygiene.

    Missing columns are added as NA and outliers are masked as NA.  No sample or
    arbitrary substitute values are generated here.
    """
    clean = clean_text_frame(df)
    clean = prepare_official_macro_csv(clean, path)
    clean.to_csv(path, index=False, encoding="utf-8-sig")



# ============================================================
# 희토류 수집 함수
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

re_session = requests.Session()
re_session.headers.update(HEADERS)


@retry(stop=stop_after_attempt(int(os.getenv("MACRO_HTTP_RETRY_TOTAL", "1"))), wait=wait_exponential(multiplier=0.3, min=0.3, max=2))
def safe_get(url, **kwargs):
    r = re_session.get(url, timeout=float(os.getenv("MACRO_HTTP_TIMEOUT_SEC", "5")), **kwargs)
    r.raise_for_status()
    return r


def safe_float(x):
    if x is None:
        return None
    x = str(x).replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", x)
    return float(m.group()) if m else None


def fetch_rare_earth_fred():
    print("  [FRED 희토류]")
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=IP28"
    try:
        r = re_session.get(url, timeout=(5, 20))
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        if df.empty or df.shape[1] < 2:
            print("  ⚠️ FRED [IP28]: 빈 응답")
            return pd.DataFrame(columns=["date", "희토류수입가격지수"])
        df.columns = ["date", "희토류수입가격지수"]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["희토류수입가격지수"] = pd.to_numeric(df["희토류수입가격지수"], errors="coerce")
        df = df.dropna().sort_values("date").reset_index(drop=True)
        print(f"  ✅ FRED [IP28]: {len(df)}행")
        return df
    except Exception as e:
        print(f"  ⚠️ FRED [IP28]: {type(e).__name__} → skip")
        return pd.DataFrame(columns=["date", "희토류수입가격지수"])


SMM_PAGES = {
    "네오디뮴_Nd_USD_t": {
        "url": "https://www.metal.com/Rare-Earth-Metals/201102250470",
        "min_valid": 5000,
        "max_valid": 500000,
    },
}


def fetch_all_smm(today):
    print("  [SMM 스크래핑]")
    dfs = []
    for label, meta in SMM_PAGES.items():
        try:
            r = re_session.get(meta["url"], timeout=(5, 25))
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "lxml")
            text = soup.get_text(" ", strip=True)
            if any(s.lower() in text.lower() for s in ["Sign in to view", "No data yet"]):
                print(f"  ⚠️ SMM [{label}]: 로그인 필요 → skip")
                continue
            candidates = []
            for el in soup.select('[class*="price"], [class*="Price"]'):
                val = safe_float(el.get_text(" ", strip=True))
                if val and meta.get("min_valid", 0) <= val <= meta.get("max_valid", 9e9):
                    candidates.append(val)
            if not candidates:
                print(f"  ⚠️ SMM [{label}]: 공개 가격 없음 → skip")
                continue
            price = min(candidates)
            dfs.append(pd.DataFrame([{"date": pd.Timestamp(today.date()), label: price}]))
            print(f"  ✅ SMM [{label}]: {price}")
        except Exception as e:
            print(f"  ⚠️ SMM [{label}]: {e}")
        time.sleep(1.2)

    if dfs:
        result = dfs[0]
        for df in dfs[1:]:
            result = pd.merge(result, df, on="date", how="outer")
        return result.sort_values("date").reset_index(drop=True)
    return pd.DataFrame()


USGS_RE_MANUAL = {
    "date": pd.to_datetime(["2019-01-01", "2020-01-01", "2021-01-01", "2022-01-01", "2023-01-01"]),
    "희토류_미국수입_천톤": [1.67, 2.13, 1.87, 1.88, 2.00],
    "네오디뮴산화물_USD_kg_참고": [55, 50, 105, 105, 60],
}


def fetch_usgs_rare_earth():
    print("  [USGS 희토류]")
    try:
        r = safe_get("https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-rare-earths.pdf")
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            pdf.pages[0].extract_text()
        print("  ✅ USGS 희토류 PDF 접근 성공 → 수동 테이블 사용")
    except Exception as e:
        print(f"  ⚠️ USGS 희토류 접근 실패 → 수동 데이터 사용: {e}")
    return pd.DataFrame(USGS_RE_MANUAL)


# ============================================================
# 헬륨 수집 함수
# ============================================================

USGS_HELIUM_MANUAL = {
    "date": pd.to_datetime(["2018-01-01", "2019-01-01", "2020-01-01",
                            "2021-01-01", "2022-01-01", "2023-01-01"]),
    "헬륨_BLM입찰가_USD_Mcf": [280, 292, 294, 283, 259, 261],
    "헬륨_시장추정가_USD_리터": [0.030, 0.032, 0.031, 0.040, 0.065, 0.055],
    "헬륨_미국생산_백만m3": [74, 67, 67, 71, 71, 72],
}


def fetch_usgs_helium():
    print("  [USGS 헬륨]")
    try:
        r = safe_get("https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-helium.pdf")
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            pdf.pages[0].extract_text()
        print("  ✅ USGS 헬륨 PDF 접근 성공 → 수동 테이블 사용")
    except Exception as e:
        print(f"  ⚠️ USGS 헬륨 접근 실패 → 수동 데이터 사용: {e}")
    return pd.DataFrame(USGS_HELIUM_MANUAL)


def fetch_blm_helium(today):
    print("  [BLM 헬륨]")
    url = "https://www.blm.gov/programs/energy-and-minerals/helium"
    try:
        r = safe_get(url)
        soup = BeautifulSoup(r.text, "lxml")
        title = soup.title.get_text(strip=True) if soup.title else "BLM Helium"
        df = pd.DataFrame([{
            "date": pd.Timestamp(today.date()),
            "source": "BLM", "status": "page_alive",
            "title": title, "url": url,
        }])
        print("  ✅ BLM 페이지 접근 성공")
        return df
    except Exception as e:
        print(f"  ❌ BLM: {e}")
        return pd.DataFrame()


def fetch_helium_news():
    print("  [GDELT 헬륨 뉴스]")
    params = {
        "query": "helium price OR helium shortage OR helium supply sourcelang:english",
        "mode": "artlist", "maxrecords": 5, "format": "json",
        "sort": "DateDesc", "timespan": "90d",
    }
    data, err = _gdelt_get(params, timeout=30)
    if err:
        print(f"  ⚠️ GDELT 헬륨 뉴스 스킵: {err}")
        return pd.DataFrame()

    rows = []
    for a in (data or {}).get("articles", []):
        date_raw = a.get("seendate", "")[:8]
        rows.append({
            "date": pd.to_datetime(date_raw, format="%Y%m%d", errors="coerce"),
            "title": a.get("title", "")[:150],
            "url": a.get("url", ""),
            "domain": a.get("domain", ""),
        })
    df = pd.DataFrame(rows)
    print(f"  ✅ GDELT 헬륨 뉴스: {len(df)}건")
    return df


# ============================================================
# 외신 뉴스 수집 함수
# ============================================================

GDELT_URL   = "https://api.gdeltproject.org/api/v2/doc/doc"
NEWSAPI_URL = "https://newsapi.org/v2/everything"
SERPER_URL  = "https://google.serper.dev/news"
SERPER_SEARCH_URL = "https://google.serper.dev/search"

# GDELT는 공개 API라 짧은 시간에 여러 번 호출하면 429가 자주 발생한다.
# 기본값을 보수적으로 둬서 macro intake 전체가 실패하지 않도록 한다.
_GDELT_LAST_REQUEST_TS = 0.0


def _env_float(name, default):
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return float(default)


def _env_bool(name, default=True):
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    return str(raw).strip().lower() not in {"0", "false", "no", "off", ""}


def _valid_api_key(value):
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    placeholders = {"none", "null", "na", "n/a", "your_key", "your-api-key", "여기에_실제키"}
    return text.lower() not in placeholders


def _today_stage_files(save_dir: Path, today_str: str) -> dict[str, Path | None]:
    """Return today's canonical macro output files if they exist.

    Data Intake uses a consolidated macro output layout with only three files.
    """
    wanted = {
        "macro_daily": f"macro_일별_{today_str}.csv",
        "macro_monthly": f"macro_월별_{today_str}.csv",
        "macro_common": f"macro_공통_{today_str}.csv",
    }
    out: dict[str, Path | None] = {}
    for key, name in wanted.items():
        path = save_dir / name
        out[key] = path if path.exists() and path.stat().st_size > 0 else None
    return out


def _reuse_today_outputs_if_complete(save_dir: Path, today_str: str) -> bool:
    if not _env_bool("MACRO_REUSE_TODAY_OUTPUTS", True):
        return False
    if _env_bool("MACRO_FORCE_REFRESH", False):
        return False
    files = _today_stage_files(save_dir, today_str)
    missing = [key for key, path in files.items() if path is None]
    if missing:
        return False
    print("\n♻️ Macro Intake: 오늘 날짜 통합 macro 출력물이 이미 모두 있어 재수집을 생략합니다.")
    print("   강제 재수집이 필요하면 PowerShell에서 $env:MACRO_FORCE_REFRESH='1' 설정 후 재실행하세요.")
    for key, path in files.items():
        if path is not None:
            print(f"  - {key}: {path.name} ({path.stat().st_size / 1024:.1f} KB)")
    return True


def _write_run_summary(save_dir: Path, today_str: str) -> None:
    files = sorted(save_dir.glob(f"*_{today_str}.csv"))
    rows = []
    for path in files:
        rows.append({
            "file": path.name,
            "size_kb": round(path.stat().st_size / 1024, 2),
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    if rows:
        pd.DataFrame(rows).to_csv(save_dir / f"macro_run_summary_{today_str}.csv", index=False, encoding="utf-8-sig")
    payload = {
        "date": today_str,
        "save_dir": str(save_dir),
        "file_count": len(rows),
        "files": rows,
        "notes": [
            "GDELT/Serper/NewsAPI failures are non-fatal because RSS, Google News RSS, official fallback, USGS, FRED and PortWatch layers are merged.",
            "SMM login-protected prices are not bypassed. Use SMM_COOKIE or SMM_BEARER_TOKEN only with legitimate access.",
            "Set MACRO_FORCE_REFRESH=1 to force full recollection; otherwise same-day outputs are reused to avoid bottlenecks.",
        ],
    }
    summary_json = save_dir / f"macro_run_summary_{today_str}.json"
    summary_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # Dashboard/agent loaders can now use stable latest pointers without guessing today's filename.
    (save_dir / "macro_run_summary_latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if rows:
        pd.DataFrame(rows).to_csv(save_dir / "macro_run_summary_latest.csv", index=False, encoding="utf-8-sig")


def _cleanup_legacy_macro_files(save_dir: Path) -> None:
    patterns = [
        "ecos_*.csv",
        "ext_*.csv",
        "희토류_*.csv",
        "헬륨_*.csv",
        "반도체_공급망_리스크_*.csv",
        "AI_크레딧_리스크_*.csv",
        "뉴스_*.csv",
        "규제_*.csv",
        "반도체_뉴스_fallback_*.csv",
        "규제_fallback_*.csv",
    ]
    for pattern in patterns:
        for path in save_dir.glob(pattern):
            try:
                path.unlink()
            except Exception:
                pass


def _gdelt_get(params, *, timeout=35):
    global _GDELT_LAST_REQUEST_TS

    if not _env_bool("MACRO_ENABLE_GDELT", True):
        return None, "disabled"

    min_interval = _env_float("MACRO_GDELT_MIN_INTERVAL_SEC", 0.8)
    elapsed = time.time() - _GDELT_LAST_REQUEST_TS
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed + random.uniform(0.3, 1.2))

    try:
        response = requests.get(GDELT_URL, params=params, timeout=timeout)
        _GDELT_LAST_REQUEST_TS = time.time()

        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            wait = float(retry_after) if retry_after and str(retry_after).isdigit() else max(min_interval * 2, 30)
            return None, f"rate_limited_429_wait_{int(wait)}s"

        if not response.text.strip():
            return None, "empty_response"

        response.raise_for_status()

        try:
            return response.json(), None
        except Exception as exc:
            preview = response.text[:160].replace("\n", " ")
            return None, f"json_parse_error: {exc}; preview={preview}"

    except requests.exceptions.Timeout:
        return None, "timeout"
    except Exception as exc:
        return None, str(exc)

NEWS_GDELT_QUERIES = {
    "반도체_수출규제": "semiconductor export control advanced chips entity list",
    "반도체_공급망":   "semiconductor supply chain HBM DRAM memory advanced packaging",
    "AI_데이터센터":   "artificial intelligence datacenter GPU HBM power demand semiconductor",
    "미중_무역":       "United States China trade tariff export controls semiconductors",
    "Fed_금리":        "Federal Reserve interest rates FOMC policy",
    "지정학_리스크":   "Taiwan Korea Japan sanctions geopolitical risk semiconductor",
    "원자재_에너지":   "copper oil rare earth helium commodity prices semiconductor",
}

RSS_FEEDS = {
    "반도체_공급망": [
        "https://feeds.reuters.com/reuters/technologyNews",
        "https://www.semiconductordigest.com/feed/",
        "https://www.tomshardware.com/feeds/all",
        "https://www.semianalysis.com/feed",
    ],
    "AI_데이터센터": [
        "https://www.tomshardware.com/feeds/all",
        "https://www.semianalysis.com/feed",
    ],
    "미중_무역": [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://www.scmp.com/rss/4/feed",
    ],
    "Fed_금리": [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://www.federalreserve.gov/feeds/press_all.xml",
    ],
    "지정학_리스크": [
        "https://feeds.reuters.com/reuters/worldNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ],
    "원자재_에너지": [
        "https://feeds.reuters.com/reuters/businessNews",
        "https://oilprice.com/rss/main",
    ],
}

RSS_KEYWORDS = {
    "반도체_공급망":  ["semiconductor", "chip", "DRAM", "HBM", "memory", "supply chain", "packaging", "foundry"],
    "AI_데이터센터":  ["AI", "GPU", "datacenter", "data center", "HBM", "semiconductor", "chip"],
    "미중_무역":      ["China", "tariff", "trade war", "export control", "United States", "US-China"],
    "Fed_금리":       ["Fed", "Federal Reserve", "interest rate", "FOMC", "rate hike", "rate cut"],
    "지정학_리스크":  ["geopolitic", "Taiwan", "sanction", "export ban", "Korea", "Japan"],
    "원자재_에너지":  ["copper", "oil", "natural gas", "rare earth", "helium", "gallium", "germanium", "commodity"],
}


def fetch_news_gdelt_ext(keyword, label, retries=None):
    if retries is None:
        retries = 1 if _env_bool("MACRO_GDELT_RETRY_ON_429", False) else 0
    params = {
        "query": f"{keyword} sourcelang:english",
        "mode": "artlist", "maxrecords": int(os.getenv("MACRO_GDELT_MAXRECORDS", "3")),
        "format": "json", "sort": "DateDesc", "timespan": "30d",
    }
    for attempt in range(retries + 1):
        data, err = _gdelt_get(params, timeout=35)
        if err:
            if "rate_limited_429" in err and attempt < retries:
                wait = _env_float("MACRO_GDELT_429_SLEEP_SEC", 3)
                print(f"  ⏳ GDELT [{label}] 429 회피 대기 {int(wait)}초")
                time.sleep(wait + random.uniform(1, 3))
                continue
            print(f"  ⚠️ GDELT [{label}] 스킵: {err}")
            return pd.DataFrame()

        rows = []
        for a in (data or {}).get("articles", []):
            title = clean(a.get("title", ""))
            if not is_english(title):
                continue
            rows.append({
                "source": "GDELT", "category": label,
                "date": a.get("seendate", "")[:8],
                "title": title, "url": a.get("url", ""),
                "domain": a.get("domain", ""),
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
            df = df.dropna(subset=["date"]).sort_values("date", ascending=False).reset_index(drop=True)
        print(f"  ✅ GDELT [{label}] {len(df)}건")
        return df
    return pd.DataFrame()

def fetch_rss(category, today):
    feeds    = RSS_FEEDS.get(category, [])
    keywords = [kw.lower() for kw in RSS_KEYWORDS.get(category, [])]
    rows = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:30]:
                title    = clean(entry.get("title", ""))
                summary  = clean(entry.get("summary", ""))
                combined = (title + " " + summary).lower()
                if not is_english(title):
                    continue
                if not any(kw in combined for kw in keywords):
                    continue
                published = entry.get("published", "") or entry.get("updated", "")
                try:
                    date = pd.to_datetime(published, utc=True).tz_localize(None)
                except Exception:
                    date = pd.NaT
                if pd.notna(date) and date < pd.Timestamp(today - timedelta(days=30)):
                    continue
                rows.append({
                    "source": "RSS", "category": category,
                    "date": date, "title": title,
                    "url": entry.get("link", ""),
                    "domain": feed_url.split("/")[2],
                })
            time.sleep(_env_float("MACRO_API_LOOP_SLEEP_SEC", 0.05))
        except Exception as e:
            print(f"  ⚠️ RSS 피드 오류 ({feed_url[:40]}...): {e}")

    df = pd.DataFrame(rows)
    if not df.empty:
        df = (df.drop_duplicates(subset=["title"])
                .sort_values("date", ascending=False)
                .reset_index(drop=True)
                .head(10))
    print(f"  ✅ RSS [{category}] {len(df)}건")
    return df


# ============================================================
# 규제 수집 함수
# ============================================================

NEWSAPI_QUERIES = [
    ("export control semiconductor chip ban entity list BIS",          "미국", "수출규제", "NewsAPI_미국수출"),
    ("EPA greenhouse gas emission regulation clean air chemical PFAS", "미국", "환경규제", "NewsAPI_미국환경"),
    ("China export control ban rare earth semiconductor MOFCOM",       "중국", "수출규제", "NewsAPI_중국수출"),
    ("China carbon emission ETS environmental regulation MEE",         "중국", "환경규제", "NewsAPI_중국환경"),
    ("Japan METI export control semiconductor technology restriction",  "일본", "수출규제", "NewsAPI_일본수출"),
    ("Japan carbon emission climate MOE environment regulation",       "일본", "환경규제", "NewsAPI_일본환경"),
    ("EU export control dual-use sanction regulation EUR-Lex",         "EU",   "수출규제", "NewsAPI_EU수출"),
    ("EU CBAM carbon border ETS emission regulation Green Deal",       "EU",   "환경규제", "NewsAPI_EU환경"),
]

REG_GDELT_QUERIES = [
    ("export controls semiconductor advanced chips BIS entity list sourcelang:english",       "미국", "수출규제", "GDELT_미국수출"),
    ("United States EPA greenhouse gas PFAS chemical regulation semiconductor sourcelang:english", "미국", "환경규제", "GDELT_미국환경"),
    ("China export controls gallium germanium rare earth semiconductor MOFCOM sourcelang:english", "중국", "수출규제", "GDELT_중국수출"),
    ("China carbon emissions trading environmental regulation MEE sourcelang:english",        "중국", "환경규제", "GDELT_중국환경"),
    ("Japan METI export controls semiconductor technology restrictions sourcelang:english",    "일본", "수출규제", "GDELT_일본수출"),
    ("Japan carbon climate green transformation environmental regulation sourcelang:english",  "일본", "환경규제", "GDELT_일본환경"),
    ("European Union dual use export control sanctions semiconductor regulation sourcelang:english", "EU", "수출규제", "GDELT_EU수출"),
    ("European Union CBAM carbon border adjustment ETS Green Deal regulation sourcelang:english",    "EU", "환경규제", "GDELT_EU환경"),
]

SERPER_QUERIES = [
    ("BIS export controls semiconductor site:bis.doc.gov OR site:federalregister.gov",         "미국", "수출규제", "Serper_미국BIS"),
    ("EPA regulation rule final site:epa.gov OR site:federalregister.gov",                     "미국", "환경규제", "Serper_미국EPA"),
    ("China export control semiconductor rare earth ban 2024 OR 2025",                         "중국", "수출규제", "Serper_중국수출"),
    ("EU export control dual-use regulation site:eur-lex.europa.eu OR site:ec.europa.eu",      "EU",   "수출규제", "Serper_EU수출"),
    ("EU CBAM carbon border adjustment mechanism site:ec.europa.eu OR site:eur-lex.europa.eu", "EU",   "환경규제", "Serper_EU환경"),
    ("Japan METI export control Korea semiconductor 2024 OR 2025",                             "일본", "수출규제", "Serper_일본수출"),
    ("Japan GX green transformation carbon neutrality regulation",                              "일본", "환경규제", "Serper_일본환경"),
    ("China MEE environmental regulation carbon ETS 2024 OR 2025",                             "중국", "환경규제", "Serper_중국환경"),
]


def fetch_newsapi_reg(query, country, reg_type, source_name, news_api_key):
    if not _env_bool("MACRO_ENABLE_NEWSAPI", True):
        print(f"  ⚠️ {source_name}: NewsAPI 비활성화 → skip")
        return pd.DataFrame()
    if not _valid_api_key(news_api_key):
        print(f"  ⚠️ {source_name}: NEWS_API_KEY 없음/미설정 → skip")
        return pd.DataFrame()

    params = {
        "q": query, "language": "en", "sortBy": "publishedAt",
        "pageSize": 15, "apiKey": news_api_key,
    }
    try:
        r = requests.get(NEWSAPI_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "ok":
            print(f"  ⚠️ {source_name}: {data.get('message', '')}")
            return pd.DataFrame()
        rows = [make_reg_row(country, reg_type, parse_date(a.get("publishedAt")),
                             a.get("title", ""), a.get("url", ""), source_name)
                for a in data.get("articles", []) if a.get("title")]
        df = pd.DataFrame(rows)
        print(f"  ✅ {source_name}: {len(df)}건")
        return df
    except Exception as e:
        print(f"  ❌ {source_name}: {e}")
        return pd.DataFrame()


def fetch_reg_gdelt(query, country, reg_type, source_name, retries=None):
    if retries is None:
        retries = 1 if _env_bool("MACRO_GDELT_RETRY_ON_429", False) else 0
    # REG_GDELT_QUERIES already includes sourcelang filters.
    params = {
        "query": query, "mode": "artlist", "maxrecords": int(os.getenv("MACRO_GDELT_MAXRECORDS", "3")),
        "format": "json", "sort": "DateDesc", "timespan": "30d",
    }
    for attempt in range(retries + 1):
        data, err = _gdelt_get(params, timeout=35)
        if err:
            if "rate_limited_429" in err and attempt < retries:
                wait = _env_float("MACRO_GDELT_429_SLEEP_SEC", 3)
                print(f"  ⏳ {source_name}: 429 회피 대기 {int(wait)}초")
                time.sleep(wait + random.uniform(1, 3))
                continue
            print(f"  ⚠️ {source_name}: GDELT 스킵: {err}")
            return pd.DataFrame()

        rows = []
        for a in (data or {}).get("articles", []):
            title = clean(a.get("title", ""))
            if not title or not is_english(title):
                continue
            rows.append(make_reg_row(
                country, reg_type,
                pd.to_datetime(a.get("seendate", "")[:8], format="%Y%m%d", errors="coerce"),
                title, a.get("url", ""), source_name,
            ))
        df = pd.DataFrame(rows)
        print(f"  ✅ {source_name}: {len(df)}건")
        return df
    return pd.DataFrame()

def fetch_serper_reg(query, country, reg_type, source_name, serper_api_key):
    if not _env_bool("MACRO_ENABLE_SERPER", True):
        print(f"  ⚠️ {source_name}: Serper 비활성화 → skip")
        return pd.DataFrame()

    if not _valid_api_key(serper_api_key):
        print(f"  ⚠️ {source_name}: SERPER_API_KEY 없음/미설정 → skip")
        return pd.DataFrame()

    headers = {
        "X-API-KEY": str(serper_api_key).strip(),
        "Content-Type": "application/json",
    }

    # Serper news endpoint is sensitive to very complex Google syntax.
    # Try original query first, then a simplified query, then general search endpoint.
    simplified_query = re.sub(r"\s+OR\s+", " ", query, flags=re.I)
    simplified_query = re.sub(r"site:[^\s]+", "", simplified_query).strip() or query

    attempts = [
        (SERPER_URL, query, "news-original"),
        (SERPER_URL, simplified_query, "news-simplified"),
        (SERPER_SEARCH_URL, simplified_query, "search-fallback"),
    ]

    last_error = ""
    for endpoint, q, mode in attempts:
        try:
            r = requests.post(
                endpoint,
                headers=headers,
                json={"q": q, "gl": "us", "hl": "en", "num": 10, "tbs": "qdr:m"},
                timeout=25,
            )
            if r.status_code == 400:
                last_error = (r.text or "400 Bad Request")[:220].replace("\n", " ")
                continue
            if r.status_code in {401, 403}:
                print(f"  ⚠️ {source_name}: Serper 인증/권한 오류 {r.status_code} → API 키 확인")
                return pd.DataFrame()
            r.raise_for_status()
            payload = r.json()

            items = payload.get("news") or payload.get("organic") or []
            rows = []
            for item in items:
                title = item.get("title", "")
                link = item.get("link") or item.get("url") or ""
                date_raw = item.get("date") or item.get("publishedDate") or item.get("snippetDate")
                rows.append(make_reg_row(country, reg_type, parse_date(date_raw), title, link, source_name))
            df = pd.DataFrame([row for row in rows if row.get("title")])
            print(f"  ✅ {source_name}: {len(df)}건 ({mode})")
            return df
        except Exception as e:
            last_error = str(e)
            continue

    print(f"  ⚠️ {source_name}: Serper 스킵: {last_error}")
    return pd.DataFrame()


# ============================================================
# 메인 실행
# ============================================================

def run():
    from dotenv import load_dotenv
    load_dotenv()

    NEWS_API_KEY   = os.getenv("NEWS_API_KEY")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")

    # Use Korea Standard Time by default so file names reflect the user's local execution date.
    tz_hours = int(os.getenv("MACRO_INTAKE_TZ_HOURS", "9"))
    TODAY = datetime.now(timezone(timedelta(hours=tz_hours))).replace(tzinfo=None)

    # Fast default: use a recent-enough rolling window for percentile/level criteria.
    # Override with MACRO_HISTORY_START_YEAR=1900 only when a full historical rebuild is required.
    history_start_year = _env_int("MACRO_HISTORY_START_YEAR", 2018)
    start_date = datetime(history_start_year, 1, 1)
    D_START  = _env_str("MACRO_D_START", start_date.strftime("%Y%m%d"))
    CUTOFF = datetime(2025, 6, 1)
    D_END    = TODAY.strftime("%Y%m%d")
    M_START  = _env_str("MACRO_M_START", start_date.strftime("%Y%m"))
    M_END    = TODAY.strftime("%Y%m")
    FRED_START = _env_str("MACRO_FRED_START", start_date.strftime("%Y-%m-%d"))
    FRED_END   = TODAY.strftime("%Y-%m-%d")
    Q_START  = _env_str("MACRO_Q_START", f"{history_start_year}Q1")
    Q_END    = f"{TODAY.year}Q4"
    YF_START = _env_str("MACRO_YF_START", start_date.strftime("%Y-%m-%d"))
    YF_END   = TODAY.strftime("%Y-%m-%d")

    # Macro 원천 데이터는 전역 공통 경로 하나로 통일한다.
    # Canonical: data/_global_common/macro
    SAVE_DIR = macro_common_dir(create=True)

    today_str = TODAY.strftime("%Y%m%d")

    if _reuse_today_outputs_if_complete(SAVE_DIR, today_str):
        _write_run_summary(SAVE_DIR, today_str)
        return

    _cleanup_legacy_macro_files(SAVE_DIR)

    # ============================================================
    # 1. ECOS
    # ============================================================
    print("\n📊 ECOS 데이터 수집 시작")

    if _env_bool("MACRO_SHOW_ITEM_CODES", False):
        show_item_codes("817Y002")

    daily_list = [
        normalize(fetch_ecos("817Y002", "D", D_START, D_END, "010210000", label="국고채_10년")),
        normalize(fetch_ecos("817Y002", "D", D_START, D_END, "010200000", label="국고채_3년")),
        normalize(fetch_ecos("817Y002", "D", D_START, D_END, "010101000", label="콜금리")),
        normalize(fetch_ecos("817Y002", "D", D_START, D_END, "010502000", label="CD금리_91일")),
        normalize(fetch_ecos("817Y002", "D", D_START, D_END, "010300000", label="회사채_AA-")),
        normalize(fetch_ecos("817Y002", "D", D_START, D_END, "010320000", label="회사채_BBB-")),
        normalize(fetch_ecos("731Y001", "D", D_START, D_END, "0000001",   label="원달러")),
        normalize(fetch_ecos("731Y001", "D", D_START, D_END, "0000003",   label="원유로")),
        normalize(fetch_ecos("731Y001", "D", D_START, D_END, "0000002",   label="원엔_100")),
        normalize(fetch_ecos("731Y001", "D", D_START, D_END, "0000053",   label="원위안")),
    ]

    df_daily = merge_dfs([df for df in daily_list if df is not None and not df.empty])
    if df_daily is not None:
        df_daily = normalize(df_daily)
        if "국고채_10년" in df_daily.columns and "국고채_3년" in df_daily.columns:
            df_daily["국고채_10년_3년_스프레드"] = df_daily["국고채_10년"] - df_daily["국고채_3년"]
        if "국고채_3년" in df_daily.columns:
            if "회사채_AA-" in df_daily.columns:
                df_daily["신용스프레드_AA-"] = df_daily["회사채_AA-"] - df_daily["국고채_3년"]
            if "회사채_BBB-" in df_daily.columns:
                df_daily["신용스프레드_BBB-"] = df_daily["회사채_BBB-"] - df_daily["국고채_3년"]
        print("📊 ECOS 일별 완료")

    time.sleep(_env_float("MACRO_SHORT_SLEEP_SEC", 0.05))

    monthly_list = [
        normalize(fetch_ecos("722Y001", "M", M_START, M_END, "0101000",     label="한국_기준금리")),
        normalize(fetch_ecos("901Y027", "M", M_START, M_END, "I61BC",       label="실업률")),
        normalize(fetch_ecos("901Y027", "M", M_START, M_END, "I61E",        label="고용률_15세이상")),
        normalize(fetch_ecos("512Y013", "M", M_START, M_END, "99988", "AA", label="BSI_전산업_실적")),
        normalize(fetch_ecos("512Y014", "M", M_START, M_END, "99988", "BA", label="BSI_전산업_전망")),
        normalize(fetch_ecos("901Y009", "M", M_START, M_END, "0",           label="CPI_전년비")),
        normalize(fetch_ecos("732Y001", "M", M_START, M_END, "99",          label="외환보유액_백만달러")),
    ]

    df_monthly = merge_dfs([df for df in monthly_list if df is not None and not df.empty])
    if df_monthly is not None:
        df_monthly = normalize(df_monthly)
        if "한국은행_기준금리" in df_monthly.columns and "한국_기준금리" not in df_monthly.columns:
            df_monthly = df_monthly.rename(columns={"한국은행_기준금리": "한국_기준금리"})

    if df_daily is not None and df_monthly is not None:
        df_daily = attach_monthly_policy_rate_to_daily(
            df_daily=df_daily,
            df_monthly_rate=df_monthly,
            rate_col="한국은행_기준금리",
        )

    quarterly_list = [
        normalize(fetch_ecos("200Y102", "Q", Q_START, Q_END, "10111", label="GDP성장률_전기비")),
        normalize(fetch_ecos("200Y102", "Q", Q_START, Q_END, "10211", label="GDP성장률_전년비")),
    ]

    df_quarterly = merge_dfs([df for df in quarterly_list if df is not None and not df.empty])
    if df_quarterly is not None:
        df_quarterly = normalize(df_quarterly)

    validate_dataset(df_daily,     "ecos_daily")
    validate_dataset(df_monthly,   "ecos_monthly")
    validate_dataset(df_quarterly, "ecos_quarterly")
    print("🎉 ECOS 완료")

    # ============================================================
    # 2. 외부 거시지표 (FRED + yfinance + OECD)
    # ============================================================
    print("\n📊 외부 거시지표 수집 시작")

    # ext_일별:
    # - 미국_국채_10년: 글로벌 장기 금리, 한국 딥테크 할인율 참고용
    # - 미국_국채_13주: 단기 금리, 10Y-13W 스프레드를 통한 경기 사이클 확인
    # - 달러인덱스_DXY: 글로벌 달러 강세/약세 지표, 원달러와 함께 교차 검증
    # - 유가_WTI/Brent: 원가 부담·인플레이션과 경기 회복 신호가 혼재하므로 평균/스프레드로 보완
    # - 천연가스: 에너지 비용·AI/데이터센터 전력 비용 부담 지표로 해석
    # - 구리: 경기 선행 신호이자 원자재 수요/원가 압력 참고용

    ext_daily_list = [
        fetch_fred_daily("DFF",       "미국_연방기금금리_DFF",       FRED_START, FRED_END),
        fetch_fred_daily("DFEDTARU",  "미국_정책금리_상단",          FRED_START, FRED_END),
        fetch_fred_daily("DFEDTARL",  "미국_정책금리_하단",          FRED_START, FRED_END),

        fetch_yf("^TNX",     "미국_국채_10년",  YF_START, YF_END),
        fetch_yf("^IRX",     "미국_국채_13주",  YF_START, YF_END),
        fetch_fred_daily("DGS2", "미국_국채_2년",   FRED_START, FRED_END),
        fetch_yf("DX-Y.NYB", "달러인덱스_DXY",  YF_START, YF_END),
        fetch_yf("CL=F",     "유가_WTI",        YF_START, YF_END),
        fetch_yf("BZ=F",     "유가_Brent",      YF_START, YF_END),
        fetch_yf("NG=F",     "천연가스",        YF_START, YF_END),
        fetch_yf("HG=F",     "구리",            YF_START, YF_END),
    ]

    df_ext_daily = merge_dfs([normalize(df) for df in ext_daily_list if df is not None and not df.empty])
    if df_ext_daily is not None:
        df_ext_daily = normalize(df_ext_daily)
        if "미국_국채_10년" in df_ext_daily.columns and "미국_국채_13주" in df_ext_daily.columns:
            df_ext_daily["미국_국채_10년_13주_스프레드"] = (
                df_ext_daily["미국_국채_10년"] - df_ext_daily["미국_국채_13주"]
            )
        if "미국_국채_10년" in df_ext_daily.columns and "미국_국채_2년" in df_ext_daily.columns:
            df_ext_daily["미국_국채_10년_2년_스프레드"] = (
                df_ext_daily["미국_국채_10년"] - df_ext_daily["미국_국채_2년"]
            )
        if "유가_WTI" in df_ext_daily.columns and "유가_Brent" in df_ext_daily.columns:
            df_ext_daily["유가_평균"] = df_ext_daily[["유가_WTI", "유가_Brent"]].mean(axis=1)
            df_ext_daily["유가_브렌트_WTI_스프레드"] = (
                df_ext_daily["유가_Brent"] - df_ext_daily["유가_WTI"]
            )
        if "구리" in df_ext_daily.columns and "천연가스" in df_ext_daily.columns:
            df_ext_daily["구리_천연가스_평균"] = df_ext_daily[["구리", "천연가스"]].mean(axis=1)
        print("📊 외부 일별 완료")

    time.sleep(_env_float("MACRO_SHORT_SLEEP_SEC", 0.05))

    ext_monthly_list = [
        fetch_fred("FEDFUNDS",        "미국_기준금리_FFR",     FRED_START, FRED_END),
        fetch_fred("EFFR",            "미국_콜금리_EFFR",      FRED_START, FRED_END),
        fetch_fred("DTB3",            "미국_단기금리_3M",      FRED_START, FRED_END),
        fetch_fred("SOFR",            "미국_SOFR",             FRED_START, FRED_END),
        fetch_fred("BAMLC0A1CAAAEY",  "미국_회사채_AAA",       FRED_START, FRED_END),  # ✅ 수정
        fetch_fred("BAMLC0A4CBBBEY",  "미국_회사채_BBB",       FRED_START, FRED_END),  # ✅ 수정
        fetch_fred("BAMLH0A0HYM2",    "미국_하이일드_스프레드", FRED_START, FRED_END),
        fetch_fred("BAMLC0A0CM",      "미국_IG_스프레드",      FRED_START, FRED_END),
        fetch_fred("UNRATE",          "미국_실업률",           FRED_START, FRED_END),
        fetch_fred("EMRATIO",         "미국_고용률",           FRED_START, FRED_END),
        fetch_fred("BSCICP03USM665S", "미국_기업심리_BSI대용", FRED_START, FRED_END),
        fetch_oecd_cli("KOR", "OECD_CLI_한국", M_START + "01", M_END + "01"),
        fetch_oecd_cli("USA", "OECD_CLI_미국", M_START + "01", M_END + "01"),
        fetch_oecd_cli("G20", "G20_CLI",       M_START + "01", M_END + "01"),
    ]

    df_ext_monthly = merge_dfs([normalize(df) for df in ext_monthly_list if df is not None and not df.empty])
    if df_ext_monthly is not None:
        df_ext_monthly = normalize(df_ext_monthly)
        print("📊 외부 월별 완료")

    if df_ext_daily is not None:
        validate_dataset(df_ext_daily, "ext_daily")
    if df_ext_monthly is not None and not df_ext_monthly.empty:
        validate_dataset(df_ext_monthly, "ext_monthly")
    else:
        print("⚠️ ext_monthly 데이터 없음 → 검증 생략")

    print("🎉 외부 거시지표 완료")

    # ============================================================
    # 2-1. 시장 공통 벤치마크 지수
    # ============================================================
    # Macro Agent가 개별 기업 부진, 한국 시장 risk-off, 반도체 섹터 동반 약세를
    # 분리해서 볼 수 있도록 KOSPI/KOSDAQ/섹터/미국 대표 지수를 일별 입력에 합친다.
    df_market_indices = collect_market_index_benchmarks(YF_START, YF_END)
    if df_market_indices is not None and not df_market_indices.empty:
        if df_ext_daily is not None and not df_ext_daily.empty:
            df_ext_daily = pd.merge(df_ext_daily, df_market_indices, on="date", how="outer", sort=True)
        else:
            df_ext_daily = df_market_indices.copy()
        df_ext_daily = normalize(df_ext_daily)
        validate_dataset(df_ext_daily, "ext_daily")
    else:
        print("⚠️ 시장 공통 벤치마크 지수 없음 → Macro Agent 시장/섹터 분해 점수 생략 가능")

    # ============================================================
    # 3. 희토류 + 헬륨
    # ============================================================
    print("\n🪨 희토류 + 헬륨 수집 시작")

    df_re_fred = material_collectors.fetch_rare_earth_fred(TODAY)
    df_re_smm  = material_collectors.fetch_all_smm(TODAY)
    df_re_usgs = material_collectors.fetch_usgs_rare_earth(TODAY)

    rare_frames = []
    for df, src in [(df_re_fred, "FRED"), (df_re_smm, "SMM"), (df_re_usgs, "USGS")]:
        if df is not None and not df.empty:
            tmp = normalize_rare_earth(df.copy())
            tmp["source"] = src
            rare_frames.append(tmp)

    if rare_frames:
        df_rare_all = pd.concat(rare_frames, ignore_index=True, sort=False)
    else:
        df_rare_all = None
        print("⚠️ 희토류 데이터 없음")

    df_he_usgs = material_collectors.fetch_usgs_helium(TODAY)
    df_he_blm  = material_collectors.fetch_blm_helium(TODAY)
    df_he_news = material_collectors.fetch_helium_news(TODAY)

    helium_frames = []
    for df, src in [(df_he_usgs, "USGS"), (df_he_blm, "BLM"), (df_he_news, "GDELT")]:
        if df is not None and not df.empty:
            tmp = normalize_helium(df.copy())
            tmp["source"] = src
            helium_frames.append(tmp)

    if helium_frames:
        df_helium_all = pd.concat(helium_frames, ignore_index=True, sort=False)
    else:
        df_helium_all = None
        print("⚠️ 헬륨 데이터 없음")

    print("🎉 희토류 + 헬륨 완료")

    # ============================================================
    # 3-1. WorldMonitor 참고형 반도체 공급망/소재/항만 리스크 보강
    # ============================================================
    print("\n🧭 반도체 공급망/소재/항만 리스크 보강 수집 시작")
    df_supply_risk = collect_semiconductor_supply_chain_risks(TODAY)
    if df_supply_risk is None or df_supply_risk.empty:
        print("⚠️ 반도체 공급망/소재/항만 리스크 보강 데이터 없음")

    # ============================================================
    # 3-2. 업로드 리서치 기반 AI/크레딧 스프레드 리스크 보강
    # ============================================================
    print("\n🏦 AI/빅테크 크레딧 스프레드 리스크 보강 저장")
    df_bigtech_credit = build_bigtech_credit_macro_signals(TODAY)
    if df_bigtech_credit is None or df_bigtech_credit.empty:
        print("⚠️ AI/빅테크 크레딧 스프레드 리스크 보강 데이터 없음")

    # ============================================================
    # 4. 외신 뉴스
    # ============================================================
    print("\n📰 외신 뉴스 수집 시작")

    news_dfs = []
    for label, kw in NEWS_GDELT_QUERIES.items():
        df = fetch_news_gdelt_ext(kw, label)
        if not df.empty:
            news_dfs.append(df)
        time.sleep(_env_float("MACRO_GDELT_LOOP_SLEEP_SEC", 0.05))

    for category in RSS_FEEDS:
        df = fetch_rss(category, TODAY)
        if not df.empty:
            news_dfs.append(df)
        time.sleep(_env_float("MACRO_RSS_LOOP_SLEEP_SEC", 0.05))

    # GDELT/Reuters RSS가 막히거나 부족할 때 WorldMonitor 참고형 Google News/RSS fallback 추가
    df_wm_news = fetch_semiconductor_worldmonitor_news(TODAY)
    if df_wm_news is not None and not df_wm_news.empty:
        news_dfs.append(df_wm_news)

    if news_dfs:
        df_news = pd.concat(news_dfs, ignore_index=True)
        df_news["_key"] = df_news["title"].str[:40].str.lower()
        df_news = (df_news.drop_duplicates(subset=["_key"])
                          .drop(columns=["_key"])
                          .sort_values(["category", "date"], ascending=[True, False])
                          .reset_index(drop=True))
    else:
        df_news = None
        print("⚠️ 외신 뉴스 없음")

    print("🎉 외신 뉴스 완료")

    # ============================================================
    # 5. 규제 공고
    # ============================================================
    print("\n⚖️ 규제 공고 수집 시작")

    if _env_bool("MACRO_GDELT_PRE_WAIT", False):
        print("⏳ GDELT rate limit 회피 대기 (10초)...")
        time.sleep(10)

    reg_dfs = []

    print("\n▶ NewsAPI 수집 중...")
    for query, country, reg_type, source in NEWSAPI_QUERIES:
        df = fetch_newsapi_reg(query, country, reg_type, source, NEWS_API_KEY)
        if not df.empty:
            reg_dfs.append(df)
        time.sleep(_env_float("MACRO_API_LOOP_SLEEP_SEC", 0.05))

    print("\n▶ GDELT 규제 수집 중...")
    for query, country, reg_type, source in REG_GDELT_QUERIES:
        df = fetch_reg_gdelt(query, country, reg_type, source)
        if not df.empty:
            reg_dfs.append(df)
        time.sleep(_env_float("MACRO_GDELT_LOOP_SLEEP_SEC", 0.05))

    print("\n▶ Serper 수집 중...")
    for query, country, reg_type, source in SERPER_QUERIES:
        df = fetch_serper_reg(query, country, reg_type, source, SERPER_API_KEY)
        if not df.empty:
            reg_dfs.append(df)
        time.sleep(_env_float("MACRO_API_LOOP_SLEEP_SEC", 0.05))

    print("\n▶ WorldMonitor 참고형 공식/RSS 규제 fallback 수집 중...")
    df_wm_reg = fetch_regulatory_worldmonitor_fallback(TODAY)
    if df_wm_reg is not None and not df_wm_reg.empty:
        reg_dfs.append(df_wm_reg)

    since_180d = (TODAY - timedelta(days=180)).strftime("%Y-%m-%d")

    if reg_dfs:
        df_reg = pd.concat(reg_dfs, ignore_index=True)
        df_reg = df_reg[
            df_reg["date"].isna() | (df_reg["date"] >= pd.Timestamp(since_180d))
        ]
        df_reg["_key"] = df_reg["title"].str[:60].str.lower().str.strip()
        df_reg = (df_reg.drop_duplicates(subset=["_key"])
                        .drop(columns=["_key"])
                        .sort_values(["country", "type", "date"], ascending=[True, True, False])
                        .reset_index(drop=True))
    else:
        df_reg = None
        print("⚠️ 규제 데이터 없음")

    print("🎉 규제 공고 완료")

    # ============================================================
    # 6. 통합 output 파일 쓰기
    # ============================================================
    print("\n💾 macro_일별 / macro_월별 / macro_공통 통합 저장 시작")

    df_macro_daily, df_macro_monthly = _align_daily_monthly(
        daily_frames=[df_daily, df_ext_daily],
        monthly_frames=[df_monthly, df_quarterly, df_ext_monthly],
    )

    common_frames = []
    for optional_df in [df_rare_all, df_helium_all, df_supply_risk, df_bigtech_credit, df_news, df_reg]:
        if optional_df is not None and not optional_df.empty:
            common_frames.append(optional_df)
    df_macro_common = pd.concat(common_frames, ignore_index=True, sort=False) if common_frames else None

    for file in SAVE_DIR.glob("macro_*.csv"):
        file.unlink()

    if df_macro_daily is not None and not df_macro_daily.empty:
        fname = SAVE_DIR / f"macro_일별_{today_str}.csv"
        _safe_write_csv(df_macro_daily, fname)
        print(f"✅ 저장 완료: {fname}")
    else:
        print("⚠️ macro_일별 데이터 없음")

    if df_macro_monthly is not None and not df_macro_monthly.empty:
        fname = SAVE_DIR / f"macro_월별_{today_str}.csv"
        _safe_write_csv(df_macro_monthly, fname)
        print(f"✅ 저장 완료: {fname}")
    else:
        print("⚠️ macro_월별 데이터 없음")

    if df_macro_common is not None and not df_macro_common.empty:
        fname = SAVE_DIR / f"macro_공통_{today_str}.csv"
        _safe_write_csv(df_macro_common, fname)
        print(f"✅ 저장 완료: {fname}")
    else:
        print("⚠️ macro_공통 데이터 없음")

    print("🎉 macro 통합 출력 완료")

    # ============================================================
    # 완료 요약
    # ============================================================
    print(f"\n{'='*50}")
    print(f"🏁 전체 데이터 수집 완료")
    print(f"📁 저장 위치: {SAVE_DIR}")
    print(f"{'='*50}")
    for f in sorted(SAVE_DIR.glob(f"*_{today_str}.csv")):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    run()


# ---------------------------------------------------------------------
# AlphaProve unified data_intake wrapper
# ---------------------------------------------------------------------
def run_macro_intake(company_dir: str | None = None, company: str | None = None, **_: object):
    import json
    from datetime import datetime
    from common.data_paths import company_agent_dir

    out_dir = company_agent_dir(company_dir or "global", "macro", create=True) / "intake"
    out_dir.mkdir(parents=True, exist_ok=True)
    status = "OK"
    error = None
    try:
        result = run()
    except Exception as exc:
        result = None
        status = "PARTIAL"
        error = str(exc)

    manifest = {
        "agent": "macro",
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "company_dir": company_dir,
        "company": company,
        "result_type": type(result).__name__,
        "error": error,
        "principle": "macro_intake 기존 run()을 unified data_intake에서 호출",
    }
    path = out_dir / "macro_intake_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Macro Intake] manifest 저장: {path}")
    return manifest


def run_intake(company_dir: str | None = None, company: str | None = None, **kwargs: object):
    return run_macro_intake(company_dir=company_dir, company=company, **kwargs)
