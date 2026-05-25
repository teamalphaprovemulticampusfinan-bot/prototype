# 재무제표 수집/분석 코드
import re
import zipfile
from io import BytesIO
from pathlib import Path
import os
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
# =========================
# 설정
# =========================
STOCK_CODE = "014680"
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(r"C:\Users\smile\team-a\src\.env")
API_KEY = os.getenv("DART_API_KEY")
if not API_KEY:
    raise ValueError("DART_API_KEY 없음 (.env 확인)")
YEARS = [2022, 2023, 2024, 2025]
# 사업보고서 주석에서 확인한 연구개발비 보정값
# 단위: 천원 → 원으로 변환
RND_PATH = BASE_DIR / "rnd.csv"

rnd_df = pd.read_csv(RND_PATH, dtype={"stock_code": str})
rnd_df["year"] = rnd_df["year"].astype(int)
rnd_df["rnd"] = pd.to_numeric(rnd_df["rnd"], errors="coerce")
CORP_CODES_PATH = BASE_DIR / "corp_codes.csv"

# =========================
# 기업코드 불러오기
# =========================
corp_df = pd.read_csv(CORP_CODES_PATH, dtype=str)
matched = corp_df[corp_df["stock_code"] == STOCK_CODE]

if matched.empty:
    raise ValueError(f"{STOCK_CODE} 해당 종목 없음")

company = matched.iloc[0]

corp_code = company["corp_code"]
company_name = company["corp_name"]
OUTPUT_PATH = Path(r"C:\Users\smile\team-a\data\finance_data\financial statements_data") / f"{company_name}_재무데이터.csv"

print(f"회사명: {company_name}")
print(f"corp_code: {corp_code}")

#사업보고서 번호 가져오기
def get_business_report_rcept_no(api_key, corp_code, year):
    url = "https://opendart.fss.or.kr/api/list.json"

    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": f"{year}0101",
        "end_de": f"{year}1231",
        "pblntf_ty": "A",
        "pblntf_detail_ty": "A001",
        "page_count": 100
    }

    data = requests.get(url, params=params).json()

    if data.get("status") != "000":
        return None

    items = data.get("list", [])
    if not items:
        return None

    return items[-1]["rcept_no"]
#XML 다운로드
def download_document_zip(api_key, rcept_no):
    url = "https://opendart.fss.or.kr/api/document.xml"

    return requests.get(url, params={
        "crtfc_key": api_key,
        "rcept_no": rcept_no
    }).content

#XML → 텍스트 변환
def extract_xml_text(zip_bytes):
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        xml_name = zf.namelist()[0]
        raw = zf.read(xml_name).decode("utf-8", errors="ignore")
        soup = BeautifulSoup(raw, "xml")
        return soup.get_text("\n", strip=True)
#
def extract_xml_tables(zip_bytes):
    tables = []

    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        for xml_name in zf.namelist():
            raw = zf.read(xml_name).decode("utf-8", errors="ignore")

            # DART XML은 태그 구조가 불안정해서 html.parser가 더 잘 잡힘
            soup = BeautifulSoup(raw, "html.parser")

            for table in soup.find_all("table"):
                rows = []

                for tr in table.find_all("tr"):
                    cells = []

                    for cell in tr.find_all(["th", "td"]):
                        txt = cell.get_text(" ", strip=True)
                        cells.append(txt)

                    if cells:
                        rows.append(cells)

                if rows:
                    tables.append(rows)

    print("추출된 TABLE 수:", len(tables))
    return tables

def to_number(value):
    if value is None:
        return None

    value = str(value).replace(",", "").replace(" ", "")

    if value in ["", "-", "　"]:
        return 0

    try:
        return int(value)
    except:
        return None
    
