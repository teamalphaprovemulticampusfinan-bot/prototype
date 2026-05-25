# src/data_intake/finance_intake/runner.py
"""
finance_intake 파이프라인 실행 진입점.
collect → normalize → validate → save 순서로 실행합니다.

사용 예시:
    python -m src.data_intake.finance_intake.runner --mode warning
    python -m src.data_intake.finance_intake.runner --mode financial --stock 014680
    python -m src.data_intake.finance_intake.runner --mode stock --stock 033640
    python -m src.data_intake.finance_intake.runner --mode all --stock 014680
"""

import argparse
import importlib.util
import json
import os
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from .schemas import STOCK_CODES
from .schemas import (
    FinancialConfig, StockConfig, WarningConfig,
    WARNING_COLS, STOCK_DISPLAY_COLS,
    BASE_DIR, DATA_DIR, WARNING_DIR, STOCK_DIR, FINANCIAL_DIR,
    CORP_CODES_PATH, RND_PATH, VKOSPI_CSV,
)
from .collector import (
    fetch_kind_warning_excel,
    fetch_financials_raw, fetch_financials_all_raw,
    fetch_business_report_zip,
    fetch_dart_quarterly_raw, fetch_shares_from_dart, fetch_shares_yfinance,
    fetch_shares_from_marketcap, fetch_shares_from_csv,
    fetch_stock_price, fetch_market_index, fetch_vix, fetch_vkospi,
    fetch_naver_investor_trend,
    resolve_ticker, get_market_ticker,
)
from .normalizer import (
    normalize_warning, merge_warning,
    normalize_financials, normalize_capex_ocf, normalize_interest,
    normalize_amortization, normalize_rnd_from_xml,
    compute_financial_metrics,
    normalize_stock_price, normalize_market_return, normalize_volatility,
    normalize_car, normalize_eps_psr, normalize_supply, rename_stock_columns,
)
from .validator import validate_warning, validate_financials, validate_stock, report_issues

load_dotenv()


# =========================
# 공통 유틸
# =========================

def _load_corp_code(stock_code: str) -> tuple[str, str]:
    """stock_code → (corp_code, corp_name)"""
    corp_df = pd.read_csv(CORP_CODES_PATH, dtype=str)
    matched = corp_df[corp_df["stock_code"] == stock_code]
    if matched.empty:
        raise ValueError(f"{stock_code}: corp_codes.csv에서 찾을 수 없습니다.")
    row = matched.iloc[0]
    return row["corp_code"], row["corp_name"]


def _load_rnd_csv(stock_code: str, year: int) -> float | None:
    """rnd.csv에서 해당 종목/연도 R&D 비용 조회"""
    rnd_df = pd.read_csv(RND_PATH, dtype={"stock_code": str})
    rnd_df["year"] = rnd_df["year"].astype(int)
    rnd_df["rnd"]  = pd.to_numeric(rnd_df["rnd"], errors="coerce")
    temp = rnd_df[(rnd_df["stock_code"] == stock_code) & (rnd_df["year"] == year)]
    return None if temp.empty else temp.iloc[0]["rnd"]


def _read_kind_excel(path: str) -> pd.DataFrame:
    """
    KIND에서 다운로드한 파일 읽기.
    확장자는 .xls지만 실제 내용이 HTML인 경우가 많아
    openpyxl → xlrd → HTML 순으로 시도합니다.
    """
    # 1. openpyxl (xlsx 형식인 경우)
    try:
        return pd.read_excel(path, engine="openpyxl")
    except Exception:
        pass

    # 2. xlrd (진짜 xls 바이너리인 경우)
    try:
        return pd.read_excel(path, engine="xlrd")
    except Exception:
        pass

    # 3. HTML 테이블 (확장자만 xls인 경우 — KIND에서 가장 흔함)
    try:
        from io import StringIO
        with open(path, encoding="utf-8", errors="ignore") as f:
            html = f.read()
        tables = pd.read_html(StringIO(html))
        if tables:
            return tables[0]
    except Exception:
        pass

    raise ValueError(f"파일을 읽을 수 없습니다: {path}")



