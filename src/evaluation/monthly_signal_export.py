from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from evaluation.monthly_eval import (
    AGENTS,
    MonthWindow,
    build_all_snapshots,
    project_root,
    read_universe,
)
from auditor_agent.dynamic_model_averaging import compute_dma_weights


# Fixed preset agent weights were removed.  Monthly export uses the same DMA
# posterior used by the Auditor.  If no realized history CSV is available,
# compute_dma_weights returns the objective uniform prior over available agents.
DEFAULT_WEIGHTS: dict[str, float] = {}


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        value = float(value)
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    text = str(value).replace(",", "").replace("%", "").replace("원", "").strip()

    if not text or text.lower() in {"nan", "none", "null", "확인 제한"}:
        return None

    try:
        value = float(text)
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    except Exception:
        return None


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _round(value: Any, digits: int = 4) -> float | None:
    num = _to_float(value)
    if num is None:
        return None
    return round(num, digits)


def _get_nested(data: Any, path: list[str], default: Any = None) -> Any:
    cur = data

    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)

    return cur if cur not in (None, "", [], {}) else default


def _deep_find(data: Any, keys: list[str], max_depth: int = 7) -> Any:
    if max_depth < 0:
        return None

    if isinstance(data, dict):
        for key in keys:
            if key in data and data[key] not in (None, "", [], {}):
                return data[key]

        for value in data.values():
            found = _deep_find(value, keys, max_depth - 1)
            if found not in (None, "", [], {}):
                return found

    elif isinstance(data, list):
        for value in data[:50]:
            found = _deep_find(value, keys, max_depth - 1)
            if found not in (None, "", [], {}):
                return found

    return None


def _signal_description(signal: float) -> str:
    """DMA weighted_signal의 방향성 설명 (Catania & Nonejad eDMA 기반)
    
    임계값 기반 판정이 아니라, 동적으로 평균된 신호의 방향성만 표시합니다.
    신호 값 자체(weighted_signal)가 최종 판정이며, 여러 모형의 가중치가 
    시간에 따라 동적으로 업데이트됩니다.
    """
    if signal > 0.25:
        return "긍정적 신호"
    if signal < -0.25:
        return "부정적 신호"
    return "중립적 신호"


def _score100_to_signal(score: Any, *, neutral: float = 50.0, scale: float = 50.0) -> float:
    num = _to_float(score)

    if num is None:
        return 0.0

    return _clamp((num - neutral) / scale)


def _label_to_signal(label: Any) -> float:
    text = str(label or "").upper().strip()

    if text in {"BUY", "매수", "POSITIVE", "우호", "상향"}:
        return 1.0

    if text in {"SELL", "매도", "NEGATIVE", "부담", "하향"}:
        return -1.0

    return 0.0


