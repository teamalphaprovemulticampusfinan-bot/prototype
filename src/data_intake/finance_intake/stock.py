# =========================
# 1. 라이브러리 설치
# =========================

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
from io import StringIO
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import os
from dotenv import load_dotenv
load_dotenv()
import re
import requests

start = (datetime.now() - relativedelta(years=3, months=3)).strftime("%Y-%m-%d")

# =========================
# 2. 종목 설정
# =========================
def auto_ticker(stock_code):
    import yfinance as yf

    ks = yf.Ticker(f"{stock_code}.KS")
    data_ks = ks.history(period="5d")

    if not data_ks.empty:
        return f"{stock_code}.KS"

    kq = yf.Ticker(f"{stock_code}.KQ")
    data_kq = kq.history(period="5d")

    if not data_kq.empty:
        return f"{stock_code}.KQ"

    raise ValueError("KS/KQ 둘 다 없음")
ticker = auto_ticker("033640")
start = (datetime.now() - relativedelta(years=3, months=3)).strftime("%Y-%m-%d")
price_col = "Close"
pure_code = ticker.split(".")[0]   # ".ks"삭제

# =========================
# 3. 시장지수 자동 선택
# =========================
def get_market_ticker(stock_ticker):
    stock_ticker = stock_ticker.upper()
    if stock_ticker.endswith(".KS"):
        return "^KS11"
    elif stock_ticker.endswith(".KQ"):
        return "^KQ11"
    else:
        raise ValueError("ticker 끝에 .KS 또는 .KQ가 있어야 합니다.")

market_ticker = get_market_ticker(ticker)
print("선택된 시장지수:", market_ticker)

# =========================
# 4. 주가 데이터 다운로드
# =========================

df = yf.download(ticker, start=start, auto_adjust=True)

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df.index = pd.to_datetime(df.index)
df = df.sort_index()

# =========================
# 5. 수익률
# =========================
df["Return"] = df[price_col].pct_change()

# =========================
# 6. 시장수익률 + 이상수익률
# =========================
mkt = yf.download(market_ticker, start=start, auto_adjust=True)

if isinstance(mkt.columns, pd.MultiIndex):
    mkt.columns = mkt.columns.get_level_values(0)

mkt.index = pd.to_datetime(mkt.index)
mkt = mkt.sort_index()
mkt = mkt[[price_col]].rename(columns={price_col: "Market_Close"})
mkt["market_return"] = mkt["Market_Close"].pct_change()

df = df.join(mkt[["Market_Close", "market_return"]], how="left")
df["market_return"] = df["market_return"].ffill()
df["ABNRET"] = df["Return"] - df["market_return"]

# =========================
# 7. MDD
# =========================
cum = (1 + df["Return"]).cumprod()
peak = cum.cummax()
df["MDD"] = (cum - peak) / peak
max_mdd = df["MDD"].min()

# =========================
# 8. 이동평균 비율
# =========================
df["MA20"] = df[price_col].rolling(20).mean()
df["MA60"] = df[price_col].rolling(60).mean()
df["MA20_ratio"] = df[price_col] / df["MA20"]
df["MA60_ratio"] = df[price_col] / df["MA60"]

# =========================
# 9. VIX / VKOSPI
# =========================
vix = yf.download("^VIX", start=start, auto_adjust=True)
vkospi = yf.download("^KQ11", start=start, auto_adjust=True)

if isinstance(vix.columns, pd.MultiIndex):
    vix.columns = vix.columns.get_level_values(0)
if isinstance(vkospi.columns, pd.MultiIndex):
    vkospi.columns = vkospi.columns.get_level_values(0)

vix.index = pd.to_datetime(vix.index)
vkospi.index = pd.to_datetime(vkospi.index)

vix = vix[[price_col]].rename(columns={price_col: "VIX"})
vkospi = vkospi[[price_col]].rename(columns={price_col: "VKOSPI"})

df = df.join(vix, how="left")
df = df.join(vkospi, how="left")
df[["VIX", "VKOSPI"]] = df[["VIX", "VKOSPI"]].ffill()

# =========================
# 10. EPS / PSR (DART 분기 시계열)
# =========================
stock = yf.Ticker(ticker)
info = stock.info

DART_API_KEY = os.getenv("DART_API_KEY")  # https://opendart.fss.or.kr 에서 발급

# ── corp_code 조회 ────────────────────────────
df_corp = pd.read_csv(
    r"C:\Users\smile\team-a\src\data_intake\finance_intake\corp_codes.csv",
    encoding="utf-8-sig",
    dtype={"stock_code": str, "corp_code": str}
)
df_corp["stock_code"] = df_corp["stock_code"].str.strip().str.zfill(6)

