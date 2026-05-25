from __future__ import annotations

from math import sqrt
from typing import Any

from .utils import to_float

MISSING_TEXT = "보조 산출값 없음"


def _safe_div(a: Any, b: Any) -> float | None:
    x = to_float(a)
    y = to_float(b)
    if x is None or y in (None, 0):
        return None
    return x / y


def _clean(values: list[Any]) -> list[float]:
    out: list[float] = []
    for v in values:
        n = to_float(v)
        if n is not None and n == n and n not in (float("inf"), float("-inf")):
            out.append(float(n))
    return sorted(out)


def _quantile(values: list[Any], q: float) -> float | None:
    arr = _clean(values)
    if not arr:
        return None
    if len(arr) == 1:
        return arr[0]
    pos = (len(arr) - 1) * max(0.0, min(1.0, q))
    lo = int(pos)
    hi = min(lo + 1, len(arr) - 1)
    frac = pos - lo
    return arr[lo] * (1 - frac) + arr[hi] * frac


def _latest(normalized: list[dict[str, Any]]) -> dict[str, Any]:
    if not normalized:
        return {}
    return sorted(normalized, key=lambda r: str(r.get("year") or ""))[-1]


def _per_share(value: Any, shares: Any) -> float | None:
    return _safe_div(value, shares)


def _equity_from_ev(ev: Any, cash: Any, liabilities: Any) -> float | None:
    ev_n = to_float(ev)
    if ev_n is None:
        return None
    return ev_n + (to_float(cash) or 0.0) - (to_float(liabilities) or 0.0)


def _range_label(price: Any, current_price: Any) -> str:
    p = to_float(price)
    c = to_float(current_price)
    if p is None or c in (None, 0):
        return "보조 산출 필요"
    gap = p / c - 1.0
    if gap >= 0.20:
        return "상승여력 우호"
    if gap <= -0.20:
        return "밸류에이션 부담"
    return "중립권"


def _coverage_status(value: Any) -> str:
    return "확보" if to_float(value) is not None or bool(value) else "대체 산출 필요"


def _method_row(
    *,
    method_code: str,
    method_kr: str,
    base_value: float | None,
    low_value: float | None,
    high_value: float | None,
    shares: float | None,
    current_price: float | None,
    source: str,
    reliability: str,
) -> dict[str, Any]:
    base_price = _per_share(base_value, shares)
    low_price = _per_share(low_value, shares)
    high_price = _per_share(high_value, shares)
    upside = _safe_div(base_price, current_price)
    if upside is not None:
        upside -= 1.0
    return {
        "method_code": method_code,
        "method_kr": method_kr,
        "low_equity_value": low_value,
        "base_equity_value": base_value,
        "high_equity_value": high_value,
        "low_implied_price": low_price,
        "base_implied_price": base_price,
        "high_implied_price": high_price,
        "current_price": current_price,
        "upside_downside_pct": upside,
        "interpretation_kr": _range_label(base_price, current_price),
        "source": source,
        "reliability_kr": reliability,
    }


def _enterprise_market_value(price_summary: dict[str, Any], latest: dict[str, Any]) -> float | None:
    market_cap = to_float(price_summary.get("market_cap"))
    if market_cap is None:
        latest_close = to_float(price_summary.get("latest_close"))
        shares = to_float(price_summary.get("shares_outstanding"))
        if latest_close is not None and shares is not None:
            market_cap = latest_close * shares
    if market_cap is None:
        return None
    return market_cap + (to_float(latest.get("liabilities")) or 0.0) - (to_float(latest.get("cash")) or 0.0)


def _pv_with_terminal_growth(projection: list[dict[str, Any]], wacc: float, g: float) -> float | None:
    if not projection or wacc <= g:
        return None
    total = 0.0
    last_fcf = None
    last_year = len(projection)
    for idx, row in enumerate(projection, start=1):
        fcf = to_float(row.get("fcf"))
        if fcf is None:
            continue
        last_fcf = fcf
        total += fcf / ((1 + wacc) ** idx)
    if last_fcf is None:
        return None
    terminal = last_fcf * (1 + g) / (wacc - g)
    total += terminal / ((1 + wacc) ** last_year)
    return total