def _finance_signal(payload: dict[str, Any]) -> tuple[float, str]:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}

    sales_growth = _to_float(metrics.get("sales_growth_%"))
    op_margin = _to_float(metrics.get("operating_margin_%"))
    roe = _to_float(metrics.get("ROE_%"))
    debt_ratio = _to_float(metrics.get("debt_ratio_%"))
    current_ratio = _to_float(metrics.get("current_ratio_%"))
    fcf = _to_float(metrics.get("fcf"))
    mdd = _to_float(metrics.get("annual_mdd_%") or metrics.get("mdd_pct"))
    monthly_return = _to_float(metrics.get("monthly_return_%") or metrics.get("monthly_return_pct"))

    signal = 0.0
    reasons: list[str] = []

    if sales_growth is not None:
        if sales_growth >= 15:
            signal += 0.18
            reasons.append(f"매출성장률 우호({sales_growth:.2f}%)")
        elif sales_growth < 0:
            signal -= 0.18
            reasons.append(f"매출성장률 부진({sales_growth:.2f}%)")

    if op_margin is not None:
        if op_margin >= 10:
            signal += 0.22
            reasons.append(f"영업이익률 우호({op_margin:.2f}%)")
        elif op_margin < 0:
            signal -= 0.25
            reasons.append(f"영업적자/마진 부진({op_margin:.2f}%)")

    if roe is not None:
        if roe >= 8:
            signal += 0.10
            reasons.append(f"ROE 우호({roe:.2f}%)")
        elif roe < 0:
            signal -= 0.12
            reasons.append(f"ROE 부진({roe:.2f}%)")

    if fcf is not None:
        if fcf > 0:
            signal += 0.20
            reasons.append("FCF 양호")
        elif fcf < 0:
            signal -= 0.20
            reasons.append("FCF 음수")

    if debt_ratio is not None:
        if debt_ratio <= 100:
            signal += 0.12
            reasons.append(f"부채비율 안정({debt_ratio:.2f}%)")
        elif debt_ratio >= 200:
            signal -= 0.18
            reasons.append(f"부채비율 부담({debt_ratio:.2f}%)")

    if current_ratio is not None:
        if current_ratio >= 120:
            signal += 0.08
            reasons.append(f"유동비율 양호({current_ratio:.2f}%)")
        elif current_ratio < 80:
            signal -= 0.10
            reasons.append(f"유동비율 부담({current_ratio:.2f}%)")

    if mdd is not None and mdd <= -25:
        signal -= 0.08
        reasons.append(f"월중 낙폭 부담({mdd:.2f}%)")

    if monthly_return is not None and monthly_return >= 8:
        signal += 0.05
        reasons.append(f"월간 가격 모멘텀 우호({monthly_return:.2f}%)")

    signal = _clamp(signal)

    return signal, "; ".join(reasons[:5]) or "재무 지표 확인 제한/중립"


def _market_signal(payload: dict[str, Any]) -> tuple[float, str]:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}

    total_score = _to_float(metrics.get("total_score"))
    monthly_return = _to_float(metrics.get("monthly_return_pct") or metrics.get("monthly_return_%"))
    mdd = _to_float(metrics.get("mdd_pct") or metrics.get("annual_mdd_%"))
    vol = _to_float(metrics.get("annualized_volatility_pct"))
    volume_ratio = _to_float(metrics.get("volume_ma_ratio"))

    pieces: list[float] = []
    reasons: list[str] = []

    if total_score is not None:
        pieces.append(_score100_to_signal(total_score) * 0.50)
        reasons.append(f"시장 점수 {total_score:.2f}/100")

    if monthly_return is not None:
        pieces.append(_clamp(monthly_return / 15.0) * 0.30)
        reasons.append(f"월간 수익률 {monthly_return:.2f}%")

    if mdd is not None:
        if mdd <= -20:
            pieces.append(-0.15)
            reasons.append(f"MDD 부담({mdd:.2f}%)")
        elif mdd > -8:
            pieces.append(0.05)
            reasons.append(f"MDD 안정({mdd:.2f}%)")

    if vol is not None and vol >= 80:
        pieces.append(-0.08)
        reasons.append(f"변동성 부담({vol:.2f}%)")

    if volume_ratio is not None:
        if volume_ratio >= 1.5:
            pieces.append(0.07)
            reasons.append(f"거래량 증가({volume_ratio:.2f})")
        elif volume_ratio <= 0.6:
            pieces.append(-0.05)
            reasons.append(f"거래량 둔화({volume_ratio:.2f})")

    signal = _clamp(sum(pieces))

    return signal, "; ".join(reasons[:5]) or "시장 데이터 확인 제한/중립"