def _standardize_stock_old_df(old_df: pd.DataFrame) -> pd.DataFrame:
    """
    기존 주식 CSV가 한글 컬럼/영문 컬럼/레거시 컬럼 중 무엇이든
    현재 표준 영어 컬럼(STOCK_DISPLAY_COLS)으로 맞춥니다.
    """
    rename_map = {
        # date-like columns are handled before this function
        "시가": "open",
        "고가": "high",
        "저가": "low",
        "종가": "close",
        "거래량": "volume",
        "시가총액": "market_cap",

        "수익률": "return",
        "시장수익률": "market_return",
        "이상수익률": "abnormal_return",

        "최대낙폭": "mdd",

        "20일이동평균": "ma20",
        "60일이동평균": "ma60",
        "20일이평비율": "ma20_ratio",
        "60일이평비율": "ma60_ratio",

        "VIX": "vix",
        "VKOSPI": "vkospi",

        "EPS": "eps",
        "PSR": "psr",

        "누적이상수익률_3일": "car_3",
        "누적이상수익률_5일": "car_5",

        "기관_순매매": "inst_net_buy",
        "외국인_순매매": "foreign_net_buy",
        "보유주수": "foreign_holding_shares",
        "보유 주수": "foreign_holding_shares",
        "보유율_%": "foreign_holding_pct",

        # legacy yfinance columns
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "Return": "return",
        "Market_Close": "market_close",
        "ABNRET": "abnormal_return",
        "MDD": "mdd",
        "MA20": "ma20",
        "MA60": "ma60",
        "MA20_ratio": "ma20_ratio",
        "MA60_ratio": "ma60_ratio",
        "CAR_3": "car_3",
        "CAR_5": "car_5",
    }

    old_df = old_df.copy()
    old_df.columns = old_df.columns.astype(str).str.strip()
    old_df = old_df.rename(columns=rename_map)
    old_df = old_df.loc[:, ~old_df.columns.duplicated()]
    old_df = old_df.reindex(columns=STOCK_DISPLAY_COLS)

    return old_df


def _read_existing_stock_csv(output_path: Path) -> pd.DataFrame | None:
    """
    기존 주식 CSV를 읽어서 날짜 인덱스를 복원합니다.
    날짜 컬럼명이 date/날짜/Date/일자/Unnamed: 0 등으로 달라도 처리합니다.
    """
    try:
        old_df = pd.read_csv(output_path)
    except Exception as e:
        print(f"[stock] 기존 파일 읽기 실패 → 기존 파일 무시: {output_path} / {e}")
        return None

    old_df.columns = old_df.columns.astype(str).str.strip()

    date_col = next(
        (
            c for c in ["date", "날짜", "Date", "일자", "Unnamed: 0"]
            if c in old_df.columns
        ),
        None,
    )

    if date_col is None:
        print(f"[stock] 기존 파일 날짜 컬럼 없음 → 기존 파일 무시: {output_path}")
        return None

    old_df[date_col] = pd.to_datetime(old_df[date_col], errors="coerce")
    old_df = (
        old_df
        .dropna(subset=[date_col])
        .set_index(date_col)
        .sort_index()
    )
    old_df.index.name = "date"

    return _standardize_stock_old_df(old_df)


def _parse_env_date(*names: str) -> pd.Timestamp | None:
    for name in names:
        raw = str(os.getenv(name, "")).strip()
        if not raw:
            continue
        parsed = pd.to_datetime(raw, errors="coerce")
        if not pd.isna(parsed):
            return pd.Timestamp(parsed).normalize()
    return None


def _finance_stock_start_ts() -> pd.Timestamp | None:
    return _parse_env_date("FINANCE_STOCK_START_DATE", "FINANCE_START_DATE", "ALPHAPROVE_DATA_START_DATE")


