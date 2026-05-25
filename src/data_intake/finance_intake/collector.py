import os
import time
import glob
import zipfile
from io import StringIO, BytesIO
from pathlib import Path
import numpy as np
import pandas as pd
import requests
import yfinance as yf


# =========================
# 공통 / 주가
# =========================

def resolve_ticker(stock_code: str) -> str:
    """종목코드 → yfinance ticker 자동 판별"""
    stock_code = str(stock_code).zfill(6)

    for suffix in [".KS", ".KQ"]:
        ticker = f"{stock_code}{suffix}"
        data = yf.Ticker(ticker).history(period="5d")
        if not data.empty:
            return ticker

    raise ValueError(f"{stock_code}: KS/KQ 둘 다 yfinance 조회 실패")


def get_market_ticker(stock_ticker: str) -> str:
    stock_ticker = stock_ticker.upper()

    if stock_ticker.endswith(".KS"):
        return "^KS11"
    if stock_ticker.endswith(".KQ"):
        return "^KQ11"

    raise ValueError("ticker 끝에 .KS 또는 .KQ가 있어야 합니다.")


def fetch_stock_price(ticker: str, start: str) -> pd.DataFrame:
    df = yf.download(ticker, start=start, auto_adjust=True)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def fetch_market_index(market_ticker: str, start: str) -> pd.DataFrame:
    df = yf.download(market_ticker, start=start, auto_adjust=True)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.index = pd.to_datetime(df.index)
    return df.sort_index()


def fetch_vix(start: str) -> pd.DataFrame:
    return fetch_market_index("^VIX", start)


def _vkospi_csv_candidates(csv_path: str | None = None) -> list[Path]:
    base = Path(__file__).resolve().parents[3]
    candidates: list[Path] = []
    if csv_path:
        candidates.append(Path(csv_path))
    candidates.extend(
        [
            base / "data" / "_global_common" / "vkospi.csv",
            base / "data" / "finance_data" / "vkospi_data" / "vkospi.csv",
        ]
    )

    out: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()) if path.is_absolute() else str(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def _read_vkospi_csv(path: Path, start_dt: pd.Timestamp) -> pd.DataFrame:
    df_csv = pd.read_csv(path)
    date_col = next((c for c in ["date", "Date", "날짜", "일자"] if c in df_csv.columns), None)
    value_col = next((c for c in ["vkospi", "VKOSPI", "Close", "close", "종가"] if c in df_csv.columns), None)
    if not date_col or not value_col:
        raise ValueError(f"required columns not found: date={date_col}, value={value_col}")

    df_csv[date_col] = pd.to_datetime(df_csv[date_col], errors="coerce")
    df_csv[value_col] = pd.to_numeric(
        df_csv[value_col].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )
    df_csv = df_csv.dropna(subset=[date_col, value_col])
    df_csv = df_csv.set_index(date_col).sort_index()
    df_csv = df_csv.rename(columns={value_col: "Close"})
    df_csv = df_csv[["Close"]]
    return df_csv[df_csv.index >= start_dt]


def fetch_vkospi(start: str, csv_path: str | None = None) -> pd.DataFrame:
    """
    VKOSPI 수집 (우선순위 순):
      1. csv_path CSV 파일
      2. data/_global_common/vkospi.csv
      3. legacy data/finance_data/vkospi_data/vkospi.csv
      4. 네이버 크롤링
      5. 실패 시 빈 DataFrame 반환 → normalizer에서 NaN 처리
    """
    start_dt = pd.to_datetime(start)

    # --- 1. CSV 우선 ---
    csv_errors: list[str] = []
    for candidate in _vkospi_csv_candidates(csv_path):
        if not candidate.exists():
            continue
        try:
            df_csv = _read_vkospi_csv(candidate, start_dt)
            if not df_csv.empty:
                print(f"[vkospi] CSV 로드 성공: {candidate} ({len(df_csv)}행)")
                return df_csv
            csv_errors.append(f"{candidate}: rows before start date only")
        except Exception as e:
            csv_errors.append(f"{candidate}: {e}")

    if csv_errors:
        print(f"[vkospi] CSV 로드 실패/공백 → 네이버 시도: {'; '.join(csv_errors[:3])}")
    else:
        print("[vkospi] CSV 없음 → 네이버 시도")

    # --- 2. 네이버 폴백 ---
    try:
        url = "https://finance.naver.com/sise/sise_vkospi.naver"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        r.encoding = "euc-kr"

        tables = pd.read_html(StringIO(r.text))
        df = tables[0].copy().dropna()
        df.columns = ["Date", "Close", "Change"]
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Close"] = (
            df["Close"]
            .astype(str)
            .str.replace(",", "", regex=False)
        )
        df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        df = df.dropna(subset=["Date", "Close"])
        df = df.set_index("Date").sort_index()
        df = df[df.index >= start_dt]

        if not df.empty:
            print(f"[vkospi] 네이버 크롤링 성공 ({len(df)}행)")
            return df[["Close"]].asfreq("B")

    except Exception as e:
        print(f"[vkospi] 네이버 크롤링 실패 → NaN 처리: {e}")

    # --- 3. 최종 폴백 ---
    return pd.DataFrame(columns=["Close"])


