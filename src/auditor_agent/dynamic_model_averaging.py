from __future__ import annotations

"""Dynamic Model Averaging utilities for AlphaProve Auditor/Chair.

This module deliberately removes fixed agent weights such as
preset finance/tech/etc. weights.  Each specialist agent is treated as a candidate model
and its weight is updated by the Dynamic Model Averaging (DMA) posterior
probability formula.

Formula implemented
-------------------
For available agents i = 1..N:

    prior_i,0 = 1 / N

    prior_i,t|t-1 =
        posterior_i,t-1 ** alpha
        / sum_j(posterior_j,t-1 ** alpha)

    posterior_i,t =
        prior_i,t|t-1 * predictive_likelihood_i,t
        / sum_j(prior_j,t|t-1 * predictive_likelihood_j,t)

When a historical signal/performance CSV is available, the predictive
likelihood is computed from the realized target and each agent's historical
signal with a Gaussian predictive density.  When no realized history is
available, the module returns an equal prior over the currently available
agents instead of inventing subjective agent ranges.

References
----------
- Raftery, Karny & Ettler (2010), Dynamic Model Averaging.
- Catania & Nonejad (2018), "Dynamic Model Averaging for Practitioners in
  Economics and Finance: The eDMA Package".
"""

import csv
import math
import os
from pathlib import Path
from typing import Any, Iterable

AGENT_ORDER: tuple[str, ...] = (
    "finance",
    "valuation",
    "tech",
    "market",
    "issue",
    "macro",
)

LABEL_ORDER: tuple[str, ...] = ("매수", "보유", "매도")

LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "매수": ("매수", "buy", "strong_buy", "positive", "bullish", "+1", "1"),
    "보유": ("보유", "hold", "neutral", "중립", "관망", "0"),
    "매도": ("매도", "sell", "negative", "bearish", "avoid", "비중축소", "-1"),
}

AGENT_ALIASES: dict[str, tuple[str, ...]] = {
    "finance": ("finance", "finance_signal", "finance_auditor_signal", "재무", "재무_signal"),
    "valuation": ("valuation", "valuation_signal", "valuation_auditor_signal", "가치평가", "밸류에이션"),
    "tech": ("tech", "tech_signal", "tech_auditor_signal", "기술", "tech_to_value"),
    "market": ("market", "market_signal", "market_auditor_signal", "시장"),
    "issue": ("issue", "issue_signal", "issue_auditor_signal", "이슈"),
    "macro": ("macro", "macro_signal", "macro_auditor_signal", "거시"),
}

TARGET_COLUMNS: tuple[str, ...] = (
    "target_signal",
    "actual_signal",
    "future_signal",
    "realized_signal",
    "excess_return_signal",
    "excess_return",
    "future_excess_return",
    "realized_excess_return",
    "next_1m_excess_return",
    "one_month_excess_return",
    "actual_excess_return",
    "return_excess_1m",
    "next_month_excess_return",
    "excess_return_1m",
    "stock_return_1m",
    "benchmark_return_1m",
    "target_return_1m",
    "future_return",
    "realized_return",
    "actual_return",
    "next_1m_return",
    "final_label_actual",
    "actual_label",
    "target_label",
)


def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        return v if math.isfinite(v) else None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "na", "n/a", "확인 제한"}:
        return None
    text = text.replace(",", "").replace("%", "")
    try:
        v = float(text)
    except Exception:
        return None
    return v if math.isfinite(v) else None


def _clip_signal(value: Any) -> float | None:
    v = _safe_float(value)
    if v is None:
        return None
    if abs(v) > 1.0 and abs(v) <= 100.0:
        # Some exported files store percentages or scores.  Direction is what
        # matters for DMA likelihood, so rescale safely to [-1, 1].
        v = v / 100.0
    return max(-1.0, min(1.0, float(v)))