def _finance_stock_end_ts() -> pd.Timestamp | None:
    return _parse_env_date("FINANCE_STOCK_CUTOFF_DATE", "FINANCE_PRICE_CUTOFF_DATE", "FINANCE_END_DATE", "FINANCE_AS_OF_DATE", "ALPHAPROVE_DATA_CUTOFF_DATE")


def _finance_intake_years_from_env(default_years: list[int] | None = None) -> list[int]:
    if default_years:
        return default_years
    start_raw = os.getenv("FINANCE_FINANCIAL_START_YEAR") or os.getenv("FINANCE_START_DATE", "2021")[:4]
    end_raw = os.getenv("FINANCE_FINANCIAL_END_YEAR") or os.getenv("FINANCE_CUTOFF_YEAR", "")
    try:
        start_year = int(str(start_raw)[:4])
        end_year = int(float(str(end_raw))) if str(end_raw).strip() else datetime.now().year - 1
    except Exception:
        return [2022, 2023, 2024, 2025]
    if end_year < start_year:
        return [end_year]
    return list(range(start_year, end_year + 1))


def _timestamp_to_ymd(value: pd.Timestamp | None) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")



# =========================
# 1. 경고 파이프라인
# =========================

def run_warning(cfg: WarningConfig) -> None:
    """KIND 투자경고 수집 → 정규화 → 검증 → 저장"""
    cfg.download_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.today()
    start_date = (today - timedelta(days=cfg.days)).strftime("%Y-%m-%d")
    end_date   = today.strftime("%Y-%m-%d")

    print(f"[warning] 조회 기간: {start_date} ~ {end_date}")

    # 1. Collect
    latest_file = fetch_kind_warning_excel(
        url=cfg.url,
        start_date=start_date,
        end_date=end_date,
        download_dir=str(cfg.download_dir),
    )
    if not latest_file:
        raise FileNotFoundError("엑셀 다운로드 완료되지 않음")
    print(f"[warning] 다운로드 파일: {latest_file}")

    new_df = _read_kind_excel(latest_file)

    # 2. Normalize
    if new_df.dropna(how="all").empty:
        print("[warning] 신규 데이터 없음")
        if cfg.mode == "update" and cfg.csv_path.exists():
            final_df = pd.read_csv(cfg.csv_path, dtype={"종목코드": str})
        else:
            final_df = pd.DataFrame(columns=WARNING_COLS)
    else:
        new_df = normalize_warning(new_df)

        if cfg.mode == "overwrite":
            final_df = new_df
        elif cfg.mode == "update":
            if cfg.csv_path.exists():
                old_df = pd.read_csv(cfg.csv_path, dtype={"종목코드": str})
                old_df = normalize_warning(old_df)   # 기존 파일도 동일 형식 보장
                final_df = merge_warning(old_df, new_df)
            else:
                final_df = new_df
        else:
            raise ValueError("mode는 'update' 또는 'overwrite'만 허용됩니다.")

    # 3. Validate
    issues = validate_warning(final_df)
    report_issues("warning", issues)

    # 4. Save
    final_df.to_csv(cfg.csv_path,  index=False, encoding="utf-8-sig")
    final_df.to_json(cfg.json_path, orient="records", force_ascii=False, indent=2)
    print(f"[warning] 저장 완료 (총 {len(final_df)}건)")


def run_warning_optional(cfg: WarningConfig) -> dict[str, str]:
    """Run KIND warning collection only when Selenium is installed."""

    if importlib.util.find_spec("selenium") is None:
        message = (
            "selenium 미설치로 KIND 투자경고 수집을 생략합니다. "
            "기존 투자경고 CSV가 있으면 finance_agent 단계에서 그대로 사용합니다."
        )
        print(f"[warning] {message}")
        return {
            "status_detail": "SKIPPED_OPTIONAL_DEPENDENCY",
            "skip_reason": message,
        }

    run_warning(cfg)
    return {"status_detail": "DONE"}


# =========================
# 2. 재무제표 파이프라인
# =========================

