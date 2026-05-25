# src/data_intake/finance_intake/validator.py
"""
정규화된 데이터의 품질을 검증합니다.
이상값, 누락값, 비즈니스 룰 위반 여부를 반환합니다.
"""

import pandas as pd


# =========================
# 경고 데이터 검증
# =========================

def validate_warning(df: pd.DataFrame) -> list[str]:
    """경고 데이터 품질 검증. 문제 메시지 리스트 반환"""
    issues = []

    null_codes = df["종목코드"].isna().sum()
    if null_codes > 0:
        issues.append(f"종목코드 누락 {null_codes}건")

    null_dates = df["지정일"].isna().sum()
    if null_dates > 0:
        issues.append(f"지정일 누락 {null_dates}건")

    dupes = df.duplicated(subset=["종목코드", "구분", "지정일"]).sum()
    if dupes > 0:
        issues.append(f"중복 행 {dupes}건 (종목코드+구분+지정일 기준)")

    return issues


# =========================
# 재무제표 데이터 검증
# =========================

def validate_financials(rows: list[dict]) -> list[str]:
    """재무제표 데이터 검증. 문제 메시지 리스트 반환"""
    issues = []

    if not rows:
        issues.append("수집된 재무 데이터가 없습니다.")
        return issues

    for row in rows:
        year = row.get("year")
        if row.get("sales") is None:
            issues.append(f"{year}: 매출액 없음")
        if row.get("total_equity") is None:
            issues.append(f"{year}: 자본총계 없음")
        if row.get("rnd") is None:
            issues.append(f"{year}: R&D 비용 없음 (CSV + XML 모두 미발견)")

    return issues


# =========================
# 주가 데이터 검증
# =========================

def validate_stock(df: pd.DataFrame) -> list[str]:
    """주가 DataFrame 검증. 문제 메시지 리스트 반환"""

    issues = []

    if df.empty:
        issues.append("stock dataframe is empty")
        return issues

    # close
    if "close" in df.columns:
        null_close = df["close"].isna().sum()
    elif "Close" in df.columns:
        null_close = df["Close"].isna().sum()
    else:
        null_close = len(df)

    if null_close > 0:
        issues.append(f"close missing: {null_close}")

    # eps
    if "eps" in df.columns and df["eps"].isna().all():
        issues.append("eps fully missing")

    # psr
    if "psr" in df.columns and df["psr"].isna().all():
        issues.append("psr fully missing")

    # supply
    supply_cols = [
        "inst_net_buy",
        "foreign_net_buy",
    ]

    for col in supply_cols:
        if col in df.columns and df[col].isna().all():
            issues.append(f"{col} fully missing")

    return issues

# =========================
# 공통 출력 헬퍼
# =========================

def report_issues(label: str, issues: list[str]) -> None:
    if not issues:
        print(f"[{label}] 검증 통과 ✓")
    else:
        print(f"[{label}] 검증 경고 {len(issues)}건:")
        for msg in issues:
            print(f"  - {msg}")