matched = df_corp[df_corp["stock_code"] == pure_code]
if matched.empty:
    print("corp_code 없음 - EPS/PSR 스킵")
    corp_code = None
    corp_name = pure_code
else:
    corp_code = matched.iloc[0]["corp_code"]
    corp_name = matched.iloc[0]["corp_name"]  # 👉 추가
    print("corp_code:", corp_code)
    print("회사명:", corp_name)

# ── DART 분기 재무 데이터 ─────────────────────
def get_shares_from_dart(corp_code, api_key):
    """DART에서 발행주식수 가져오기"""
    try:
        r = requests.get(
            "https://opendart.fss.or.kr/api/stockTotqySttus.json",
            params={
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bsns_year": year ,
                "reprt_code": "11011"  # 사업보고서
            },
            timeout=10
        )
        data = r.json()

        if data.get("status") != "000":
            return np.nan

        for item in data["list"]:
            val = item.get("istc_totqy", "").replace(",", "")
            if val:
                return float(val)

        return np.nan

    except:
        return np.nan
def get_dart_quarterly(corp_code, api_key, start_year=2022):
    """분기별 순이익 + 매출 가져오기"""
    records = []
    reprt_map = {
        "11013": "1Q",
        "11012": "2Q", 
        "11014": "3Q",
        "11011": "4Q"
    }

    for year in range(start_year, datetime.now().year + 1):
        for reprt_code, qname in reprt_map.items():
            try:
                r = requests.get(
                    "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json",
                    params={
                        "crtfc_key": api_key,
                        "corp_code": corp_code,
                        "bsns_year": year ,
                        "reprt_code": reprt_code,
                        "fs_div": "CFS"  # 연결재무제표 (없으면 OFS로 fallback)
                    },
                    timeout=10
                )
                data = r.json()

                if data.get("status") != "000":
                    # 연결 없으면 개별재무제표로 재시도
                    r2 = requests.get(
                        "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json",
                        params={
                            "crtfc_key": api_key,
                            "corp_code": corp_code,
                            "bsns_year": year,
                            "reprt_code": reprt_code,
                            "fs_div": "OFS"
                        },
                        timeout=10
                    )
                    data = r2.json()

                if data.get("status") != "000":
                    continue

                net_income = np.nan
                revenue = np.nan

                for item in data["list"]:
                    acnt = item.get("account_nm", "")
                    val = item.get("thstrm_amount", "").replace(",", "")
                    try:
                        val = float(val)
                    except:
                        continue

                    if any(key in acnt for key in ["당기순이익", "분기순이익", "반기순이익"]):
                        net_income = val

                    elif any(key in acnt for key in ["매출액", "수익"]):
                        revenue = val

                records.append({
                    "year": year,
                    "quarter": qname,
                    "reprt_code": reprt_code,
                    "net_income": net_income,
                    "revenue": revenue
                })
                time.sleep(0.3)

            except Exception as e:
                print(f"  DART {year} {qname} 오류: {e}")
                continue

    return pd.DataFrame(records)

# ── 날짜 매핑 (분기 종료일 기준) ──────────────
quarter_end_map = {
    "1Q": "-03-31",
    "2Q": "-06-30",
    "3Q": "-09-30",
    "4Q": "-12-31"
}

eps_series = pd.Series(dtype=float)
psr_series = pd.Series(dtype=float)
shares = np.nan