def run_financial(cfg: FinancialConfig, sector: str = "") -> None:
    """DART 재무제표 수집 → 정규화 → 검증 → 저장"""

    corp_code, company_name = _load_corp_code(cfg.stock_code)
    api_key = cfg.dart_api_key or os.getenv("DART_API_KEY")
    if not api_key:
        raise ValueError("DART_API_KEY 없음 (.env 또는 cfg 확인)")

    print(f"[financial] {company_name} ({corp_code}) / {cfg.years}")

    rows = []
    for year in cfg.years:
        # 1. Collect
        fin_raw     = fetch_financials_raw(api_key, corp_code, year)
        all_raw     = fetch_financials_all_raw(api_key, corp_code, year)
        all_raw_ofs = fetch_financials_all_raw(api_key, corp_code, year, fs_div="OFS")
        report_zip  = fetch_business_report_zip(api_key, corp_code, year)  # 1회만 다운로드

        if not fin_raw:
            print(f"  {year}: 재무데이터 없음 - 스킵")
            continue

        # 2. Normalize
        fin    = normalize_financials(fin_raw, year)
        capex, ocf = normalize_capex_ocf(all_raw)
        interest   = normalize_interest(all_raw, all_raw_ofs)
        amort      = normalize_amortization(report_zip, year)

        rnd = _load_rnd_csv(cfg.stock_code, year)
        if rnd is None:
            rnd = normalize_rnd_from_xml(report_zip, year)

        fin["rnd"]      = rnd
        fin["capex"]    = capex
        fin["ocf"]      = ocf
        fin["fcf"]      = (ocf or 0) - (capex or 0)
        fin["interest_expense"] = interest
        fin.update(amort)

        rows.append(fin)

    df = pd.DataFrame(rows)
    if df.empty:
        print(f"[financial] {company_name}: 저장할 재무데이터 없음 - 스킵")
        return

    df = compute_financial_metrics(df)
    df = df.loc[:, ~df.columns.astype(str).str.startswith("amort_")]
    # 3. Validate
    issues = validate_financials(rows)
    report_issues("financial", issues)

    # 4. Save
    output_path = BASE_DIR / "data" / sector / company_name / "finance" / f"{company_name}_재무.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[financial] 저장 완료: {output_path}")
    print(df)


# =========================
# 3. 주가 파이프라인
# =========================