def fetch_shares_yfinance(ticker: str) -> float:
    try:
        info = yf.Ticker(ticker).info
        shares = info.get("sharesOutstanding")
        return float(shares) if shares else np.nan
    except Exception:
        return np.nan


def fetch_shares_from_marketcap(ticker: str, last_price: float) -> float:
    """
    yfinance marketCap / 최근 종가로 발행주식수 역산.
    DART·yfinance sharesOutstanding 둘 다 실패했을 때 3순위 fallback.
    """
    try:
        market_cap = yf.Ticker(ticker).info.get("marketCap")
        if market_cap and last_price and last_price > 0:
            return float(market_cap) / float(last_price)
        return np.nan
    except Exception:
        return np.nan


def fetch_shares_from_csv(stock_code: str, csv_path=None) -> float:
    """
    shares.csv에서 발행주식수 조회.
    DART·yfinance·marketCap 모두 실패했을 때 4순위 (수동 보완) fallback.

    shares.csv 형식: stock_code, shares
    기본 경로: finance_intake/shares.csv
    """
    try:
        if csv_path is None:
            csv_path = str(Path(__file__).resolve().parent / "shares.csv")

        df_shares = pd.read_csv(csv_path, dtype={"stock_code": str})
        df_shares["stock_code"] = df_shares["stock_code"].str.zfill(6)

        matched = df_shares[df_shares["stock_code"] == str(stock_code).zfill(6)]
        if not matched.empty:
            return float(matched.iloc[0]["shares"])

        return np.nan
    except Exception:
        return np.nan


# =========================
# DART
# =========================

def fetch_shares_from_dart(api_key: str, corp_code: str, year: int) -> float:
    try:
        r = requests.get(
            "https://opendart.fss.or.kr/api/stockTotqySttus.json",
            params={
                "crtfc_key": api_key,
                "corp_code": corp_code,
                "bsns_year": year,
                "reprt_code": "11011",
            },
            timeout=10,
        )
        data = r.json()

        if data.get("status") != "000":
            return np.nan

        for item in data.get("list", []):
            val = item.get("istc_totqy", "").replace(",", "")
            if val:
                return float(val)

        return np.nan

    except Exception:
        return np.nan


def fetch_dart_quarterly_raw(
    api_key: str,
    corp_code: str,
    start_year: int = 2021,
) -> pd.DataFrame:
    records = []

    reprt_map = {
        "11013": "1Q",
        "11012": "2Q",
        "11014": "3Q",
        "11011": "4Q",
    }

    current_year = pd.Timestamp.today().year

    for year in range(start_year, current_year + 1):
        for reprt_code, qname in reprt_map.items():
            data = None

            for fs_div in ["CFS", "OFS"]:
                try:
                    r = requests.get(
                        "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json",
                        params={
                            "crtfc_key": api_key,
                            "corp_code": corp_code,
                            "bsns_year": year,
                            "reprt_code": reprt_code,
                            "fs_div": fs_div,
                        },
                        timeout=10,
                    )
                    temp = r.json()

                    if temp.get("status") == "000":
                        data = temp
                        break

                except Exception:
                    continue

            if not data:
                continue

            net_income = np.nan
            revenue = np.nan

            for item in data.get("list", []):
                acnt = item.get("account_nm", "")
                val = item.get("thstrm_amount", "").replace(",", "")

                try:
                    val = float(val)
                except Exception:
                    continue

                if any(k in acnt for k in ["당기순이익", "분기순이익", "반기순이익"]):
                    net_income = val
                elif any(k in acnt for k in ["매출액", "수익"]):
                    revenue = val

            records.append(
                {
                    "year": year,
                    "quarter": qname,
                    "reprt_code": reprt_code,
                    "net_income": net_income,
                    "revenue": revenue,
                }
            )

            time.sleep(0.3)

    return pd.DataFrame(records)


