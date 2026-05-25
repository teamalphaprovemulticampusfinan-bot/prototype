# src/data_intake/finance_intake/warning.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from datetime import datetime, timedelta
import pandas as pd
import os
import time
import glob


# ===============================
# 설정
# ===============================

MODE = "update"   # "update" 또는 "overwrite"
DAYS = 1

URL = "https://kind.krx.co.kr/investwarn/investattentwarnrisky.do?method=investattentwarnriskyMain"


# ===============================
# 경로 설정
# ===============================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)

download_dir = os.path.join(BASE_DIR, "data", "finance_data", "warning_data")
os.makedirs(download_dir, exist_ok=True)

csv_path = os.path.join(download_dir, "warning_data.csv")
json_path = os.path.join(download_dir, "warning_data.json")


# ===============================
# 날짜 설정
# ===============================

today = datetime.today()
start = today - timedelta(days=DAYS)

start_date = start.strftime("%Y-%m-%d")
end_date = today.strftime("%Y-%m-%d")

print("조회 기간:", start_date, "~", end_date)
print("다운로드 경로:", download_dir)


# ===============================
# 기존 임시 엑셀 파일 정리
# ===============================

for file in glob.glob(os.path.join(download_dir, "*.xls*")):
    try:
        os.remove(file)
    except Exception as e:
        print("기존 엑셀 삭제 실패:", file, e)


# ===============================
# 다운로드 대기 함수
# ===============================

def wait_for_download(folder, timeout=60):
    end_time = time.time() + timeout

    while time.time() < end_time:
        temp_files = glob.glob(os.path.join(folder, "*.crdownload"))
        excel_files = glob.glob(os.path.join(folder, "*.xls*"))

        if excel_files and not temp_files:
            return max(excel_files, key=os.path.getctime)

        time.sleep(1)

    return None


# ===============================
# 입력값 강제 세팅 함수
# ===============================

def set_input_value(driver, element, value):
    driver.execute_script(
        """
        arguments[0].value = arguments[1];
        arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
        arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """,
        element,
        value,
    )


# ===============================
# KIND 데이터 다운로드
# ===============================

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
    options=options
)

latest_file = None

try:
    wait = WebDriverWait(driver, 20)

    driver.get(URL)

    wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
    )

    # ===============================
    # 날짜 입력창 찾기
    # ===============================

    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
    print("text input 개수:", len(inputs))

    for i, inp in enumerate(inputs):
        print(
            i,
            "id=", inp.get_attribute("id"),
            "name=", inp.get_attribute("name"),
            "value=", inp.get_attribute("value"),
            "class=", inp.get_attribute("class"),
        )

    start_input = None
    end_input = None

    selectors = [
        ("input[name='startDate']", "input[name='endDate']"),
        ("input[id='startDate']", "input[id='endDate']"),
        ("input[name*='start']", "input[name*='end']"),
        ("input[id*='start']", "input[id*='end']"),
        ("input[name*='from']", "input[name*='to']"),
        ("input[id*='from']", "input[id*='to']"),
        ("input[name*='strt']", "input[name*='end']"),
        ("input[id*='strt']", "input[id*='end']"),
    ]

    for start_sel, end_sel in selectors:
        starts = driver.find_elements(By.CSS_SELECTOR, start_sel)
        ends = driver.find_elements(By.CSS_SELECTOR, end_sel)

        if starts and ends:
            start_input = starts[0]
            end_input = ends[0]
            print("날짜 selector 사용:", start_sel, end_sel)
            break

    if start_input is None or end_input is None:
        if len(inputs) < 2:
            raise RuntimeError("날짜 입력창을 찾지 못했습니다.")

        print("명확한 날짜 selector를 못 찾아 마지막 2개 input 사용")
        start_input = inputs[-2]
        end_input = inputs[-1]

    # 날짜 입력
    set_input_value(driver, start_input, start_date)
    set_input_value(driver, end_input, end_date)

    time.sleep(1)

    print("입력된 시작일:", start_input.get_attribute("value"))
    print("입력된 종료일:", end_input.get_attribute("value"))

    # ===============================
    # 검색 실행
    # ===============================

    print("검색 실행 중...")

    try:
        driver.execute_script("fnSearch1();")
        print("fnSearch1() 실행 완료")
    except Exception as e:
        print("fnSearch1() 실패:", e)
        print("검색 버튼 클릭 방식으로 재시도")

        search_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[contains(@onclick, 'fnSearch1')]")
            )
        )
        driver.execute_script("arguments[0].click();", search_btn)

    time.sleep(5)

    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    print("검색 후 table row 수:", len(rows))
    print("검색 후 첫 행:", rows[0].text if rows else "없음")

    # ===============================
    # 엑셀 다운로드 실행
    # ===============================

    print("엑셀 다운로드 실행 중...")

    # 우선 실제 EXCEL 버튼 찾기
    excel_xpath = """
    //*[contains(text(), 'EXCEL')
    or contains(text(), 'Excel')
    or contains(text(), '엑셀')
    or contains(@title, 'EXCEL')
    or contains(@title, 'Excel')
    or contains(@title, '엑셀')
    or contains(@alt, 'EXCEL')
    or contains(@alt, 'Excel')
    or contains(@alt, '엑셀')
    or contains(@class, 'excel')
    or contains(@class, 'Excel')
    or contains(@class, 'xls')
    or contains(@onclick, 'excel')
    or contains(@onclick, 'Excel')
    or contains(@onclick, 'xls')
    or contains(@onclick, 'Xls')
    or contains(@href, 'excel')
    or contains(@href, 'xls')]
    """

    excel_candidates = driver.find_elements(By.XPATH, excel_xpath)

    for i, el in enumerate(excel_candidates):
        print(
            "엑셀 후보:",
            i,
            "tag=", el.tag_name,
            "text=", el.text.strip(),
            "title=", el.get_attribute("title"),
            "alt=", el.get_attribute("alt"),
            "class=", el.get_attribute("class"),
            "onclick=", el.get_attribute("onclick"),
            "href=", el.get_attribute("href"),
            "src=", el.get_attribute("src"),
        )

    clicked = False

    for el in excel_candidates:
        try:
            if el.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView(true);", el)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", el)
                print("엑셀 버튼 클릭 완료")
                clicked = True
                break
        except Exception as e:
            print("엑셀 후보 클릭 실패:", e)

    # 버튼 클릭 실패 시 KIND에서 자주 쓰는 JS 함수 직접 호출
    if not clicked:
        print("엑셀 버튼 직접 클릭 실패, JS 함수 호출 시도")

        excel_js_candidates = [
            "fnDownload();",
            "fnExcelDownload();",
            "fnExcel();",
            "fnDownExcel();",
            "fnSearchExcel();",
            "fnSaveAsExcel();",
            "fnExcelDown();",
            "fn_fileDownload();",
        ]

        for js in excel_js_candidates:
            try:
                driver.execute_script(js)
                print("엑셀 JS 호출 성공:", js)
                clicked = True
                break
            except Exception as e:
                print("엑셀 JS 호출 실패:", js, e)

    if not clicked:
        print("전체 버튼 디버깅 출력")
        buttons = driver.find_elements(By.XPATH, "//a | //button | //input | //span | //img")

        for i, el in enumerate(buttons):
            print(
                i,
                "tag=", el.tag_name,
                "text=", el.text.strip(),
                "title=", el.get_attribute("title"),
                "alt=", el.get_attribute("alt"),
                "class=", el.get_attribute("class"),
                "onclick=", el.get_attribute("onclick"),
                "href=", el.get_attribute("href"),
                "src=", el.get_attribute("src"),
            )

        raise RuntimeError("엑셀 다운로드 버튼 또는 JS 함수를 찾지 못했습니다.")

    latest_file = wait_for_download(download_dir, timeout=60)