if corp_code:
        # 1️⃣ DART 시도
    shares = get_shares_from_dart(corp_code, DART_API_KEY)

    # 2️⃣ yfinance fallback
    if pd.isna(shares):
        shares = info.get("sharesOutstanding")
        print("yfinance fallback 사용")

    # 3️⃣ marketCap으로 역산
    if pd.isna(shares):
        market_cap = info.get("marketCap")
        if market_cap and not df.empty:
            shares = market_cap / df["종가"].iloc[-1]
            print("marketCap으로 shares 추정")

    # 👉 🔥 여기 추가 (핵심 위치)
    # 4️⃣ 수동 파일 fallback
    if pd.isna(shares):
        shares_path = r"C:\Users\smile\team-a\src\data_intake\finance_intake\shares.csv"

        if os.path.exists(shares_path):
            df_shares = pd.read_csv(shares_path, dtype={"stock_code": str})
            df_shares["stock_code"] = df_shares["stock_code"].str.zfill(6)

            matched_shares = df_shares[df_shares["stock_code"] == pure_code]

            if not matched_shares.empty:
                shares = float(matched_shares.iloc[0]["shares"])
                print("수동 shares.csv fallback 사용")

    # 최종 체크
    if pd.isna(shares):
        print("발행주식수 완전히 없음 → EPS/PSR 계산 불가")
        shares = np.nan

    df_dart = get_dart_quarterly(corp_code, DART_API_KEY, start_year=2021)

    if not df_dart.empty:
        # 분기 종료일을 날짜 인덱스로 변환
        df_dart["date"] = pd.to_datetime(
            df_dart["year"].astype(str) + df_dart["quarter"].map(quarter_end_map)
        )
        df_dart = df_dart.set_index("date").sort_index()

        # TTM = 최근 4분기 합산
        df_dart["ttm_net_income"] = df_dart["net_income"].rolling(4).sum()
        df_dart["ttm_revenue"] = df_dart["revenue"].rolling(4).sum()

        if not pd.isna(shares):
            # EPS = TTM 순이익 / 발행주식수
            df_dart["EPS"] = df_dart["ttm_net_income"] / shares

            # PSR = 시가총액 / TTM 매출
            mktcap_q = df[price_col].reindex(df_dart.index, method="nearest") * shares
            df_dart["PSR"] = mktcap_q / df_dart["ttm_revenue"]

            eps_series = df_dart["EPS"]
            psr_series = df_dart["PSR"]
        else:
            df_dart["EPS"] = np.nan
            df_dart["PSR"] = np.nan

# ── df에 병합 후 ffill ────────────────────────
if not eps_series.empty:
    df = df.join(eps_series.rename("EPS"), how="left")
    df["EPS"] = df["EPS"].ffill()
else:
    df["EPS"] = np.nan

if not psr_series.empty:
    df = df.join(psr_series.rename("PSR"), how="left")
    df["PSR"] = df["PSR"].ffill()
else:
    df["PSR"] = np.nan
# =========================
# 11. CAR
# =========================
df["CAR_3"] = df["ABNRET"].rolling(3).sum()
df["CAR_5"] = df["ABNRET"].rolling(5).sum()

# =========================
# 12. 수급 데이터 (네이버 금융)
# =========================
def get_naver_investor_trend(pure_code, start_date, total_pages=80):
    all_dfs = []
    start_dt = pd.to_datetime(start_date)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://finance.naver.com/"
    }

    print("수급 데이터 수집 중...")

    for page in range(1, total_pages + 1):
        try:
            r = requests.get(
                "https://finance.naver.com/item/frgn.nhn",
                params={"code": pure_code, "page": page},
                headers=headers,
                timeout=10
            )
            r.encoding = "euc-kr"
            dfs = pd.read_html(StringIO(r.text))

            df_page = None

            for table in dfs:
                table = table.dropna(how="all")

                # 첫 컬럼에 날짜 형태가 있는 테이블만 선택
                first_col = table.iloc[:, 0].astype(str)
                has_date = first_col.str.contains(r"\d{4}\.\d{2}\.\d{2}", regex=True).any()

                if has_date and table.shape[1] >= 9:
                    df_page = table.iloc[:, :9].copy()
                    break

            if df_page is None:
                continue

            df_page.columns = [
                "날짜", "종가", "전일비", "등락률", "거래량",
                "기관_순매매", "외국인_순매매", "보유주수", "보유율"
            ]

            df_page = df_page.dropna(subset=["날짜"])
            df_page["날짜"] = pd.to_datetime(df_page["날짜"], format="%Y.%m.%d", errors="coerce")
            df_page = df_page.dropna(subset=["날짜"])

            if df_page["날짜"].max() < start_dt:
                print(f"  → start_date 도달 (page {page}), 수집 완료")
                break

            df_page = df_page[df_page["날짜"] >= start_dt]
            all_dfs.append(df_page)

            if page % 30 == 0:
                print(f"  page {page} / 현재 최소날짜: {df_page['날짜'].min().date()}")

            time.sleep(0.3)

        except Exception as e:
            print(f"  page {page} 오류: {e}")
            time.sleep(1)
            continue

    if not all_dfs:
        print("수급 데이터 수집 실패")
        return pd.DataFrame()

    result = pd.concat(all_dfs, ignore_index=True)

    for col in ["종가", "거래량", "기관_순매매", "외국인_순매매", "보유주수"]:
        result[col] = pd.to_numeric(
            result[col].astype(str).str.replace(",", ""),
            errors="coerce"
        )

    result["보유율_%"] = pd.to_numeric(
        result["보유율"].astype(str).str.replace("%", ""),
        errors="coerce"
    )

    result = result.drop(columns=["보유율", "종가", "전일비", "등락률", "거래량"])
    result = (
        result.sort_values("날짜")
        .drop_duplicates(subset=["날짜"])
        .set_index("날짜")
    )

    return result

