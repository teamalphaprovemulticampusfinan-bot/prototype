from __future__ import annotations

"""
Robust material collectors for AlphaProve Macro Data Intake.

Why this file exists
--------------------
The original macro intake had three fragile points:
1) FRED IP28 sometimes timed out.
2) SMM rare-earth prices are often hidden behind login.
3) USGS data was only checked by PDF availability and then static tables were used.

This module keeps the same output contract used by runner.py:
- fetch_rare_earth_fred(today) -> DataFrame with date + numeric columns
- fetch_all_smm(today) -> DataFrame with date + numeric columns
- fetch_usgs_rare_earth(today) -> DataFrame with date + numeric columns
- fetch_usgs_helium(today) -> DataFrame with date + numeric columns
- fetch_blm_helium(today) -> DataFrame with date/status/source/url
- fetch_helium_news(today) -> DataFrame with date/title/url/domain

It never writes to workspace. All final writes remain controlled by runner.py.
"""

import io
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus

import feedparser
import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup

try:
    from common.data_paths import macro_common_dir
except Exception:  # pragma: no cover
    macro_common_dir = None  # type: ignore


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/csv,text/html,application/xml,text/xml,*/*",
    "Accept-Language": "en-US,en;q=0.9,ko;q=0.7",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ---------------------------------------------------------------------------
# small utilities
# ---------------------------------------------------------------------------

def _env_bool(name: str, default: bool = True) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return bool(default)
    return str(raw).strip().lower() not in {"0", "false", "no", "off", ""}


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return float(default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default))))
    except Exception:
        return int(default)


def _valid_key(value: str | None) -> bool:
    if not value:
        return False
    text = value.strip()
    if not text:
        return False
    return text.lower() not in {"none", "null", "na", "n/a", "your_key", "your-api-key", "여기에_실제키"}


def _clean(text: str | None, limit: int = 500) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _safe_float(value) -> float | None:
    if value is None:
        return None
    text = str(value).replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        return float(m.group())
    except Exception:
        return None


def _parse_date(value) -> pd.Timestamp:
    if value is None or value == "":
        return pd.NaT
    try:
        return pd.to_datetime(value, utc=True).tz_localize(None)
    except Exception:
        return pd.NaT


def _request_get(url: str, *, params: dict | None = None, timeout: float | tuple[float, float] | None = None, retries: int | None = None, sleep: float | None = None) -> requests.Response:
    retries = _env_int("MACRO_MATERIAL_RETRIES", 1) if retries is None else int(retries)
    sleep = _env_float("MACRO_MATERIAL_RETRY_SLEEP_SEC", 0.3) if sleep is None else float(sleep)
    timeout = timeout or (_env_float("MACRO_MATERIAL_CONNECT_TIMEOUT", 3), _env_float("MACRO_MATERIAL_READ_TIMEOUT", 8))
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = SESSION.get(url, params=params, timeout=timeout)
            if resp.status_code in {429, 500, 502, 503, 504} and attempt < retries:
                wait = sleep * attempt
                print(f"  ⏳ HTTP {resp.status_code} retry {attempt}/{retries} after {wait:.1f}s: {url[:80]}")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < retries:
                wait = sleep * attempt
                print(f"  ⏳ {type(exc).__name__} retry {attempt}/{retries} after {wait:.1f}s: {url[:80]}")
                time.sleep(wait)
    if last_exc:
        raise last_exc
    raise RuntimeError(f"request failed: {url}")


def _macro_dir() -> Path | None:
    if macro_common_dir is None:
        return None
    try:
        return macro_common_dir(create=True)
    except Exception:
        return None


def _write_debug(name: str, text: str) -> None:
    if not _env_bool("MACRO_MATERIAL_WRITE_DEBUG", True):
        return
    base = _macro_dir()
    if base is None:
        return
    try:
        (base / "debug").mkdir(parents=True, exist_ok=True)
        (base / "debug" / name).write_text(text, encoding="utf-8")
    except Exception:
        pass


def _google_news_rss(query: str, *, days: int = 30) -> str:
    q = f"{query} when:{max(1, int(days))}d"
    return f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"


# ---------------------------------------------------------------------------
# FRED rare-earth proxy
# ---------------------------------------------------------------------------

def _fred_observations_api(series_id: str, label: str, start: str | None, end: str | None) -> pd.DataFrame:
    api_key = os.getenv("FRED_API_KEY")
    if not _valid_key(api_key):
        return pd.DataFrame()
    params = {
        "series_id": series_id,
        "api_key": api_key.strip(),
        "file_type": "json",
        "sort_order": "asc",
    }
    if start:
        params["observation_start"] = start
    if end:
        params["observation_end"] = end
    resp = _request_get("https://api.stlouisfed.org/fred/series/observations", params=params)
    data = resp.json()
    rows = []
    for obs in data.get("observations", []):
        value = obs.get("value")
        if value in {None, "", "."}:
            continue
        rows.append({"date": obs.get("date"), label: value})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df[label] = pd.to_numeric(df[label], errors="coerce")
    return df.dropna(subset=["date", label]).sort_values("date").reset_index(drop=True)


def _fred_graph_csv(series_id: str, label: str) -> pd.DataFrame:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    resp = _request_get(url, params={"id": series_id})
    text = resp.text
    if not text.strip():
        return pd.DataFrame()
    df = pd.read_csv(io.StringIO(text))
    if df.empty or len(df.columns) < 2:
        return pd.DataFrame()
    df = df.iloc[:, :2].copy()
    df.columns = ["date", label]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df[label] = pd.to_numeric(df[label], errors="coerce")
    return df.dropna(subset=["date", label]).sort_values("date").reset_index(drop=True)


def _load_latest_material_cache(pattern: str, wanted_col: str) -> pd.DataFrame:
    base = _macro_dir()
    if base is None:
        return pd.DataFrame()
    files = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in files:
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
            if "date" in df.columns and wanted_col in df.columns:
                df = df[["date", wanted_col]].copy()
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df[wanted_col] = pd.to_numeric(df[wanted_col], errors="coerce")
                df = df.dropna(subset=["date", wanted_col])
                if not df.empty:
                    print(f"  ✅ cache fallback: {path.name} {len(df)}행")
                    return df
        except Exception:
            continue
    return pd.DataFrame()


def fetch_rare_earth_fred(today: datetime | None = None) -> pd.DataFrame:
    """Fetch FRED IP28 with API -> fredgraph.csv -> local cache fallback."""
    print("  [FRED 희토류]")
    label = os.getenv("MACRO_RARE_EARTH_FRED_LABEL", "희토류수입가격지수")
    series_id = os.getenv("MACRO_RARE_EARTH_FRED_SERIES", "IP28").strip() or "IP28"
    today = today or datetime.today()
    start = (today - timedelta(days=365 * _env_int("MACRO_MATERIAL_FRED_YEARS", 10))).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    errors: list[str] = []
    try:
        df = _fred_observations_api(series_id, label, start, end)
        if not df.empty:
            print(f"  ✅ FRED API [{series_id}]: {len(df)}행")
            return df
    except Exception as exc:  # noqa: BLE001
        errors.append(f"api={type(exc).__name__}: {exc}")

    try:
        df = _fred_graph_csv(series_id, label)
        if not df.empty:
            # Keep the latest horizon similar to the rest of macro intake.
            df = df[df["date"] >= pd.Timestamp(start)]
            print(f"  ✅ FRED graph.csv [{series_id}]: {len(df)}행")
            return df.reset_index(drop=True)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"graph={type(exc).__name__}: {exc}")

    df_cache = _load_latest_material_cache("희토류_*.csv", label)
    if not df_cache.empty:
        print(f"  ⚠️ FRED [{series_id}] 신규 수집 실패 → 기존 캐시 사용")
        return df_cache

    print(f"  ⚠️ FRED [{series_id}] 실패 → skip ({'; '.join(errors)[:240]})")
    return pd.DataFrame(columns=["date", label])


# ---------------------------------------------------------------------------
# SMM / public price proxy
# ---------------------------------------------------------------------------

SMM_PAGES = {
    "네오디뮴_Nd_USD_t": {
        "url": "https://www.metal.com/Rare-Earth-Metals/201102250470",
        "min_valid": 5000,
        "max_valid": 500000,
    },
}

PRICE_NEWS_QUERIES = {
    "네오디뮴_가격뉴스_건수": "neodymium price rare earth oxide USD kg",
    "갈륨_가격뉴스_건수": "gallium price semiconductor export control",
    "게르마늄_가격뉴스_건수": "germanium price semiconductor export control",
    "헬륨_가격뉴스_건수": "helium price shortage semiconductor",
}


def _smm_headers() -> dict:
    headers = dict(HEADERS)
    cookie = os.getenv("SMM_COOKIE", "").strip()
    if cookie:
        headers["Cookie"] = cookie
    token = os.getenv("SMM_BEARER_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_smm_public_prices(today: datetime) -> pd.DataFrame:
    rows = []
    headers = _smm_headers()
    for label, meta in SMM_PAGES.items():
        try:
            resp = SESSION.get(meta["url"], headers=headers, timeout=(_env_float("MACRO_MATERIAL_CONNECT_TIMEOUT", 3), _env_float("MACRO_MATERIAL_READ_TIMEOUT", 8)))
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            text = soup.get_text(" ", strip=True)
            lower = text.lower()
            if any(s in lower for s in ["sign in to view", "login", "no data yet"]):
                print(f"  ⚠️ SMM [{label}]: 로그인 필요/공개값 없음")
                continue
            candidates = []
            for el in soup.select('[class*="price"], [class*="Price"], [data-price]'):
                val = _safe_float(el.get_text(" ", strip=True) or el.get("data-price"))
                if val and meta.get("min_valid", 0) <= val <= meta.get("max_valid", 10**9):
                    candidates.append(val)
            if not candidates:
                # HTML text regex fallback
                for m in re.finditer(r"(?<!\d)(\d{4,6}(?:\.\d+)?)(?!\d)", text):
                    val = _safe_float(m.group(1))
                    if val and meta.get("min_valid", 0) <= val <= meta.get("max_valid", 10**9):
                        candidates.append(val)
            if candidates:
                price = float(candidates[0])
                rows.append({"date": pd.Timestamp(today.date()), label: price})
                print(f"  ✅ SMM [{label}]: {price}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠️ SMM [{label}] 실패: {type(exc).__name__}: {exc}")
        time.sleep(_env_float("MACRO_SMM_SLEEP_SEC", 0.05))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.groupby("date", as_index=False).first()


def _fetch_price_news_proxy(today: datetime) -> pd.DataFrame:
    if not _env_bool("MACRO_ENABLE_MATERIAL_PRICE_NEWS_PROXY", True):
        return pd.DataFrame()
    days = _env_int("MACRO_MATERIAL_PRICE_NEWS_DAYS", 30)
    row = {"date": pd.Timestamp(today.date())}
    total = 0
    for col, query in PRICE_NEWS_QUERIES.items():
        try:
            parsed = feedparser.parse(_google_news_rss(query, days=days))
            count = 0
            for entry in parsed.entries[:30]:
                title = _clean(entry.get("title", ""), 220)
                if not title:
                    continue
                count += 1
            row[col] = count
            total += count
        except Exception:
            row[col] = 0
        time.sleep(_env_float("MACRO_MATERIAL_NEWS_SLEEP_SEC", 0.05))
    if total <= 0:
        return pd.DataFrame()
    row["가격뉴스_총건수"] = total
    print(f"  ✅ 소재 가격뉴스 proxy: {total}건")
    return pd.DataFrame([row])


def fetch_all_smm(today: datetime | None = None) -> pd.DataFrame:
    """Try SMM only when it is useful, then always add price-news proxy.

    SMM often hides real-time prices behind login. The collector does not bypass
    login. To avoid a repeated bottleneck, it skips the SMM page by default when
    neither SMM_COOKIE nor SMM_BEARER_TOKEN is present, and uses Google News RSS
    based material-price pressure proxy instead.

    To force a public-page attempt without credentials, set
    MACRO_SMM_PUBLIC_TRY=1.
    """
    print("  [SMM/소재 가격 보강]")
    today = today or datetime.today()
    frames = []
    has_smm_auth = bool(os.getenv("SMM_COOKIE", "").strip() or os.getenv("SMM_BEARER_TOKEN", "").strip())
    should_try_smm = _env_bool("MACRO_ENABLE_SMM", True) and (has_smm_auth or _env_bool("MACRO_SMM_PUBLIC_TRY", False))
    if should_try_smm:
        df_smm = _fetch_smm_public_prices(today)
        if not df_smm.empty:
            frames.append(df_smm)
    else:
        print("  ℹ️ SMM 인증정보 없음 → SMM 직접 조회 생략, 가격뉴스 proxy 사용")
    df_proxy = _fetch_price_news_proxy(today)
    if not df_proxy.empty:
        frames.append(df_proxy)
    if not frames:
        print("  ⚠️ SMM/가격 proxy 모두 0건")
        return pd.DataFrame()
    out = frames[0]
    for df in frames[1:]:
        out = pd.merge(out, df, on="date", how="outer")
    return out.sort_values("date").reset_index(drop=True)


# ---------------------------------------------------------------------------
# USGS PDF parsing + robust static fallback
# ---------------------------------------------------------------------------

USGS_RARE_EARTH_PDFS = [
    "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-rare-earths.pdf",
    "https://pubs.usgs.gov/periodicals/mcs2025/mcs2025-rare-earths.pdf",
    "https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-rare-earths.pdf",
]

USGS_HELIUM_PDFS = [
    "https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-helium.pdf",
    "https://pubs.usgs.gov/periodicals/mcs2025/mcs2025-helium.pdf",
    "https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-helium.pdf",
]

# Conservative fallback rows. These are intentionally sparse; they keep the pipeline alive
# while the latest USGS PDF text is also saved under data/_global_common/macro/debug/.
USGS_RE_STATIC_ROWS = [
    {"date": "2025-01-01", "희토류_미국생산_REO_ton": 51000, "희토류_미국생산가치_백만달러": 240, "희토류_USGS_자료연도": 2026},
]

USGS_HELIUM_STATIC_ROWS = [
    {"date": "2025-01-01", "헬륨_미국생산_백만m3": 72, "헬륨_USGS_자료연도": 2026},
]


def _pdf_text(urls: Iterable[str], debug_prefix: str) -> tuple[str, str]:
    errors = []
    for url in urls:
        try:
            resp = _request_get(url, timeout=(_env_float("MACRO_MATERIAL_CONNECT_TIMEOUT", 3), _env_float("MACRO_MATERIAL_READ_TIMEOUT", 8)), retries=_env_int("MACRO_MATERIAL_RETRIES", 1))
            with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages[:3])
            if text.strip():
                _write_debug(f"{debug_prefix}_latest_text.txt", f"URL: {url}\n\n{text}")
                return text, url
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{url}: {type(exc).__name__}")
            continue
    raise RuntimeError("; ".join(errors))


def _extract_rare_earth_row_from_text(text: str, url: str) -> pd.DataFrame:
    # Typical MCS wording: "An estimated 51,000 tons ... was produced and was valued at $240 million."
    prod = None
    val = None
    m_prod = re.search(r"estimated\s+([\d,]+)\s+tons\s+of\s+REO", text, flags=re.I)
    if m_prod:
        prod = _safe_float(m_prod.group(1))
    m_val = re.search(r"valued\s+at\s+\$?([\d,.]+)\s+million", text, flags=re.I)
    if m_val:
        val = _safe_float(m_val.group(1))
    year = None
    m_year = re.search(r"in\s+(20\d{2})", text[:1200], flags=re.I)
    if m_year:
        year = int(m_year.group(1))
    if prod is None and val is None:
        return pd.DataFrame()
    row = {
        "date": pd.Timestamp(f"{year or datetime.today().year}-01-01"),
        "희토류_미국생산_REO_ton": prod,
        "희토류_미국생산가치_백만달러": val,
        "희토류_USGS_자료연도": (year + 1 if year else datetime.today().year),
        "source": "USGS_MCS_PDF_PARSED",
    }
    return pd.DataFrame([row])


def fetch_usgs_rare_earth(today: datetime | None = None) -> pd.DataFrame:
    print("  [USGS 희토류]")
    if not _env_bool("MACRO_ENABLE_USGS_RARE_EARTH", True):
        return pd.DataFrame()
    try:
        text, url = _pdf_text(USGS_RARE_EARTH_PDFS, "usgs_rare_earth")
        df = _extract_rare_earth_row_from_text(text, url)
        if not df.empty:
            print(f"  ✅ USGS 희토류 PDF 파싱 성공: {len(df)}행")
            return df
        print("  ⚠️ USGS 희토류 PDF 접근 성공, 수치 파싱 실패 → static fallback")
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠️ USGS 희토류 PDF 실패 → static fallback: {type(exc).__name__}: {exc}")
    df = pd.DataFrame(USGS_RE_STATIC_ROWS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["source"] = "USGS_MCS_STATIC_FALLBACK"
    return df


def _extract_helium_row_from_text(text: str, url: str) -> pd.DataFrame:
    # Helium MCS PDFs vary more than rare-earths. Keep parsing conservative.
    year = None
    m_year = re.search(r"in\s+(20\d{2})", text[:1200], flags=re.I)
    if m_year:
        year = int(m_year.group(1))
    # Try to find "United States" production table value; fallback remains available.
    production = None
    m_prod = re.search(r"United\s+States\s+([\d,.]+)\s+([\d,.]+)\s+([\d,.]+)", text, flags=re.I)
    if m_prod:
        production = _safe_float(m_prod.group(3))
    if production is None:
        return pd.DataFrame()
    row = {
        "date": pd.Timestamp(f"{year or datetime.today().year}-01-01"),
        "헬륨_미국생산_백만m3": production,
        "헬륨_USGS_자료연도": (year + 1 if year else datetime.today().year),
        "source": "USGS_MCS_PDF_PARSED",
    }
    return pd.DataFrame([row])


def fetch_usgs_helium(today: datetime | None = None) -> pd.DataFrame:
    print("  [USGS 헬륨]")
    if not _env_bool("MACRO_ENABLE_USGS_HELIUM", True):
        return pd.DataFrame()
    try:
        text, url = _pdf_text(USGS_HELIUM_PDFS, "usgs_helium")
        df = _extract_helium_row_from_text(text, url)
        if not df.empty:
            print(f"  ✅ USGS 헬륨 PDF 파싱 성공: {len(df)}행")
            return df
        print("  ⚠️ USGS 헬륨 PDF 접근 성공, 수치 파싱 실패 → static fallback")
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠️ USGS 헬륨 PDF 실패 → static fallback: {type(exc).__name__}: {exc}")
    df = pd.DataFrame(USGS_HELIUM_STATIC_ROWS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["source"] = "USGS_MCS_STATIC_FALLBACK"
    return df


# ---------------------------------------------------------------------------
# Helium BLM and news fallback
# ---------------------------------------------------------------------------

def fetch_blm_helium(today: datetime | None = None) -> pd.DataFrame:
    print("  [BLM 헬륨]")
    today = today or datetime.today()
    url = "https://www.blm.gov/programs/energy-and-minerals/helium"
    try:
        resp = _request_get(url, timeout=(_env_float("MACRO_MATERIAL_CONNECT_TIMEOUT", 3), _env_float("MACRO_MATERIAL_READ_TIMEOUT", 8)), retries=2)
        soup = BeautifulSoup(resp.text, "lxml")
        title = soup.title.get_text(strip=True) if soup.title else "BLM Helium"
        print("  ✅ BLM 페이지 접근 성공")
        return pd.DataFrame([{
            "date": pd.Timestamp(today.date()),
            "source": "BLM",
            "status": "page_alive",
            "title": _clean(title, 180),
            "url": url,
        }])
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠️ BLM 실패: {type(exc).__name__}: {exc}")
        return pd.DataFrame()


def fetch_helium_news(today: datetime | None = None) -> pd.DataFrame:
    print("  [헬륨 뉴스 fallback]")
    today = today or datetime.today()
    rows = []
    days = _env_int("MACRO_HELIUM_NEWS_DAYS", 90)
    queries = [
        "helium price shortage semiconductor supply",
        "helium supply chip fabrication",
        "helium market shortage electronics",
    ]
    for query in queries:
        try:
            parsed = feedparser.parse(_google_news_rss(query, days=days))
            for entry in parsed.entries[:15]:
                title = _clean(entry.get("title", ""), 180)
                if not title:
                    continue
                rows.append({
                    "date": _parse_date(entry.get("published") or entry.get("updated")) or pd.Timestamp(today.date()),
                    "title": title,
                    "url": entry.get("link", ""),
                    "domain": "GoogleNewsRSS",
                })
        except Exception:
            continue
        time.sleep(_env_float("MACRO_HELIUM_NEWS_SLEEP_SEC", 0.05))
    df = pd.DataFrame(rows)
    if df.empty:
        print("  ⚠️ 헬륨 뉴스 0건")
        return df
    df["_key"] = df["title"].str.lower().str.replace(r"\W+", " ", regex=True).str[:80]
    df = df.drop_duplicates("_key").drop(columns="_key")
    df = df.sort_values("date", ascending=False).head(_env_int("MACRO_HELIUM_NEWS_MAX_ROWS", 20)).reset_index(drop=True)
    print(f"  ✅ 헬륨 뉴스 fallback: {len(df)}건")
    return df


# ---------------------------------------------------------------------------
# direct test entrypoint
# ---------------------------------------------------------------------------

def run_material_probe() -> dict:
    today = datetime.today()
    result = {
        "rare_fred_rows": len(fetch_rare_earth_fred(today)),
        "smm_or_proxy_rows": len(fetch_all_smm(today)),
        "usgs_rare_rows": len(fetch_usgs_rare_earth(today)),
        "usgs_helium_rows": len(fetch_usgs_helium(today)),
        "blm_helium_rows": len(fetch_blm_helium(today)),
        "helium_news_rows": len(fetch_helium_news(today)),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result