def run_stock(cfg: StockConfig, sector: str = "") -> None:
    """주가 수집 → 정규화 → 검증 → 저장"""

    api_key = cfg.dart_api_key or os.getenv("DART_API_KEY")

    # corp_code / 회사명
    try:
        corp_code, corp_name = _load_corp_code(cfg.stock_code)
    except ValueError:
        corp_code = None
        corp_name = cfg.stock_code
        print(f"[stock] corp_codes.csv 미발견 → EPS/PSR 스킵")

    output_path = BASE_DIR / "data" / sector / corp_name / "finance" / f"{corp_name}_주식.csv"

    # 기존 파일 기반 start 날짜 결정. Monthly backtest env가 있으면
    # 기존 파일의 미래 행을 먼저 제외해 no-look-ahead 누수를 막습니다.
    start_bound = _finance_stock_start_ts()
    end_bound = _finance_stock_end_ts()

    if output_path.exists():
        old_df = _read_existing_stock_csv(output_path)
        if old_df is not None and not old_df.empty and end_bound is not None:
            old_df = old_df[old_df.index <= end_bound]

        if old_df is not None and not old_df.empty:
            start_ts = old_df.index.max() - timedelta(days=90)
            if start_bound is not None:
                start_ts = min(pd.Timestamp(start_ts), start_bound)
            start = pd.Timestamp(start_ts).strftime("%Y-%m-%d")
        else:
            from dateutil.relativedelta import relativedelta

            old_df = None
            start = _timestamp_to_ymd(start_bound) or (
                datetime.now() - relativedelta(years=cfg.lookback_years)
            ).strftime("%Y-%m-%d")

            print("[stock] 기존 파일 사용 불가 → 초기 수집 시작")

    else:
        old_df = None

        from dateutil.relativedelta import relativedelta

        start = _timestamp_to_ymd(start_bound) or (
            datetime.now() - relativedelta(years=cfg.lookback_years)
        ).strftime("%Y-%m-%d")

        print("[stock] 초기 수집 시작")

    ticker       = resolve_ticker(cfg.stock_code)
    pure_code    = ticker.split(".")[0]
    market_ticker = get_market_ticker(ticker)
    price_col    = "Close"

    print(f"[stock] {corp_name} | ticker={ticker} | market={market_ticker} | start={start}")

    # 1. Collect
    df      = fetch_stock_price(ticker, start)
    mkt     = fetch_market_index(market_ticker, start)
    vix_df  = fetch_vix(start)
    vkospi_df = fetch_vkospi(start, csv_path=str(VKOSPI_CSV))

    shares = np.nan
    df_dart = pd.DataFrame()
    if corp_code and api_key:
        # 1순위: DART API
        shares_year = int(os.getenv("FINANCE_CUTOFF_YEAR", "") or ((end_bound.year if end_bound is not None else datetime.now().year) - 1))
        shares = fetch_shares_from_dart(api_key, corp_code,
                                        year=shares_year)
        # 2순위: yfinance sharesOutstanding
        if np.isnan(shares):
            shares = fetch_shares_yfinance(ticker)
        # 3순위: marketCap / 최근 종가 역산
        if np.isnan(shares) and not df.empty:
            last_price = df["Close"].dropna().iloc[-1] if "Close" in df.columns else np.nan
            shares = fetch_shares_from_marketcap(ticker, last_price)
            if not np.isnan(shares):
                print(f"[stock] marketCap 역산으로 shares 추정")
        # 4순위: shares.csv 수동 보완
        if np.isnan(shares):
            shares = fetch_shares_from_csv(cfg.stock_code)
            if not np.isnan(shares):
                print(f"[stock] shares.csv fallback 사용")
        if np.isnan(shares):
            print(f"[stock] 발행주식수 없음 → EPS/PSR NaN 처리")
        df_dart = fetch_dart_quarterly_raw(api_key, corp_code,
                                           start_year=cfg.dart_start_year)

    df_supply = fetch_naver_investor_trend(pure_code, start)

    # 2. Normalize
    df = normalize_stock_price(df, price_col)
    df = normalize_market_return(df, mkt, price_col)
    df = normalize_volatility(df, vix_df, vkospi_df, price_col)
    df = normalize_car(df)
    df = normalize_eps_psr(df, df_dart, shares, price_col)
    df = normalize_supply(df, df_supply)
    df = rename_stock_columns(df, shares, price_col)

    # 워밍업 기간 제거 (MA 계산 안정화)
    from datetime import datetime as dt
    from dateutil.relativedelta import relativedelta
    start_dt = dt.strptime(start, "%Y-%m-%d")
    df = df[df.index >= start_dt + timedelta(days=90)]

    df_save = df[STOCK_DISPLAY_COLS].copy()

    if old_df is not None:
        old_df = _standardize_stock_old_df(old_df)
        df_save = pd.concat([old_df, df_save])

    df_save = df_save.loc[:, ~df_save.columns.duplicated()]
    df_save = df_save.reindex(columns=STOCK_DISPLAY_COLS)
    df_save = df_save[~df_save.index.duplicated(keep="last")].sort_index()

    if start_bound is not None:
        df_save = df_save[df_save.index >= start_bound]
    else:
        cutoff = dt.now() - relativedelta(years=cfg.lookback_years)
        df_save = df_save[df_save.index >= cutoff]
    if end_bound is not None:
        df_save = df_save[df_save.index <= end_bound]

    # 3. Validate
    issues = validate_stock(df_save)
    report_issues("stock", issues)

    # 4. Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_save.to_csv(output_path, index=True, index_label="date", encoding="utf-8-sig")
    print(f"[stock] 저장 완료: {output_path}")
    print(df_save[STOCK_DISPLAY_COLS].tail())


# =========================
# VKOSPI 업데이트
# =========================

