import re
import zipfile
from io import BytesIO

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup


# =========================
# 공통
# =========================

def _to_number(value):
    if value is None:
        return None

    value = str(value).replace(",", "").replace(" ", "")

    if value in ["", "-", "　", "nan", "None"]:
        return 0

    try:
        return float(value)
    except Exception:
        return None


# =========================
# warning
# =========================

def normalize_warning(new_df: pd.DataFrame) -> pd.DataFrame:
    cols = ["회사명", "종목코드", "구분", "지정일", "해제일", "비고"]

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

    return new_df


def merge_warning(old_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    final_df = pd.concat([old_df, new_df], ignore_index=True)

    final_df = final_df.drop_duplicates(
        subset=["종목코드", "구분", "지정일"],
        keep="last",
    )

    return final_df


# =========================
# financial
# =========================

def normalize_financials(raw: dict, year: int) -> dict:
    df = pd.DataFrame(raw.get("list", []))

    def get_amount(patterns):
        for pattern in patterns:
            temp = df[df["account_nm"].str.contains(pattern, na=False, regex=True)]
            if not temp.empty:
                return temp.iloc[0].get("thstrm_amount")
        return None

    result = {
        "year": year,
        "sales": get_amount([r"^매출액$", r"^매출$", r"^영업수익$"]),
        "operating_income": get_amount([r"^영업이익$"]),
        "net_income": get_amount([r"^당기순이익\(손실\)$", r"^당기순이익$", r"당기순이익"]),
        "total_assets": get_amount([r"^자산총계$"]),
        "total_liabilities": get_amount([r"^부채총계$"]),
        "total_equity": get_amount([r"^자본총계$"]),
        "current_assets": get_amount([r"^유동자산$"]),
        "current_liabilities": get_amount([r"^유동부채$"]),
    }

    for key, value in result.items():
        if key != "year":
            result[key] = _to_number(value)

    return result


def normalize_capex_ocf(raw: dict):
    if not raw:
        return None, None

    df = pd.DataFrame(raw.get("list", []))
    if df.empty or "sj_div" not in df.columns:
        return None, None

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
            errors="coerce",
        )

        return values.sum()

    capex_val = extract_sum([
        r"유형자산.*취득",
        r"무형자산.*취득",
        r"유무형자산.*취득",
    ])

    ocf_val = extract_sum([
        r"영업활동.*현금흐름",
    ])

    return abs(capex_val) if capex_val else None, ocf_val


def normalize_interest(raw_cfs: dict, raw_ofs: dict = None):
    for raw in [raw_cfs, raw_ofs]:
        if not raw:
            continue

        df = pd.DataFrame(raw.get("list", []))
        if df.empty:
            continue

        patterns = [
            r"이자비용",
            r"차입금.*이자",
            r"사채.*이자",
            r"지급이자",
            r"금융원가",
            r"금융비용",
        ]

        for pattern in patterns:
            temp = df[df["account_nm"].str.contains(pattern, na=False, regex=True)]
            if not temp.empty:
                return _to_number(temp.iloc[0].get("thstrm_amount"))

    return None


def _extract_xml_text(zip_bytes):
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        xml_name = zf.namelist()[0]
        raw = zf.read(xml_name).decode("utf-8", errors="ignore")
        soup = BeautifulSoup(raw, "xml")
        return soup.get_text("\n", strip=True)


def _extract_xml_tables(zip_bytes):
    tables = []

    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        for xml_name in zf.namelist():
            raw = zf.read(xml_name).decode("utf-8", errors="ignore")
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

    return tables