def fetch_financials_raw(api_key: str, corp_code: str, year: int):
    r = requests.get(
        "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json",
        params={
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": "11011",
            "fs_div": "CFS",
        },
        timeout=10,
    )
    data = r.json()
    return data if data.get("status") == "000" else None


def fetch_financials_all_raw(
    api_key: str,
    corp_code: str,
    year: int,
    fs_div: str = "CFS",
):
    r = requests.get(
        "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json",
        params={
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": "11011",
            "fs_div": fs_div,
        },
        timeout=10,
    )
    data = r.json()
    return data if data.get("status") == "000" else None


def _get_business_report_rcept_no(api_key: str, corp_code: str, year: int):
    r = requests.get(
        "https://opendart.fss.or.kr/api/list.json",
        params={
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bgn_de": f"{year}0101",
            "end_de": f"{year}1231",
            "pblntf_ty": "A",
            "pblntf_detail_ty": "A001",
            "page_count": 100,
        },
        timeout=10,
    )
    data = r.json()

    if data.get("status") != "000":
        return None

    items = data.get("list", [])
    if not items:
        return None

    return items[-1]["rcept_no"]


def _download_document_zip(api_key: str, rcept_no: str):
    r = requests.get(
        "https://opendart.fss.or.kr/api/document.xml",
        params={
            "crtfc_key": api_key,
            "rcept_no": rcept_no,
        },
        timeout=20,
    )
    return r.content


def fetch_business_report_zip(api_key: str, corp_code: str, year: int):
    """
    사업보고서 ZIP을 한 번만 다운로드합니다.
    amortization / rnd 둘 다 같은 ZIP을 사용하므로 통합했습니다.
    runner.py에서 zip_bytes를 받아 각 normalize 함수에 전달하세요.
    """
    rcept_no = _get_business_report_rcept_no(api_key, corp_code, year)
    if rcept_no is None:
        return None
    return _download_document_zip(api_key, rcept_no)


# 하위 호환용 alias (기존 코드가 남아 있을 경우를 대비)
fetch_amortization_zip = fetch_business_report_zip
fetch_rnd_zip = fetch_business_report_zip


# =========================
# 네이버 수급
# =========================

def fetch_naver_investor_trend(
    pure_code: str,
    start_date: str,
    total_pages: int = 80,
) -> pd.DataFrame:
    all_dfs = []
    start_dt = pd.to_datetime(start_date)

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://finance.naver.com/",
    }

    for page in range(1, total_pages + 1):
        try:
            r = requests.get(
                "https://finance.naver.com/item/frgn.nhn",
                params={"code": pure_code, "page": page},
                headers=headers,
                timeout=10,
            )
            r.encoding = "euc-kr"

            dfs = pd.read_html(StringIO(r.text))
            df_page = None

            for table in dfs:
                table = table.dropna(how="all")
                first_col = table.iloc[:, 0].astype(str)
                has_date = first_col.str.contains(
                    r"\d{4}\.\d{2}\.\d{2}",
                    regex=True,
                ).any()

                if has_date and table.shape[1] >= 9:
                    df_page = table.iloc[:, :9].copy()
                    break

            if df_page is None:
                continue

            df_page.columns = [
                "날짜", "종가", "전일비", "등락률", "거래량",
                "기관_순매매", "외국인_순매매", "보유주수", "보유율",
            ]

            df_page = df_page.dropna(subset=["날짜"])
            df_page["날짜"] = pd.to_datetime(
                df_page["날짜"],
                format="%Y.%m.%d",
                errors="coerce",
            )
            df_page = df_page.dropna(subset=["날짜"])

            if df_page["날짜"].max() < start_dt:
                break

            df_page = df_page[df_page["날짜"] >= start_dt]
            all_dfs.append(df_page)

            time.sleep(0.3)

        except Exception:
            time.sleep(1)
            continue

    if not all_dfs:
        return pd.DataFrame()

    result = pd.concat(all_dfs, ignore_index=True)

    for col in ["종가", "거래량", "기관_순매매", "외국인_순매매", "보유주수"]:
        result[col] = pd.to_numeric(
            result[col].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        )

    result["보유율_%"] = pd.to_numeric(
        result["보유율"].astype(str).str.replace("%", "", regex=False),
        errors="coerce",
    )

    result = result.drop(
        columns=["보유율", "종가", "전일비", "등락률", "거래량"],
        errors="ignore",
    )

    result = (
        result.sort_values("날짜")
        .drop_duplicates(subset=["날짜"])
        .set_index("날짜")
    )

    return result


# =========================
# KIND warning
# =========================

