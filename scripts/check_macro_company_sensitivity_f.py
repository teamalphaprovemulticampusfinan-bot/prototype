from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from macro_agent.feature_builder import build_macro_features
from macro_agent.scorer import calculate_macro_score


def build_synthetic_macro_frames() -> dict[str, pd.DataFrame]:
    dates = pd.bdate_range("2025-01-01", periods=90)
    ecos_daily = pd.DataFrame(
        {
            "date": dates,
            "원달러": [1300 + i * 0.9 for i in range(len(dates))],
            "국고채_10년": [3.0 + i * 0.01 for i in range(len(dates))],
            "국고채_3년": [2.8 + i * 0.012 for i in range(len(dates))],
            "신용스프레드_bbb-": [2.5 + i * 0.01 for i in range(len(dates))],
            "신용스프레드_aa-": [0.8 + i * 0.003 for i in range(len(dates))],
        }
    )
    ext_daily = pd.DataFrame(
        {
            "date": dates,
            "달러인덱스_dxy": [100 + i * 0.04 for i in range(len(dates))],
            "미국_국채_10년": [4.0 + i * 0.006 for i in range(len(dates))],
            "미국_국채_13주": [4.8 + i * 0.002 for i in range(len(dates))],
            "유가_평균": [75 + i * 0.08 for i in range(len(dates))],
            "천연가스": [2.5 + i * 0.01 for i in range(len(dates))],
            "구리": [8500 + i * 3 for i in range(len(dates))],
            "hbm_memory_proxy": [100 + i * 0.3 for i in range(len(dates))],
        }
    )
    regulation = pd.DataFrame(
        {
            "date": dates[-30:],
            "title": ["BIS export control semiconductor manufacturing equipment restriction"] * 30,
            "summary": ["advanced semiconductor equipment export control and Entity List regulation"] * 30,
        }
    )
    return {"ecos_일별": ecos_daily, "ext_일별": ext_daily, "규제": regulation}


def main() -> int:
    parser = argparse.ArgumentParser(description="F. 기업별 macro 민감도 기준 패치 동작 확인")
    parser.add_argument("--company-dir", default="nepes")
    parser.add_argument("--company", default="네패스")
    args = parser.parse_args()

    feature_data = build_macro_features(build_synthetic_macro_frames())
    result = calculate_macro_score(
        feature_data,
        company_dir=args.company_dir,
        company=args.company,
    )
    sensitivity = result.get("company_macro_sensitivity") or {}
    print("[OK] calculate_macro_score completed")
    print("[score]", result.get("score"))
    print("[company_sensitivity_score]", sensitivity.get("score"))
    print(json.dumps(sensitivity, ensure_ascii=False, indent=2)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