def _solve_implied_terminal_growth(projection: list[dict[str, Any]], wacc: Any, target_ev: Any) -> float | None:
    w = to_float(wacc)
    target = to_float(target_ev)
    if w is None or target is None or not projection:
        return None
    lo = -0.05
    hi = min(w - 0.005, 0.08)
    if hi <= lo:
        return None
    pv_lo = _pv_with_terminal_growth(projection, w, lo)
    pv_hi = _pv_with_terminal_growth(projection, w, hi)
    if pv_lo is None or pv_hi is None:
        return None
    # If target is outside the solvable range, return boundary rather than null so the dashboard can explain it.
    if target <= min(pv_lo, pv_hi):
        return lo
    if target >= max(pv_lo, pv_hi):
        return hi
    for _ in range(80):
        mid = (lo + hi) / 2.0
        pv_mid = _pv_with_terminal_growth(projection, w, mid)
        if pv_mid is None:
            break
        if pv_mid < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _build_multiples_methods(latest: dict[str, Any], peer: dict[str, Any], dcf: dict[str, Any], price_summary: dict[str, Any]) -> list[dict[str, Any]]:
    peer_rows = peer.get("peer_rows") or []
    shares = to_float(price_summary.get("shares_outstanding") or dcf.get("shares_outstanding"))
    current_price = to_float(price_summary.get("latest_close") or dcf.get("latest_close"))
    revenue = to_float(latest.get("revenue"))
    equity = to_float(latest.get("equity"))
    net_income = to_float(latest.get("net_income"))
    op = to_float(latest.get("operating_profit"))
    fcf = to_float(latest.get("fcf"))
    cash = to_float(latest.get("cash")) or 0.0
    liabilities = to_float(latest.get("liabilities")) or 0.0

    rows: list[dict[str, Any]] = []
    # DCF anchor
    equity_value = to_float(dcf.get("equity_value"))
    if equity_value is not None:
        rows.append(_method_row(
            method_code="DCF_BASE",
            method_kr="DCF 기준가치",
            low_value=equity_value * 0.85,
            base_value=equity_value,
            high_value=equity_value * 1.15,
            shares=shares,
            current_price=current_price,
            source="Valuation Agent DCF",
            reliability="핵심 모델",
        ))

    def add_equity_multiple(code: str, label: str, base_metric: float | None, multiple_key: str, source_name: str) -> None:
        if base_metric is None or base_metric <= 0:
            return
        qs = [_quantile([r.get(multiple_key) for r in peer_rows], q) for q in (0.25, 0.50, 0.75)]
        if qs[1] is None:
            return
        rows.append(_method_row(
            method_code=code,
            method_kr=label,
            low_value=base_metric * qs[0] if qs[0] is not None else None,
            base_value=base_metric * qs[1],
            high_value=base_metric * qs[2] if qs[2] is not None else None,
            shares=shares,
            current_price=current_price,
            source=source_name,
            reliability="피어 중앙값 기반",
        ))

    def add_ev_multiple(code: str, label: str, base_metric: float | None, multiple_key: str, source_name: str) -> None:
        if base_metric is None or base_metric <= 0:
            return
        qs = [_quantile([r.get(multiple_key) for r in peer_rows], q) for q in (0.25, 0.50, 0.75)]
        if qs[1] is None:
            return
        rows.append(_method_row(
            method_code=code,
            method_kr=label,
            low_value=_equity_from_ev(base_metric * qs[0], cash, liabilities) if qs[0] is not None else None,
            base_value=_equity_from_ev(base_metric * qs[1], cash, liabilities),
            high_value=_equity_from_ev(base_metric * qs[2], cash, liabilities) if qs[2] is not None else None,
            shares=shares,
            current_price=current_price,
            source=source_name,
            reliability="EV 조정 피어 기준",
        ))

    add_equity_multiple("PSR_COMP", "P/S 상대가치", revenue, "psr", "시가총액/매출 피어 비교")
    add_equity_multiple("PBR_COMP", "P/B 상대가치", equity, "pbr", "시가총액/자본 피어 비교")
    add_equity_multiple("PER_COMP", "PER 상대가치", net_income, "per", "시가총액/순이익 피어 비교")
    add_equity_multiple("PFCF_COMP", "P/FCF 상대가치", fcf, "p_fcf", "시가총액/FCF 피어 비교")
    add_ev_multiple("EV_SALES_COMP", "EV/Sales 상대가치", revenue, "ev_sales", "EV/매출 피어 비교")
    add_ev_multiple("EV_EBIT_COMP", "EV/EBIT 상대가치", op, "ev_ebit", "EV/영업이익 피어 비교")
    return rows


