from __future__ import annotations

from typing import Any

from .utils import pct, to_float

MISSING_TEXT = "해당 없음"


def _fmt_money(v: Any) -> str:
    num = to_float(v)
    if num is None:
        return MISSING_TEXT
    return f"{num/100_000_000:,.1f}억원"


def _fmt_price(v: Any) -> str:
    num = to_float(v)
    if num is None:
        return MISSING_TEXT
    return f"{num:,.0f}원"


def _fmt_score(v: Any) -> str:
    num = to_float(v)
    if num is None:
        return MISSING_TEXT
    return f"{num:.1f}/100"


def _fmt_multiple(v: Any) -> str:
    num = to_float(v)
    if num is None:
        return MISSING_TEXT
    return f"{num:.2f}배"


def _safe_text(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else MISSING_TEXT


def build_report(company: str, company_dir: str, metrics: dict[str, Any], validation: dict[str, Any]) -> str:
    wacc = metrics.get("wacc", {})
    dcf = metrics.get("dcf", {})
    ml = metrics.get("ml_overlay", {})
    peer = metrics.get("peer_comps", {})
    price = metrics.get("price_summary", {}) or {}
    ref = metrics.get("reference_universe_summary") or {}
    scorecard = metrics.get("scorecard") or {}
    advanced = metrics.get("advanced_valuation") or {}
    football = advanced.get("football_field") or {}
    reverse_dcf = advanced.get("reverse_dcf") or {}
    owner = advanced.get("owner_earnings") or {}

    lines = [
        f"# {company} 독립 Valuation Agent 리포트",
        "",
        "## 1. 역할과 차별점",
        "이 보고서는 finance_agent 산출물을 사용하지 않고 Valuation Agent 전용 intake 데이터(DART 재무제표, 주가, 발행주식 수, 피어 데이터, 모델링 가정)만으로 생성한 보조 가치평가 산출물입니다.",
        "업로드한 파이낸셜 모델링 자료는 런타임 원천 데이터로 복사하지 않고 DCF/WACC/Peer/Scenario/Dashboard 워크북 구조와 검증 체계로 코드화했습니다.",
        "",
        "## 2. 핵심 결과",
        f"- WACC: **{pct(wacc.get('wacc'))}**",
        f"- DCF 기업가치(EV): **{_fmt_money(dcf.get('enterprise_value'))}**",
        f"- DCF 지분가치: **{_fmt_money(dcf.get('equity_value'))}**",
        f"- 현재가: **{_fmt_price(price.get('latest_close') or dcf.get('latest_close'))}**",
        f"- DCF 내재주가: **{_fmt_price(dcf.get('implied_price'))}**",
        f"- 현재가 대비 괴리율: **{pct(dcf.get('upside_downside_pct'))}**",
        f"- Peer P/S: **{_fmt_multiple(peer.get('target_psr'))}** / Peer 중앙값 **{_fmt_multiple(peer.get('median_psr'))}**",
        f"- P/S 해석: **{_safe_text(peer.get('psr_signal_kr'))}**",
        f"- 208개 반도체 reference universe: **{ref.get('reference_universe_rows', 0)}개**, Target 그룹 **{_safe_text(ref.get('target_peer_group'))}**",
        f"- Valuation 보조 스코어카드: **{_fmt_score(scorecard.get('score'))} / {_safe_text(scorecard.get('label_kr'))}**",
        f"- 종합 가치평가 점수: **{_fmt_score(advanced.get('advanced_valuation_score'))}**",
        f"- 가치범위 중앙값/안전마진: **{_fmt_price(football.get('base_price'))} / {pct(football.get('margin_of_safety_pct'))}**",
        f"- 역산 DCF 역산 영구성장률: **{pct(reverse_dcf.get('implied_terminal_growth_rate'))}**",
        f"- 오너 이익 주당가치/EPV: **{_fmt_price(owner.get('owner_earnings_value_per_share'))} / {_fmt_price(owner.get('epv_price'))}**",
        f"- 1년 수익률 / MDD / 변동성: **{pct(price.get('return_1y'))} / {pct(price.get('mdd'))} / {pct(price.get('volatility_annualized'))}**",
        f"- 시가총액 / 발행주식 수 / 20일 평균 거래대금: **{_fmt_money(price.get('market_cap'))} / {_safe_text(price.get('shares_outstanding'))}주 / {_fmt_money(price.get('avg_trading_value_20d'))}**",
        f"- ML 보조 가치평가 품질: **{_safe_text(ml.get('label_kr') or ml.get('label'))}** ({_fmt_score(ml.get('composite_score'))})",
        f"- 검증 상태: **{validation.get('status')}**",
        "",
        "## 3. 자동 생성 워크북 구조",
        "- 00_대시보드: 투자자용 요약 카드, 가치평가 핵심 결과, 차트",
        "- 01_사용안내~05_정규재무제표: 출처, 원천 데이터, 전처리 재무제표",
        "- 04_주가_데이터: 종가, 이동평균, 수익률, 드로다운, 롤링 변동성, 거래대금",
        "- 06_핵심비율~10_피어비교: 수익성·안정성·현금흐름·PSR/PER/PBR 상대가치 분석",
        "- 11_ML_보조판단~12_민감도: ML overlay와 DCF 민감도",
        "- 22_종합가치평가~25_데이터수집현황: 가치범위표, 역산 DCF, 오너 이익/EPV, 시장내재 배수, 데이터 수집현황",
        "- 17_투자자요약~21_품질_커버리지: 투자자용 요약, 208개 Universe, 가치평가 브릿지, 시나리오, 품질 커버리지",
        "",
        "## 4. Chair·대시보드 반영 원칙",
        "Valuation Agent는 기존 5개 에이전트 판단을 대체하지 않고, Chair 최종 리포트의 보조 가치평가 근거와 대시보드 다운로드용 재무모델 산출물로 사용합니다.",
        "",
        "## 5. 주요 검증/주의사항",
    ]
    issues = validation.get("issues") or []
    if issues:
        for item in issues[:10]:
            lines.append(f"- [{item.get('severity')}] {item.get('code')}: {item.get('message')}")
    else:
        lines.append("- 주요 validation warning 없음")
    return "\n".join(lines) + "\n"