#무형자산상각비 자동 추출 함수
def get_amortization_by_function(api_key, corp_code, year):
    try:
        rcept_no = get_business_report_rcept_no(api_key, corp_code, year)
        if rcept_no is None:
            return {"amort_cogs": None, "amort_sga": None, "amort_total": None}

        zip_bytes = download_document_zip(api_key, rcept_no)
        tables = extract_xml_tables(zip_bytes)

        for rows in tables:
            table_text = " ".join(" ".join(row) for row in rows)
            if re.search(r"상각|무형|영업권|연구|개발", table_text):
                print(f"\n===== {year} 관련 TABLE =====")
                for row in rows[:20]:
                    print(row)
            # 핵심 키워드 완화
            if not re.search(r"기타\s*상각비|영업권\s*이외의\s*무형자산|무형자산", table_text):
                continue

            if not re.search(r"매출원가|판매비|일반관리비|기능별|항목", table_text):
                continue

            for row in rows:
                row_text = " ".join(row)

                # 이 행만 잡기
                if not re.search(r"기타\s*상각비|영업권\s*이외의\s*무형자산", row_text):
                    continue

                nums = [to_number(x) for x in row]
                nums = [x for x in nums if x is not None]

                print(f"{year} amort 후보 row:", row)
                print(f"{year} amort 후보 nums:", nums)

                if len(nums) >= 3:
                    return {
                        "amort_cogs": nums[-3] * 1000,
                        "amort_sga": nums[-2] * 1000,
                        "amort_total": nums[-1] * 1000
                    }

                if len(nums) == 2:
                    return {
                        "amort_cogs": 0,
                        "amort_sga": nums[-2] * 1000,
                        "amort_total": nums[-1] * 1000
                    }

        return {"amort_cogs": None, "amort_sga": None, "amort_total": None}

    except Exception as e:
        print(f"{year} 무형자산상각비 추출 실패:", e)
        return {"amort_cogs": None, "amort_sga": None, "amort_total": None}
# =========================
# R&D
# =========================
def get_rnd_from_csv(stock_code, year):
    temp = rnd_df[
        (rnd_df["stock_code"] == str(stock_code)) &
        (rnd_df["year"] == int(year))
    ]

    if temp.empty:
        return None

    return temp.iloc[0]["rnd"]

def get_rnd_expense(api_key, corp_code, year):
    try:
        rcept_no = get_business_report_rcept_no(api_key, corp_code, year)
        if rcept_no is None:
            return None

        zip_bytes = download_document_zip(api_key, rcept_no)
        text = extract_xml_text(zip_bytes)

        lines = text.splitlines()
        num_pattern = re.compile(r"\(?-?\d[\d,]*\)?")

        keyword_patterns = [
            r"연구\s*개발\s*비",
            r"연구\s*개발\s*비용",
            r"경상\s*연구\s*개발\s*비",
            r"개발\s*비",
            r"R\s*&\s*D"
        ]

        for i, line in enumerate(lines):
            if not any(re.search(p, line, re.IGNORECASE) for p in keyword_patterns):
                continue

            # 연구개발활동, 연구인력 같은 제목/설명 줄 제외
            if re.search(r"활동|인력|조직|현황|과제|실적", line):
                continue

            window = lines[i:min(len(lines), i + 10)]
            context = " ".join(window)

            nums = num_pattern.findall(context)
            nums = [
                n.replace(",", "").replace("(", "-").replace(")", "")
                for n in nums
            ]

            parsed = []
            for n in nums:
                try:
                    parsed.append(abs(int(n)))
                except:
                    pass

            # 10억 미만은 인원수/건수/비율일 가능성이 커서 제외
            parsed = [v for v in parsed if v >= 1_000_000_000]

            if parsed:
                print(f"{year} RND XML 후보:", line, parsed[:5])
                return min(parsed)

        return None

    except Exception as e:
        print(f"{year} RND XML 추출 실패:", e)
        return None