def _build_owner_earnings(latest: dict[str, Any], price_summary: dict[str, Any], wacc: dict[str, Any], dcf: dict[str, Any]) -> dict[str, Any]:
    cfo = to_float(latest.get("cfo"))
    capex = to_float(latest.get("capex"))
    fcf = to_float(latest.get("fcf"))
    op = to_float(latest.get("operating_profit"))
    tax_rate = to_float(wacc.get("tax_rate")) or 0.24
    w = to_float(wacc.get("wacc")) or 0.10
    shares = to_float(price_summary.get("shares_outstanding") or dcf.get("shares_outstanding"))
    market_cap = to_float(price_summary.get("market_cap"))
    equity = to_float(latest.get("equity"))
    net_income = to_float(latest.get("net_income"))

    owner_earnings = fcf
    method = "FCF = CFO - CAPEX"
    if owner_earnings is None and cfo is not None:
        owner_earnings = cfo - (capex or 0.0)
        method = "CFO - CAPEX 보조 산식"
    epv_operating = op * (1 - tax_rate) / w if op is not None and w > 0 else None
    epv_equity = _equity_from_ev(epv_operating, latest.get("cash"), latest.get("liabilities")) if epv_operating is not None else None
    owner_value = owner_earnings / w if owner_earnings is not None and w > 0 else None
    eps = _safe_div(net_income, shares)
    bps = _safe_div(equity, shares)
    graham_number = sqrt(22.5 * eps * bps) if eps is not None and bps is not None and eps > 0 and bps > 0 else None
    return {
        "owner_earnings": owner_earnings,
        "owner_earnings_method_kr": method,
        "owner_earnings_yield": _safe_div(owner_earnings, market_cap),
        "owner_earnings_value": owner_value,
        "owner_earnings_value_per_share": _per_share(owner_value, shares),
        "epv_equity_value": epv_equity,
        "epv_price": _per_share(epv_equity, shares),
        "eps": eps,
        "bps": bps,
        "graham_number": graham_number,
        "method_note_kr": "오너 이익, EPV, Graham Number는 DCF를 보완하는 보수적 교차검증 지표입니다.",
    }


def _build_reverse_dcf(latest: dict[str, Any], dcf: dict[str, Any], wacc: dict[str, Any], price_summary: dict[str, Any]) -> dict[str, Any]:
    market_ev = _enterprise_market_value(price_summary, latest)
    model_ev = to_float(dcf.get("enterprise_value"))
    projection = dcf.get("projection") or []
    implied_g = _solve_implied_terminal_growth(projection, wacc.get("wacc"), market_ev)
    return {
        "current_price": price_summary.get("latest_close") or dcf.get("latest_close"),
        "market_cap": price_summary.get("market_cap"),
        "market_implied_enterprise_value": market_ev,
        "model_enterprise_value": model_ev,
        "market_vs_model_ev_gap_pct": (_safe_div(market_ev, model_ev) - 1.0) if _safe_div(market_ev, model_ev) is not None else None,
        "required_fcf_yield_on_ev": _safe_div(latest.get("fcf"), market_ev),
        "implied_terminal_growth_rate": implied_g,
        "wacc_used": wacc.get("wacc"),
        "interpretation_kr": "현재 주가가 요구하는 FCF yield와 영구성장률을 역산해 DCF 가정의 현실성을 점검합니다.",
    }


def _build_market_implied_multiples(latest: dict[str, Any], price_summary: dict[str, Any]) -> dict[str, Any]:
    market_cap = to_float(price_summary.get("market_cap"))
    shares = to_float(price_summary.get("shares_outstanding"))
    close = to_float(price_summary.get("latest_close"))
    revenue = to_float(latest.get("revenue"))
    equity = to_float(latest.get("equity"))
    net_income = to_float(latest.get("net_income"))
    op = to_float(latest.get("operating_profit"))
    fcf = to_float(latest.get("fcf"))
    ev = _enterprise_market_value(price_summary, latest)
    eps = _safe_div(net_income, shares)
    bps = _safe_div(equity, shares)
    return {
        "latest_close": close,
        "market_cap": market_cap,
        "enterprise_value_proxy": ev,
        "psr_market": _safe_div(market_cap, revenue),
        "pbr_market": _safe_div(market_cap, equity),
        "per_market": _safe_div(market_cap, net_income) if net_income and net_income > 0 else None,
        "p_fcf_market": _safe_div(market_cap, fcf) if fcf and fcf > 0 else None,
        "ev_sales_market": _safe_div(ev, revenue),
        "ev_ebit_market": _safe_div(ev, op) if op and op > 0 else None,
        "eps_derived": eps,
        "bps_derived": bps,
        "fcf_yield_market": _safe_div(fcf, market_cap),
        "sales_yield_market": _safe_div(revenue, market_cap),
        "source_kr": "DART 정규화 재무제표 + Valuation Agent 주가/발행주식 수 intake로 자동 산출",
    }


