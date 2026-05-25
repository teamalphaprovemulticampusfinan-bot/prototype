# ============================================================
# FRED + yfinance + OECD + GDELT 보조 지표 수집기 (Windows VSCode용)
# - .env 사용
# - CSV 저장 제거
# - OECD 전체 대신 G20 CLI 사용
# - GDELT retry / timeout / rate limit 대응
# ============================================================

import os
import time
import random
from io import StringIO
from datetime import datetime, timedelta
from fredapi import Fred
import requests
import pandas as pd
import yfinance as yf
from pathlib import Path
import matplotlib
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ── 0. Windows 한글 폰트 설정 ──────────────────────────────
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False
print("✅ 패키지 및 폰트 설정 완료")

# ── 1. .env 로드 ───────────────────────────────────────────
# ── 1. .env 로드 ───────────────────────────────────────────
load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
fred = Fred(api_key=FRED_API_KEY) if FRED_API_KEY else Fred()

# ── 2. 공통 세션: timeout / 일시적 오류 / 429 재시도 ───────
session = requests.Session()
retry = Retry(
    total=4,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True,
)
session.mount("https://", HTTPAdapter(max_retries=retry))
session.mount("http://", HTTPAdapter(max_retries=retry))

TODAY = datetime.today()
START_3Y = (TODAY - timedelta(days=365 * 3)).strftime("%Y-%m-%d")
START_5Y = (TODAY - timedelta(days=365 * 5)).strftime("%Y-%m-%d")
END = TODAY.strftime("%Y-%m-%d")


# ── 공통 헬퍼 ─────────────────────────────────────────────
def to_daily_df(series, label):
    df = series.dropna().reset_index()
    df.columns = ["date", label]
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df[label] = pd.to_numeric(df[label], errors="coerce")
    df = df.groupby("date", as_index=False)[label].mean()
    df = df.sort_values("date").reset_index(drop=True)
    print(f"  ✅ [{label}] {len(df)}행 ({df['date'].min().date()} ~ {df['date'].max().date()})")
    return df


def to_monthly_df(series, label):
    df = series.dropna().reset_index()
    df.columns = ["date", label]
    df["date"] = pd.to_datetime(
        df["date"]
    ).dt.tz_localize(None, ambiguous="NaT", nonexistent="NaT")
    df[label] = pd.to_numeric(df[label], errors="coerce")
    df = df.dropna(subset=["date"])
    df = df.groupby("date", as_index=False)[label].mean()
    df = df.sort_values("date").reset_index(drop=True)
    print(f"  ✅ [{label}] {len(df)}행 ({df['date'].min().date()} ~ {df['date'].max().date()})")
    return df


def merge_dfs(dfs):
    result = None
    for df in dfs:
        if df is None or df.empty:
            continue
        result = df if result is None else pd.merge(result, df, on="date", how="outer")
    return result.sort_values("date").reset_index(drop=True) if result is not None else None


# ── yfinance ───────────────────────────────────────────────
def fetch_yf(ticker, label, start=START_3Y):
    try:
        raw = yf.download(
            ticker,
            start=start,
            end=END,
            auto_adjust=True,
            progress=False,
            threads=False,
        )["Close"]

        if isinstance(raw, pd.DataFrame):
            raw = raw.squeeze()

        return to_daily_df(raw, label)

    except Exception as e:
        print(f"  ❌ [{label}] yfinance 오류: {e}")
        return pd.DataFrame()


# ── FRED ───────────────────────────────────────────────────
# ── FRED ───────────────────────────────────────────────────
def fetch_fred(series_id, label, start=START_5Y):
    try:
        raw = fred.get_series(
            series_id,
            observation_start=start,
            observation_end=END,
        ).dropna()

        return to_monthly_df(raw, label)

    except Exception as e:
        print(f"  ❌ [{label}] FRED 오류: {e}")
        return pd.DataFrame()


