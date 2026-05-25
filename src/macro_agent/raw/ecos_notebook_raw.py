# ============================================================
# 한국은행 ECOS API - 거시경제 지표 수집기 (VSCode Windows용)
# ============================================================

import os
from dotenv import load_dotenv
import requests
import pandas as pd
import time
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from pathlib import Path

plt.rcParams['font.family'] = 'Malgun Gothic'  # 윈도우 기본 한글 폰트
plt.rcParams['axes.unicode_minus'] = False

# ── 1. API KEY 로드 (.env 사용) ─────────────────────────────
load_dotenv()
API_KEY = os.getenv("ECOS_API_KEY")
BASE_URL = "https://ecos.bok.or.kr/api"

if not API_KEY:
    raise ValueError("❌ ECOS_API_KEY가 .env에 없습니다")

print("✅ API KEY 로드 완료")

# ── 2. 항목코드 조회 함수 ──────────────────────────────────
def show_item_codes(stat_code):
    url = f"{BASE_URL}/StatisticItemList/{API_KEY}/json/kr/1/200/{stat_code}"
    r = requests.get(url, timeout=15).json()
    rows = r.get("StatisticItemList", {}).get("row", [])

    if not rows:
        print(f"⚠️ [{stat_code}] 항목 없음 또는 코드 오류")
        return pd.DataFrame()

    df = pd.DataFrame(rows)[["ITEM_CODE", "ITEM_NAME"]]
    print(f"\n▶ {stat_code} 항목 목록")
    print(df.to_string(index=False))
    return df

# ── 3. 데이터 수집 함수 ──────────────────────────────────
def fetch_ecos(stat_code, cycle, start, end, item_code1="?", label=None):
    url = (
        f"{BASE_URL}/StatisticSearch/{API_KEY}/json/kr/1/10000"
        f"/{stat_code}/{cycle}/{start}/{end}/{item_code1}"
    )

    try:
        rows = requests.get(url, timeout=15).json() \
            .get("StatisticSearch", {}).get("row", [])

        if not rows:
            print(f"⚠️ [{label}] 데이터 없음")
            return pd.DataFrame()

        col = label
        df = pd.DataFrame(rows)[["TIME", "DATA_VALUE"]]
        df.columns = ["date", col]

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna()
        df = df.sort_values("date")

        print(f"✅ [{col}] {len(df)}개 데이터")
        return df

    except Exception as e:
        print(f"❌ [{label}] 오류:", e)
        return pd.DataFrame()

# ── 4. 기간 설정 ──────────────────────────────────────────
TODAY = datetime.today()
D_START = (TODAY - timedelta(days=365)).strftime("%Y%m%d")
D_END = TODAY.strftime("%Y%m%d")

# ── 5. 데이터 수집 ───────────────────────────────────────
print("\n📊 데이터 수집 시작")

df_rate = fetch_ecos("817Y002", "D", D_START, D_END, "010200000", "국고채10년")
df_usd  = fetch_ecos("731Y001", "D", D_START, D_END, "0000001", "원달러")

# 병합
df = pd.merge(df_rate, df_usd, on="date", how="inner")
print(df.head())   # 앞 5개
print(df.tail())   # 뒤 5개

# ============================================================
# 한국은행 ECOS API - 거시경제 지표 수집기 v4 (Windows VSCode용)
# 핵심 수정: Colab/apt 제거, .env 사용, Windows 한글 폰트 적용
# ============================================================

import os
import time
from datetime import datetime, timedelta

import requests
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import matplotlib

# ── 0. Windows 한글 폰트 설정 ──────────────────────────────
matplotlib.rcParams["font.family"] = "Malgun Gothic"
matplotlib.rcParams["axes.unicode_minus"] = False
print("✅ Windows 한글 폰트 설정 완료")

# ── 1. API KEY 로드 (.env 사용) ────────────────────────────
load_dotenv()
API_KEY = os.getenv("ECOS_API_KEY")
BASE_URL = "https://ecos.bok.or.kr/api"

if not API_KEY:
    raise ValueError("❌ ECOS_API_KEY가 .env 파일에 없습니다.")

print("✅ API KEY 로드 완료")


# ════════════════════════════════════════════════════════════
# [STEP 0] 항목코드 탐색 함수
# ════════════════════════════════════════════════════════════
def show_item_codes(stat_code):
    """
    통계표 코드의 전체 항목코드 목록 출력
    예) show_item_codes("817Y002")
    """
    url = f"{BASE_URL}/StatisticItemList/{API_KEY}/json/kr/1/200/{stat_code}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()

    rows = data.get("StatisticItemList", {}).get("row", [])
    if not rows:
        print(f"⚠️ [{stat_code}] 항목 없음 또는 코드 오류")
        return pd.DataFrame()

    df = pd.DataFrame(rows)[["ITEM_CODE", "ITEM_NAME", "CYCLE", "START_TIME", "END_TIME"]]
    print(f"\n▶ {stat_code} 항목 목록 ({len(df)}개)")
    print(df.to_string(index=False))
    return df