def run_vkospi_update() -> None:
    """
    data/_global_common/vkospi.csv를 읽어서
    data 아래 회사별 *_stock.csv의 VKOSPI 컬럼을 업데이트합니다.
    """
    if not VKOSPI_CSV.exists():
        print(f"[vkospi] CSV 없음: {VKOSPI_CSV}")
        print("[vkospi] src/data_intake/finance_intake/vkospi.py를 먼저 실행해 주세요.")
        return

    vk = pd.read_csv(VKOSPI_CSV)
    date_col = next((c for c in ["date", "Date", "날짜", "일자"] if c in vk.columns), None)
    value_col = next((c for c in ["vkospi", "VKOSPI", "Close", "close", "종가"] if c in vk.columns), None)
    if not date_col or not value_col:
        print(f"[vkospi] CSV 컬럼 인식 실패: {VKOSPI_CSV} / columns={list(vk.columns)}")
        return
    vk[date_col] = pd.to_datetime(vk[date_col], errors="coerce")
    vk[value_col] = pd.to_numeric(vk[value_col].astype(str).str.replace(",", "", regex=False), errors="coerce")
    vk = vk.dropna(subset=[date_col, value_col]).set_index(date_col).sort_index()
    vk = vk[[value_col]].rename(columns={value_col: "VKOSPI"})

    stock_files = [
        p for p in STOCK_DIR.rglob("*_stock.csv")
        if "_global_common" not in p.parts and "_sector_common" not in p.parts
    ]
    if not stock_files:
        print(f"[vkospi] data 아래 *_stock.csv 없음: {STOCK_DIR}")
        return

    for stock_file in stock_files:
        try:
            df = pd.read_csv(stock_file)
            stock_date_col = next((c for c in ["날짜", "date", "Date", "일자"] if c in df.columns), None)
            if not stock_date_col:
                print(f"[vkospi] {stock_file.name} 날짜 컬럼 없음 → 건너뜀")
                continue
            df[stock_date_col] = pd.to_datetime(df[stock_date_col], errors="coerce")
            df = df.dropna(subset=[stock_date_col]).set_index(stock_date_col).sort_index()

            # VKOSPI 컬럼이 없거나 전부 NaN인 날짜만 업데이트
            if "VKOSPI" not in df.columns:
                df["VKOSPI"] = np.nan

            overlap = df.index.intersection(vk.index)
            df.loc[overlap, "VKOSPI"] = vk.loc[overlap, "VKOSPI"].values

            df.to_csv(stock_file, index=True, index_label=stock_date_col, encoding="utf-8-sig")
            filled = df["VKOSPI"].notna().sum()
            print(f"[vkospi] {stock_file.name} 업데이트 완료 ({filled}행 채움)")

        except Exception as e:
            print(f"[vkospi] {stock_file.name} 업데이트 실패: {e}")


# =========================
# CLI 진입점
# =========================

def main(argv=None):
    parser = argparse.ArgumentParser(description="finance_intake runner")
    parser.add_argument(
        "--mode",
        choices=["warning", "financial", "stock", "vkospi", "all"],
        required=True,
    )
    parser.add_argument("--stock", type=str, help="종목코드 (financial / stock 필수)")
    parser.add_argument("--years", type=int, nargs="+", default=[2022, 2023, 2024, 2025])
    parser.add_argument("--warning-mode", choices=["update", "overwrite"], default="update")
    parser.add_argument("--warning-days", type=int, default=1)
    parser.add_argument("--sector", type=str, default="반도체", help="섹터 폴더명 (예: 반도체)")  # 추가
    args = parser.parse_args(argv)

    if args.mode in ("warning", "all"):
        run_warning(WarningConfig(mode=args.warning_mode, days=args.warning_days))

    if args.mode in ("financial", "all"):
        codes = [args.stock] if args.stock else STOCK_CODES
        for code in codes:
            run_financial(FinancialConfig(stock_code=code, years=args.years), sector=args.sector)  # sector 추가

    if args.mode in ("stock", "all"):
        codes = [args.stock] if args.stock else STOCK_CODES
        for code in codes:
            run_stock(StockConfig(stock_code=code), sector=args.sector)  # sector 추가

    if args.mode in ("vkospi",):
        run_vkospi_update()