def normalize_amortization(zip_bytes, year: int) -> dict:
    if not zip_bytes:
        return {
            "amort_cogs": None,
            "amort_sga": None,
            "amort_total": None,
        }

    try:
        tables = _extract_xml_tables(zip_bytes)

        for rows in tables:
            table_text = " ".join(" ".join(row) for row in rows)

            if not re.search(r"기타\s*상각비|영업권\s*이외의\s*무형자산|무형자산", table_text):
                continue

            if not re.search(r"매출원가|판매비|일반관리비|기능별|항목", table_text):
                continue

            for row in rows:
                row_text = " ".join(row)

                if not re.search(r"기타\s*상각비|영업권\s*이외의\s*무형자산", row_text):
                    continue

                nums = [_to_number(x) for x in row]
                nums = [x for x in nums if x is not None]

                if len(nums) >= 3:
                    return {
                        "amort_cogs": nums[-3] * 1000,
                        "amort_sga": nums[-2] * 1000,
                        "amort_total": nums[-1] * 1000,
                    }

                if len(nums) == 2:
                    return {
                        "amort_cogs": 0,
                        "amort_sga": nums[-2] * 1000,
                        "amort_total": nums[-1] * 1000,
                    }

    except Exception:
        pass

    return {
        "amort_cogs": None,
        "amort_sga": None,
        "amort_total": None,
    }


def normalize_rnd_from_xml(zip_bytes, year: int):
    if not zip_bytes:
        return None

    try:
        text = _extract_xml_text(zip_bytes)
        lines = text.splitlines()

        num_pattern = re.compile(r"\(?-?\d[\d,]*\)?")

        keyword_patterns = [
            r"연구\s*개발\s*비",
            r"연구\s*개발\s*비용",
            r"경상\s*연구\s*개발\s*비",
            r"개발\s*비",
            r"R\s*&\s*D",
        ]

        for i, line in enumerate(lines):
            if not any(re.search(p, line, re.IGNORECASE) for p in keyword_patterns):
                continue

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
                except Exception:
                    pass

            parsed = [v for v in parsed if v >= 1_000_000_000]

            if parsed:
                return min(parsed)

    except Exception:
        pass

    return None


def compute_financial_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    for col in df.columns:
        if col != "year":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["roe"] = df["net_income"] / df["total_equity"] * 100

    df["operating_margin"] = (
        df["operating_income"] / df["sales"] * 100
    )

    df["current_ratio_%"] = (
        df["current_assets"] / df["current_liabilities"] * 100
    )
    df["debt_ratio"] = (
        df["total_liabilities"] / df["total_equity"] * 100
    )
    df["interest_coverage"] = (
        df["operating_income"] / df["interest_expense"]
    )
    df["sales_growth"] = df["sales"].pct_change() * 100
    return df


# =========================
# stock
# =========================

def normalize_stock_price(df: pd.DataFrame, price_col: str = "Close") -> pd.DataFrame:
    df = df.copy()
    df["Return"] = df[price_col].pct_change()
    return df


def normalize_market_return(
    df: pd.DataFrame,
    mkt: pd.DataFrame,
    price_col: str = "Close",
) -> pd.DataFrame:
    df = df.copy()
    mkt = mkt.copy()

    mkt = mkt[[price_col]].rename(columns={price_col: "Market_Close"})
    mkt["market_return"] = mkt["Market_Close"].pct_change()

    df = df.join(mkt[["Market_Close", "market_return"]], how="left")
    df["market_return"] = df["market_return"].ffill()
    df["ABNRET"] = df["Return"] - df["market_return"]

    return df


def normalize_volatility(
    df: pd.DataFrame,
    vix_df: pd.DataFrame,
    vkospi_df: pd.DataFrame,
    price_col: str = "Close",
) -> pd.DataFrame:
    df = df.copy()
    df.index = pd.to_datetime(df.index).normalize()

    # VIX 처리
    if vix_df is not None and not vix_df.empty and price_col in vix_df.columns:
        vix_df = vix_df.copy()
        vix_df.index = pd.to_datetime(vix_df.index).normalize()

        vix = vix_df[[price_col]].rename(columns={price_col: "VIX"})
        df = df.join(vix, how="left")
    else:
        df["VIX"] = np.nan

    # VKOSPI 처리
    if vkospi_df is not None and not vkospi_df.empty and price_col in vkospi_df.columns:
        vkospi_df = vkospi_df.copy()
        vkospi_df.index = pd.to_datetime(vkospi_df.index).normalize()

        vkospi = vkospi_df[[price_col]].rename(columns={price_col: "VKOSPI"})
        df = df.join(vkospi, how="left")
    else:
        df["VKOSPI"] = np.nan

    df[["VIX", "VKOSPI"]] = (
        df[["VIX", "VKOSPI"]]
        .ffill()
        .bfill()
    )

    return df