# ════════════════════════════════════════════════════════════
# 공통 수집 함수
# ════════════════════════════════════════════════════════════
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
    url = (
        f"{BASE_URL}/StatisticSearch/{API_KEY}/json/kr/1/10000"
        f"/{stat_code}/{cycle}/{start}/{end}"
        f"/{item_code1}/{item_code2}/{item_code3}/{item_code4}"
    )

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        rows = response.json().get("StatisticSearch", {}).get("row", [])

        if not rows:
            print(f"⚠️ [{label or stat_code}] 데이터 없음 — 항목코드 확인 필요")
            return pd.DataFrame()

        col = label or rows[0].get("ITEM_NAME1", stat_code)
        df = pd.DataFrame(rows)[["TIME", "DATA_VALUE"]].copy()
        df.columns = ["date", col]

        def parse_date(x):
            x = str(x)
            for q, m in [("Q1", "01"), ("Q2", "04"), ("Q3", "07"), ("Q4", "10")]:
                if q in x:
                    return x.replace(q, "") + m + "01"
            return x + "01" if len(x) == 6 else x

        df["date"] = pd.to_datetime(df["date"].apply(parse_date), errors="coerce")
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["date"])
        df = df.groupby("date", as_index=False)[col].mean()
        df = df.sort_values("date").reset_index(drop=True)

        print(f"✅ [{col}] {len(df)}행 ({df['date'].min().date()} ~ {df['date'].max().date()})")
        return df

    except Exception as e:
        print(f"❌ [{label or stat_code}] 오류: {e}")
        return pd.DataFrame()


def merge_dfs(dfs):
    result = None
    for df in dfs:
        if df is None or df.empty:
            continue
        result = df if result is None else pd.merge(result, df, on="date", how="outer")
    return result.sort_values("date").reset_index(drop=True) if result is not None else None


# ── 기간 설정 ──────────────────────────────────────────────
TODAY = datetime.today()
D_START = (TODAY - timedelta(days=365 * 3)).strftime("%Y%m%d")
D_END = TODAY.strftime("%Y%m%d")
M_START = (TODAY - timedelta(days=365 * 5)).strftime("%Y%m")
M_END = TODAY.strftime("%Y%m")
Q_START = f"{TODAY.year - 7}Q1"
Q_END = f"{TODAY.year}Q4"


# ════════════════════════════════════════════════════════════
# [STEP 0 실행] 817Y002 항목코드 목록 조회
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("  [STEP 0] 817Y002 항목코드 목록 조회")
print("=" * 55)
df_items = show_item_codes("817Y002")


# ════════════════════════════════════════════════════════════
# ① 일별 데이터 수집 (금리 + 환율)
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("  ① 일별 데이터 수집")
print("=" * 55)

df_국고채10년 = fetch_ecos("817Y002", "D", D_START, D_END, "010210000", label="국고채_10년")
df_국고채3년  = fetch_ecos("817Y002", "D", D_START, D_END, "010200000", label="국고채_3년")
df_콜금리     = fetch_ecos("817Y002", "D", D_START, D_END, "010101000", label="콜금리")
df_CD금리     = fetch_ecos("817Y002", "D", D_START, D_END, "010502000", label="CD금리_91일")
df_회사채AA   = fetch_ecos("817Y002", "D", D_START, D_END, "010300000", label="회사채_AA-")
df_회사채BBB  = fetch_ecos("817Y002", "D", D_START, D_END, "010320000", label="회사채_BBB-")

df_usd = fetch_ecos("731Y001", "D", D_START, D_END, "0000001", label="원달러")
df_eur = fetch_ecos("731Y001", "D", D_START, D_END, "0000003", label="원유로")
df_jpy = fetch_ecos("731Y001", "D", D_START, D_END, "0000002", label="원엔_100")
df_cny = fetch_ecos("731Y001", "D", D_START, D_END, "0000053", label="원위안")

time.sleep(0.3)

daily_list = [
    df_국고채10년, df_국고채3년, df_콜금리, df_CD금리,
    df_회사채AA, df_회사채BBB, df_usd, df_eur, df_jpy, df_cny
]
df_daily = merge_dfs([d for d in daily_list if not d.empty])

if df_daily is not None:
    if "국고채_3년" in df_daily.columns:
        if "회사채_AA-" in df_daily.columns:
            df_daily["신용스프레드_AA-"] = df_daily["회사채_AA-"] - df_daily["국고채_3년"]
        if "회사채_BBB-" in df_daily.columns:
            df_daily["신용스프레드_BBB-"] = df_daily["회사채_BBB-"] - df_daily["국고채_3년"]
        print("📊 신용스프레드 계산 완료")
    else:
        print("⚠️ 국고채_3년 없음 → 신용스프레드 계산 건너뜀")
        print("   → show_item_codes('817Y002') 결과에서 항목코드 확인 후 재실행")

print(f"\n일별 shape: {df_daily.shape if df_daily is not None else 'None'}")
print(f"컬럼: {list(df_daily.columns) if df_daily is not None else []}")


# ════════════════════════════════════════════════════════════
# ② 월별 데이터 수집
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("  ② 월별 데이터 수집")
print("=" * 55)