def _tech_signal(payload: dict[str, Any]) -> tuple[float, str]:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}

    final_score = _to_float(
        metrics.get("final_tech_investor_score")
        or metrics.get("peer_adjusted_bridge_score")
        or _deep_find(payload, ["final_bridge_score_after_ip_evidence", "peer_adjusted_bridge_score"])
    )
    ip_score = _to_float(
        metrics.get("ip_evidence_composite_score")
        or _deep_find(payload, ["ip_evidence_composite_score"])
    )
    patent_count = _to_float(
        metrics.get("patent_count")
        or _deep_find(payload, ["patent_count", "company_matched_patents", "normalized_patent_count"])
    )

    signal = 0.0
    reasons: list[str] = []

    if final_score is not None:
        signal += _score100_to_signal(final_score, neutral=60, scale=40) * 0.75
        reasons.append(f"기술/사업화 점수 {final_score:.2f}")

    if ip_score is not None:
        signal += _score100_to_signal(ip_score, neutral=50, scale=50) * 0.20
        reasons.append(f"IP Evidence {ip_score:.2f}")

    if patent_count is not None:
        if patent_count >= 100:
            signal += 0.05
            reasons.append(f"특허 레코드 {patent_count:.0f}건")
        elif patent_count <= 5:
            signal -= 0.05
            reasons.append(f"특허 레코드 제한({patent_count:.0f}건)")

    signal = _clamp(signal)

    return signal, "; ".join(reasons[:5]) or "기술/IP 데이터 확인 제한/중립"


def _valuation_signal(payload: dict[str, Any]) -> tuple[float, str]:
    scorecard = payload.get("scorecard") if isinstance(payload.get("scorecard"), dict) else {}
    peer_comps = payload.get("peer_comps") if isinstance(payload.get("peer_comps"), dict) else {}
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}

    score = _to_float(scorecard.get("score") or metrics.get("score"))
    psr_gap = _to_float(peer_comps.get("psr_gap"))
    upside = _to_float(_get_nested(payload, ["dcf", "upside_downside_pct"]))

    signal = 0.0
    reasons: list[str] = []

    if score is not None:
        signal += _score100_to_signal(score) * 0.50
        reasons.append(f"valuation score {score:.2f}/100")

    if psr_gap is not None:
        # peer 대비 P/S gap이 음수면 상대적으로 싸다는 의미로 보수적 가산
        signal += _clamp(-psr_gap / 100.0) * 0.35
        reasons.append(f"peer P/S gap {psr_gap:.2f}%")

    if upside is not None:
        signal += _clamp(upside / 50.0) * 0.30
        reasons.append(f"DCF upside {upside:.2f}%")

    fcf = _to_float(metrics.get("fcf"))
    if fcf is not None:
        if fcf > 0:
            signal += 0.05
            reasons.append("FCF 양수")
        elif fcf < 0:
            signal -= 0.05
            reasons.append("FCF 음수")

    signal = _clamp(signal)

    return signal, "; ".join(reasons[:5]) or "valuation 데이터 확인 제한/중립"


def _issue_signal(payload: dict[str, Any]) -> tuple[float, str]:
    import re as _re
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}

    news_count = _to_float(
        metrics.get("monthly_issue_count") or metrics.get("news_count")
    ) or 0.0

    if news_count <= 0:
        for ev in payload.get("evidences") or []:
            val = ev.get("value") or {}
            if isinstance(val, dict):
                c = _to_float(val.get("news_count") or val.get("monthly_issue_count"))
                if c and c > 0:
                    news_count = c
                    break
            elif ev.get("metric") == "news_count":
                c = _to_float(ev.get("value"))
                if c and c > 0:
                    news_count = c
                    break

    if news_count <= 0:
        for claim in (payload.get("claims") or payload.get("key_points") or []):
            text = str(claim.get("text") or claim) if isinstance(claim, dict) else str(claim)
            m = _re.search(r"news_count.*?(\d+)", text)
            if m:
                news_count = float(m.group(1))
                break

    pos = _to_float(metrics.get("positive_terms")) or 0.0
    neg = _to_float(metrics.get("negative_terms")) or 0.0

    if news_count <= 0 and pos <= 0 and neg <= 0:
        return 0.0, "해당 월 날짜 확인 이슈 없음"

    if pos <= 0 and neg <= 0:
        signal = min(0.1, news_count / 100.0)
        return round(signal, 4), f"이슈 {news_count:.0f}건 (감성 미집계)"

    signal = _clamp((pos - neg) / max(pos + neg + 3.0, 3.0))
    return signal, f"월내 이슈 {news_count:.0f}건, 긍정 {pos:.0f}, 부정 {neg:.0f}"