if __name__ == "__main__":
    main()

# # schemas.py의 STOCK_CODES 전체 실행
# python -m src.data_intake.finance_intake.runner --mode all

# # 특정 종목만 그때그때 지정
# python -m src.data_intake.finance_intake.runner --mode all --stock 005930 --sector 반도체

# # warning은 종목 무관
# python -m src.data_intake.finance_intake.runner --mode warning

# ---------------------------------------------------------------------
# AlphaProve unified data_intake wrapper
# ---------------------------------------------------------------------
def run_finance_intake(
    company_dir: str | None = None,
    company: str | None = None,
    field: str = "반도체",
    stock_code: str | None = None,
    mode: str = "all",
    years: list[int] | None = None,
    force_fetch: bool = False,
    skip_network: bool = False,
    continue_on_error: bool = True,
    **_: object,
):
    """Wrapper used by src/data_intake/runner.py.

    The original finance_intake CLI requires --mode and optionally --stock.
    Unified data_intake only knows company-dir/company, so this function resolves
    the stock code and calls the existing finance collection functions directly.
    """
    from common.data_paths import company_agent_dir, company_config_path, company_slug

    STOCK_CODE_BY_SLUG = {
        "nepes": "033640",
        "hanmi": "042700",
        "hansol": "014680",
        "duksan": "317330",
        "ltc": "170920",
    }

    def _resolve_stock() -> str | None:
        if stock_code:
            s = str(stock_code).strip()
            return s.zfill(6) if s.isdigit() else s
        raw = str(company_dir or company or "").strip()
        if raw.isdigit() and len(raw) == 6:
            return raw
        try:
            slug = company_slug(raw)
        except Exception:
            slug = raw.lower()
        if slug in STOCK_CODE_BY_SLUG:
            return STOCK_CODE_BY_SLUG[slug]
        try:
            cfg_path = company_config_path(slug, create_parent=False)
            if cfg_path.exists():
                try:
                    import yaml  # type: ignore
                    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
                except UnicodeDecodeError:
                    import yaml  # type: ignore
                    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8-sig")) or {}
                code = str(cfg.get("stock_code") or "").strip()
                if code:
                    return code.zfill(6) if code.isdigit() else code
        except Exception:
            pass
        return None

    started = datetime.now()
    slug = company_dir or company or "unknown"
    out_dir = company_agent_dir(slug, "finance", create=True) / "intake"
    out_dir.mkdir(parents=True, exist_ok=True)
    resolved_stock = _resolve_stock()
    years = _finance_intake_years_from_env(years)
    steps: list[dict[str, object]] = []

    if skip_network:
        manifest = {
            "agent": "finance",
            "status": "SKIPPED_NETWORK_DISABLED",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "company_dir": company_dir,
            "company": company,
            "field": field,
            "stock_code": resolved_stock,
            "mode": mode,
            "reason": "--skip-network 지정으로 DART/주가/KIND 수집을 생략했습니다.",
            "start_date": _timestamp_to_ymd(_finance_stock_start_ts()),
            "end_date": _timestamp_to_ymd(_finance_stock_end_ts()),
            "years": years,
        }
        path = out_dir / "finance_intake_manifest.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[Finance Intake] manifest 저장: {path}")
        return manifest

    if not resolved_stock and mode in {"financial", "stock", "all"}:
        manifest = {
            "agent": "finance",
            "status": "FAILED_NO_STOCK_CODE",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "company_dir": company_dir,
            "company": company,
            "field": field,
            "mode": mode,
            "start_date": _timestamp_to_ymd(_finance_stock_start_ts()),
            "end_date": _timestamp_to_ymd(_finance_stock_end_ts()),
            "years": years,
            "error": "stock_code를 확인하지 못했습니다.",
        }
        path = out_dir / "finance_intake_manifest.json"
        path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        if not continue_on_error:
            raise ValueError(manifest["error"])
        return manifest

    def _step(name: str, func) -> dict[str, object]:
        step_started = datetime.now()
        try:
            result = func()
            record = {
                "name": name,
                "status": "OK",
                "started_at": step_started.isoformat(timespec="seconds"),
                "ended_at": datetime.now().isoformat(timespec="seconds"),
            }
            if isinstance(result, dict):
                record.update({str(k): v for k, v in result.items() if k not in {"name", "started_at", "ended_at"}})
            return record
        except Exception as exc:
            tb = traceback.format_exc()
            print(f"[Finance Intake] {name} failed: {exc}")
            if not continue_on_error:
                raise
            return {
                "name": name,
                "status": "FAILED",
                "started_at": step_started.isoformat(timespec="seconds"),
                "ended_at": datetime.now().isoformat(timespec="seconds"),
                "error": str(exc),
                "traceback": tb,
            }

    step_jobs: list[tuple[str, object]] = []

    if mode in ("warning", "all"):
        step_jobs.append(("warning", lambda: run_warning_optional(WarningConfig(mode="update", days=1))))

    if mode in ("financial", "all"):
        assert resolved_stock is not None
        step_jobs.append(("financial", lambda: run_financial(FinancialConfig(stock_code=resolved_stock, years=years), sector=field)))

    if mode in ("stock", "all"):
        assert resolved_stock is not None
        step_jobs.append(("stock", lambda: run_stock(StockConfig(stock_code=resolved_stock), sector=field)))

    if mode in ("vkospi",):
        step_jobs.append(("vkospi", run_vkospi_update))

    parallel_steps = (
        mode == "all"
        and len(step_jobs) > 1
        and str(os.getenv("FINANCE_INTAKE_PARALLEL", "1")).strip().lower() in {"1", "true", "yes", "y", "on"}
    )
    if parallel_steps:
        worker_count = min(len(step_jobs), int(os.getenv("FINANCE_INTAKE_MAX_WORKERS", "3") or "3"))
        print(f"[Finance Intake] 병렬 실행 활성화: max_workers={worker_count}")
        ordered: list[dict[str, object] | None] = [None] * len(step_jobs)
        with ThreadPoolExecutor(max_workers=max(1, worker_count)) as executor:
            future_map = {
                executor.submit(_step, name, func): (idx, name)
                for idx, (name, func) in enumerate(step_jobs)
            }
            for future in as_completed(future_map):
                idx, name = future_map[future]
                try:
                    ordered[idx] = future.result()
                except Exception:
                    if not continue_on_error:
                        raise
                    ordered[idx] = {
                        "name": name,
                        "status": "FAILED",
                        "started_at": datetime.now().isoformat(timespec="seconds"),
                        "ended_at": datetime.now().isoformat(timespec="seconds"),
                        "error": traceback.format_exc(),
                    }
        steps.extend([s for s in ordered if isinstance(s, dict)])
    else:
        for name, func in step_jobs:
            steps.append(_step(name, func))

    status = "OK" if all(s.get("status") == "OK" for s in steps) else "PARTIAL"
    manifest = {
        "agent": "finance",
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "started_at": started.isoformat(timespec="seconds"),
        "ended_at": datetime.now().isoformat(timespec="seconds"),
        "company_dir": company_dir,
        "company": company,
        "field": field,
        "stock_code": resolved_stock,
        "mode": mode,
        "years": years,
        "start_date": _timestamp_to_ymd(_finance_stock_start_ts()),
        "end_date": _timestamp_to_ymd(_finance_stock_end_ts()),
        "force_fetch": force_fetch,
        "steps": steps,
    }
    path = out_dir / "finance_intake_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Finance Intake] manifest 저장: {path}")
    print(f"[Finance Intake] status: {status}")
    return manifest


def run_intake(company_dir: str | None = None, company: str | None = None, **kwargs: object):
    return run_finance_intake(company_dir=company_dir, company=company, **kwargs)