finally:
    driver.quit()


if latest_file is None:
    raise FileNotFoundError("엑셀 다운로드가 완료되지 않았습니다.")

print("다운로드 파일:", latest_file)


# ===============================
# 엑셀 읽기
# ===============================

try:
    new_df = pd.read_excel(latest_file)
except Exception:
    new_df = pd.read_excel(latest_file, engine="xlrd")

print("엑셀 원본 크기:", new_df.shape)
print("엑셀 원본 컬럼:", list(new_df.columns))

new_df = new_df.dropna(how="all")


# ===============================
# 컬럼명 정리 및 데이터 처리
# ===============================

cols = ["회사명", "종목코드", "구분", "지정일", "해제일", "비고"]

if new_df.empty:
    print("조회된 신규 데이터가 없습니다.")

    if MODE == "update" and os.path.exists(csv_path):
        final_df = pd.read_csv(csv_path, dtype={"종목코드": str})
    else:
        final_df = pd.DataFrame(columns=cols)

else:
    rename_map = {}

    for col in new_df.columns:
        col_str = str(col).strip()

        if "종목" in col_str and "코드" in col_str:
            rename_map[col] = "종목코드"
        elif "회사" in col_str or "종목명" in col_str or "법인명" in col_str:
            rename_map[col] = "회사명"
        elif "구분" in col_str or "조치" in col_str or "유형" in col_str:
            rename_map[col] = "구분"
        elif "지정" in col_str:
            rename_map[col] = "지정일"
        elif "해제" in col_str:
            rename_map[col] = "해제일"
        elif "비고" in col_str or "사유" in col_str:
            rename_map[col] = "비고"

    print("컬럼 rename_map:", rename_map)

    new_df = new_df.rename(columns=rename_map)

    for col in cols:
        if col not in new_df.columns:
            new_df[col] = None

    new_df = new_df[cols].copy()

    new_df["종목코드"] = (
        new_df["종목코드"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.zfill(6)
    )

    new_df.loc[
        new_df["종목코드"].isin(["000nan", "00None", "000000"]),
        "종목코드"
    ] = None

    for date_col in ["지정일", "해제일"]:
        new_df[date_col] = pd.to_datetime(new_df[date_col], errors="coerce")
        new_df[date_col] = new_df[date_col].dt.strftime("%Y-%m-%d")

    print("신규 데이터 크기:", new_df.shape)
    print(new_df.head())

    if MODE == "overwrite":
        final_df = new_df

    elif MODE == "update":
        if os.path.exists(csv_path):
            old_df = pd.read_csv(csv_path, dtype={"종목코드": str})

            for col in cols:
                if col not in old_df.columns:
                    old_df[col] = None

            old_df = old_df[cols].copy()

            final_df = pd.concat([old_df, new_df], ignore_index=True)

            final_df["종목코드"] = (
                final_df["종목코드"]
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.zfill(6)
            )

            final_df.loc[
                final_df["종목코드"].isin(["000nan", "00None", "000000"]),
                "종목코드"
            ] = None

            final_df = final_df.drop_duplicates(
                subset=["종목코드", "구분", "지정일"],
                keep="last"
            )

        else:
            final_df = new_df

    else:
        raise ValueError("MODE는 'update' 또는 'overwrite'만 가능합니다.")


# ===============================
# 최종 저장
# ===============================

final_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
final_df.to_json(json_path, orient="records", force_ascii=False, indent=2)

print("CSV 저장:", csv_path)
print("JSON 저장:", json_path)
print("총 데이터 수:", len(final_df))