def _macro_signal(payload: dict[str, Any]) -> tuple[float, str]:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}

    label_signal = _label_to_signal(
        metrics.get("macro_signal")
        or payload.get("signal")
        or payload.get("risk_level")
    )

    score = _to_float(metrics.get("macro_score") or payload.get("score"))

    if score is not None:
        score_signal = _score100_to_signal(score)
        signal = _clamp(score_signal * 0.75 + label_signal * 0.25)
        return signal, f"macro score {score:.2f}/100"

    return label_signal, "macro label 기반 신호"


def _agent_signal(agent: str, payload: dict[str, Any]) -> tuple[float, str]:
    if agent == "finance":
        return _finance_signal(payload)

    if agent == "market":
        return _market_signal(payload)

    if agent == "tech":
        return _tech_signal(payload)

    if agent == "valuation":
        return _valuation_signal(payload)

    if agent == "issue":
        return _issue_signal(payload)

    if agent == "macro":
        return _macro_signal(payload)

    return 0.0, "unknown agent"


def _extract_metric(payload: dict[str, Any], *keys: str) -> Any:
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}

    for key in keys:
        if key in metrics and metrics[key] not in (None, "", [], {}):
            return metrics[key]

    for key in keys:
        found = _deep_find(payload, [key])
        if found not in (None, "", [], {}):
            return found

    return None


def _build_signal_row(
    *,
    month: str,
    as_of_date: str,
    target: Any,
    snapshots: dict[str, dict[str, Any]],
    weights: dict[str, float] | None,
    run_id: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "date": month,
        "field": target.field,
        "company": target.company_name,
        "ticker": getattr(target, "ticker", "") or target.company_name,
        "stock_code": target.stock_code,
        "recommendation": "",
        "weighted_signal": 0.0,
        "company_dir": target.company_dir,
        "as_of_date": as_of_date,
        "signal_source": "monthly_signal_export_dma",
        "run_id": run_id,
    }

    current_signals: dict[str, float] = {}
    reasons: dict[str, str] = {}
    for agent in AGENTS:
        payload = snapshots.get(agent) or {}
        signal, reason = _agent_signal(agent, payload)
        current_signals[agent] = signal
        reasons[agent] = reason

    available_packets = {agent: (snapshots.get(agent) or {"agent": agent}) for agent in AGENTS if agent in current_signals}
    dma = compute_dma_weights(available_packets, signals=current_signals)
    dma_weights = {
        agent: float(weight)
        for agent, weight in (dma.get("weights_adjusted") or dma.get("weights") or {}).items()
        if agent in current_signals
    }

    # Optional explicit weights are accepted only for backward compatibility in
    # external callers.  The default path is DMA, not a hard-coded preset.
    if weights:
        dma_weights = {agent: float(weights.get(agent, 0.0)) for agent in AGENTS if agent in current_signals}

    total_w = sum(dma_weights.values())
    if total_w <= 0:
        dma_weights = {agent: 1.0 / len(current_signals) for agent in current_signals}
    else:
        dma_weights = {agent: weight / total_w for agent, weight in dma_weights.items()}

    weighted_signal = 0.0
    for agent in AGENTS:
        signal = float(current_signals.get(agent, 0.0) or 0.0)
        weight = float(dma_weights.get(agent, 0.0) or 0.0)
        weighted_contribution = signal * weight
        weighted_signal += weighted_contribution

        row[f"{agent}_signal"] = round(signal, 4)
        row[f"{agent}_weighted_signal"] = round(weighted_contribution, 4)
        row[f"{agent}_signal_direction"] = _signal_description(signal)
        row[f"{agent}_weight"] = round(weight, 6)
        row[f"{agent}_reason"] = reasons.get(agent, "")

    row["weighted_signal"] = round(_clamp(weighted_signal), 4)
    row["signal_direction"] = _signal_description(row["weighted_signal"])
    row["dma_method"] = "eDMA_Catania_Nonejad_2018_dynamic_posterior"
    row["dma_history_used"] = dma.get("history_used")
    row["dma_history_observations"] = dma.get("history_observations")
    row["dma_history_csv"] = dma.get("history_csv")
    row["dma_alpha"] = dma.get("alpha")

    finance = snapshots.get("finance") or {}
    market = snapshots.get("market") or {}
    tech = snapshots.get("tech") or {}
    valuation = snapshots.get("valuation") or {}
    issue = snapshots.get("issue") or {}
    macro = snapshots.get("macro") or {}

    row.update(
        {
            "monthly_return_pct": _round(_extract_metric(market, "monthly_return_pct", "monthly_return_%")),
            "mdd_pct": _round(_extract_metric(market, "mdd_pct", "annual_mdd_%")),
            "market_total_score": _round(_extract_metric(market, "total_score")),
            "sales_growth_pct": _round(_extract_metric(finance, "sales_growth_%")),
            "operating_margin_pct": _round(_extract_metric(finance, "operating_margin_%")),
            "debt_ratio_pct": _round(_extract_metric(finance, "debt_ratio_%")),
            "fcf": _round(_extract_metric(finance, "fcf"), 2),
            "valuation_score": _round(_get_nested(valuation, ["scorecard", "score"]) or _extract_metric(valuation, "score")),
            "valuation_psr_gap": _round(_get_nested(valuation, ["peer_comps", "psr_gap"])),
            "tech_score": _round(
                _extract_metric(
                    tech,
                    "final_tech_investor_score",
                    "peer_adjusted_bridge_score",
                    "final_bridge_score_after_ip_evidence",
                )
            ),
            "ip_evidence_score": _round(_extract_metric(tech, "ip_evidence_composite_score")),
            "issue_news_count": _round(_extract_metric(issue, "news_count"), 0),
            "issue_positive_terms": _round(_extract_metric(issue, "positive_terms"), 0),
            "issue_negative_terms": _round(_extract_metric(issue, "negative_terms"), 0),
            "macro_score": _round(_extract_metric(macro, "macro_score")),
        }
    )

    return row