# ── OECD CLI (G20 사용) ────────────────────────────────────
def fetch_oecd_cli(country_code, label):
    start_m = START_5Y[:7]
    end_m = END[:7]

    query = f"{country_code}.M.LI...AA...H"
    url = (
        "https://sdmx.oecd.org/public/rest/data/"
        f"OECD.SDD.STES,DSD_STES@DF_CLI/{query}"
        f"?startPeriod={start_m}"
        f"&endPeriod={end_m}"
        f"&dimensionAtObservation=AllDimensions"
        f"&format=csvfilewithlabels"
    )

    try:
        r = session.get(url, timeout=40)
        r.raise_for_status()

        df = pd.read_csv(StringIO(r.text))

        date_col = "TIME_PERIOD" if "TIME_PERIOD" in df.columns else "TIME_PERIOD:Time period"
        value_col = "OBS_VALUE" if "OBS_VALUE" in df.columns else "OBS_VALUE:Observation value"

        df = df[[date_col, value_col]].copy()
        df.columns = ["date", label]
        df["date"] = pd.to_datetime(df["date"] + "-01", errors="coerce")
        df[label] = pd.to_numeric(df[label], errors="coerce")
        df = df.dropna().sort_values("date").reset_index(drop=True)

        print(f"  ✅ [{label}] {len(df)}행 ({df['date'].min().date()} ~ {df['date'].max().date()})")
        return df

    except Exception as e:
        print(f"  ❌ [{label}] OECD 오류: {e}")
        return pd.DataFrame()


# ── GDELT 뉴스 ─────────────────────────────────────────────
def is_english(text):
    if not text:
        return False
    ascii_count = sum(1 for c in text if ord(c) < 128)
    return (ascii_count / len(text)) > 0.7


def fetch_gdelt_news(keyword, label, max_results=3):
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
            r = session.get(url, params=params, timeout=30)

            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 20))
                time.sleep(wait + random.uniform(1, 3))
                continue

            r.raise_for_status()
            arts = r.json().get("articles", [])

            rows = []
            for a in arts:
                title = a.get("title", "")
                if not is_english(title):
                    continue
                rows.append(
                    {
                        "date": a.get("seendate", "")[:8],
                        "title": title,
                        "url": a.get("url", ""),
                        "source": a.get("domain", ""),
                    }
                )

            df = pd.DataFrame(rows)
            if not df.empty:
                df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")
                df = df.sort_values("date", ascending=False).reset_index(drop=True)

            print(f"  ✅ [{label}] {len(df)}건 (영어 필터 적용)")
            return df

        except requests.exceptions.Timeout:
            if attempt < 3:
                time.sleep((attempt + 1) * 10)
                continue
            print(f"  ❌ [{label}] GDELT 오류: timeout")
            return pd.DataFrame()

        except Exception as e:
            print(f"  ❌ [{label}] GDELT 오류: {e}")
            return pd.DataFrame()

    print(f"  ❌ [{label}] GDELT 오류: rate limit 초과")
    return pd.DataFrame()


# ════════════════════════════════════════════════════════════
# ① 미국 금리 + 달러인덱스 (yfinance)
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("  ① 미국 금리 + 달러인덱스 (yfinance)")
print("=" * 55)

df_us10y = fetch_yf("^TNX", "미국_국채_10년")
df_us13w = fetch_yf("^IRX", "미국_국채_13주")
df_dxy = fetch_yf("DX-Y.NYB", "달러인덱스_DXY")
time.sleep(1)


# ════════════════════════════════════════════════════════════
# ② FRED 데이터 (fredapi)
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("  ② FRED 데이터 (fredapi)")
print("=" * 55)

FRED_SERIES = {
    "미국_기준금리_FFR": "FEDFUNDS",
    "미국_SOFR": "SOFR",
    "미국_하이일드_스프레드": "BAMLH0A0HYM2",
    "미국_IG_스프레드": "BAMLC0A0CM",
    "미국_콜금리_EFFR": "EFFR",
    "미국_단기금리_3M": "DTB3",
    "미국_회사채_AAA": "BAMLC0A1CAAAEY",
    "미국_회사채_BBB": "BAMLC0A4CBBBEY",
    "미국_실업률": "UNRATE",
    "미국_고용률": "EMRATIO",
    "미국_기업심리_BSI대용": "BSCICP03USM665S",
}

fred_dfs = {}
for label, sid in FRED_SERIES.items():
    fred_dfs[label] = fetch_fred(sid, label)

time.sleep(1)


# ════════════════════════════════════════════════════════════
# ③ 원자재 가격 (yfinance)
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("  ③ 원자재 가격 (yfinance)")
print("=" * 55)

df_wti = fetch_yf("CL=F", "유가_WTI")
df_brent = fetch_yf("BZ=F", "유가_Brent")
df_gas = fetch_yf("NG=F", "천연가스")
df_cu = fetch_yf("HG=F", "구리")
time.sleep(1)


