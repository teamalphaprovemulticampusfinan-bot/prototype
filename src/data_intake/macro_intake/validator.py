# validator.py

import pandas as pd

from .schemas import SCHEMAS, REQUIRED_COLUMNS, VALUE_RANGES


def validate_not_empty(df, name="data"):
    if df is None or df.empty:
        raise ValueError(f"❌ {name} 데이터가 비어 있습니다.")


def validate_schema_name(schema_name):
    if schema_name not in SCHEMAS:
        raise ValueError(f"❌ 알 수 없는 schema_name: {schema_name}")


def validate_columns(df, schema_name):
    expected_columns = SCHEMAS[schema_name]

    missing = [col for col in expected_columns if col not in df.columns]

    if missing:
        print(f"⚠️ {schema_name} 일부 컬럼 누락: {missing}")
        # 추가 진단: 누락된 컬럼의 카테고리 분석
        market_cols = [c for c in missing if any(x in c for x in ['지수', '수익률', '변동성', '모멘텀', 'risk_off', '스프레드'])]
        if market_cols:
            print(f"   → 시장 지수 관련 누락 ({len(market_cols)}): pykrx/Yahoo 수집 실패 가능성")


def validate_required_columns(df, schema_name):
    required = REQUIRED_COLUMNS.get(schema_name, [])

    missing = [col for col in required if col not in df.columns]

    if missing:
        raise ValueError(f"❌ {schema_name} 필수 컬럼 누락: {missing}")


def validate_date_column(df, schema_name):
    if "date" not in df.columns:
        raise ValueError(f"❌ {schema_name} date 컬럼이 없습니다.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    if df["date"].isna().any():
        print(f"⚠️ {schema_name} date 컬럼에 변환 실패 값이 있습니다.")


def validate_duplicate_dates(df, schema_name):
    if "date" not in df.columns:
        return

    duplicated_count = df["date"].duplicated().sum()

    if duplicated_count > 0:
        print(f"⚠️ {schema_name} date 중복 {duplicated_count}개 발견")


def validate_value_ranges(df, schema_name):
    for col, (min_value, max_value) in VALUE_RANGES.items():
        if col not in df.columns:
            continue

        numeric_col = pd.to_numeric(df[col], errors="coerce")
        invalid_idx = (numeric_col < min_value) | (numeric_col > max_value)
        invalid = df[invalid_idx]

        if not invalid.empty:
            invalid_count = len(invalid)
            pct = (invalid_count / len(df)) * 100 if len(df) > 0 else 0
            print(f"⚠️ {schema_name} {col} 이상값 {invalid_count}개 발견 ({pct:.1f}%)")
            if invalid_count <= 5:
                sample_vals = invalid[col].dropna().head(3).tolist()
                print(f"   → 샘플값: {sample_vals}")


def validate_text_columns(df, schema_name):
    text_columns = ["title", "url", "source", "domain", "category", "country", "type"]

    for col in text_columns:
        if col in df.columns:
            empty_count = df[col].astype(str).str.strip().eq("").sum()

            if empty_count > 0:
                print(f"⚠️ {schema_name} {col} 빈 값 {empty_count}개 발견")


def validate_dataset(df, schema_name):
    """
    사용 예:
    validate_dataset(df_daily, "ecos_daily")
    validate_dataset(df_daily_ext, "ext_daily")
    validate_dataset(df_news, "news")
    validate_dataset(df_reg, "regulation")
    """

    validate_schema_name(schema_name)
    validate_not_empty(df, schema_name)

    df = df.copy()

    validate_required_columns(df, schema_name)
    validate_columns(df, schema_name)

    if "date" in df.columns:
        validate_date_column(df, schema_name)
        validate_duplicate_dates(df, schema_name)

    validate_value_ranges(df, schema_name)

    if schema_name in ["news", "regulation", "helium"]:
        validate_text_columns(df, schema_name)

    print(f"✅ {schema_name} 데이터 검증 완료")