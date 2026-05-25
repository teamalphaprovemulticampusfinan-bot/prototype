from pathlib import Path

path = Path(r".\src\chair_agent\adapters.py")
text = path.read_text(encoding="utf-8")

insert_marker = '''    original_summary = (
        source.get("summary")
        or source.get("market_summary")
        or source.get("analysis_summary")
        or source.get("analysis")
        or ""
    )
'''

priority_fix = r'''    # as_of_date replay에서는 valuation/current snapshot보다
    # 가격 CSV에서 as_of_date 기준으로 계산한 값이 더 우선이다.
    # 기존 payload/valuation 값은 CSV 계산값이 없을 때만 fallback으로 사용한다.
    current_price = _first_non_empty(file_metrics.get("current_price"), current_price)
    annual_return = _first_non_empty(file_metrics.get("annual_return"), annual_return)
    recent_1m_return = _first_non_empty(file_metrics.get("recent_1m_return"), recent_1m_return)
    mdd = _first_non_empty(file_metrics.get("mdd"), mdd)
    volatility = _first_non_empty(file_metrics.get("volatility"), volatility)
    avg_trading_value_20d = _first_non_empty(file_metrics.get("avg_trading_value_20d"), avg_trading_value_20d)
    turnover_proxy = _first_non_empty(file_metrics.get("turnover_proxy"), turnover_proxy)
    liquidity_status = _first_non_empty(file_metrics.get("liquidity_status"), liquidity_status)

    # 숫자 필드는 문자열로 들어온 기존 snapshot 값을 float로 정규화한다.
    current_price = _safe_metric_float(current_price)
    annual_return = _safe_metric_float(annual_return)
    recent_1m_return = _safe_metric_float(recent_1m_return)
    mdd = _safe_metric_float(mdd)
    volatility = _safe_metric_float(volatility)
    avg_trading_value_20d = _safe_metric_float(avg_trading_value_20d)
    turnover_proxy = _safe_metric_float(turnover_proxy)
    market_cap = _safe_metric_float(market_cap)

'''

if priority_fix.strip() in text:
    print("[SKIP] market metric priority fix already exists.")
else:
    if insert_marker not in text:
        raise RuntimeError("insert marker not found: original_summary block")
    text = text.replace(insert_marker, priority_fix + "\n" + insert_marker, 1)
    path.write_text(text, encoding="utf-8")
    print("[OK] market metric priority fixed: price CSV values now override snapshot fallback.")