def _build_quality_diagnostics(normalized: list[dict[str, Any]], latest: dict[str, Any], price_summary: dict[str, Any], methods: list[dict[str, Any]], reverse_dcf: dict[str, Any], owner: dict[str, Any]) -> list[dict[str, Any]]:
    years = len(normalized)
    price_rows = int(to_float(price_summary.get("price_rows")) or 0)
    method_count = len([m for m in methods if to_float(m.get("base_implied_price")) is not None])
    op_margin = to_float(latest.get("op_margin"))
    fcf_margin = to_float(latest.get("fcf_margin"))
    debt_ratio = to_float(latest.get("debt_ratio"))
    rows = [
        {
            "진단항목": "재무제표 기간",
            "상태": "충분" if years >= 5 else "부분 확보",
            "근거값": years,
            "해석": "5개년이면 DCF 추세 가정과 CAGR 산정에 충분합니다.",
        },
        {
            "진단항목": "주가 이력",
            "상태": "충분" if price_rows >= 700 else ("사용 가능" if price_rows >= 240 else "보강 권장"),
            "근거값": price_rows,
            "해석": "현재가, 52주 범위, MDD, 변동성, 거래대금 지표 품질을 좌우합니다.",
        },
        {
            "진단항목": "가치평가 방법 수",
            "상태": "충분" if method_count >= 5 else ("사용 가능" if method_count >= 3 else "보강 권장"),
            "근거값": method_count,
            "해석": "DCF 하나가 아니라 상대가치·EV 멀티플·현금창출 지표까지 교차검증합니다.",
        },
        {
            "진단항목": "수익성",
            "상태": "우호" if op_margin is not None and op_margin > 0.08 else ("중립" if op_margin is not None and op_margin > 0 else "주의"),
            "근거값": op_margin,
            "해석": "영업이익률이 높을수록 DCF의 현금흐름 안정성이 높습니다.",
        },
        {
            "진단항목": "현금창출",
            "상태": "우호" if fcf_margin is not None and fcf_margin > 0.03 else ("중립" if fcf_margin is not None and fcf_margin >= 0 else "주의"),
            "근거값": fcf_margin,
            "해석": "FCF margin과 오너 이익 수익률이 DCF 품질의 핵심입니다.",
        },
        {
            "진단항목": "재무 레버리지",
            "상태": "보수적" if debt_ratio is not None and debt_ratio < 1.0 else ("관리 필요" if debt_ratio is not None else "보조 산출 필요"),
            "근거값": debt_ratio,
            "해석": "부채/자본이 높으면 WACC와 지분가치 산정에 보수 가정을 적용합니다.",
        },
        {
            "진단항목": "시장 내재가정",
            "상태": "계산 완료" if reverse_dcf.get("implied_terminal_growth_rate") is not None else "보조 산출 필요",
            "근거값": reverse_dcf.get("implied_terminal_growth_rate"),
            "해석": "현재 시가총액이 요구하는 영구성장률을 역산해 과도한 기대가 반영됐는지 확인합니다.",
        },
        {
            "진단항목": "오너 이익",
            "상태": "계산 완료" if owner.get("owner_earnings_value_per_share") is not None else "보조 산출 필요",
            "근거값": owner.get("owner_earnings_value_per_share"),
            "해석": "CFO-CAPEX 또는 FCF 기반 보수 가치가 DCF와 같은 방향인지 확인합니다.",
        },
    ]
    return rows


