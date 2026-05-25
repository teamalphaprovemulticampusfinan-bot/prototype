# src/market_agent/excel_exporter.py
from __future__ import annotations
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd

DB_PATH    = Path(__file__).resolve().parents[2] / "data" / "market_issues.db"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "market_excel"
REPO_ROOT  = Path(__file__).resolve().parents[2]


def export_market_excel(reports: dict) -> str:
    """LLM 분석 결과만 Excel로 저장"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for company, report in reports.items():
        if isinstance(report, dict):
            analysis = report.get("raw_payload", {}).get("analysis", {})
            scoring  = analysis.get("scoring", {})
            
            rows.append({
                "거시환경":       scoring.get("거시환경",  {}).get("score", 0),
                "거시환경_근거":   scoring.get("거시환경",  {}).get("reason", ""),
                "산업매력도":     scoring.get("산업매력도", {}).get("score", 0),
                "산업매력도_근거": scoring.get("산업매력도", {}).get("reason", ""),
                "경쟁위치":       scoring.get("경쟁위치",  {}).get("score", 0),
                "경쟁위치_근거":   scoring.get("경쟁위치",  {}).get("reason", ""),
                "정책수혜":       scoring.get("정책수혜",  {}).get("score", 0),
                "정책수혜_근거":   scoring.get("정책수혜",  {}).get("reason", ""),
                "시장모멘텀":     scoring.get("시장모멘텀", {}).get("score", 0),
                "시장모멘텀_근거": scoring.get("시장모멘텀", {}).get("reason", ""),
            })
        else:
            rows.append({"기업명": company, "투자의견": "보유", "총점": 0})

    companies_str = "_".join(list(reports.keys())[:2])
    fname = f"market_report_{companies_str}.xlsx"
    fpath = OUTPUT_DIR / fname

    pd.DataFrame(rows).to_excel(str(fpath), index=False)
    print(f"✅ Excel 생성: {fpath}")
    _upload_to_github(str(fpath))
    return str(fpath)


def export_final_excel(reports: dict) -> str:
    """LLM 분석 + DART + NTIS 데이터 합쳐서 파이널 Excel 저장"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # LLM 분석 결과
    llm_rows = []
    for company, report in reports.items():
        if isinstance(report, dict):
            analysis = (
                report.get("raw_payload", {}).get("analysis", {})
                or report.get("analysis", {})
                or {}
            )
            scoring = analysis.get("scoring", {})
            llm_rows.append({
                "기업명":     company,
                "투자의견":   analysis.get("opinion", "보유"),
                "총점":       analysis.get("total_score", 0),
                "거시환경":   scoring.get("거시환경",  {}).get("score", 0),
                "산업매력도": scoring.get("산업매력도", {}).get("score", 0),
                "경쟁위치":   scoring.get("경쟁위치",  {}).get("score", 0),
                "정책수혜":   scoring.get("정책수혜",  {}).get("score", 0),
                "시장모멘텀": scoring.get("시장모멘텀", {}).get("score", 0),
                "요약":       analysis.get("summary", ""),
            })
        else:
            llm_rows.append({"기업명": company, "투자의견": "보유", "총점": 0})

    df_llm = pd.DataFrame(llm_rows)

    # DB에서 수집 데이터 로드
    try:
        conn      = sqlite3.connect(str(DB_PATH))
        df_vc     = pd.read_sql("SELECT * FROM value_chain",    conn)
        df_growth = pd.read_sql("SELECT * FROM industry_growth", conn)
        df_comp   = pd.read_sql("SELECT * FROM competition",    conn)
        df_policy = pd.read_sql("""
            SELECT segment, keyword, year, proj_count, gov_fund
            FROM policy_trend ORDER BY segment, keyword, year
        """, conn)
        conn.close()

        # 정책 피벗
        df_policy["gov_fund_억"] = (df_policy["gov_fund"] / 1e8).round(1)
        df_pivot = df_policy.pivot_table(
            index=["segment", "keyword"],
            columns="year",
            values="gov_fund_억",
            aggfunc="sum"
        ).reset_index()
        df_pivot.columns.name = None

        # 종합현황 = LLM + 밸류체인 머지
        df_final = df_llm.merge(
            df_vc[["company_name", "vc_role", "direct_flag",
                   "platform_flag", "confidence"]].rename(
                columns={"company_name": "기업명",
                         "vc_role":      "밸류체인 위치",
                         "direct_flag":  "직접생산",
                         "platform_flag":"플랫폼기업",
                         "confidence":   "데이터신뢰도"}),
            on="기업명", how="left"
        )

    except Exception as e:
        print(f"  ⚠️ DB 로드 실패 ({e}) → LLM 결과만 저장")
        df_final  = df_llm
        df_growth = pd.DataFrame()
        df_comp   = pd.DataFrame()
        df_pivot  = pd.DataFrame()

    # Excel 저장
    companies_str = "_".join(list(reports.keys())[:2])  # 최대 2개 기업명
    fname = f"market_final_{companies_str}.xlsx"
    fpath = OUTPUT_DIR / fname

    with pd.ExcelWriter(str(fpath), engine="openpyxl") as writer:
        df_final.to_excel(writer,  sheet_name="종합현황",    index=False)
        df_llm.to_excel(writer,    sheet_name="마켓점수",    index=False)
        if not df_vc.empty if 'df_vc' in dir() else False:
            df_vc.to_excel(writer, sheet_name="밸류체인",    index=False)
        if not df_comp.empty:
            df_comp.to_excel(writer, sheet_name="경쟁구조",  index=False)
        if not df_growth.empty:
            df_growth.to_excel(writer, sheet_name="산업성장률", index=False)
        if not df_pivot.empty:
            df_pivot.to_excel(writer, sheet_name="정부R&D정책", index=False)

    print(f"✅ 파이널 Excel 생성: {fpath}")
    _upload_to_github(str(fpath))
    return str(fpath)


def _upload_to_github(file_path: str) -> bool:
    if not (REPO_ROOT / ".git").exists():
        print("  [GitHub] git repository 아님 → 업로드 건너뜀")
        return True

    msg = f"Auto update: {Path(file_path).name} ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
    cmds = [
        ["git", "-C", str(REPO_ROOT), "add", file_path],
        ["git", "-C", str(REPO_ROOT), "commit", "-m", msg],
        ["git", "-C", str(REPO_ROOT), "push"],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            if "nothing to commit" in result.stdout + result.stderr:
                print("  [GitHub] 변경사항 없음 → 건너뜀")
                return True
            print(f"  [GitHub] ❌ {result.stderr.strip()}")
            return False
        print(f"  [GitHub] ✅ {' '.join(cmd[3:5])}")
    print("  [GitHub] 🎉 업로드 완료")
    return True