monthly_list = [
    fetch_ecos("722Y001", "M", M_START, M_END, "0101000", label="한국_기준금리"),
    fetch_ecos("901Y027", "M", M_START, M_END, "I61BC", label="실업률"),
    fetch_ecos("901Y027", "M", M_START, M_END, "I61E", label="고용률_15세이상"),
    fetch_ecos("512Y013", "M", M_START, M_END, "99988", "AA", label="BSI_전산업_실적"),
    fetch_ecos("512Y014", "M", M_START, M_END, "99988", "BA", label="BSI_전산업_전망"),
    fetch_ecos("901Y009", "M", M_START, M_END, "0", label="CPI_전년비"),
    fetch_ecos("732Y001", "M", M_START, M_END, "99", label="외환보유액_백만달러"),
]
df_monthly = merge_dfs([d for d in monthly_list if not d.empty])

print(f"\n월별 shape: {df_monthly.shape if df_monthly is not None else 'None'}")


# ════════════════════════════════════════════════════════════
# ③ 분기별 데이터 수집
# ════════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("  ③ 분기별 데이터 수집")
print("=" * 55)

quarterly_list = [
    fetch_ecos("200Y102", "Q", Q_START, Q_END, "10111", label="GDP성장률_전기비"),
    fetch_ecos("200Y102", "Q", Q_START, Q_END, "10211", label="GDP성장률_전년비"),
]
df_quarterly = merge_dfs([d for d in quarterly_list if not d.empty])

print(f"\n분기별 shape: {df_quarterly.shape if df_quarterly is not None else 'None'}")

BASE_DIR = Path(__file__).resolve().parents[3]
SAVE_DIR = BASE_DIR / "data"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
# ════════════════════════════════════════════════════════════
# ④ CSV 저장
# ════════════════════════════════════════════════════════════
today_str = TODAY.strftime("%Y%m%d")
for name, df in [("일별", df_daily), ("월별", df_monthly), ("분기별", df_quarterly)]:
    if df is not None and not df.empty:
        fname = SAVE_DIR / f"ecos_{name}_{today_str}.csv"
        df.to_csv(fname, index=False, encoding="utf-8-sig")

print("\n▶ 일별 (최근 5행):")
if df_daily is not None:
    print(df_daily.tail().to_string(index=False))
else:
    print("없음")

print("\n▶ 월별 (최근 5행):")
if df_monthly is not None:
    print(df_monthly.tail().to_string(index=False))
else:
    print("없음")


# # ════════════════════════════════════════════════════════════
# # ⑤ 시각화
# # ════════════════════════════════════════════════════════════
# ONE_YEAR_AGO = pd.Timestamp(TODAY - timedelta(days=365))
# COLORS = ["#2563EB", "#16A34A", "#DC2626", "#D97706", "#7C3AED", "#0891B2"]

# def safe_col(src, col):
#     if src is None or src.empty or col not in src.columns:
#         return None
#     return src[src["date"] >= ONE_YEAR_AGO][["date", col]].dropna()

# spread_aa = "신용스프레드_AA-" if (df_daily is not None and "신용스프레드_AA-" in df_daily.columns) else None
# spread_bbb = "신용스프레드_BBB-" if (df_daily is not None and "신용스프레드_BBB-" in df_daily.columns) else None

# plot_targets = [
#     (df_daily, "원달러", "환율 (원/달러)"),
#     (df_daily, "국고채_10년", "국고채 10년 (%)"),
#     (df_daily, spread_aa, "신용스프레드 AA- (%)"),
#     (df_daily, spread_bbb, "신용스프레드 BBB- (%)"),
#     (df_monthly, "실업률", "실업률 (%)"),
#     (df_monthly, "BSI_전산업_전망", "BSI 전산업 전망"),
# ]

# fig, axes = plt.subplots(3, 2, figsize=(16, 14))
# fig.suptitle("한국 거시경제 주요 지표 (ECOS)", fontsize=16, fontweight="bold", y=1.01)

# for i, (src, col, title) in enumerate(plot_targets):
#     ax = axes[i // 2][i % 2]
#     ax.set_title(title, fontsize=11)
#     ax.grid(True, alpha=0.3)

#     tmp = safe_col(src, col) if col else None
#     if tmp is None or tmp.empty:
#         msg = "항목코드 확인 필요\n(show_item_codes 실행)" if col else "데이터 없음"
#         ax.text(0.5, 0.5, msg, ha="center", va="center",
#                 transform=ax.transAxes, color="gray", fontsize=9)
#         continue

#     color = COLORS[i % len(COLORS)]
#     ax.plot(tmp["date"], tmp[col], linewidth=1.5, color=color)
#     ax.fill_between(tmp["date"], tmp[col], alpha=0.07, color=color)
#     ax.tick_params(axis="x", rotation=30, labelsize=8)

# plt.tight_layout()
# plt.savefig("ecos_dashboard.png", dpi=150, bbox_inches="tight")
# #plt.show()
#print("📈 ecos_dashboard.png 저장 완료")