def run_monthly_signal_export(
    *,
    month: str,
    universe_csv: str | Path,
    field: str = "반도체",
    limit: int | None = None,
    output_dir: str | Path | None = None,
    weights: dict[str, float] | None = None,
    run_id: str | None = None,
) -> Path:
    window = MonthWindow.parse(month)
    weights = weights or DEFAULT_WEIGHTS

    targets = read_universe(
        universe_csv,
        field=field,
        limit=limit,
    )

    if not targets:
        raise RuntimeError(f"universe CSV에서 실행 대상을 찾지 못했습니다: {universe_csv}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id = run_id or f"eval_direct_{window.month}_{ts}"

    print(
        f"[start/direct] month={window.month}, "
        f"as_of_date={window.as_of_date}, "
        f"companies={len(targets)}, "
        f"run_id={run_id}"
    )
    print("[mode] Google Sheets Chair replay를 사용하지 않고 evaluation mini-chair로 CSV 1개만 생성합니다.")

    rows: list[dict[str, Any]] = []

    for idx, target in enumerate(targets, 1):
        print(f"[{idx}/{len(targets)}] {target.company_name}/{target.company_dir} 월별 snapshot 생성 중...")

        snapshots = build_all_snapshots(target, window)

        row = _build_signal_row(
            month=window.month,
            as_of_date=window.as_of_date,
            target=target,
            snapshots=snapshots,
            weights=weights,
            run_id=run_id,
        )

        rows.append(row)

    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = (
            project_root()
            / "data"
            / field
            / "_sector_common"
            / "history_sheets_exports"
        )

    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"signal_df_{window.month}_{ts}.csv"

    df = pd.DataFrame(rows)

    front_cols = [
        "date",
        "field",
        "company",
        "ticker",
        "stock_code",
        "recommendation",
        "weighted_signal",
        "as_of_date",
        "signal_source",
    ]
    for agent in AGENTS:
        front_cols.extend([
            f"{agent}_signal",
            f"{agent}_weighted_signal",
            f"{agent}_recommendation",
            f"{agent}_weight",
        ])

    df = df[[c for c in front_cols if c in df.columns] + [c for c in df.columns if c not in front_cols]]
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"[DONE] monthly signal_df 저장 완료: {out_path}")

    return out_path