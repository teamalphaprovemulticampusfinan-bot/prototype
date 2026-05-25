from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from macro_agent.feature_builder import build_macro_features
from macro_agent.rolling_criteria import score_rolling_criteria


def main() -> None:
    dates = pd.bdate_range("2024-01-01", periods=280)
    df = pd.DataFrame({
        "date": dates,
        "원달러": [1300 + i * 0.15 for i in range(280)],
        "국고채_10년": [3.2 + i * 0.002 for i in range(280)],
        "나스닥": [15000 + i * 8 for i in range(280)],
    })

    # 마지막 값에 충격을 주어 flag가 실제로 생성되는지 확인
    df.loc[df.index[-1], "원달러"] = df.loc[df.index[-2], "원달러"] * 1.08

    featured = build_macro_features({"ext_일별": df})["ext_일별"]

    required_cols = [
        "원달러_chg_1bd_pct",
        "원달러_chg_5bd_pct",
        "원달러_chg_20bd_pct",
        "원달러_chg_60bd_pct",
        "원달러_zscore_252bd",
        "원달러_mean_reversion_signal",
        "원달러_shock_flag",
        "원달러_shock_cutoff_upper_99pct",
    ]
    missing = [c for c in required_cols if c not in featured.columns]
    if missing:
        raise AssertionError(f"필수 rolling feature 누락: {missing}")

    score, reasons, details = score_rolling_criteria(featured, dataset_name="ext_일별")
    print("[OK] rolling criteria feature 생성/요약 성공")
    print(json.dumps({
        "score": score,
        "reasons": reasons[:3],
        "triggered_count": details.get("triggered_count"),
        "basis": details.get("basis"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