def _build_source_completion_plan(latest: dict[str, Any], price_summary: dict[str, Any], peer: dict[str, Any], reference_summary: dict[str, Any], market_snapshot: dict[str, Any] | None) -> list[dict[str, Any]]:
    ms = market_snapshot or {}
    available_metric_count = int(to_float(ms.get("available_metric_count")) or 0)
    checks = [
        ("DART 재무제표", latest.get("revenue") is not None and latest.get("equity") is not None, "OpenDART fnlttSinglAcntAll/fnlttSinglAcnt", "매출·자본·순이익·현금흐름 확보"),
        ("주가 이력", (price_summary.get("price_rows") or 0) >= 240, "yfinance → Yahoo chart → Naver 일별시세 fallback", "현재가·변동성·MDD·거래대금 확보"),
        ("발행주식 수", price_summary.get("shares_outstanding") is not None, "OpenDART stockTotqySttus", "내재주가·시가총액 계산"),
        ("피어 멀티플", bool(peer.get("peer_rows")) and peer.get("target_psr") is not None, "Valuation 전용 live peer intake", "P/S·PER·PBR·EV/Sales 비교"),
        ("208개 Universe", (reference_summary.get("reference_universe_rows") or 0) >= 100, "Tech universe 축 복제 + valuation proxy", "대규모 상대 위치 비교"),
        ("보조 투자지표", available_metric_count > 0, "Naver finance live + DART/주가 자동 산출 fallback", "외부 표시 PER/PBR/EPS/BPS 또는 자체 산출값"),
    ]
    rows = []
    for block, ok, source, reason in checks:
        rows.append({
            "데이터블록": block,
            "상태": "확보" if ok else "대체 산출 경로 지정",
            "수집경로": source,
            "가치평가 활용": reason,
            "대시보드 표시": "표시 가능" if ok else "보완 배지 표시",
        })
    return rows


def _score_advanced(methods: list[dict[str, Any]], reverse_dcf: dict[str, Any], owner: dict[str, Any], price_summary: dict[str, Any], quality_rows: list[dict[str, Any]]) -> float:
    current = to_float(price_summary.get("latest_close"))
    usable = [m for m in methods if to_float(m.get("base_implied_price")) is not None]
    if not usable or current in (None, 0):
        return 50.0
    upsides = [to_float(m.get("upside_downside_pct")) for m in usable]
    upsides = [x for x in upsides if x is not None]
    median_upside = _quantile(upsides, 0.50) or 0.0
    coverage_bonus = min(15.0, len(usable) * 2.5)
    owner_yield = to_float(owner.get("owner_earnings_yield")) or 0.0
    reverse_gap = abs(to_float(reverse_dcf.get("market_vs_model_ev_gap_pct")) or 0.0)
    quality_bonus = 0.0
    for row in quality_rows:
        if str(row.get("상태")) in {"충분", "우호", "계산 완료", "보수적"}:
            quality_bonus += 1.0
    score = 48.0 + max(-25.0, min(25.0, median_upside * 80.0)) + coverage_bonus + min(8.0, quality_bonus)
    if owner_yield > 0.06:
        score += 5.0
    elif owner_yield < 0:
        score -= 6.0
    if reverse_gap > 1.0:
        score -= 8.0
    return round(max(0.0, min(100.0, score)), 2)


