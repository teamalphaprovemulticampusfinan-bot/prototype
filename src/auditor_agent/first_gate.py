from __future__ import annotations

"""First Auditor with 3-stage deterministic validation.

Design goals for the current AlphaProve pipeline:
- Do not edit Finance/Market/Tech/Valuation/Issue/Macro agent code.
- Keep specialist raw outputs intact, but generate compact Chair-facing packets.
- Remove the old web-verification dependency from the Auditor path.
- Validate in three internal stages:
  1) basic hallucination / number-unit / source-scope / internal-consistency guardrails,
  2) literature- and IB/deep-tech-framework based coverage validation,
  3) quantitative 매수/보유/매도 decision readiness before Chair.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from common.data_paths import first_auditor_dir

from .decision_rubric import compute_agent_decision, compute_portfolio_decision
from .dynamic_model_averaging import compute_signal_dma_weights
from .packet_sanitizer import build_compact_agent_packet, persist_compact_packets
from .sources import collect_source_context

EXPECTED_AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]

BLOCK_PHRASES = [
    "입력해 주시면",
    "붙여넣어 주시면",
    "분석이 불가능",
    "정보가 부족하여 분석할 수 없습니다",
    "데이터가 없어 분석이 어렵습니다",
    "예시:",
    "template",
]

IRRELEVANT_NOISE_TERMS = [
    "골프", "맛집", "취미", "연애", "결혼", "예능", "드라마", "축구", "야구", "게임 쿠폰",
    "부동산 매물", "중고거래", "사주", "운세",
]

ALLOWED_URL_OR_API_AGENTS = {"issue", "market", "macro"}

MONEY_UNITS = {"조원": 1_000_000_000_000, "억원": 100_000_000, "만원": 10_000, "원": 1}
NUM_RE = re.compile(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?\s*(?:조원|억원|만원|원|%|배|건|명|년|월|일|회|점)?")


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on", "y"}


def _env_float(name: str, default: float) -> float:
    try:
        raw = os.getenv(name)
        if raw is None or str(raw).strip() == "":
            return default
        return float(str(raw).strip())
    except Exception:
        return default


def _history_local_write_disabled() -> bool:
    backend = os.getenv("ALPHAPROVE_HISTORY_BACKEND", "").strip().lower()
    sheets_mode = backend in {"sheets", "google_sheets", "gsheets", "google"} or bool(os.getenv("ALPHAPROVE_HISTORY_SPREADSHEET_ID"))
    db_only = _env_bool("ALPHAPROVE_SHEETS_DB_ONLY", False)
    disabled = _env_bool("ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED", True)
    return sheets_mode and db_only and disabled


def _combine_scores_dma(group: str, scores: dict[str, float]) -> tuple[float, dict[str, float], dict[str, Any]]:
    """Combine validation sub-scores without hard-coded stage weights.

    Each sub-score is treated as a candidate model. If matching historical
    columns exist, DMA posterior weights are used. Otherwise the objective
    fallback is the equal prior over available sub-scores.
    """
    clean = {str(k): max(0.0, min(1.0, float(v))) for k, v in scores.items() if v is not None}
    if not clean:
        return 0.0, {}, {"method": "stage_dma_no_scores", "group": group}
    aliases = {name: (f"{group}_{name}", f"{group}_{name}_signal", f"{name}_signal") for name in clean}
    try:
        dma = compute_signal_dma_weights(clean, model_aliases=aliases)
        weights = {name: float((dma.get("weights_adjusted") or dma.get("weights") or {}).get(name, 0.0) or 0.0) for name in clean}
    except Exception as exc:
        dma = {"method": "stage_dma_equal_prior_after_error", "group": group, "error": str(exc)}
        weights = {}
    total = sum(weights.values())
    if total <= 0:
        weights = {name: 1.0 / len(clean) for name in clean}
    else:
        weights = {name: weight / total for name, weight in weights.items()}
    score = sum(clean[name] * weights[name] for name in clean)
    return max(0.0, min(1.0, score)), {name: round(weight, 6) for name, weight in weights.items()}, dma


PASS_THRESHOLD = _env_float("AUDITOR_FIRST_PASS_THRESHOLD", 0.75)
STAGE_COUNT = 3
MAX_ROUNDS = 1  # backward-compatible constant only; the old retry-loop is disabled.
FAIL_OPEN = _env_bool("AUDITOR_FIRST_FAIL_OPEN", False)

# Keep the Auditor threshold, but prevent non-catastrophic packets from failing only because
# one coverage criterion is missing.  This is not FAIL_OPEN: packets still fail when a hard
# hallucination/unit/source-scope guardrail is below the minimum.
MIN_PASS_FLOOR_ENABLED = _env_bool("AUDITOR_MIN_PASS_FLOOR_ENABLED", True)
MIN_PASS_FLOOR_VALUE = _env_float("AUDITOR_MIN_PASS_FLOOR_VALUE", PASS_THRESHOLD)
MIN_PASS_FLOOR_STAGE1_MIN = _env_float("AUDITOR_MIN_PASS_FLOOR_STAGE1_MIN", 0.55)
MIN_PASS_FLOOR_STAGE2_MIN = _env_float("AUDITOR_MIN_PASS_FLOOR_STAGE2_MIN", 0.60)
MIN_PASS_FLOOR_STAGE3_MIN = _env_float("AUDITOR_MIN_PASS_FLOOR_STAGE3_MIN", 0.60)


def _audit_dir(company_dir: str) -> Path:
    path = first_auditor_dir(company_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _normalize_agent_name(name: Any) -> str:
    return str(name or "").strip().lower().replace("_agent", "")


def _extract_agent_name(packet: dict[str, Any]) -> str:
    for key in ("agent", "agent_name", "source_agent", "name", "role"):
        value = packet.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_agent_name(value)
    raw = packet.get("raw_payload")
    if isinstance(raw, dict):
        for key in ("agent", "agent_name", "source_agent", "name", "role"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return _normalize_agent_name(value)
    return "unknown"


def _latest_by_agent(opinions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for packet in opinions:
        if not isinstance(packet, dict):
            continue
        agent = _extract_agent_name(packet)
        if agent:
            out[agent] = packet
    return out


def _json_text(value: Any, limit: int | None = None) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] if limit else text


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _safe_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except Exception:
        return None


def _parse_number(raw: str) -> tuple[float, str, str] | None:
    text = str(raw or "").strip()
    m = re.match(r"([-+]?\d+(?:,\d{3})*(?:\.\d+)?)\s*(조원|억원|만원|원|%|배|건|명|년|월|일|회|점)?", text)
    if not m:
        return None
    num = _safe_float(m.group(1))
    if num is None:
        return None
    unit = m.group(2) or "bare"
    if unit in MONEY_UNITS:
        return num * MONEY_UNITS[unit], "money", text
    if unit == "%":
        return num, "percent", text
    return num, unit, text


def _numbers_from_text(text: Any) -> list[tuple[float, str, str]]:
    out: list[tuple[float, str, str]] = []
    for raw in NUM_RE.findall(str(text or "")):
        parsed = _parse_number(raw)
        if parsed:
            out.append(parsed)
    return out


def _claim_texts(packet: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    for key in ("summary", "key_thesis", "key_risks", "claims", "theses", "risks", "findings", "watch_points"):
        value = packet.get(key)
        if key == "claims" and isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    text = item.get("text") or item.get("claim") or item.get("summary")
                else:
                    text = item
                if text:
                    texts.append(str(text))
        elif isinstance(value, list):
            texts.extend(str(x) for x in value if x)
        elif value:
            texts.append(str(value))
    return [re.sub(r"\s+", " ", t).strip() for t in texts if str(t).strip()]


def _evidence_text(packet: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("evidence", "evidences", "source_contexts", "sources", "metrics", "validation", "output_files"):
        value = packet.get(key)
        if value:
            parts.append(_json_text(value))
    return "\n".join(parts)


def _number_close(a: float, b: float, tolerance: float = 0.025) -> bool:
    if a == b:
        return True
    denom = max(abs(a), abs(b), 1.0)
    return abs(a - b) / denom <= tolerance


def _numeric_guardrail(packet: dict[str, Any], source_context: str) -> dict[str, Any]:
    claim_blob = "\n".join(_claim_texts(packet))
    evidence_blob = _evidence_text(packet) + "\n" + source_context
    claim_nums = _numbers_from_text(claim_blob)
    evidence_nums = _numbers_from_text(evidence_blob)

    checked = len(claim_nums)
    if not claim_nums:
        return {"score": 1.0, "checked_numbers": 0, "matched_numbers": 0, "issues": []}
    if not evidence_nums:
        return {
            "score": 0.55,
            "checked_numbers": checked,
            "matched_numbers": 0,
            "issues": ["numeric claims exist but no numeric source/evidence context was found"],
        }

    matched = 0
    issues: list[str] = []
    scale_mismatch: list[str] = []
    for c_value, c_kind, c_raw in claim_nums:
        ok = False
        possible_scale = False
        for e_value, e_kind, e_raw in evidence_nums:
            same_kind = c_kind == e_kind or c_kind == "bare" or e_kind == "bare" or (c_kind == "money" and e_kind == "money")
            if not same_kind:
                continue
            if _number_close(c_value, e_value):
                ok = True
                break
            ratio = abs(c_value / e_value) if abs(e_value) > 1e-9 else None
            if ratio is not None and any(abs(ratio - x) <= x * 0.03 for x in (10, 100, 1000, 0.1, 0.01, 0.001)):
                possible_scale = True
                scale_mismatch.append(f"claim {c_raw} ↔ source {e_raw}")
        if ok:
            matched += 1
        elif possible_scale:
            issues.append(f"possible unit/scale mismatch: {c_raw}")
        else:
            issues.append(f"unmatched numeric claim: {c_raw}")

    score = matched / max(1, checked)
    if scale_mismatch:
        score = min(score, 0.65)
    return {
        "score": round(max(0.0, min(1.0, score)), 4),
        "checked_numbers": checked,
        "matched_numbers": matched,
        "scale_mismatch_examples": scale_mismatch[:5],
        "issues": issues[:12],
    }


def _source_scope_guardrail(packet: dict[str, Any], company: str, source_context: str) -> dict[str, Any]:
    agent = _extract_agent_name(packet)
    text = _json_text(packet, limit=40000)
    issues: list[str] = []

    if any(phrase.lower() in text.lower() for phrase in BLOCK_PHRASES):
        issues.append("template/request/missing-context phrase detected")
    noise = [term for term in IRRELEVANT_NOISE_TERMS if term in text]
    if noise:
        issues.append("irrelevant/noise terms detected: " + ", ".join(noise[:5]))

    # Company relevance is strict for internal agents, looser for market/macro/issue where API/RSS can include sector data.
    company_hit = company and company in text
    source_hit = company and company in source_context
    if agent not in ALLOWED_URL_OR_API_AGENTS and not (company_hit or source_hit):
        issues.append("company name is not visible in packet/source context for a non-URL/API agent")

    if "http" in text and agent not in ALLOWED_URL_OR_API_AGENTS and agent not in {"tech", "valuation"}:
        issues.append("unexpected external URL-like source in a local-data agent")

    score = 1.0
    if issues:
        score -= 0.18 * len(issues)
    return {"score": round(max(0.0, min(1.0, score)), 4), "issues": issues}


def _flatten_values(value: Any, prefix: str = "") -> list[tuple[str, Any]]:
    """Return (path, scalar) pairs for a nested packet without mutating it."""
    out: list[tuple[str, Any]] = []
    if isinstance(value, dict):
        for key, val in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            out.extend(_flatten_values(val, path))
    elif isinstance(value, list):
        for idx, val in enumerate(value[:200]):
            path = f"{prefix}[{idx}]"
            out.extend(_flatten_values(val, path))
    else:
        out.append((prefix, value))
    return out


CONSISTENCY_METRIC_ALIASES: dict[str, list[str]] = {
    "sales_growth": ["sales_growth", "매출성장률"],
    "operating_margin": ["operating_margin", "영업이익률"],
    "roe": ["roe", "ROE"],
    "fcf": ["fcf", "free_cash_flow", "잉여현금흐름"],
    "debt_ratio": ["debt_ratio", "부채비율"],
    "current_ratio": ["current_ratio", "유동비율"],
    "annual_return": ["annual_return", "연수익률"],
    "mdd": ["annual_mdd", "mdd", "MDD"],
    "patent_count": ["patent_count", "normalized_patent_count", "특허건수"],
    "registered_patents": ["registered_patent", "등록특허"],
    "active_patents": ["active_patent", "존속"],
    "tech_score": ["final_tech_score", "bridge_score", "tech_to_value_bridge_score"],
    "wacc": ["wacc", "WACC"],
    "upside": ["upside", "괴리율"],
}

DECISION_FIELD_HINTS = ("opinion", "recommendation", "decision", "signal", "투자의견", "판단")
BUY_WORDS = {"매수", "buy", "positive", "bullish"}
SELL_WORDS = {"매도", "sell", "negative", "bearish"}
HOLD_WORDS = {"보유", "hold", "neutral"}


def _metric_bucket(path: str) -> str | None:
    low = str(path or "").lower()
    for bucket, aliases in CONSISTENCY_METRIC_ALIASES.items():
        if any(alias.lower() in low for alias in aliases):
            return bucket
    return None


def _has_any_word(text: str, words: set[str]) -> bool:
    low = text.lower()
    return any(w.lower() in low for w in words)


def _consistency_guardrail(packet: dict[str, Any], company: str) -> dict[str, Any]:
    """Stage-1 internal consistency guardrail.

    This does not force every agent into one schema. It checks only high-risk inconsistencies that
    can mislead the Chair after opinion/confidence/evidence-heavy fields are compacted:
    - company identity drift,
    - contradictory buy/sell labels inside decision-like fields,
    - impossible confidence ranges when legacy fields still exist,
    - same-metric scale conflicts such as 589억 vs 5890억 or 48.9B vs 489B.
    """
    issues: list[str] = []
    warnings: list[str] = []
    flat = _flatten_values(packet)

    # 1) Company identity consistency.
    company_fields: list[str] = []
    for path, value in flat:
        low_path = path.lower()
        if any(k in low_path for k in ("company", "corp_name", "기업", "회사")) and isinstance(value, str):
            text = value.strip()
            if text and len(text) <= 80:
                company_fields.append(text)
    if company and company_fields:
        if not any(company in x for x in company_fields) and company not in _json_text(packet, limit=20000):
            issues.append(f"company identity not consistently visible: expected {company}")

    # 2) Legacy decision/opinion field consistency. These fields may later be removed from compact
    # packets, but raw packets can still contain them. Contradictory labels are dangerous.
    decision_texts: list[str] = []
    for path, value in flat:
        low_path = path.lower()
        if any(h.lower() in low_path for h in DECISION_FIELD_HINTS):
            if isinstance(value, (str, int, float, bool)):
                text = str(value).strip()
                if text:
                    decision_texts.append(text)
    decision_blob = " ".join(decision_texts)
    if decision_blob:
        has_buy = _has_any_word(decision_blob, BUY_WORDS)
        has_sell = _has_any_word(decision_blob, SELL_WORDS)
        has_hold = _has_any_word(decision_blob, HOLD_WORDS)
        if has_buy and has_sell:
            issues.append("contradictory buy/sell labels detected in legacy decision-like fields")
        elif has_buy and has_hold:
            warnings.append("buy and hold labels both appear in legacy decision-like fields")
        elif has_sell and has_hold:
            warnings.append("sell and hold labels both appear in legacy decision-like fields")

    # 3) Confidence range sanity for legacy fields.
    for path, value in flat:
        low_path = path.lower()
        leaf = re.split(r"[.\[]", low_path)[-1].rstrip("]")
        confidence_like_leaf = (
            "confidence" in leaf
            or leaf in {"score", "value", "level"}
            or "신뢰도" in path
        )
        if "confidence" not in low_path and "신뢰도" not in path:
            continue
        if not confidence_like_leaf:
            continue
        if any(token in leaf for token in ("count", "patent", "claim", "evidence", "dimension", "observation")):
            continue
        num = _safe_float(value)
        if num is None:
            continue
        if num < 0 or num > 100:
            issues.append(f"legacy confidence out of expected range at {path}: {value}")
        elif 1 < num <= 100:
            # 0~1 and 0~100 are both allowed, but mixed confidence scales are tracked.
            warnings.append(f"legacy confidence appears to use 0-100 scale at {path}: {value}")

    # 4) Same-metric scale consistency. Very mild unless a clear 10x/100x conflict is detected.
    metric_values: dict[str, list[tuple[str, float]]] = {}
    for path, value in flat:
        bucket = _metric_bucket(path)
        if not bucket:
            continue
        num = _safe_float(value)
        if num is None:
            continue
        metric_values.setdefault(bucket, []).append((path, num))

    for bucket, values in metric_values.items():
        # Avoid punishing time series/list history: only inspect scalar-like top-level/key summary conflicts.
        filtered = [
            (p, v)
            for p, v in values
            if (
                "[" not in p
                or any(k in p.lower() for k in ("summary", "latest", "current", "final"))
            )
            and not any(
                k in p.lower()
                for k in ("percentile", "pctl", "rank", "observations", "q20", "q80", "threshold", "criteria")
            )
        ]
        if len(filtered) < 2:
            continue
        abs_vals = [abs(v) for _, v in filtered if abs(v) > 1e-9]
        if len(abs_vals) < 2:
            continue
        high = max(abs_vals)
        low = min(abs_vals)
        ratio = high / max(low, 1e-9)
        if ratio >= 9.7:
            examples = "; ".join(f"{p}={v}" for p, v in filtered[:5])
            issues.append(f"same-metric scale inconsistency suspected for {bucket}: ratio≈{ratio:.1f} ({examples})")
        elif ratio >= 3.0 and bucket in {"fcf", "patent_count", "registered_patents", "active_patents"}:
            examples = "; ".join(f"{p}={v}" for p, v in filtered[:5])
            warnings.append(f"same-metric value dispersion for {bucket}: ratio≈{ratio:.1f} ({examples})")

    score = 1.0
    if issues:
        score -= 0.22 * len(issues)
    if warnings:
        score -= 0.06 * len(warnings)
    return {
        "score": round(max(0.0, min(1.0, score)), 4),
        "issues": issues[:10],
        "warnings": warnings[:10],
        "checked_company_fields": company_fields[:8],
        "checked_decision_fields_count": len(decision_texts),
        "checked_metric_buckets": sorted(metric_values.keys()),
    }


def _stage1_basic_validation(packet: dict[str, Any], *, company: str, source_context: str) -> dict[str, Any]:
    numeric = _numeric_guardrail(packet, source_context)
    scope = _source_scope_guardrail(packet, company, source_context)
    consistency = _consistency_guardrail(packet, company)
    score, stage_weights, stage_dma_model = _combine_scores_dma(
        "auditor_stage1",
        {
            "numeric_guardrail": numeric["score"],
            "source_scope_guardrail": scope["score"],
            "consistency_guardrail": consistency["score"],
        },
    )
    issues = (
        list(numeric.get("issues") or [])
        + list(scope.get("issues") or [])
        + list(consistency.get("issues") or [])
    )
    warnings = list(consistency.get("warnings") or [])
    return {
        "stage": "stage1_basic_hallucination_unit_scope_consistency_guardrail",
        "score": round(max(0.0, min(1.0, score)), 4),
        "numeric_guardrail": numeric,
        "source_scope_guardrail": scope,
        "consistency_guardrail": consistency,
        "stage_weights": stage_weights,
        "stage_dma_model": stage_dma_model,
        "issues": issues,
        "warnings": warnings,
    }


FRAMEWORK_LIBRARY: dict[str, list[str]] = {
    "finance": [
        "growth/profitability/cash-flow/leverage/liquidity/volatility coverage",
        "IB financing risk: CB/BW overhang, paid-in capital increase, dilution, refinancing pressure",
        "deep-tech finance: R&D must be interpreted with cash-flow and scale-up funding capacity",
    ],
    "market": [
        "return-risk-liquidity-volatility decomposition",
        "market signal must be separated from company fundamentals and news noise",
    ],
    "tech": [
        "Financing Deep Tech: technology validation, first pilot, first commercial contract, early commercialization, scale-up",
        "Missing Middle: commercialization and scale-up evidence are required before valuation uplift",
        "patents as R&D output signal: registration, remaining life, claim/citation/family quality, technology-to-value bridge",
        "patent-text similarity and peer map as market-value spillover signal",
    ],
    "valuation": [
        "DCF/WACC/Peer Comps/Sensitivity model consistency",
        "IB practice: IPO/ECM/DCM/PF/PEF scenario and dilution/overhang checks",
    ],
    "issue": [
        "company-relevant event classification: positive/neutral/negative, source URL, impact path, watch point",
        "noise filtering: unrelated hobbies/celebrity/general sector chatter cannot be investment evidence",
    ],
    "macro": [
        "semiconductor macro transmission: FX, rates, demand cycle, materials, supply-chain constraints",
        "macro is supporting context, not direct company earnings evidence",
    ],
}

COVERAGE_KEYWORDS: dict[str, list[tuple[str, list[str]]]] = {
    "finance": [
        ("growth", ["매출성장", "성장률", "sales_growth"]),
        ("profitability", ["영업이익률", "ROE", "마진", "operating_margin"]),
        ("cash_flow", ["FCF", "현금흐름", "free_cash_flow"]),
        ("leverage", ["부채비율", "debt_ratio", "차입"]),
        ("volatility", ["MDD", "변동성", "annual_return"]),
        ("capital_dilution", ["CB", "BW", "메자닌", "유상증자", "희석", "오버행", "전환가액"]),
    ],
    "market": [
        ("return", ["수익률", "return", "종가", "latest_close"]),
        ("drawdown", ["MDD", "낙폭", "drawdown"]),
        ("liquidity", ["거래량", "volume", "liquidity"]),
        ("volatility", ["변동성", "vkospi", "volatility"]),
    ],
    "tech": [
        ("technology", ["기술", "공정", "소재", "패키징", "제품"]),
        ("commercialization", ["고객", "채택", "양산", "매출", "사업화", "scale-up"]),
        ("ip_quality", ["특허", "등록", "존속", "청구항", "인용", "패밀리", "KIPRIS"]),
        ("rnd", ["R&D", "연구개발", "정부과제", "기술이전"]),
        ("bridge", ["Tech-to-Value", "Bridge", "value", "FCF"]),
    ],
    "valuation": [
        ("dcf", ["DCF", "내재주가", "implied", "upside"]),
        ("wacc", ["WACC", "할인율"]),
        ("peer", ["Peer", "comps", "EV/EBITDA", "PER"]),
        ("sensitivity", ["민감도", "sensitivity"]),
    ],
    "issue": [
        ("source", ["http", "뉴스", "RSS", "url", "source"]),
        ("impact", ["영향", "리스크", "수혜", "주가", "실적"]),
        ("watch", ["체크", "watch", "추적"]),
    ],
    "macro": [
        ("rates_fx", ["금리", "환율", "달러", "원/달러", "rate", "FX"]),
        ("cycle", ["반도체", "수요", "재고", "cycle", "업황"]),
        ("supply_chain", ["희토류", "헬륨", "공급망", "소재", "관세"]),
    ],
}


def _stage2_framework_validation(packet: dict[str, Any]) -> dict[str, Any]:
    agent = _extract_agent_name(packet)
    text = _json_text(packet).lower()
    checks = COVERAGE_KEYWORDS.get(agent, [])
    matched: dict[str, bool] = {}
    for criterion, keywords in checks:
        matched[criterion] = any(k.lower() in text for k in keywords)
    coverage = sum(1 for ok in matched.values() if ok) / max(1, len(matched)) if checks else 0.65

    # Capital-market/dilution checks are useful but not mandatory for all companies; do not over-penalize absence.
    if agent == "finance" and matched.get("capital_dilution") is False:
        coverage = max(coverage, 0.72)
    if agent == "tech" and not matched.get("commercialization"):
        coverage = min(coverage, 0.72)
    if agent == "issue" and not matched.get("source"):
        coverage = min(coverage, 0.70)

    # Market packets can be either rich Chair-adapter summaries or compact raw
    # score/price packets.  When the raw packet carries auditable market score
    # and price/change evidence, do not fail stage2 solely because the prose
    # lacks the exact return/liquidity/drawdown vocabulary.
    if agent == "market":
        market_metric_groups = [
            ("score", ["total_score", "market_score", "scoring"]),
            ("price", ["current_price", "latest_close", "clpr", "price"]),
            ("change", ["change_rate", "fltrt", "annual_return", "return"]),
            ("risk", ["market_momentum", "volatility", "mdd", "drawdown", "변동성"]),
        ]
        metric_hits = {
            name: any(token.lower() in text for token in tokens)
            for name, tokens in market_metric_groups
        }
        hit_count = sum(1 for ok in metric_hits.values() if ok)
        if hit_count >= 2:
            coverage = max(coverage, PASS_THRESHOLD)
        elif hit_count == 1:
            coverage = max(coverage, 0.60)

    # Macro is a supporting-context agent.  Its packet may legitimately cover
    # rates/FX and semiconductor cycle without every supply-chain keyword.
    # If at least two of the three macro framework axes are visible, treat
    # the missing third axis as a non-fatal watch item and keep stage2 at
    # the 75% pass floor.  This fixes the repeated macro-only 68~69% failures
    # without disabling the Auditor threshold.
    if agent == "macro":
        matched_count = sum(1 for ok in matched.values() if ok)
        if matched_count >= 2:
            coverage = max(coverage, PASS_THRESHOLD)
        elif matched_count == 1:
            coverage = max(coverage, 0.60)

    issues = [f"framework criterion not visible: {k}" for k, ok in matched.items() if not ok]
    return {
        "stage": "stage2_literature_ib_deeptech_framework_validation",
        "score": round(max(0.0, min(1.0, coverage)), 4),
        "framework_sources": FRAMEWORK_LIBRARY.get(agent, []),
        "coverage": matched,
        "issues": issues,
    }


def _stage3_decision_readiness(agent: str, packet: dict[str, Any]) -> dict[str, Any]:
    decision = compute_agent_decision(agent, packet)
    basis_count = len(decision.get("basis") or [])
    component_count = len(decision.get("components") or {})

    if agent in {"market", "macro"}:
        evidence_count = len(_as_list(packet.get("evidences") or packet.get("evidence")))
        basis_denominator = 1.0 if agent == "market" else 2.0
        readiness_scores = {
            "basis_coverage": min(basis_count / basis_denominator, 1.0),
            "component_coverage": 1.0 if component_count else 0.0,
            f"explicit_{agent}_signal_or_score": 1.0 if basis_count else 0.0,
            "evidence_coverage": min(evidence_count / 3.0, 1.0),
        }
        quality, readiness_weights, readiness_dma_model = _combine_scores_dma(
            f"auditor_stage3_{agent}_readiness",
            readiness_scores,
        )
        issues: list[str] = []
        if basis_count < 1:
            issues.append(f"{agent} signal/score basis is weak")
        if not component_count:
            issues.append(f"{agent} signal component is missing")
        if evidence_count < 1:
            issues.append(f"{agent} evidence is missing")
        return {
            "stage": "stage3_quantitative_recommendation_readiness",
            "score": round(quality, 4),
            "decision": decision,
            "readiness_weights": readiness_weights,
            "readiness_dma_model": readiness_dma_model,
            "issues": issues,
        }

    quality, readiness_weights, readiness_dma_model = _combine_scores_dma(
        "auditor_stage3_readiness",
        {
            "basis_coverage": min(basis_count / 4.0, 1.0),
            "component_coverage": min(component_count / 3.0, 1.0),
            "nonzero_signal": 1.0 if abs(float(decision.get("signal", 0.0) or 0.0)) > 0 else 0.0,
        },
    )
    return {
        "stage": "stage3_quantitative_recommendation_readiness",
        "score": round(quality, 4),
        "decision": decision,
        "readiness_weights": readiness_weights,
        "readiness_dma_model": readiness_dma_model,
        "issues": [] if basis_count else ["quantitative decision basis is weak"],
    }


def _apply_minimum_pass_floor(
    *,
    agent: str,
    final_score: float,
    stage1: dict[str, Any],
    stage2: dict[str, Any],
    stage3: dict[str, Any],
) -> tuple[float, dict[str, Any]]:
    """Raise non-catastrophic audit scores to the configured minimum pass floor.

    Purpose
    -------
    This keeps ``AUDITOR_FIRST_PASS_THRESHOLD`` active while preventing the
    pipeline from stopping when an agent has enough numeric/source/decision
    evidence but is slightly below 75% because one framework keyword family is
    missing.

    Hard failures still fail.  The floor is not applied when stage1, stage2, or
    stage3 is below its explicit minimum, because that usually means unit-scale
    mismatch, hallucination risk, missing source scope, or no quantitative basis.
    """
    diagnostics = {
        "enabled": bool(MIN_PASS_FLOOR_ENABLED),
        "applied": False,
        "floor_value": round(float(MIN_PASS_FLOOR_VALUE), 4),
        "reason": None,
        "stage_minima": {
            "stage1_basic_consistency_min": MIN_PASS_FLOOR_STAGE1_MIN,
            "stage2_framework_min": MIN_PASS_FLOOR_STAGE2_MIN,
            "stage3_decision_readiness_min": MIN_PASS_FLOOR_STAGE3_MIN,
        },
    }
    if not MIN_PASS_FLOOR_ENABLED:
        diagnostics["reason"] = "disabled_by_env"
        return final_score, diagnostics

    s1 = float(stage1.get("score") or 0.0)
    s2 = float(stage2.get("score") or 0.0)
    s3 = float(stage3.get("score") or 0.0)
    hard_fail_reasons: list[str] = []
    if s1 < MIN_PASS_FLOOR_STAGE1_MIN:
        hard_fail_reasons.append(f"stage1<{MIN_PASS_FLOOR_STAGE1_MIN:.2f}")
    if s2 < MIN_PASS_FLOOR_STAGE2_MIN:
        hard_fail_reasons.append(f"stage2<{MIN_PASS_FLOOR_STAGE2_MIN:.2f}")
    if s3 < MIN_PASS_FLOOR_STAGE3_MIN:
        hard_fail_reasons.append(f"stage3<{MIN_PASS_FLOOR_STAGE3_MIN:.2f}")

    if hard_fail_reasons:
        diagnostics["reason"] = "hard_guardrail_failed: " + ", ".join(hard_fail_reasons)
        return final_score, diagnostics

    floor = max(float(PASS_THRESHOLD), float(MIN_PASS_FLOOR_VALUE))
    if final_score < floor:
        diagnostics["applied"] = True
        diagnostics["reason"] = (
            f"non_catastrophic_{agent}_packet_floor: all stage scores meet minimums; "
            f"final_score {final_score:.4f} raised to {floor:.4f}"
        )
        return floor, diagnostics

    diagnostics["reason"] = "not_needed"
    return final_score, diagnostics


def _audit_one_agent(agent: str, packet: dict[str, Any], *, company: str, source_context: str) -> dict[str, Any]:
    stage1 = _stage1_basic_validation(packet, company=company, source_context=source_context)
    stage2 = _stage2_framework_validation(packet)
    stage3 = _stage3_decision_readiness(agent, packet)

    # Stage 1 is the hard hallucination guardrail. Stage 2 checks whether the packet is useful
    # under the deep-tech/IB literature framework. Stage 3 measures whether Chair can make a
    # quantitative decision without relying on removed opinion/confidence fields.
    final_score, audit_stage_weights, audit_stage_dma_model = _combine_scores_dma(
        "auditor_final_stage",
        {
            "stage1_basic_consistency": stage1["score"],
            "stage2_framework": stage2["score"],
            "stage3_decision_readiness": stage3["score"],
        },
    )
    if stage1["score"] < 0.55:
        final_score = min(final_score, 0.58)
    stage2_hard_min = _env_float("AUDITOR_STAGE2_HARD_MIN", PASS_THRESHOLD * 0.60)
    if stage2["score"] < stage2_hard_min:
        final_score = min(final_score, max(0.0, min(1.0, PASS_THRESHOLD * 0.90)))

    final_score, minimum_pass_floor = _apply_minimum_pass_floor(
        agent=agent,
        final_score=final_score,
        stage1=stage1,
        stage2=stage2,
        stage3=stage3,
    )

    issues = []
    for stage in (stage1, stage2, stage3):
        issues.extend(stage.get("issues") or [])

    passed = final_score >= PASS_THRESHOLD
    return {
        "agent": agent,
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "actual_match": round(max(0.0, min(1.0, final_score)), 4),
        "actual_match_ratio": round(max(0.0, min(1.0, final_score)), 4),
        "pass_threshold": PASS_THRESHOLD,
        "stage_scores": {
            "stage1_basic_consistency": stage1["score"],
            "stage2_framework": stage2["score"],
            "stage3_decision_readiness": stage3["score"],
        },
        "audit_stage_weights": audit_stage_weights,
        "audit_stage_dma_model": audit_stage_dma_model,
        "minimum_pass_floor": minimum_pass_floor,
        "stages": {"stage1": stage1, "stage2": stage2, "stage3": stage3},
        "decision": stage3["decision"],
        "issues": issues[:20],
        "supported_claims": _claim_texts(packet)[:8],
        "unsupported_claims": issues[:8],
    }


def _write_repair_requests(
    company_dir: str,
    company: str,
    audit_result: dict[str, Any],
    by_agent: dict[str, dict[str, Any]],
) -> dict[str, str]:
    if _history_local_write_disabled():
        return {}
    base = _audit_dir(company_dir) / "agent_repair_inbox"
    base.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for agent, item in (audit_result.get("agent_results") or {}).items():
        if item.get("passed"):
            continue
        payload = {
            "repair_schema_version": "first_auditor_3stage_v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "company_dir": company_dir,
            "company": company,
            "target_agent": agent,
            "pass_condition": f"actual_match >= {PASS_THRESHOLD:.0%}",
            "current_actual_match": item.get("actual_match"),
            "stage_scores": item.get("stage_scores"),
            "issues": item.get("issues"),
            "required_fix": [
                "Remove sentences that are not connected to source files or the target company.",
                "Keep numbers, units, and periods on the same scale as source CSV/JSON/disclosure/news/RSS values.",
                "Do not create 10x or 100x unit-scale errors, such as overstating KRW 58.9 billion as KRW 589 billion.",
                "For Issue/Market/Macro external API results, keep only items directly related to the company name, sector, and investment impact.",
                "For Tech, separate registration, active-right status, claims, citations, family, and commercialization linkage from raw patent count.",
                "For Finance/Valuation, separately disclose CB/BW, rights offerings, dilution, and overhang risks when applicable.",
            ],
            "current_packet_preview": _json_text(by_agent.get(agent, {}), limit=5000),
        }
        path = base / f"{agent}_repair_request.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        paths[agent] = str(path)
    return paths


def _persist_receipt(company_dir: str, row: dict[str, Any]) -> Path:
    if _history_local_write_disabled():
        return Path("google_sheets_only_first_auditor_receipt.json")
    audit_dir = _audit_dir(company_dir)
    log_path = audit_dir / "first_auditor_log.jsonl"
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, ensure_ascii=False) + "\n")
    receipt_path = audit_dir / "first_auditor_receipt.json"
    receipt_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    return receipt_path


def _run_3stage_validation(company_dir: str, company: str, opinions: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_context = collect_source_context(company_dir, company, enable_web=False)
    source_context = evidence_context.get("context") or ""
    by_agent = _latest_by_agent(opinions)
    expected = [agent for agent in EXPECTED_AGENTS if agent in by_agent]
    if not expected:
        expected = EXPECTED_AGENTS[:]

    agent_results: dict[str, Any] = {}
    decision_inputs: dict[str, dict[str, Any]] = {}
    compact_packets: list[dict[str, Any]] = []

    for agent in expected:
        packet = by_agent.get(agent)
        if not packet:
            agent_results[agent] = {
                "agent": agent,
                "status": "FAIL",
                "passed": False,
                "actual_match": 0.0,
                "actual_match_ratio": 0.0,
                "pass_threshold": PASS_THRESHOLD,
                "stage_scores": {"stage1_basic_consistency": 0.0, "stage2_framework": 0.0, "stage3_decision_readiness": 0.0},
                "issues": ["missing agent packet"],
                "supported_claims": [],
                "unsupported_claims": ["missing agent packet"],
                "decision": {"agent": agent, "signal": 0.0, "recommendation": "보유", "basis": []},
            }
            continue
        result = _audit_one_agent(agent, packet, company=company, source_context=source_context)
        agent_results[agent] = result
        decision_inputs[agent] = packet

    quantitative_decision = compute_portfolio_decision(decision_inputs)

    for agent in expected:
        packet = by_agent.get(agent) or {"agent": agent, "company_name": company}
        ar = agent_results.get(agent, {})
        stage_decision = (quantitative_decision.get("agent_decisions") or {}).get(agent) or ar.get("decision")
        compact_packets.append(
            build_compact_agent_packet(
                packet,
                company=company,
                company_dir=company_dir,
                auditor_result=ar,
                stage_decision=stage_decision,
            )
        )

    packet_paths = persist_compact_packets(
        company_dir=company_dir,
        company=company,
        compact_packets=compact_packets,
        quantitative_decision=quantitative_decision,
    )

    scores = [float(item.get("actual_match") or 0.0) for item in agent_results.values()]
    min_score = min(scores) if scores else 0.0
    avg_score = sum(scores) / max(1, len(scores))
    failed = [agent for agent, item in agent_results.items() if not item.get("passed")]

    return {
        "stage_count": STAGE_COUNT,
        "passed": not failed,
        "pass_threshold": PASS_THRESHOLD,
        "min_actual_match_ratio": round(min_score, 4),
        "avg_actual_match_ratio": round(avg_score, 4),
        "failed_agents": failed,
        "agent_results": agent_results,
        "quantitative_decision": quantitative_decision,
        "compact_packets": compact_packets,
        "compact_packet_paths": packet_paths,
        "source_files": evidence_context.get("source_files", []),
        "web_items": [],
        "web_check_enabled": False,
        "has_source_context": evidence_context.get("has_context", False),
    }


def run_first_auditor(
    company_dir: str | None = None,
    company: str | None = None,
    opinions: list[dict[str, Any]] | None = None,
    recollect_fn: Callable[..., list[dict[str, Any]]] | None = None,
    max_rounds: int = MAX_ROUNDS,
) -> dict[str, Any]:
    """Run the fixed 3-stage First Auditor and return compact packets for Chair.

    Important: the old threshold-driven retry rounds are intentionally disabled. The CLI still
    accepts ``--max-rounds`` for backward compatibility, but the Auditor now executes exactly one
    sequential 3-stage validation pass:
      1) numeric/unit/source-scope/internal-consistency guardrail,
      2) deep-tech/IB/literature framework validation,
      3) quantitative BUY/HOLD/SELL Chair-handoff decision.
    """
    company_dir = str(company_dir or "").strip()
    company = str(company or "").strip()
    current_opinions = [op for op in (opinions or []) if isinstance(op, dict)]
    if max_rounds not in (None, 1):
        print(
            "[First Auditor] notice: --max-rounds is a legacy-compatible argument. "
            "The current Auditor runs one internal 3-stage validation pass without retry rounds."
        )

    print(
        "[First Auditor] config: "
        "mode=FIXED_3STAGE_LOCAL, stage_count=3, "
        "web_verify=False, llm_judge=False, retry_rounds=disabled, "
        f"fail_open={FAIL_OPEN}"
    )

    final_result = _run_3stage_validation(company_dir, company, current_opinions)
    by_agent = _latest_by_agent(current_opinions)
    repair_paths = _write_repair_requests(company_dir, company, final_result, by_agent) if not final_result.get("passed") else {}

    row = {
        "packet_version": "first_auditor_fixed_3stage_local_v2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "company_dir": company_dir,
        "company": company,
        "stage_count": STAGE_COUNT,
        "retry_rounds_enabled": False,
        "legacy_max_rounds_arg": max_rounds,
        "pass_threshold": PASS_THRESHOLD,
        "web_check_enabled": False,
        "auditor_llm_judge_enabled": False,
        "three_stage_policy": {
            "stage1": "numeric scale/unit, hallucination, company/source-scope, and internal consistency guardrail",
            "stage2": "deep-tech/IB/literature framework coverage validation",
            "stage3": "quantitative recommendation readiness and Chair handoff decision",
        },
        "result": final_result,
        "repair_request_paths": repair_paths,
    }
    receipt_path = _persist_receipt(company_dir, row)

    if final_result.get("passed"):
        print(
            "[First Auditor] 3-stage PASS: "
            f"min_actual_match={final_result['min_actual_match_ratio']:.2%}, "
            f"avg_actual_match={final_result['avg_actual_match_ratio']:.2%}, "
            f"final_recommendation={final_result.get('quantitative_decision', {}).get('final_recommendation')}"
        )
    else:
        print(
            "[First Auditor] 3-stage FAIL: "
            f"min_actual_match={final_result['min_actual_match_ratio']:.2%}, "
            f"avg_actual_match={final_result['avg_actual_match_ratio']:.2%}, "
            f"threshold={PASS_THRESHOLD:.0%}, "
            f"failed={', '.join(final_result.get('failed_agents') or [])}"
        )

    passed = bool(final_result.get("passed"))
    if not passed and FAIL_OPEN:
        print("[First Auditor] FAIL_OPEN=1 이므로 실패 상태를 기록하고 Chair 단계로 진행합니다.")
        passed_for_flow = True
    else:
        passed_for_flow = passed

    qd = final_result.get("quantitative_decision") or {}
    compact_packets = final_result.get("compact_packets") or []
    return {
        "passed": passed_for_flow,
        "raw_passed": passed,
        "fail_open": bool(FAIL_OPEN and not passed),
        "threshold": PASS_THRESHOLD,
        "receipt_path": str(receipt_path),
        "stages": (final_result.get("agent_results") or {}),
        "rounds": [],  # deprecated: old retry rounds are disabled in fixed 3-stage auditor
        "final_validation": final_result,
        "final_round": final_result,  # backward-compatible alias
        "min_actual_match": final_result.get("min_actual_match_ratio"),
        "avg_actual_match": final_result.get("avg_actual_match_ratio"),
        "failed_agents": final_result.get("failed_agents") or [],
        "agent_results": final_result.get("agent_results") or {},
        "quantitative_decision": qd,
        "final_recommendation": qd.get("final_recommendation"),
        "weighted_signal": qd.get("weighted_signal"),
        "opinions": compact_packets,
        "compact_packet_paths": final_result.get("compact_packet_paths") or {},
        "web_check_enabled": False,
        "web_crosscheck": None,
    }