# ════════════════════════════════════════════════════════════
# ④ OECD 경기선행지수 CLI (G20 기준)
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("  ④ OECD 경기선행지수 CLI (G20 기준)")
print("=" * 55)

df_cli_kor = fetch_oecd_cli("KOR", "OECD_CLI_한국")
df_cli_usa = fetch_oecd_cli("USA", "OECD_CLI_미국")
df_cli_g20 = fetch_oecd_cli("G20", "G20_CLI")
time.sleep(1)


# ════════════════════════════════════════════════════════════
# ⑤ 외신 뉴스 (GDELT — 영어 전용)
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("  ⑤ 외신 뉴스 (GDELT — 영어 전용)")
print("=" * 55)

news_keywords = {
    "반도체_수출규제": "semiconductor export controls",
    "반도체_공급망": "semiconductor supply chain",
    "미중_무역": "\"US China\" tariff technology",
    "Fed_금리": "\"Federal Reserve\" FOMC rate",
    "지정학_리스크": "geopolitical risk Taiwan Korea Japan",
}

news_dfs = {}
for label, kw in news_keywords.items():
    news_dfs[label] = fetch_gdelt_news(kw, label, max_results=3)
    time.sleep(8)


# ════════════════════════════════════════════════════════════
# ⑥ 병합 (CSV 저장 없음)
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("  ⑥ 병합")
print("=" * 55)

# 일별 외부지표
daily_list = [
    df_us10y,
    df_us13w,
    df_dxy,
    fred_dfs.get("미국_SOFR"),
    fred_dfs.get("미국_하이일드_스프레드"),
    fred_dfs.get("미국_IG_스프레드"),
    df_wti,
    df_brent,
    df_gas,
    df_cu,
]
df_daily_ext = merge_dfs([d for d in daily_list if d is not None and not d.empty])

# 월별 외부지표
monthly_list = [
    fred_dfs.get("미국_기준금리_FFR"),
    fred_dfs.get("미국_콜금리_EFFR"),
    fred_dfs.get("미국_단기금리_3M"),
    fred_dfs.get("미국_회사채_AAA"),
    fred_dfs.get("미국_회사채_BBB"),
    fred_dfs.get("미국_실업률"),
    fred_dfs.get("미국_고용률"),
    fred_dfs.get("미국_기업심리_BSI대용"),
    df_cli_kor,
    df_cli_usa,
    df_cli_g20,
]
df_monthly_ext = merge_dfs([d for d in monthly_list if d is not None and not d.empty])

# 뉴스 통합
all_news = []
for label, df in news_dfs.items():
    if df is not None and not df.empty:
        temp = df.copy()
        temp.insert(0, "category", label)
        all_news.append(temp)

df_news_all = pd.concat(all_news, ignore_index=True) if all_news else pd.DataFrame()

if df_daily_ext is not None:
    print(f"  ✅ df_daily_ext 생성 완료 ({df_daily_ext.shape[0]}행 × {df_daily_ext.shape[1]}열)")
else:
    print("  ⚠️ df_daily_ext 없음")

if df_monthly_ext is not None:
    print(f"  ✅ df_monthly_ext 생성 완료 ({df_monthly_ext.shape[0]}행 × {df_monthly_ext.shape[1]}열)")
else:
    print("  ⚠️ df_monthly_ext 없음")

if not df_news_all.empty:
    print(f"  ✅ df_news_all 생성 완료 ({len(df_news_all)}건)")
else:
    print("  ⚠️ df_news_all 없음")

# ════════════════════════════════════════════════════════════
# ⑥-1 CSV 저장 (일별 / 월별)
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("  ⑥-1 CSV 저장")
print("=" * 55)

today_str = datetime.today().strftime("%Y%m%d")

# 저장 경로 (원하면 수정)
BASE_DIR = Path(__file__).resolve().parents[3]
SAVE_DIR = BASE_DIR / "data"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# 일별 CSV
if df_daily_ext is not None and not df_daily_ext.empty:
    daily_path = os.path.join(SAVE_DIR, f"ext_일별_{today_str}.csv")
    df_daily_ext.to_csv(daily_path, index=False, encoding="utf-8-sig")
    print(f"  ✅ 일별 CSV 저장 완료: {daily_path}")