# =========================
# 재무제표
# =========================
def get_financials(api_key, corp_code, year):
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"

    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": "11011",
        "fs_div": "CFS"
    }

    data = requests.get(url, params=params).json()

    if data.get("status") != "000":
        return None

    df = pd.DataFrame(data.get("list", []))

    def get_amount(patterns):
        for pattern in patterns:
            temp = df[df["account_nm"].str.contains(pattern, na=False, regex=True)]
            if not temp.empty:
                return temp.iloc[0]["thstrm_amount"]
        return None

    return {
        "year": year,
        "sales": get_amount([r"^매출액$", r"^매출$", r"^영업수익$"]),
        "operating_income": get_amount([r"^영업이익$"]),
        "net_income": get_amount([r"^당기순이익\(손실\)$", r"^당기순이익$", r"당기순이익"]),
        "total_assets": get_amount([r"^자산총계$"]),
        "total_liabilities": get_amount([r"^부채총계$"]),
        "total_equity": get_amount([r"^자본총계$"]),
    }

# =========================
# CAPEX / OCF
# =========================
def get_capex_ocf(api_key, corp_code, year):
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"

    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": str(year),
        "reprt_code": "11011",
        "fs_div": "CFS"
    }

    data = requests.get(url, params=params).json()

    if data.get("status") != "000":
        return None, None

    df = pd.DataFrame(data.get("list", []))
    df_cf = df[df["sj_div"] == "CF"]

    def extract_sum(patterns):
        temp_all = pd.DataFrame()

        for p in patterns:
            temp = df_cf[df_cf["account_nm"].str.contains(p, na=False, regex=True)]
            if not temp.empty:
                temp_all = pd.concat([temp_all, temp])

        if temp_all.empty:
            return None

        values = pd.to_numeric(
            temp_all["thstrm_amount"].astype(str).str.replace(",", "", regex=False),
            errors="coerce"
        )

        return values.sum()

    capex_val = extract_sum([
        r"유형자산.*취득",
        r"무형자산.*취득",
        r"유무형자산.*취득"
    ])

    ocf_val = extract_sum([
        r"영업활동.*현금흐름"
    ])

    return abs(capex_val) if capex_val else None, ocf_val

# =========================
# 이자비용
# =========================
def get_interest(api_key, corp_code, year):
    url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"

    for fs_type in ["CFS", "OFS"]:
        params = {
            "crtfc_key": api_key,
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": "11011",
            "fs_div": fs_type
        }

        data = requests.get(url, params=params).json()
        if data.get("status") != "000":
            continue

        df = pd.DataFrame(data.get("list", []))
        if df.empty:
            continue

        patterns = [
            r"이자비용",
            r"차입금.*이자",
            r"사채.*이자",
            r"지급이자",
            r"금융원가",
            r"금융비용"
        ]

        for pattern in patterns:
            temp = df[df["account_nm"].str.contains(pattern, na=False)]
            if not temp.empty:
                return temp.iloc[0]["thstrm_amount"]

    return None
# =========================
# 메인
# =========================
rows = []

for y in YEARS:
    fin = get_financials(API_KEY, corp_code, y)
    if not fin:
        print(f"{y} 재무데이터 없음 - 스킵")
        continue

    rnd = get_rnd_from_csv(STOCK_CODE, y)
    amort = None
    if rnd is None:
        rnd = get_rnd_expense(API_KEY, corp_code, y)

    if amort is None:
        amort = get_amortization_by_function(API_KEY, corp_code, y) or {
            "amort_cogs": None,
            "amort_sga": None,
            "amort_total": None
        }

    print(f"{y} amort:", amort)
    capex, ocf = get_capex_ocf(API_KEY, corp_code, y)
    interest = get_interest(API_KEY, corp_code, y)

    fin["rnd"] = rnd
    fin["capex"] = capex
    fin["ocf"] = ocf
    fin["fcf"] = (ocf or 0) - (capex or 0)
    fin["interest"] = interest

    rows.append(fin)
df = pd.DataFrame(rows)

# 숫자 변환
for col in df.columns:
    if col != "year":
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "", regex=False),
            errors="coerce"
        )

# 지표 계산
df["ROE"] = df["net_income"] / df["total_equity"] * 100
df["영업이익률"] = df["operating_income"] / df["sales"] * 100
df["부채비율"] = df["total_liabilities"] / df["total_equity"] * 100
df["이자보상배율"] = df["operating_income"] / df["interest"]
df["sales_growth"] = df["sales"].pct_change() * 100
print(df)

df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
print("저장 완료:", OUTPUT_PATH)