df_supply = get_naver_investor_trend(pure_code, start)

# =========================
# 13. 수급 데이터 병합
# =========================
supply_cols = ["기관_순매매", "외국인_순매매", "보유주수", "보유율_%"]

if not df_supply.empty:
    df_supply.index = pd.to_datetime(df_supply.index)

    # 👉 컬럼 공백 제거 (중요)
    df_supply.columns = df_supply.columns.str.strip()

    # 👉 기존 겹치는 컬럼 제거
    df = df.drop(columns=supply_cols, errors="ignore")

    # 👉 병합
    df = df.join(df_supply, how="left")

    # 👉 결측값 채우기
    df[supply_cols] = df[supply_cols].ffill()

    print("수급 데이터 병합 완료")
else:
    # 👉 수급 없을 때 컬럼 생성
    for col in supply_cols:
        df[col] = np.nan

    print("수급 데이터 없음 - 병합 생략")

# =========================
# 14. 컬럼명 한글 통일
# =========================
rename_dict = {
    "Open": "시가",
    "High": "고가",
    "Low": "저가",
    "Close": "종가",
    "Volume": "거래량",
    "Return": "수익률",
    "Market_Close": "시장종가",
    "market_return": "시장수익률",
    "ABNRET": "이상수익률",
    "MDD": "최대낙폭",
    "MA20": "20일이동평균",
    "MA60": "60일이동평균",
    "MA20_ratio": "20일이평비율",
    "MA60_ratio": "60일이평비율",
    "VIX": "VIX",
    "VKOSPI": "VKOSPI",
    "EPS": "EPS",
    "PSR": "PSR",
    "CAR_3": "누적이상수익률_3일",
    "CAR_5": "누적이상수익률_5일"
}

df = df.rename(columns=rename_dict)
if not pd.isna(shares):
    df["시가총액"] = df["종가"] * shares
else:
    df["시가총액"] = np.nan

# =========================
# 15. 결과 출력
# =========================
print("\n시장지수:", market_ticker)
print("EPS:", eps_series.tail(1))
print("PSR:", psr_series.tail(1))
print("최대 MDD:", max_mdd)

display_cols = [
    "시가", "고가", "저가", "종가", "거래량","시가총액",
    "수익률", "시장수익률", "이상수익률",
    "최대낙폭", "20일이동평균", "60일이동평균",
    "20일이평비율", "60일이평비율",
    "VIX", "VKOSPI", "EPS", "PSR",
    "누적이상수익률_3일", "누적이상수익률_5일",
    "기관_순매매", "외국인_순매매", "보유주수", "보유율_%"
]

print(df[display_cols].tail())

start_dt = datetime.strptime(start, "%Y-%m-%d")
start_plus_60 = start_dt + timedelta(days=90)

df = df[df.index >= start_plus_60]

project_root = r"c:\Users\smile\team-a"

stock = yf.Ticker(ticker)

name = corp_name

# 파일명 깨짐 방지 (특수문자 제거)
name = re.sub(r'[\\/:*?"<>|]', '', name)

output_path = os.path.join(
    project_root,
    "data",
    "finance_data",
    "stock_data",
    f"{name}_stock.csv"
)

os.makedirs(os.path.dirname(output_path), exist_ok=True)

# 2️⃣ 그 다음 기존 파일 체크
if os.path.exists(output_path):
    old_df = pd.read_csv(output_path, index_col="날짜", parse_dates=True)
    last_date = old_df.index.max()
    start = (last_date - timedelta(days=90)).strftime("%Y-%m-%d")
else:
    old_df = None
    start = (datetime.now() - relativedelta(years=3)).strftime("%Y-%m-%d")
    print("초기 3년 다운로드")

df_save = df[display_cols].copy()

if old_df is not None:
    df_save = pd.concat([old_df, df_save])

df_save = df_save[~df_save.index.duplicated(keep="last")]
df_save = df_save.sort_index()

cutoff_date = datetime.now() - relativedelta(years=3)
df_save = df_save[df_save.index >= cutoff_date]

df_save.to_csv(
    output_path,
    index=True,
    index_label="날짜",
    encoding="utf-8-sig"
)

print("저장 완료:", os.path.abspath(output_path))