def _build_market_share_sensitivity(
    base_revenue: float | None,
    dcf: dict[str, Any],
) -> dict[str, Any]:
    """매출액 1% 변화가 적정가에 미치는 영향을 계산합니다.

    시장 점유율 데이터 없이 base_revenue × 1% 를 매출 충격으로 근사합니다.
    FCF margin, WACC, terminal growth, 발행주식 수는 DCF 기준값을 그대로 사용합니다.
    """
    if base_revenue is None:
        return {"status": "NO_REVENUE", "price_impact_per_share": None, "note_kr": "매출액 데이터 없음"}

    wacc_val = to_float(dcf.get("wacc")) or 0.095
    tgr = to_float(dcf.get("terminal_growth_rate")) or 0.015
    fcf_margin = to_float(dcf.get("assumed_fcf_margin")) or 0.10
    shares = to_float(dcf.get("shares_outstanding"))
    cash = to_float(dcf.get("cash")) or 0.0
    liabilities = to_float(dcf.get("debt_proxy_liabilities")) or 0.0
    projection_years = int(to_float(dcf.get("projection_years")) or 5)

    if wacc_val <= tgr or shares in (None, 0):
        return {"status": "INVALID_PARAMS", "price_impact_per_share": None, "note_kr": "WACC/TGR/발행주식 수 확인 필요"}

    # 매출 1% 충격 → FCF 변화 → EV 변화 → 주당가치 변화
    revenue_shock = base_revenue * 0.01
    annual_fcf_delta = revenue_shock * fcf_margin

    # 잔여가치 기준: 영구연금 근사 (projection 기간 중 평균 할인 + terminal)
    # 간단하게 terminal value 방식으로 계산
    # terminal: delta_fcf / (wacc - g), 현재가치로 할인
    pv_terminal_delta = (annual_fcf_delta / (wacc_val - tgr)) / ((1 + wacc_val) ** projection_years)

    # projection 기간 FCF 현재가치 합
    pv_projection_delta = sum(
        annual_fcf_delta / ((1 + wacc_val) ** t)
        for t in range(1, projection_years + 1)
    )

    ev_delta = pv_projection_delta + pv_terminal_delta
    price_impact = ev_delta / shares  # 주당 영향

    return {
        "status": "OK",
        "revenue_shock_1pct": revenue_shock,
        "annual_fcf_delta": annual_fcf_delta,
        "ev_delta": ev_delta,
        "price_impact_per_share": price_impact,
        "price_impact_display": f"±{abs(price_impact):,.0f}원",
        "basis_kr": "base_revenue × 1% 매출 변화 기준 (시장 점유율 1%p 근사)",
        "note_kr": "assumptions.json에 addressable_market_size를 입력하면 실제 점유율 기준으로 개선됩니다.",
    }


def build_advanced_valuation(
    *,
    normalized: list[dict[str, Any]],
    dcf: dict[str, Any],
    peer: dict[str, Any],
    price_summary: dict[str, Any],
    wacc: dict[str, Any],
    reference_summary: dict[str, Any] | None = None,
    market_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    latest = _latest(normalized)
    methods = _build_multiples_methods(latest, peer, dcf, price_summary)
    current_price = to_float(price_summary.get("latest_close") or dcf.get("latest_close"))
    implied_prices = [m.get("base_implied_price") for m in methods]
    low = _quantile(implied_prices, 0.25)
    base = _quantile(implied_prices, 0.50)
    high = _quantile(implied_prices, 0.75)
    margin = (_safe_div(base, current_price) - 1.0) if _safe_div(base, current_price) is not None else None
    reverse_dcf = _build_reverse_dcf(latest, dcf, wacc, price_summary)
    owner = _build_owner_earnings(latest, price_summary, wacc, dcf)
    market_multiples = _build_market_implied_multiples(latest, price_summary)
    quality = _build_quality_diagnostics(normalized, latest, price_summary, methods, reverse_dcf, owner)
    source_plan = _build_source_completion_plan(latest, price_summary, peer, reference_summary or {}, market_snapshot)
    score = _score_advanced(methods, reverse_dcf, owner, price_summary, quality)
    confidence_grade = "높음" if score >= 70 and (price_summary.get("price_rows") or 0) >= 700 else ("보통" if score >= 45 else "낮음")
    base_revenue = to_float(latest.get("revenue"))
    sensitivity_breakeven = _build_market_share_sensitivity(base_revenue, dcf)
    return {
        "method_kr": "DCF + 피어 멀티플 가치범위표 + 역산 DCF + 오너 이익/EPV + 시장내재 배수 + 데이터 커버리지",
        "advanced_valuation_score": score,
        "confidence_grade_kr": confidence_grade,
        "football_field": {
            "method_count": len([m for m in methods if to_float(m.get("base_implied_price")) is not None]),
            "low_price": low,
            "base_price": base,
            "high_price": high,
            "current_price": current_price,
            "margin_of_safety_pct": margin,
            "interpretation_kr": _range_label(base, current_price),
        },
        "valuation_methods": methods,
        "reverse_dcf": reverse_dcf,
        "owner_earnings": owner,
        "market_implied_multiples": market_multiples,
        "valuation_quality_diagnostics": quality,
        "source_completion_plan": source_plan,
        "market_snapshot": market_snapshot or {},
        "sensitivity_breakeven": sensitivity_breakeven,
        "dashboard_note_kr": "투자은행식 valuation pack에서 자주 쓰는 DCF·Comps·역산 DCF·오너 이익·시장내재배수 교차검증을 제공합니다.",
    }