def _label_to_signal(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    if text in {"매수", "buy", "strong_buy", "positive", "상향", "+1", "1"}:
        return 1.0
    if text in {"보유", "hold", "neutral", "중립", "0"}:
        return 0.0
    if text in {"매도", "sell", "negative", "하향", "-1"}:
        return -1.0
    return None


def normalize_recommendation_label(value: Any) -> str | None:
    """Normalize Korean/English buy-hold-sell labels.

    This helper never maps a numeric signal threshold to a recommendation.
    It only normalizes labels that already exist in a packet/history file.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    low = text.lower()
    for label, aliases in LABEL_ALIASES.items():
        if low in aliases or text in aliases:
            return label
    if "매수" in text or "buy" in low or "bullish" in low:
        return "매수"
    if "매도" in text or "sell" in low or "bearish" in low or "avoid" in low:
        return "매도"
    if "보유" in text or "hold" in low or "neutral" in low or "중립" in text or "관망" in text:
        return "보유"
    return None


def _target_label(row: dict[str, Any]) -> str | None:
    """Extract realized target label from a history row.

    Preferred targets are explicit labels.  If only realized return/excess-return
    columns exist, the realized sign is used as the objective outcome direction:
    positive excess return -> 매수, negative excess return -> 매도, exactly zero -> 보유.
    This is outcome labeling for training/evaluation, not a current signal cutoff.
    """
    for col in TARGET_COLUMNS:
        if col not in row:
            continue
        label = normalize_recommendation_label(row.get(col))
        if label:
            return label
        numeric = _safe_float(row.get(col))
        if numeric is None:
            continue
        if "return" in col.lower() or "수익률" in col or "excess" in col.lower():
            if numeric > 0:
                return "매수"
            if numeric < 0:
                return "매도"
            return "보유"
    return None


def _label_signal(label: str | None) -> float | None:
    if label == "매수":
        return 1.0
    if label == "보유":
        return 0.0
    if label == "매도":
        return -1.0
    return None


def _target_signal_from_label_or_numeric(row: dict[str, Any]) -> float | None:
    label = _target_label(row)
    if label is not None:
        return _label_signal(label)
    return None


def _get_agent_label(row: dict[str, Any], agent: str) -> str | None:
    preferred = (
        f"{agent}_recommendation",
        f"{agent}_label",
        f"{agent}_prediction",
        f"{agent}_auditor_recommendation",
        f"{agent}_final_recommendation",
    )
    for col in preferred:
        if col in row:
            label = normalize_recommendation_label(row.get(col))
            if label:
                return label
    for col, value in row.items():
        lc = str(col).lower()
        if agent in lc and any(tok in lc for tok in ("recommend", "label", "prediction", "opinion")):
            label = normalize_recommendation_label(value)
            if label:
                return label
    return None


def _target_signal(row: dict[str, Any]) -> float | None:
    label_signal = _target_signal_from_label_or_numeric(row)
    if label_signal is not None:
        return label_signal
    for col in TARGET_COLUMNS:
        if col not in row:
            continue
        label_signal = _label_to_signal(row.get(col))
        if label_signal is not None:
            return label_signal

        numeric = _safe_float(row.get(col))
        if numeric is None:
            continue

        # Return columns are used only by sign.  This avoids arbitrary return
        # scaling assumptions while preserving objective direction.
        if "return" in col.lower() or "수익률" in col:
            if numeric > 0:
                return 1.0
            if numeric < 0:
                return -1.0
            return 0.0

        return _clip_signal(numeric)
    return None


def _get_agent_signal(row: dict[str, Any], agent: str) -> float | None:
    for col in AGENT_ALIASES.get(agent, (agent,)):
        if col in row:
            v = _clip_signal(row.get(col))
            if v is not None:
                return v
    # Flexible fallback: columns such as finance_weighted_signal or
    # finance_direction_signal.
    for col, value in row.items():
        lc = str(col).lower()
        if agent in lc and "signal" in lc:
            v = _clip_signal(value)
            if v is not None:
                return v
    return None


def _normal_pdf(y: float, mean: float, sigma: float) -> float:
    sigma = max(float(sigma), 1e-6)
    z = (y - mean) / sigma
    return math.exp(-0.5 * z * z) / (math.sqrt(2.0 * math.pi) * sigma)


def _normalize_weights(weights: dict[str, float], available_agents: Iterable[str]) -> dict[str, float]:
    cleaned = {a: max(0.0, float(weights.get(a, 0.0))) for a in available_agents}
    total = sum(cleaned.values())
    if total <= 0:
        agents = list(available_agents)
        if not agents:
            return {}
        return {a: 1.0 / len(agents) for a in agents}
    return {a: cleaned[a] / total for a in cleaned}


def _forget(weights: dict[str, float], alpha: float) -> dict[str, float]:
    alpha = max(0.0, min(1.0, float(alpha)))
    powered = {a: max(w, 1e-12) ** alpha for a, w in weights.items()}
    return _normalize_weights(powered, powered.keys())


def discover_dma_history_csv(project_root: str | Path | None = None) -> Path | None:
    """Find the latest local signal/performance CSV for DMA.

    Override with ALPHAPROVE_DMA_HISTORY_CSV when a specific file should be
    used.  The function never downloads data and never fabricates observations.
    """

    env_path = os.getenv("ALPHAPROVE_DMA_HISTORY_CSV", "").strip().strip('"')
    if env_path:
        p = Path(env_path)
        return p if p.exists() else None

    base = Path(project_root or Path.cwd())
    patterns = [
        "data/*/_sector_common/history_sheets_exports/**/*.csv",
        "data/**/history_sheets_exports/**/*.csv",
        "data/**/signal_df*.csv",
        "data/**/eval_*signal*.csv",
    ]
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(base.glob(pattern))

    candidates = [p for p in candidates if p.is_file() and p.stat().st_size > 0]
    if not candidates:
        return None

    def has_realized_target(path: Path) -> bool:
        try:
            rows = _read_history_rows(path, max_rows=25)
        except Exception:
            return False
        return any(_target_label(row) is not None or _target_signal(row) is not None for row in rows)

    target_candidates = [p for p in candidates if has_realized_target(p)]
    if target_candidates:
        return max(target_candidates, key=lambda p: p.stat().st_mtime)
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _read_history_rows(path: Path, max_rows: int = 5000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
    except UnicodeDecodeError:
        with path.open("r", encoding="cp949", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
    except Exception:
        return []

    # Keep the most recent rows if the file is very large.
    if len(rows) > max_rows:
        rows = rows[-max_rows:]
    return rows


def _sort_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    date_cols = ("date", "as_of_date", "기준일", "month", "월")
    def key(row: dict[str, Any]) -> str:
        for col in date_cols:
            if row.get(col):
                return str(row.get(col))
        return ""
    return sorted(rows, key=key)


def _posterior_from_history(
    rows: list[dict[str, Any]],
    available_agents: list[str],
    *,
    alpha: float,
) -> tuple[dict[str, float], dict[str, float], int]:
    """Sequential DMA update using historical realized direction."""

    weights = {a: 1.0 / len(available_agents) for a in available_agents}
    squared_errors: dict[str, list[float]] = {a: [] for a in available_agents}
    likelihood_sums: dict[str, float] = {a: 0.0 for a in available_agents}
    used = 0

    for row in _sort_rows(rows):
        y = _target_signal(row)
        if y is None:
            continue

        signals = {a: _get_agent_signal(row, a) for a in available_agents}
        if all(v is None for v in signals.values()):
            continue

        prior = _forget(weights, alpha)
        likelihoods: dict[str, float] = {}

        for agent in available_agents:
            signal = signals.get(agent)
            if signal is None:
                likelihoods[agent] = 1e-12
                continue

            # Use the agent's own rolling RMSE when at least three past errors
            # exist; otherwise start with sigma=1 on the [-1, 1] signal scale.
            past_errors = squared_errors[agent]
            if len(past_errors) >= 3:
                sigma = math.sqrt(sum(past_errors) / len(past_errors))
                sigma = max(sigma, 0.10)
            else:
                sigma = 1.0

            ll = _normal_pdf(float(y), float(signal), sigma)
            likelihoods[agent] = max(ll, 1e-12)

        weights = _normalize_weights(
            {a: prior[a] * likelihoods[a] for a in available_agents},
            available_agents,
        )

        for agent, signal in signals.items():
            if signal is not None:
                squared_errors[agent].append((float(y) - float(signal)) ** 2)
                likelihood_sums[agent] += likelihoods.get(agent, 0.0)

        used += 1

    if used == 0:
        return {a: 1.0 / len(available_agents) for a in available_agents}, {a: 1.0 for a in available_agents}, 0

    avg_likelihood = {
        a: likelihood_sums[a] / max(1, len(squared_errors[a]))
        for a in available_agents
    }
    return weights, avg_likelihood, used


def _weight_ranges(weights: dict[str, float], effective_n: int) -> dict[str, dict[str, float]]:
    """Approximate 95% uncertainty ranges for posterior weights.

    If no realized history exists, no artificial range is created: lower=upper=weight.
    """

    ranges: dict[str, dict[str, float]] = {}
    if effective_n <= 1:
        for a, w in weights.items():
            ranges[a] = {"lower": round(w, 6), "upper": round(w, 6)}
        return ranges

    n = float(effective_n)
    for a, w in weights.items():
        se = math.sqrt(max(w * (1.0 - w), 0.0) / n)
        lower = max(0.0, w - 1.96 * se)
        upper = min(1.0, w + 1.96 * se)
        ranges[a] = {"lower": round(lower, 6), "upper": round(upper, 6)}
    return ranges


def compute_dma_weights(
    agent_packets: dict[str, dict[str, Any]],
    *,
    signals: dict[str, float] | None = None,
    history_csv: str | Path | None = None,
    project_root: str | Path | None = None,
    alpha: float | None = None,
) -> dict[str, Any]:
    """Return DMA posterior weights for the currently available agents.

    Parameters
    ----------
    agent_packets:
        Mapping from agent name to Chair/Auditor packet.  Only agents with a
        packet are included in the posterior.
    signals:
        Optional current signal mapping.  It is stored in diagnostics but does
        not override realized historical likelihood.
    history_csv:
        Optional explicit CSV path.  If omitted, the function checks
        ALPHAPROVE_DMA_HISTORY_CSV and then searches common local export folders.
    alpha:
        DMA forgetting factor.  Default 0.99 follows the eDMA paper's practical
        monthly/quarterly recommendation; override with ALPHAPROVE_DMA_ALPHA.
    """

    available_agents = [a for a in AGENT_ORDER if isinstance(agent_packets.get(a), dict)]
    if not available_agents:
        return {
            "method": "dma_no_available_agents",
            "weights": {},
            "weights_adjusted": {},
            "history_used": False,
            "history_observations": 0,
        }

    if alpha is None:
        alpha = _safe_float(os.getenv("ALPHAPROVE_DMA_ALPHA")) or 0.99
    alpha = max(0.0, min(1.0, float(alpha)))

    csv_path = Path(history_csv) if history_csv else discover_dma_history_csv(project_root)
    rows = _read_history_rows(csv_path) if csv_path and csv_path.exists() else []

    weights, likelihoods, used = _posterior_from_history(rows, available_agents, alpha=alpha)

    # If no realized performance history exists, the only objective prior is the
    # equal prior over available models.  This is intentionally not replaced by
    # subjective finance/tech/valuation base weights.
    history_used = used > 0
    if not history_used:
        weights = {a: 1.0 / len(available_agents) for a in available_agents}
        likelihoods = {a: 1.0 for a in available_agents}

    weights = _normalize_weights(weights, available_agents)

    return {
        "method": "dynamic_model_averaging_posterior",
        "reference": "Raftery et al. (2010); Catania & Nonejad (2018 eDMA)",
        "prior_policy": "uniform_prior_over_available_agents; no fixed finance/tech/valuation base weights",
        "update_formula": (
            "pi_pred_i = pi_prev_i^alpha / sum_j(pi_prev_j^alpha); "
            "pi_post_i = pi_pred_i * predictive_likelihood_i / sum_j(pi_pred_j * predictive_likelihood_j)"
        ),
        "alpha": round(alpha, 6),
        "history_csv": str(csv_path) if csv_path else None,
        "history_used": history_used,
        "history_observations": used,
        "available_agents": available_agents,
        "agent_likelihoods": {a: round(float(likelihoods.get(a, 0.0)), 6) for a in available_agents},
        "current_signals": {a: round(float(signals[a]), 6) for a in (signals or {}) if a in available_agents and signals.get(a) is not None},
        "weights": {a: round(float(weights[a]), 6) for a in available_agents},
        "weights_adjusted": {a: round(float(weights[a]), 6) for a in available_agents},
        "weight_ranges_95": _weight_ranges(weights, used),
    }



def _empty_label_distribution() -> dict[str, float]:
    return {label: 0.0 for label in LABEL_ORDER}


def _normalize_distribution(values: dict[str, float]) -> dict[str, float]:
    cleaned = {label: max(0.0, float(values.get(label, 0.0) or 0.0)) for label in LABEL_ORDER}
    total = sum(cleaned.values())
    if total <= 0:
        return {label: 1.0 / len(LABEL_ORDER) for label in LABEL_ORDER}
    return {label: cleaned[label] / total for label in LABEL_ORDER}




def _directional_label_from_signal(signal: float | None) -> str:
    """Convert a signed signal to a direction without a fixed no-trade band.

    This is used only when an old agent packet has no explicit categorical
    recommendation.  Positive mass maps to Buy, negative mass maps to Sell,
    and exact zero/missing remains Hold.  There is intentionally no fixed numeric Buy/Hold/Sell band or
    other arbitrary middle band here.
    """
    v = _safe_float(signal)
    if v is None or not math.isfinite(v):
        return "보유"
    if v > 0:
        return "매수"
    if v < 0:
        return "매도"
    return "보유"


def _signal_label_distribution(signal: float | None) -> dict[str, float]:
    """Soft Buy/Hold/Sell distribution from a signed signal.

    The distribution is not a threshold classifier.  It keeps Hold as a
    reject/no-trade option only when direction is unavailable or the Buy/Sell
    direction is exactly tied.  Otherwise most probability mass follows the
    sign of the continuous signal while the remaining mass expresses residual
    uncertainty.
    """
    v = _safe_float(signal)
    if v is None or not math.isfinite(v):
        return {"매수": 0.0, "보유": 1.0, "매도": 0.0}
    v = max(-1.0, min(1.0, float(v)))
    mag = abs(v)
    if mag == 0:
        return {"매수": 0.0, "보유": 1.0, "매도": 0.0}
    # Directional mass increases smoothly with magnitude.  The constants below
    # are calibration parameters for probability shaping, not a decision band.
    directional_mass = 0.50 + 0.45 * mag
    hold_mass = max(0.0, 1.0 - directional_mass)
    if v > 0:
        return {"매수": directional_mass, "보유": hold_mass, "매도": 0.0}
    return {"매수": 0.0, "보유": hold_mass, "매도": directional_mass}


def _label_from_distribution(dist: dict[str, float], *, signal: float | None = None) -> str:
    """Select a label from posterior probabilities without fixed thresholds.

    If Buy and Sell posterior masses are tied, Hold is used as the
    reject/no-trade class.  Otherwise the stronger directional mass wins even
    when Hold is numerically large, so weak-but-directional signals are no
    longer automatically absorbed into Hold.
    """
    buy = float(dist.get("매수", 0.0) or 0.0)
    sell = float(dist.get("매도", 0.0) or 0.0)
    if buy > sell:
        return "매수"
    if sell > buy:
        return "매도"
    return _directional_label_from_signal(signal)


def _empirical_label_distribution(
    rows: list[dict[str, Any]],
    agent: str,
    current_label: str | None,
    *,
    current_signal: float | None = None,
    smoothing: float,
) -> tuple[dict[str, float], int, str]:
    """P(realized label | current agent forecast) from history.

    Preferred calibration is categorical: P(y | current_label).  When an old
    packet has no categorical label, a nonparametric empirical calibration uses
    historical rows with similar continuous signal values.  This still avoids a
    hard buy/hold/sell cutoff on the current weighted signal.
    """
    counts = {label: float(smoothing) for label in LABEL_ORDER}
    used = 0

    if current_label:
        for row in rows:
            target = _target_label(row)
            if target not in LABEL_ORDER:
                continue
            pred = _get_agent_label(row, agent)
            if pred != current_label:
                continue
            counts[target] += 1.0
            used += 1
        if used:
            return _normalize_distribution(counts), used, "conditional_realized_distribution_by_agent_label"

    # If there is no usable categorical history for the current label, calibrate
    # from similar historical signal values.  The bandwidth is the empirical
    # standard deviation of that agent's historical signals, so it is data-based.
    sig = _clip_signal(current_signal)
    signal_rows: list[tuple[float, str]] = []
    for row in rows:
        target = _target_label(row)
        if target not in LABEL_ORDER:
            continue
        past_signal = _get_agent_signal(row, agent)
        if past_signal is not None:
            signal_rows.append((float(past_signal), target))
    if sig is not None and signal_rows:
        vals = [x for x, _ in signal_rows]
        mean = sum(vals) / len(vals)
        variance = sum((x - mean) ** 2 for x in vals) / max(1, len(vals) - 1)
        bandwidth = math.sqrt(variance) if variance > 0 else 1.0
        bandwidth = max(bandwidth, 1e-6)
        counts = {label: float(smoothing) for label in LABEL_ORDER}
        for past_signal, target in signal_rows:
            z = (float(sig) - past_signal) / bandwidth
            kernel_w = math.exp(-0.5 * z * z)
            counts[target] += kernel_w
            used += 1
        return _normalize_distribution(counts), used, "kernel_calibrated_realized_distribution_by_agent_signal"

    # Last objective fallback: unconditional realized distribution for this agent.
    counts = {label: float(smoothing) for label in LABEL_ORDER}
    for row in rows:
        target = _target_label(row)
        if target not in LABEL_ORDER:
            continue
        if _get_agent_label(row, agent) is None and _get_agent_signal(row, agent) is None:
            continue
        counts[target] += 1.0
        used += 1
    source = "agent_unconditional_realized_distribution" if used else "no_realized_label_history"
    return _normalize_distribution(counts), used, source


def compute_dma_label_posterior(
    agent_decisions: dict[str, dict[str, Any]],
    weights: dict[str, float],
    *,
    history_csv: str | Path | None = None,
    project_root: str | Path | None = None,
    smoothing: float | None = None,
) -> dict[str, Any]:
    """Combine current agent recommendation labels with DMA posterior weights.

    This function is intentionally NOT a numeric signal-threshold classifier.
    The final recommendation is selected from the DMA-weighted current
    categorical labels only:

        P_current(y=c | F_t) = sum_i pi_i,t * I(label_i,t = c)

    where pi_i,t is the DMA posterior model weight and label_i,t is the current
    recommendation label already produced by the specialist/auditor packet.

    Realized history, when available, is still computed as a diagnostic
    calibration view:

        P_calibrated(y=c | F_t)
          = sum_i pi_i,t * P(y=c | label_i,t or signal_i,t, realized history)

    but it does not override the current-label posterior final recommendation.
    This prevents the final label from being recreated from a weighted_signal
    cutoff or from an unconditional realized-return prior.
    """
    if smoothing is None:
        smoothing = _safe_float(os.getenv("ALPHAPROVE_DMA_LABEL_SMOOTHING"))
        smoothing = 0.5 if smoothing is None else max(0.0, float(smoothing))

    csv_path = Path(history_csv) if history_csv else discover_dma_history_csv(project_root)
    rows = _read_history_rows(csv_path) if csv_path and csv_path.exists() else []
    rows_with_target = [row for row in rows if _target_label(row) in LABEL_ORDER]
    history_used = bool(rows_with_target)

    available_agents = [a for a in AGENT_ORDER if isinstance(agent_decisions.get(a), dict)]
    norm_weights = _normalize_weights(weights, available_agents) if available_agents else {}

    current_posterior = _empty_label_distribution()
    calibrated_posterior = _empty_label_distribution()
    agent_label_models: dict[str, Any] = {}

    for agent in available_agents:
        dec = agent_decisions.get(agent, {})
        current_label = normalize_recommendation_label(
            dec.get("recommendation")
            or dec.get("auditor_recommendation")
            or dec.get("original_recommendation")
        )
        w = float(norm_weights.get(agent, 0.0) or 0.0)

        current_dist = _empty_label_distribution()
        if current_label in LABEL_ORDER and str(dec.get("recommendation_label_source") or "") != "neutral_placeholder_no_categorical_label":
            current_dist[current_label] = 1.0
            current_source = "current_label_one_hot"
        else:
            # Old packets often have no explicit Buy/Hold/Sell label.  The v49
            # placeholder set those packets to Hold, which made Hold dominate.
            # v50 instead converts the continuous agent signal into a soft
            # directional probability distribution with Hold reserved for exact
            # tie/missing direction.
            current_dist = _signal_label_distribution(dec.get("signal"))
            current_source = "signal_soft_directional_distribution_no_fixed_band"

        for label in LABEL_ORDER:
            current_posterior[label] += w * float(current_dist.get(label, 0.0) or 0.0)

        if history_used:
            calibrated_dist, used, calibrated_source = _empirical_label_distribution(
                rows_with_target,
                agent,
                current_label,
                current_signal=dec.get("signal"),
                smoothing=float(smoothing),
            )
        else:
            calibrated_dist = dict(current_dist)
            used = 0
            calibrated_source = "current_label_distribution_no_realized_history"

        for label in LABEL_ORDER:
            calibrated_posterior[label] += w * float(calibrated_dist.get(label, 0.0) or 0.0)

        agent_label_models[agent] = {
            "current_label": current_label or "",
            "weight": round(w, 6),
            "current_label_source": current_source,
            "current_label_distribution": {
                label: round(float(current_dist.get(label, 0.0) or 0.0), 6)
                for label in LABEL_ORDER
            },
            "history_rows_used": used,
            "calibration_source": calibrated_source,
            "calibrated_label_distribution": {
                label: round(float(calibrated_dist.get(label, 0.0) or 0.0), 6)
                for label in LABEL_ORDER
            },
        }

    current_posterior = _normalize_distribution(current_posterior)
    calibrated_posterior = _normalize_distribution(calibrated_posterior)

    final_label = _label_from_distribution(current_posterior) if current_posterior else "보유"
    calibrated_final_label = _label_from_distribution(calibrated_posterior) if calibrated_posterior else "보유"

    rounded_current = {
        label: round(float(current_posterior.get(label, 0.0) or 0.0), 6)
        for label in LABEL_ORDER
    }
    rounded_calibrated = {
        label: round(float(calibrated_posterior.get(label, 0.0) or 0.0), 6)
        for label in LABEL_ORDER
    }

    return {
        "method": "dma_signal_soft_posterior_reject_option_no_fixed_band_v50",
        "formula": "P_current(y=c|F_t)=sum_i pi_i,t * I(label_i,t=c)",
        "selection_policy": "final_recommendation follows stronger Buy-vs-Sell posterior; Hold is reject/no-trade only for tied or unavailable direction; weighted_signal is diagnostic only",
        "history_csv": str(csv_path) if csv_path else None,
        "history_used": history_used,
        "history_observations": len(rows_with_target),
        "smoothing": float(smoothing),
        # Keep the existing key for downstream compatibility.  It now explicitly
        # means the current-label posterior, not a weighted_signal cutoff.
        "label_posterior": rounded_current,
        "current_label_posterior": rounded_current,
        "realized_calibrated_label_posterior": rounded_calibrated,
        "final_recommendation": final_label,
        "realized_calibrated_final_recommendation": calibrated_final_label,
        "agent_label_models": agent_label_models,
    }


def _get_named_signal(row: dict[str, Any], model: str, aliases: dict[str, tuple[str, ...]] | None = None) -> float | None:
    """Flexible signal lookup for generic DMA models/components."""
    names = [model]
    if aliases and model in aliases:
        names.extend(list(aliases[model]))
    names.extend([f"{model}_signal", f"{model}_component_signal"])
    for col in names:
        if col in row:
            v = _clip_signal(row.get(col))
            if v is not None:
                return v
    for col, value in row.items():
        lc = str(col).lower()
        if model.lower() in lc and "signal" in lc:
            v = _clip_signal(value)
            if v is not None:
                return v
    return None


def _posterior_from_generic_history(
    rows: list[dict[str, Any]],
    model_names: list[str],
    *,
    alpha: float,
    aliases: dict[str, tuple[str, ...]] | None = None,
) -> tuple[dict[str, float], dict[str, float], int]:
    """Sequential DMA update for arbitrary model/component signal columns."""

    if not model_names:
        return {}, {}, 0

    weights = {m: 1.0 / len(model_names) for m in model_names}
    squared_errors: dict[str, list[float]] = {m: [] for m in model_names}
    likelihood_sums: dict[str, float] = {m: 0.0 for m in model_names}
    used = 0

    for row in _sort_rows(rows):
        y = _target_signal(row)
        if y is None:
            continue

        signals = {m: _get_named_signal(row, m, aliases) for m in model_names}
        if all(v is None for v in signals.values()):
            continue

        prior = _forget(weights, alpha)
        likelihoods: dict[str, float] = {}
        for model in model_names:
            signal = signals.get(model)
            if signal is None:
                likelihoods[model] = 1e-12
                continue
            past_errors = squared_errors[model]
            if len(past_errors) >= 3:
                sigma = math.sqrt(sum(past_errors) / len(past_errors))
                sigma = max(sigma, 0.10)
            else:
                sigma = 1.0
            likelihoods[model] = max(_normal_pdf(float(y), float(signal), sigma), 1e-12)

        weights = _normalize_weights({m: prior[m] * likelihoods[m] for m in model_names}, model_names)

        for model, signal in signals.items():
            if signal is not None:
                squared_errors[model].append((float(y) - float(signal)) ** 2)
                likelihood_sums[model] += likelihoods.get(model, 0.0)
        used += 1

    if used == 0:
        return {m: 1.0 / len(model_names) for m in model_names}, {m: 1.0 for m in model_names}, 0

    avg_likelihood = {m: likelihood_sums[m] / max(1, len(squared_errors[m])) for m in model_names}
    return weights, avg_likelihood, used


def compute_signal_dma_weights(
    model_signals: dict[str, float],
    *,
    model_aliases: dict[str, tuple[str, ...]] | None = None,
    history_csv: str | Path | None = None,
    project_root: str | Path | None = None,
    alpha: float | None = None,
) -> dict[str, Any]:
    """Return DMA posterior weights for arbitrary signals/components.

    This is used inside the Auditor quantitative rubric to remove hard-coded
    component weights as well as hard-coded agent weights.  Each component is
    treated as a candidate model.  If a history CSV contains matching component
    signal columns and a realized target column, DMA posterior probabilities are
    computed from the same Raftery/Catania-Nonejad update.  If no such history is
    available, the only objective fallback is the uniform prior over available
    components; no sample or subjective weights are fabricated.
    """

    clean_signals: dict[str, float] = {}
    for name, value in (model_signals or {}).items():
        v = _clip_signal(value)
        if v is not None:
            clean_signals[str(name)] = float(v)

    model_names = list(clean_signals.keys())
    if not model_names:
        return {
            "method": "dma_no_available_component_signals",
            "weights": {},
            "weights_adjusted": {},
            "history_used": False,
            "history_observations": 0,
        }

    if alpha is None:
        alpha = _safe_float(os.getenv("ALPHAPROVE_DMA_ALPHA")) or 0.99
    alpha = max(0.0, min(1.0, float(alpha)))

    env_component_history = os.getenv("ALPHAPROVE_DMA_COMPONENT_HISTORY_CSV", "").strip().strip('"')
    csv_path = Path(history_csv or env_component_history) if (history_csv or env_component_history) else discover_dma_history_csv(project_root)
    rows = _read_history_rows(csv_path) if csv_path and csv_path.exists() else []

    weights, likelihoods, used = _posterior_from_generic_history(
        rows,
        model_names,
        alpha=alpha,
        aliases=model_aliases,
    )
    history_used = used > 0
    if not history_used:
        weights = {m: 1.0 / len(model_names) for m in model_names}
        likelihoods = {m: 1.0 for m in model_names}

    weights = _normalize_weights(weights, model_names)
    return {
        "method": "dynamic_model_averaging_component_posterior",
        "reference": "Raftery et al. (2010); Catania & Nonejad (2018 eDMA)",
        "prior_policy": "uniform_prior_over_available_components; no fixed component weights",
        "alpha": round(alpha, 6),
        "history_csv": str(csv_path) if csv_path else None,
        "history_used": history_used,
        "history_observations": used,
        "available_models": model_names,
        "model_likelihoods": {m: round(float(likelihoods.get(m, 0.0)), 6) for m in model_names},
        "current_signals": {m: round(float(clean_signals[m]), 6) for m in model_names},
        "weights": {m: round(float(weights[m]), 6) for m in model_names},
        "weights_adjusted": {m: round(float(weights[m]), 6) for m in model_names},
        "weight_ranges_95": _weight_ranges(weights, used),
    }
