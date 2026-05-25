from __future__ import annotations

"""
Manual/curated macro signal rows for information that is not yet available
through a stable public API.

This is intentionally separated from live collectors:
- live data remains in ECOS/FRED/OECD/GDELT/RSS collectors
- manually supplied class material or PDF-based notes become transparent rows
  with source='manual_uploaded_research'

The first curated block reflects the user-uploaded report:
"빅테크 하일드 스프레드 분석_260511_151018.pdf".
"""

from datetime import datetime

import pandas as pd


def build_bigtech_credit_macro_signals(today: datetime | None = None) -> pd.DataFrame:
    """AI capex / credit-spread risk signals relevant to semiconductor demand.

    These rows are not price quotes. They are qualitative-to-structured macro
    watchpoints that the Macro Agent can use as an additional risk layer.
    """
    today = today or datetime.today()
    asof = pd.Timestamp("2026-04-16")
    rows = [
        {
            "date": asof,
            "category": "AI_크레딧_스프레드",
            "signal_name": "AI_CAPEX_DEBT_SUPPLY_OVERHANG",
            "direction": "risk_up",
            "importance": 5,
            "macro_channel": "AI 데이터센터 투자 확대 → IG 채권 발행 증가 → 스프레드 확대/자금조달 비용 상승 가능성",
            "semiconductor_link": "HBM·GPU·첨단패키징 수요에는 긍정적이나, ROI 지연 시 주문 속도와 밸류에이션 할인 요인이 될 수 있음",
            "watch_metric": "AI 관련 IG 발행 규모, ICE BofA IG/HY OAS, Oracle CDS, Mag7 주가 디커플링",
            "source": "manual_uploaded_research:bigtech_high_yield_spread_pdf",
            "url": "local_uploaded_pdf",
        },
        {
            "date": asof,
            "category": "AI_크레딧_스프레드",
            "signal_name": "FALLEN_ANGEL_RISK_ORACLE_CANARY",
            "direction": "risk_up",
            "importance": 4,
            "macro_channel": "빅테크/클라우드 기업의 차입 부담이 커질 경우 IG-HY 경계 신용위험이 확대될 수 있음",
            "semiconductor_link": "AI 서버 투자 체인의 선행 수요는 유지되더라도, 고객사 신용 스프레드 확대는 Capex 집행 속도 조정 리스크로 연결 가능",
            "watch_metric": "Oracle 5Y CDS, BBB/BB crossover spread, Tech HY OAS",
            "source": "manual_uploaded_research:bigtech_high_yield_spread_pdf",
            "url": "local_uploaded_pdf",
        },
        {
            "date": asof,
            "category": "AI_전력_병목",
            "signal_name": "AI_POWER_INFRA_BOTTLENECK",
            "direction": "mixed",
            "importance": 4,
            "macro_channel": "AI 인프라 Capex가 전력망·자체 발전·데이터센터 병목과 연결되며 에너지 가격/유틸리티 섹터와 상관관계 증가",
            "semiconductor_link": "AI 반도체 수요 확대의 구조적 근거이지만, 전력 인프라 병목은 데이터센터 증설 지연 및 칩 출하 속도 조정 리스크",
            "watch_metric": "전력망 투자, 유틸리티 HY OAS, 천연가스/전력 가격, 데이터센터 승인 지연 뉴스",
            "source": "manual_uploaded_research:bigtech_high_yield_spread_pdf",
            "url": "local_uploaded_pdf",
        },
    ]
    df = pd.DataFrame(rows)
    df["collected_at"] = pd.Timestamp(today)
    return df
