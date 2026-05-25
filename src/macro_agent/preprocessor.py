from __future__ import annotations

from typing import Dict
import pandas as pd


def preprocess_macro_data(data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    loader.py에서 읽어온 macro_data dict를 전처리한다.

    처리 내용:
    1. date 컬럼 통일
    2. 날짜 정렬
    3. 중복 제거
    4. 숫자 컬럼 변환
    5. 결측치 보정
    """

    cleaned = {}

    for name, df in data_dict.items():
        print(f"🧹 전처리 중: {name}")

        df = df.copy()

        # 1. 컬럼명 정리
        df.columns = df.columns.str.strip()
        df.columns = df.columns.str.lower()
        # 2. date 컬럼 찾기
        date_col = find_date_column(df)

        if date_col is None:
            print(f"  ⚠️ date 컬럼 없음 → 그대로 저장: {name}")
            cleaned[name] = df
            continue

        # 3. date 컬럼명 통일
        df = df.rename(columns={date_col: "date"})

        # 4. 날짜 변환
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

        # 날짜 변환 실패한 행 제거
        df = df.dropna(subset=["date"])

        # 5. 날짜 정렬
        df = df.sort_values("date")

        # 6. 날짜 중복 제거
        before = len(df)
        df = df.drop_duplicates(subset=["date"], keep="last")
        after = len(df)

        if before != after:
            print(f"  ⚠️ 중복 date 제거: {before - after}개")

        # 7. 숫자 컬럼 변환
        # pandas errors="ignore"는 deprecated라 FutureWarning을 발생시키므로,
        # 변환 성공률이 있는 컬럼만 numeric으로 바꾼다.
        for col in df.columns:
            if col == "date":
                continue
            converted = pd.to_numeric(df[col], errors="coerce")
            if converted.notna().sum() > 0:
                df[col] = converted

        # 8. 결측치 처리
        df = df.ffill()
        df = df.bfill()

        cleaned[name] = df

        print(f"  ✅ 완료: {len(df)}행, {len(df.columns)}컬럼")

    print("\n✅ 전체 전처리 완료")

    return cleaned


def find_date_column(df: pd.DataFrame) -> str | None:
    """
    date 컬럼 후보를 찾아 반환한다.
    """

    candidates = [
        "date",
        "Date",
        "DATE",
        "날짜",
        "기준일",
        "time",
        "TIME",
        "period",
        "Period",
        "PERIOD",
    ]

    for col in candidates:
        if col in df.columns:
            return col

    return None