def _set_input_value(driver, element, value: str) -> None:
    """Selenium input 강제 세팅 (JS dispatchEvent 방식)"""
    driver.execute_script(
        """
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """,
        element,
        value,
    )


def _wait_for_download(folder: str, timeout: int = 60) -> str | None:
    """엑셀 파일 다운로드 완료까지 대기 후 경로 반환"""
    end_time = time.time() + timeout

    while time.time() < end_time:
        temp_files = glob.glob(os.path.join(folder, "*.crdownload"))
        excel_files = glob.glob(os.path.join(folder, "*.xls*"))

        if excel_files and not temp_files:
            return max(excel_files, key=os.path.getctime)

        time.sleep(1)

    return None


def fetch_kind_warning_excel(
    url: str,
    start_date: str,
    end_date: str,
    download_dir: str,
) -> str | None:
    """
    KIND 투자경고 페이지에서 엑셀을 다운로드하고 파일 경로를 반환합니다.
    Selenium + ChromeDriver 필요 (pip install selenium webdriver-manager).
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager

    os.makedirs(download_dir, exist_ok=True)

    # 기존 임시 엑셀 파일 정리
    for file in glob.glob(os.path.join(download_dir, "*.xls*")):
        try:
            os.remove(file)
        except Exception as e:
            print(f"[warning] 기존 엑셀 삭제 실패: {file} {e}")

    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--remote-debugging-port=9222")
    options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )

    latest_file = None

    try:
        wait = WebDriverWait(driver, 20)
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']")))

        # --- 날짜 입력창 탐색 ---
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")

        start_input = end_input = None

        selectors = [
            ("input[name='startDate']",  "input[name='endDate']"),
            ("input[id='startDate']",    "input[id='endDate']"),
            ("input[name*='start']",     "input[name*='end']"),
            ("input[id*='start']",       "input[id*='end']"),
            ("input[name*='from']",      "input[name*='to']"),
            ("input[id*='from']",        "input[id*='to']"),
            ("input[name*='strt']",      "input[name*='end']"),
            ("input[id*='strt']",        "input[id*='end']"),
        ]

        for start_sel, end_sel in selectors:
            starts = driver.find_elements(By.CSS_SELECTOR, start_sel)
            ends   = driver.find_elements(By.CSS_SELECTOR, end_sel)
            if starts and ends:
                start_input, end_input = starts[0], ends[0]
                break

        if start_input is None or end_input is None:
            if len(inputs) < 2:
                raise RuntimeError("[warning] 날짜 입력창을 찾지 못했습니다.")
            start_input, end_input = inputs[-2], inputs[-1]

        _set_input_value(driver, start_input, start_date)
        _set_input_value(driver, end_input,   end_date)
        time.sleep(1)

        # --- 검색 실행 ---
        try:
            driver.execute_script("fnSearch1();")
        except Exception:
            search_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[contains(@onclick, 'fnSearch1')]")
                )
            )
            driver.execute_script("arguments[0].click();", search_btn)

        time.sleep(5)

        # --- 엑셀 다운로드 ---
        excel_xpath = """
        //*[contains(text(),'EXCEL') or contains(text(),'Excel') or contains(text(),'엑셀')
         or contains(@title,'EXCEL') or contains(@title,'Excel') or contains(@title,'엑셀')
         or contains(@alt,'EXCEL')   or contains(@alt,'Excel')   or contains(@alt,'엑셀')
         or contains(@class,'excel') or contains(@class,'xls')
         or contains(@onclick,'excel') or contains(@onclick,'xls') or contains(@onclick,'Xls')
         or contains(@href,'excel')    or contains(@href,'xls')]
        """

        clicked = False

        for el in driver.find_elements(By.XPATH, excel_xpath):
            try:
                if el.is_displayed():
                    driver.execute_script("arguments[0].scrollIntoView(true);", el)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", el)
                    clicked = True
                    break
            except Exception:
                continue

        if not clicked:
            for js in [
                "fnDownload();", "fnExcelDownload();", "fnExcel();",
                "fnDownExcel();", "fnSearchExcel();", "fnSaveAsExcel();",
                "fnExcelDown();", "fn_fileDownload();",
            ]:
                try:
                    driver.execute_script(js)
                    clicked = True
                    break
                except Exception:
                    continue

        if not clicked:
            raise RuntimeError("[warning] 엑셀 다운로드 버튼/JS 함수를 찾지 못했습니다.")

        latest_file = _wait_for_download(download_dir, timeout=60)

    finally:
        driver.quit()

    return latest_file