else:
    print("  ⚠️ 일별 데이터 없음 → 저장 생략")

# 월별 CSV
if df_monthly_ext is not None and not df_monthly_ext.empty:
    monthly_path = os.path.join(SAVE_DIR, f"ext_월별_{today_str}.csv")
    df_monthly_ext.to_csv(monthly_path, index=False, encoding="utf-8-sig")
    print(f"  ✅ 월별 CSV 저장 완료: {monthly_path}")
else:
    print("  ⚠️ 월별 데이터 없음 → 저장 생략")
# ════════════════════════════════════════════════════════════
# ⑦ 미리보기
# ════════════════════════════════════════════════════════════
print("\n▶ 일별 외부지표 (최근 5행):")
if df_daily_ext is not None:
    print(df_daily_ext.tail().to_string(index=False))
else:
    print("없음")

print("\n▶ 월별 외부지표 (최근 5행):")
if df_monthly_ext is not None:
    print(df_monthly_ext.tail().to_string(index=False))
else:
    print("없음")

print("\n▶ 최신 뉴스 (영어만):")
for label, df in news_dfs.items():
    if df is not None and not df.empty:
        print(f"\n  [{label}]")
        for _, row in df.head(3).iterrows():
            print(f"    {str(row['date'])[:10]}  {row['title'][:80]}")


# ════════════════════════════════════════════════════════════
# ⑧ 선택: 시각화
#    필요하면 아래 주석 해제해서 사용
# ════════════════════════════════════════════════════════════
# ONE_YEAR_AGO = pd.Timestamp(TODAY - timedelta(days=365))
# COLORS = [
#     "#2563EB", "#DC2626", "#16A34A",
#     "#D97706", "#7C3AED", "#0891B2",
#     "#DB2777", "#65A30D", "#EA580C"
# ]
#
# def safe_plot(ax, src, col, title, color):
#     ax.set_title(title, fontsize=10)
#     ax.grid(True, alpha=0.3)
#
#     if src is None or src.empty or col not in src.columns:
#         ax.text(0.5, 0.5, "데이터 없음", ha="center", va="center",
#                 transform=ax.transAxes, color="gray")
#         return
#
#     tmp = src[src["date"] >= ONE_YEAR_AGO][["date", col]].dropna()
#     if tmp.empty:
#         ax.text(0.5, 0.5, "최근 1년 없음", ha="center", va="center",
#                 transform=ax.transAxes, color="gray")
#         return
#
#     ax.plot(tmp["date"], tmp[col], linewidth=1.5, color=color)
#     ax.fill_between(tmp["date"], tmp[col], alpha=0.07, color=color)
#     ax.tick_params(axis="x", rotation=30, labelsize=7)
#
# fig, axes = plt.subplots(4, 3, figsize=(18, 18))
# fig.suptitle("글로벌 거시경제 보조 지표", fontsize=14, fontweight="bold", y=1.01)
#
# plots = [
#     (df_daily_ext, "미국_국채_10년", "미국 10년물 국채금리 (%)"),
#     (df_daily_ext, "달러인덱스_DXY", "달러 인덱스 (DXY)"),
#     (df_daily_ext, "미국_하이일드_스프레드", "미국 하이일드 스프레드 (%)"),
#     (df_daily_ext, "미국_IG_스프레드", "미국 IG 스프레드 (%)"),
#     (df_daily_ext, "유가_WTI", "WTI 유가 ($/bbl)"),
#     (df_daily_ext, "천연가스", "천연가스 ($/MMBtu)"),
#     (df_monthly_ext, "미국_실업률", "미국 실업률 (%)"),
#     (df_monthly_ext, "미국_고용률", "미국 고용률 (%)"),
#     (df_monthly_ext, "미국_기업심리_BSI대용", "미국 기업심리 (BSI 대용)"),
#     (df_monthly_ext, "미국_기준금리_FFR", "미국 기준금리 FFR (%)"),
#     (df_monthly_ext, "미국_회사채_BBB", "미국 회사채 BBB 수익률 (%)"),
#     (df_monthly_ext, "G20_CLI", "G20 경기선행지수"),
# ]
#
# for i, (src, col, title) in enumerate(plots):
#     safe_plot(axes[i // 3][i % 3], src, col, title, COLORS[i % len(COLORS)])
#
# plt.tight_layout()
# plt.show()