def normalize_car(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    cum = (1 + df["Return"]).cumprod()
    peak = cum.cummax()

    df["MDD"] = (cum - peak) / peak

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA60"] = df["Close"].rolling(60).mean()
    df["MA20_ratio"] = df["Close"] / df["MA20"]
    df["MA60_ratio"] = df["Close"] / df["MA60"]

    df["CAR_3"] = df["ABNRET"].rolling(3).sum()
    df["CAR_5"] = df["ABNRET"].rolling(5).sum()

    return df


def normalize_eps_psr(
    df: pd.DataFrame,
    df_dart: pd.DataFrame,
    shares: float,
    price_col: str = "Close",
) -> pd.DataFrame:
    df = df.copy()

    if df_dart is None or df_dart.empty or pd.isna(shares):
        df["EPS"] = np.nan
        df["PSR"] = np.nan
        return df

    quarter_end_map = {
        "1Q": "-03-31",
        "2Q": "-06-30",
        "3Q": "-09-30",
        "4Q": "-12-31",
    }

    df_dart = df_dart.copy()

    df_dart["date"] = pd.to_datetime(
        df_dart["year"].astype(str) + df_dart["quarter"].map(quarter_end_map)
    )

    df_dart = df_dart.set_index("date").sort_index()

    df_dart["ttm_net_income"] = df_dart["net_income"].rolling(4).sum()
    df_dart["ttm_revenue"] = df_dart["revenue"].rolling(4).sum()

    df_dart["EPS"] = df_dart["ttm_net_income"] / shares

    mktcap_q = df[price_col].reindex(df_dart.index, method="nearest") * shares
    df_dart["PSR"] = mktcap_q / df_dart["ttm_revenue"]

    df = df.join(df_dart["EPS"], how="left")
    df = df.join(df_dart["PSR"], how="left")

    df["EPS"] = df["EPS"].ffill()
    df["PSR"] = df["PSR"].ffill()

    return df


def normalize_supply(df: pd.DataFrame, df_supply: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    supply_cols = ["기관_순매매", "외국인_순매매", "보유주수", "보유율_%"]

    if df_supply is None or df_supply.empty:
        for col in supply_cols:
            df[col] = np.nan
        return df

    df_supply = df_supply.copy()
    df_supply.index = pd.to_datetime(df_supply.index)
    df_supply.columns = df_supply.columns.str.strip()

    df = df.drop(columns=supply_cols, errors="ignore")
    df = df.join(df_supply, how="left")

    df[supply_cols] = df[supply_cols].ffill()

    return df


def rename_stock_columns(
    df: pd.DataFrame,
    shares: float,
    price_col: str = "Close",
) -> pd.DataFrame:
    df = df.copy()

    rename_dict = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
        "Return": "return",
        "Market_Close": "market_close",
        "market_return": "market_return",
        "ABNRET": "abnormal_return",
        "MDD": "mdd",
        "MA20": "ma20",
        "MA60": "ma60",
        "MA20_ratio": "ma20_ratio",
        "MA60_ratio": "ma60_ratio",
        "VIX": "vix",
        "VKOSPI": "vkospi",
        "EPS": "eps",
        "PSR": "psr",
        "CAR_3": "car_3",
        "CAR_5": "car_5",
        "기관_순매매": "inst_net_buy",
        "외국인_순매매": "foreign_net_buy",
        "보유주수": "foreign_holding_shares",
        "보유율_%": "foreign_holding_pct",
    }

    df = df.rename(columns=rename_dict)

    if not pd.isna(shares) and "close" in df.columns:
        df["market_cap"] = df["close"] * shares
    else:
        df["market_cap"] = np.nan

    return df