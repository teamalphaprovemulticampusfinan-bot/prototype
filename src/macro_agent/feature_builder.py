from __future__ import annotations

from typing import Dict, List

import pandas as pd

from .rolling_criteria import add_rolling_criteria_features, is_generated_feature_column


def build_macro_features(data_dict: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    전처리된 macro_data dict를 받아서 분석에 필요한 feature 컬럼을 생성한다.

    기존 feature:
    - 전일/전기간 diff
    - 전일/전기간 pct_change
    - 5/20 이동평균
    - ma5-ma20 trend

    추가 feature(B. 변화율/rolling 기준):
    - 일별: 1/5/20/60영업일 변화율
    - 월별: 1/3/6/12개월 변화율
    - rolling z-score
    - 평균회귀 신호
    - 경험적 분위수 기반 급등/급락 cutoff
    """
    featured: Dict[str, pd.DataFrame] = {}

    for name, df in data_dict.items():
        print(f"🧪 Feature 생성 중: {name}")

        if df is None or df.empty:
            featured[name] = df
            print(f"  ⚠️ 빈 데이터 → feature 생성 생략: {name}")
            continue

        frame = df.copy()

        if "date" not in frame.columns:
            print(f"  ⚠️ date 컬럼 없음 → feature 생성 생략: {name}")
            featured[name] = frame
            continue

        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

        # 숫자 원천 컬럼만 feature 생성한다. 이미 생성된 feature 컬럼은 재귀 생성에서 제외한다.
        numeric_cols: List[str] = []
        for col in frame.columns:
            if col == "date" or is_generated_feature_column(str(col)):
                continue
            s = pd.to_numeric(frame[col], errors="coerce")
            if s.notna().sum() >= 2:
                frame[col] = s
                numeric_cols.append(str(col))

        if not numeric_cols:
            featured[name] = frame
            print(f"  ⚠️ 숫자 원천 컬럼 없음 → 기본 feature 생성 생략: {name}")
            continue

        base_features = {}
        for col in numeric_cols:
            s = pd.to_numeric(frame[col], errors="coerce")

            # 기존 호환 feature
            base_features[f"{col}_diff"] = s.diff()
            base_features[f"{col}_pct_change"] = s.pct_change(fill_method=None)
            base_features[f"{col}_ma5"] = s.rolling(window=5, min_periods=3).mean()
            base_features[f"{col}_ma20"] = s.rolling(window=20, min_periods=10).mean()
            base_features[f"{col}_trend"] = base_features[f"{col}_ma5"] - base_features[f"{col}_ma20"]

        if base_features:
            frame = pd.concat([frame, pd.DataFrame(base_features, index=frame.index)], axis=1)

        # B 기준: 변화율/rolling/z-score/평균회귀/급등급락 cutoff
        frame = add_rolling_criteria_features(frame, dataset_name=name)

        # 결측치 보정: date는 유지, 숫자 feature만 앞뒤 보정한다.
        value_cols = [c for c in frame.columns if c != "date"]
        frame[value_cols] = frame[value_cols].ffill().bfill()

        featured[name] = frame

        rolling_meta = getattr(frame, "attrs", {}).get("rolling_criteria", {}) or {}
        rolling_msg = ""
        if rolling_meta.get("applied", True):
            rolling_msg = (
                f", rolling={rolling_meta.get('frequency', 'unknown')}"
                f"/window={rolling_meta.get('z_window', '-')}"
                f"/cols={rolling_meta.get('source_column_count', '-')}"
            )

        print(f"  ✅ 완료: {len(frame)}행, {len(frame.columns)}컬럼{rolling_msg}")

    print("\n✅ 전체 Feature 생성 완료")
    return featured


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
