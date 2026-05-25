from __future__ import annotations

import json
import os
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from auditor_agent.dynamic_model_averaging import compute_dma_label_posterior, compute_dma_weights
except Exception:  # Chair must still render if auditor package is unavailable.
    compute_dma_weights = None  # type: ignore
    compute_dma_label_posterior = None  # type: ignore

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from langgraph.graph import END, START, StateGraph

from common.output_paths import agent_output_path, rel_project_path, write_json
from common.agent_history import load_agent_snapshot, save_run_result, history_source_label, using_google_sheets_history
from common.data_paths import normalize_field_name

from .adapters import (
    run_finance_for_chair,
    run_issue_for_chair,
    run_macro_for_chair,
    run_market_for_chair,
    run_tech_for_chair,
    run_valuation_for_chair,
)
from .prompts import END_MARKER, build_chair_prompt
from .state import ChairState


AGENT_ORDER = ["finance", "market", "tech", "valuation", "issue", "macro"]
AGENT_KO = {
    "finance": "재무 분석",
    "market": "시장 분석",
    "tech": "기술 분석",
    "valuation": "가치평가 분석",
    "issue": "이슈 분석",
    "macro": "거시경제",
}
AGENT_WEIGHT_POLICY = "no_static_agent_weights; fallback uses DMA uniform prior/posterior"

DEFAULT_MIN_REPORT_CHARS = 1200
MIN_REPORT_CHARS = int(os.getenv("CHAIR_MIN_REPORT_CHARS", str(DEFAULT_MIN_REPORT_CHARS)))
REPORT_MAX_TOKENS = int(os.getenv("CHAIR_REPORT_MAX_TOKENS", "5000"))
REPORT_MAX_RETRIES = int(os.getenv("CHAIR_REPORT_MAX_RETRIES", "1"))


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _safe_int(value: str | None, default: int) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(str(value).strip())
    except Exception:
        return default


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        try:
            dumped = value.model_dump()
            return dumped if isinstance(dumped, dict) else {"value": dumped}
        except Exception:
            return {"value": str(value)}
    return {"value": value}


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " / ".join(_to_text(v) for v in value if _to_text(v))
    if isinstance(value, dict):
        for key in ("summary", "text", "content", "title", "name", "basis", "value", "reason"):
            if key in value and value.get(key) not in (None, ""):
                text = _to_text(value.get(key))
                if text:
                    return text
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)
    return str(value).strip()


def _clip(text: Any, limit: int = 260) -> str:
    raw = re.sub(r"\s+", " ", _to_text(text)).strip()
    if len(raw) <= limit:
        return raw
    cut = raw[:limit].rstrip()
    boundaries = [cut.rfind(x) for x in (". ", "다. ", "요. ", "음. ", "! ", "? ", "。")]
    boundary = max(boundaries)
    if boundary >= min(80, max(10, int(limit * 0.25))):
        cut = cut[: boundary + 1].rstrip()
    else:
        comma = max(cut.rfind("다."), cut.rfind("요."), cut.rfind("음."), cut.rfind(";"))
        if comma >= min(80, max(10, int(limit * 0.20))):
            cut = cut[: comma + 1].rstrip()
    return cut.rstrip(" ,;:/·-…")


def _agent_name(packet: dict[str, Any], default: str = "unknown") -> str:
    for key in ("agent", "agent_name", "source_agent", "name"):
        value = packet.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return default


def _tag_raw_packet(agent_name: str, payload: Any) -> dict[str, Any]:
    """Tag raw specialist output for the Auditor only.

    Specialist agent source files are not modified. Raw claim/evidence-like fields may
    still exist here only so that the Auditor can validate them internally. The Chair
    report never consumes this raw packet after the Auditor step.
    """
    item = _as_dict(payload)
    item["agent"] = agent_name
    item["agent_name"] = agent_name
    return item


def _normalize_recommendation(value: Any) -> str:
    text = _to_text(value)
    if "매수" in text or text.lower() in {"buy", "bullish"}:
        return "매수"
    if "매도" in text or text.lower() in {"sell", "bearish"}:
        return "매도"
    return "보유"


def _dma_signal_to_direction(value: Any) -> str:
    """Interpret DMA weighted_signal only as a continuous direction.

    This is not a buy/hold/sell cutoff.  Final recommendation should come from
    the Auditor DMA categorical posterior when available.
    """
    try:
        num = float(value)
    except Exception:
        return "중립"
    if num > 0:
        return "긍정 방향"
    if num < 0:
        return "부정 방향"
    return "중립"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _list_text(values: Any, limit: int = 4) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list):
        values = [values]
    out: list[str] = []
    for value in values:
        text = _clip(value, 260)
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _metric_highlights(packet: dict[str, Any], limit: int = 4) -> list[str]:
    metrics = packet.get("metrics")
    if not isinstance(metrics, dict):
        return []
    highlights: list[str] = []
    preferred = [
        "sales_growth_%", "operating_margin_%", "ROE_%", "fcf", "debt_ratio_%",
        "annual_return_%", "annual_mdd_%", "current_price", "intrinsic_price", "upside_downside_pct",
        "final_tech_score", "tech_to_value_score", "ip_evidence_composite_score",
        "warning_stock", "vkospi_mean",
    ]
    for key in preferred:
        if key in metrics and metrics.get(key) not in (None, ""):
            highlights.append(f"{key}: {metrics.get(key)}")
        if len(highlights) >= limit:
            return highlights
    for key, value in metrics.items():
        if isinstance(value, (str, int, float)) and value not in (None, ""):
            highlights.append(f"{key}: {value}")
        if len(highlights) >= limit:
            break
    return highlights


def _latest_by_agent(packets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for packet in packets:
        if isinstance(packet, dict):
            latest[_agent_name(packet)] = packet
    return latest


def _first_auditor_dir(company_dir: str) -> Path:
    return agent_output_path(company_dir, "auditor", "_placeholder.json").parent / "first_auditor"


def _load_auditor_chair_bundle(company_dir: str) -> dict[str, Any] | None:
    path = _first_auditor_dir(company_dir) / "compact_agent_packets" / "auditor_chair_packet.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _load_receipt(company_dir: str) -> dict[str, Any] | None:
    path = _first_auditor_dir(company_dir) / "first_auditor_receipt.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def _extract_compact_packets(audit_result: dict[str, Any], company_dir: str) -> list[dict[str, Any]]:
    packets = audit_result.get("opinions")
    if isinstance(packets, list) and packets:
        return [p for p in packets if isinstance(p, dict)]
    packets = audit_result.get("compact_packets")
    if isinstance(packets, list) and packets:
        return [p for p in packets if isinstance(p, dict)]
    fv = audit_result.get("final_validation")
    if isinstance(fv, dict):
        packets = fv.get("compact_packets")
        if isinstance(packets, list) and packets:
            return [p for p in packets if isinstance(p, dict)]
    bundle = _load_auditor_chair_bundle(company_dir)
    if isinstance(bundle, dict) and isinstance(bundle.get("packets"), list):
        return [p for p in bundle["packets"] if isinstance(p, dict)]
    return []


def _extract_quantitative_decision(audit_result: dict[str, Any], company_dir: str) -> dict[str, Any]:
    qd = audit_result.get("quantitative_decision")
    if isinstance(qd, dict) and qd:
        return qd
    fv = audit_result.get("final_validation")
    if isinstance(fv, dict) and isinstance(fv.get("quantitative_decision"), dict):
        return fv["quantitative_decision"]
    bundle = _load_auditor_chair_bundle(company_dir)
    if isinstance(bundle, dict) and isinstance(bundle.get("quantitative_decision"), dict):
        return bundle["quantitative_decision"]
    receipt = _load_receipt(company_dir)
    result = receipt.get("result") if isinstance(receipt, dict) else None
    if isinstance(result, dict) and isinstance(result.get("quantitative_decision"), dict):
        return result["quantitative_decision"]
    return {}


def _build_auditor_summary(audit_result: dict[str, Any], company_dir: str) -> dict[str, Any]:
    qd = _extract_quantitative_decision(audit_result, company_dir)
    final_validation = audit_result.get("final_validation") if isinstance(audit_result.get("final_validation"), dict) else {}
    stage_source = final_validation or audit_result
    return {
        "mode": "FIXED_3STAGE_LOCAL",
        "stage_count": stage_source.get("stage_count", 3),
        "passed": audit_result.get("passed"),
        "raw_passed": audit_result.get("raw_passed", audit_result.get("passed")),
        "min_actual_match": audit_result.get("min_actual_match") or stage_source.get("min_actual_match_ratio"),
        "avg_actual_match": audit_result.get("avg_actual_match") or stage_source.get("avg_actual_match_ratio"),
        "failed_agents": audit_result.get("failed_agents") or stage_source.get("failed_agents") or [],
        "receipt_path": audit_result.get("receipt_path"),
        "quantitative_decision": qd,
    }


def _format_stage_scores(packet: dict[str, Any]) -> str:
    # Kept for backward compatibility. Final investor-facing report does not expose stage scores.
    scores = packet.get("auditor_stage_scores")
    if not isinstance(scores, dict):
        return "확인 제한"
    parts = []
    labels = {
        "stage1_basic_consistency": "1차",
        "stage2_framework": "2차",
        "stage3_decision_readiness": "3차",
    }
    for key, label in labels.items():
        if key in scores:
            try:
                parts.append(f"{label} {float(scores[key]) * 100:.1f}%")
            except Exception:
                parts.append(f"{label} {scores[key]}")
    return ", ".join(parts) if parts else "확인 제한"


_INVESTOR_LABEL_MAP: dict[str, str] = {
    "COMMERCIALIZATION_WATCH": "사업화 연결을 더 확인해야 하는 상태",
    "TECH_TO_VALUE_READY": "기술이 가치로 이어질 가능성이 비교적 높은 상태",
    "INVESTOR_TECH_CONVICTION": "기술 경쟁력이 강하게 확인되는 상태",
    "EVIDENCE_WEAK_OR_EARLY": "기술 근거가 아직 이른 상태",
    "IP_EVIDENCE_NEUTRAL": "특허 품질은 중립적인 상태",
    "IP_EVIDENCE_WEAK": "특허 품질 근거가 약한 상태",
    "IP_GLOBAL_EXTENSION_WEAK": "해외 권리 확장 신호가 약한 상태",
    "IP_GLOBAL_EXTENSION_NEUTRAL": "해외 권리 확장 신호는 중립적인 상태",
    "ATTRACTIVE": "상대적으로 저평가 가능성",
    "VALUATION_NEUTRAL_POSITIVE": "가치평가상 중립보다 약간 우호적인 상태",
    "VALUATION_NEUTRAL": "가치평가상 중립적인 상태",
    "MEDIUM_RISK": "중간 수준의 위험",
    "HIGH": "높은 부담",
    "LOW": "낮은 부담",
    "MEDIUM": "중간 수준의 부담",
    "NEUTRAL": "중립 수준",
    "high": "높은 구간",
    "low": "낮은 구간",
    "medium": "중간 수준",
    "neutral": "중립 구간",
    "SELL": "부담 신호",
    "BUY": "우호 신호",
    "HOLD": "관망 신호",
    "PASS": "확인됨",
    "FAILED": "확인 제한",
    "FCF": "자유현금흐름",
    "WACC": "자본비용",
    "MDD": "최대 낙폭",
    "P/S": "매출 대비 주가 수준",
    "DCF": "현금흐름 기반 가치평가",
    "Tech-to-Value": "기술의 가치 전환 가능성",
    "IP Evidence Composite": "특허 품질 종합 신호",
    "Reference Universe": "넓은 반도체 비교군",
    "Peer": "동종기업",
    "peer": "동종기업",
    "Auditor": "검증 로직",
    "compact": "요약",
    "thesis": "핵심 근거",
    "risk": "주의점",
    "signal": "신호",
    "scorecard": "평가표",
}

_INTERNAL_TERMS = re.compile(
    r"\b(weighted_signal|raw_passed|min_actual_match|avg_actual_match|failed_agents|stage_count|"
    r"auditor_signal|auditor_recommendation|auditor_decision_basis|confidence|claims?|evidences?|"
    r"validation|scorecard|final_label|label_rationale|risk_level|macro_score|total_score)\b",
    re.IGNORECASE,
)

_NUMERIC_PATTERN = re.compile(
    r"(?:[-+]?\d+(?:\.\d+)?\s*(?:%|원|억원|조원|배|건|점|/100)|[-+]?\d+(?:\.\d+)?)"
)

_TECHNICAL_KEY_PATTERN = re.compile(
    r"\b(?:[A-Za-z]+(?:_[A-Za-z0-9]+)+|[A-Za-z]+(?:\.[A-Za-z0-9_]+)+)\b"
)

_JSON_LIKE_PATTERN = re.compile(r"^[\s\-•]*[A-Za-z0-9가-힣 _-]+\s*:\s*[\{\[]")


def _looks_raw_or_technical(text: str) -> bool:
    if not text:
        return False
    return bool(_TECHNICAL_KEY_PATTERN.search(text) or _JSON_LIKE_PATTERN.search(text) or '{"' in text or "':" in text)


def _replace_labels(text: Any) -> str:
    cleaned = _to_text(text)
    for src, dst in _INVESTOR_LABEL_MAP.items():
        cleaned = cleaned.replace(src, dst)
    cleaned = cleaned.replace("→", "에서 ").replace("vs", "대비").replace("=", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _has_internal_terms(text: str) -> bool:
    return bool(_INTERNAL_TERMS.search(text or ""))


def _is_metric_like(text: str) -> bool:
    """Return True only for raw/internal metric fragments, not for natural Korean thesis text.

    Earlier versions treated any sentence with several numbers as metric-like. That
    removed useful finance sentences such as "매출성장률 12.3%" and produced broken
    wording like "매출성장률이 로".  The Chair report should preserve each agent's
    natural Korean summary/thesis/risk sentences and only translate raw keys, JSON,
    scorecards and English/internal fields.
    """
    if not text:
        return False
    lowered = text.lower()
    metric_tokens = (
        "/100", "pct", "_krw", "score", "scorecard", "ratio", "percentile", "gap",
        "current_price", "change_rate", "stock_data", "ecos daily", "macro_score",
        "risk_level", "market_total_score", "ip_evidence", "bridge_score",
        "weighted_signal", "auditor_signal", "final_label", "label_rationale",
    )
    if any(token in lowered for token in metric_tokens):
        return True
    return _looks_raw_or_technical(text)


def _qualitative_from_metric(agent: str, text: str, *, kind: str = "thesis") -> str:
    """Convert metric-heavy specialist text into investor-friendly language.

    Specialist JSON is not modified. Only the Chair report wording is softened so the
    final report can be read by individual investors without internal scores/noisy labels.
    """
    t = _replace_labels(text)
    lower = t.lower()

    if agent == "valuation":
        if any(k in t for k in ("현금흐름 기반 가치평가", "내재", "괴리", "기준 주가", "current_price", "implied")):
            return "현금흐름 기준으로 보면 기준 주가와 적정가의 차이가 크지 않아, 가격 안전마진은 아직 충분하다고 보기 어렵습니다."
        if any(k in t for k in ("매출 대비 주가 수준", "비교기업", "멀티플", "multiple")):
            return "동종기업 대비 매출가치 지표는 낮아 상대적으로 싸 보이는 면이 있지만, 그 할인이 성장성·수익성 부담 때문인지 함께 확인해야 합니다."
        if any(k in t for k in ("넓은 반도체 비교군", "universe", "후공정", "패키징")):
            return "넓은 반도체 비교군 안에서는 후공정·패키징 그룹에서 상대적 매력은 일부 확인됩니다."
        if any(k in t for k in ("자본비용", "할인율")):
            return "자본비용 가정이 높아지면 장기 현금흐름 가치가 빠르게 낮아질 수 있습니다."
        if any(k in t for k in ("최대 낙폭", "변동성", "낙폭")):
            return "과거 낙폭이 컸던 만큼, 싸 보이는 가격에도 변동성 부담은 함께 봐야 합니다."
        return "가치평가는 일부 저평가 신호와 제한적인 안전마진 신호가 함께 있어, 단독으로 강한 매수 근거가 되기는 어렵습니다."

    if agent == "tech":
        if any(k in t for k in ("동종기업", "중상위", "percentile", "보정")):
            return "동종 후공정·패키징 기업과 비교하면 기술의 사업화 연결 위치는 비교적 우호적입니다."
        if any(k in t for k in ("기술의 가치 전환", "Bridge", "가치 전환")):
            return "기술이 단순 연구 단계에 머물기보다 제품·공정 가치로 이어질 가능성은 비교적 긍정적으로 보입니다."
        if any(k in t for k in ("특허", "청구항", "인용", "패밀리", "권리", "해외")):
            if kind == "risk" or any(k in t for k in ("약", "중립", "확인")):
                return "특허의 양은 확인되지만, 특허 품질·해외 권리 확장·방어력은 아직 강한 우위라고 단정하기 어렵습니다."
            return "특허와 기술 근거는 사업화 가능성을 보조하는 신호로 볼 수 있습니다."
        if any(k in t for k in ("고객", "양산", "매출", "마진", "자유현금흐름")):
            return "기술력이 실제 고객 채택, 양산, 매출, 현금창출력으로 이어지는지가 가장 중요한 확인 지점입니다."
        return "기술 포지션은 우호적이지만, 투자 매력으로 확정하려면 사업화 연결 근거가 더 필요합니다."

    if agent == "market":
        if any(k in t for k in ("AI", "HBM", "후공정", "패키징", "고성능", "반도체")):
            return "AI·고성능 반도체 수요 확대는 후공정 패키징 기업에 우호적인 시장 배경입니다."
        if any(k in t for k in ("정부", "정책", "육성")):
            return "반도체 산업 육성 정책은 업종 전반에 긍정적인 배경이 될 수 있습니다."
        if any(k in t for k in ("경쟁", "수율", "진입 장벽", "점유율")):
            return "후공정 시장은 성장성이 있지만 경쟁, 수율 확보, 고객 인증 부담이 함께 있습니다."
        if any(k in t for k in ("주가", "하락", "변동", "모멘텀", "거래량")):
            return "최근 가격 흐름은 변동성이 커 단기 진입에는 신중함이 필요합니다."
        return "시장 환경은 성장 기대와 단기 변동성 부담이 함께 있는 상태입니다."

    if agent == "macro":
        if any(k in t for k in ("환율", "달러", "원화")):
            return "원화 약세와 달러 강세는 반도체 성장주 밸류에이션에 부담이 될 수 있습니다."
        if any(k in t for k in ("금리", "국채", "유동성")):
            return "금리 부담 완화는 일부 긍정적이지만, 성장주의 자본비용 부담은 계속 확인해야 합니다."
        if any(k in t for k in ("스프레드", "신용")):
            return "신용환경이 빡빡해지면 설비투자와 자금조달 부담이 커질 수 있습니다."
        if any(k in t for k in ("유가", "인플레이션")):
            return "에너지 가격과 물가 변수는 비용과 투자심리에 부담이 될 수 있습니다."
        if any(k in t for k in ("규제", "미중", "수출")):
            return "반도체 수출 규제와 미중 갈등은 업종 전체의 불확실성으로 남아 있습니다."
        return "거시환경은 방향성이 엇갈려, 성장 기대를 일부 누르는 보조 리스크로 보는 것이 적절합니다."

    if agent == "finance":
        if any(k in t for k in ("매출", "성장")):
            return "매출 회복 조짐은 긍정적이지만, 이것만으로 수익성 정상화를 단정하기는 어렵습니다."
        if any(k in t for k in ("자유현금흐름", "현금")):
            return "현금창출력이 유지되는 점은 기술 사업화까지 버틸 수 있는 체력 측면에서 긍정적입니다."
        if any(k in t for k in ("영업", "수익성", "ROE", "순이익")):
            return "본업 수익성과 자본 효율성은 아직 정상화 확인이 필요합니다."
        if any(k in t for k in ("부채", "레버리지", "운전자본")):
            return "부채와 운전자본 부담은 자금조달 여력과 주주가치에 부담이 될 수 있습니다."
        if any(k in t for k in ("주가", "수익률", "낙폭", "변동")):
            return "주가 반등이 있었더라도 변동성이 커, 단기 성과만으로 안정성을 판단하기는 어렵습니다."
        return "재무는 매출 회복과 현금창출력은 긍정적이나 수익성·부채 부담을 함께 봐야 합니다."

    if agent == "issue":
        if any(k in t for k in ("AI", "반도체", "삼성", "수요", "생태계", "업황")):
            return "AI 반도체와 업황 개선 기대는 투자심리에 우호적인 이슈입니다."
        if any(k in t for k in ("과열", "이격", "단기", "수급")):
            return "단기 수급이 몰린 이슈는 이후 조정 위험을 함께 만들 수 있습니다."
        if any(k in t for k in ("실적", "공시", "수주", "계약")):
            return "뉴스 기대감이 실제 실적, 수주, 공시로 확인되는지가 중요합니다."
        if any(k in t for k in ("피크", "우려", "심리", "하락")):
            return "업황 우려와 투자심리 위축 이슈는 단기 주가에 부담이 될 수 있습니다."
        return "뉴스 흐름은 우호적 소재와 단기 과열 부담이 함께 있는 보조 신호입니다."

    if _is_metric_like(t):
        return "정량 지표는 방향성 참고용으로만 보고, 실제 투자 판단은 동종기업 대비 위치와 사업화 연결성을 함께 확인해야 합니다."
    return t




def _split_sentences_korean(text: str) -> list[str]:
    """Split Korean/English summary text without variable-width look-behind.

    Python re does not allow variable-width look-behind such as
    `(?<=[.!?。]|다\\.|요\\.)\\s+`.  The previous pattern caused
    `re.error: look-behind requires fixed-width pattern` during Chair report
    generation.  This implementation first inserts a marker after common
    sentence-ending punctuation and then splits by the marker.
    """
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []

    marker = "<__CHAIR_SENT_SPLIT__>"
    marked = re.sub(r"([.!?。])\s+", rf"\1{marker}", text)
    parts = marked.split(marker)

    out: list[str] = []
    for part in parts:
        part = part.strip(" -•\t")
        if part:
            out.append(part)
    return out or [text]


def _clean_summary_text(agent: str, value: Any, limit: int = 360) -> str:
    """Keep the richer second-report summaries, but remove raw keys, score labels and JSON fragments."""
    raw = _replace_labels(value)
    if not raw:
        return ""
    raw = raw.replace("기존 Tech Agent 내부 판단은", "기존 기술 분석의 내부 참고 의견은")
    raw = raw.replace("기존 Valuation Agent 내부 판단은", "기존 가치평가 분석의 내부 참고 의견은")
    raw = raw.replace("Auditor compact에서는 이를 참고 신호로만 사용합니다.", "")
    raw = raw.replace("LLM 호출 오류가 발생해 fallback 결과를 반환합니다.", "자동 분석 결과가 제한되어 가격·시장 데이터 중심으로 보수적으로 해석합니다.")
    raw = re.sub(r"\b(?:raw_passed|stage score|min_actual_match|avg_actual_match|validation|scorecard|final_label|label_rationale)\b[^.。\n]*[.。]?", "", raw, flags=re.IGNORECASE)
    sentences = _split_sentences_korean(raw)
    kept: list[str] = []
    for sent in sentences:
        s = sent.strip()
        if not s:
            continue
        # Drop score/grade-heavy sentences, but keep natural Korean numeric summaries such as finance revenue/FCF trends.
        if any(token in s.lower() for token in ("/100", "score", "scorecard", "label=", "grade=", "signal=", "validation=", "percentile")):
            replacement = _qualitative_from_metric(agent, s, kind="summary")
            if replacement and replacement not in kept:
                kept.append(replacement)
            continue
        if _looks_raw_or_technical(s):
            replacement = _qualitative_from_metric(agent, s, kind="summary")
            if replacement and replacement not in kept:
                kept.append(replacement)
            continue
        s = re.sub(r"\s{2,}", " ", s).strip(" ,;:/·-")
        if s and s not in kept:
            kept.append(s)
        if len(" ".join(kept)) >= limit:
            break
    if not kept:
        return _default_bullet(agent, "thesis")
    text = " ".join(kept)
    text = text.replace("리스크 레벨 '중간 수준'", "부담 수준이 중간 정도")
    text = text.replace("리스크 레벨 '중립 수준'", "부담 수준이 중립 정도")
    return _clip(text, limit)


def _clean_investor_sentence(agent: str, value: Any, *, kind: str = "thesis", limit: int = 220) -> str:
    if kind == "summary":
        return _clean_summary_text(agent, value, limit=max(limit, 360))

    original_text = _to_text(value)
    text = _replace_labels(value)
    if not text:
        return ""

    # Raw scorecards / JSON / English metric keys are translated into investor language.
    # Natural Korean agent output, including useful percentages and won amounts, is preserved.
    if agent == "valuation" and any(k in text for k in ("자본비용", "할인율")) and _is_metric_like(original_text):
        text = _qualitative_from_metric(agent, text, kind=kind)
    elif agent == "macro" and any(k in text for k in ("환율", "스프레드", "국채", "금리", "유가", "규제")) and _is_metric_like(original_text):
        text = _qualitative_from_metric(agent, text, kind=kind)
    elif _has_internal_terms(text) or _is_metric_like(original_text) or _is_metric_like(text):
        text = _qualitative_from_metric(agent, text, kind=kind)

    # Remove only raw internal fragments; do not remove finance/market percentages or amounts.
    text = re.sub(r"\b(?:raw_passed|min_actual_match|avg_actual_match|validation|scorecard)\b[^.。\n]*[.。]?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:score|label|grade)\s*[:=][^,.·/\n]+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\([^)]*(?:/100|score|label|grade|PASS|SELL|BUY|HOLD)[^)]*\)", "", text, flags=re.IGNORECASE)
    text = text.replace("자본비용가", "자본비용이").replace("± 이내", "기준 범위 안")
    text = text.replace("연간 최대 낙폭가", "연간 최대 낙폭이")
    text = re.sub(r"총점\s*과", "거시 점수와", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;:/·-")
    if not text:
        text = _qualitative_from_metric(agent, value, kind=kind)
    return _clip(text, limit)


def _investor_bullets(agent: str, values: Any, *, kind: str = "thesis", limit: int = 3) -> list[str]:
    raw_items = _list_text(values, 8)
    out: list[str] = []
    for item in raw_items:
        cleaned = _clean_investor_sentence(agent, item, kind=kind)
        if cleaned and cleaned not in out:
            out.append(cleaned)
        if len(out) >= limit:
            break
    if out:
        return out
    return [_default_bullet(agent, kind)]


def _default_bullet(agent: str, kind: str = "thesis") -> str:
    defaults = {
        "finance": {
            "thesis": "매출 회복과 현금창출력은 긍정적이지만, 수익성 회복 확인이 필요합니다.",
            "risk": "부채와 수익성 부담이 남아 있어 재무 체력 확인이 필요합니다.",
        },
        "market": {
            "thesis": "AI·고성능 반도체 수요 확대는 후공정 패키징 기업에 우호적인 시장 배경입니다.",
            "risk": "성장 산업이라도 단기 가격 변동성과 경쟁 심화는 함께 봐야 합니다.",
        },
        "tech": {
            "thesis": "동종기업 대비 기술의 사업화 연결 가능성은 비교적 우호적으로 보입니다.",
            "risk": "기술력이 고객 채택, 양산, 매출, 현금창출력으로 이어지는지 확인해야 합니다.",
        },
        "valuation": {
            "thesis": "동종기업 대비 저평가처럼 보이는 부분은 있으나, 가격 안전마진은 추가 확인이 필요합니다.",
            "risk": "싸 보이는 이유가 성장성 부족이나 재무 부담 때문인지 함께 봐야 합니다.",
        },
        "issue": {
            "thesis": "AI 반도체와 업황 개선 기대는 투자심리에 우호적인 이슈입니다.",
            "risk": "뉴스 기대감은 실제 실적과 공시로 확인되기 전까지 보조 신호입니다.",
        },
        "macro": {
            "thesis": "일부 유동성 완화 신호는 있지만 거시환경은 아직 엇갈립니다.",
            "risk": "환율, 금리, 신용환경은 성장주 밸류에이션에 부담이 될 수 있습니다.",
        },
    }
    return defaults.get(agent, {}).get(kind, "추가 확인이 필요합니다.")


def _view_phrase(agent: str, recommendation: str) -> str:
    if recommendation == "매수":
        return {
            "tech": "긍정적입니다. 다만 기술이 매출과 현금흐름으로 이어지는지 확인해야 합니다.",
            "issue": "우호적입니다. 다만 뉴스 기대감은 실제 공시와 실적으로 확인되어야 합니다.",
            "market": "우호적입니다. 성장 산업 배경이 좋지만 단기 변동성은 남아 있습니다.",
            "valuation": "우호적입니다. 상대적 저평가 가능성은 있으나 할인 이유를 확인해야 합니다.",
            "finance": "우호적입니다. 현금창출력과 재무 체력이 유지되는지 확인해야 합니다.",
            "macro": "우호적입니다. 다만 거시 변수는 빠르게 바뀔 수 있습니다.",
        }.get(agent, "우호적입니다.")
    if recommendation == "매도":
        return {
            "macro": "부담스럽습니다. 환율·금리·신용환경이 투자심리에 압박을 줄 수 있습니다.",
            "finance": "부담스럽습니다. 수익성·부채·현금흐름을 먼저 확인해야 합니다.",
            "valuation": "부담스럽습니다. 현재 가격이 적정가 대비 매력적이지 않을 수 있습니다.",
        }.get(agent, "주의가 필요합니다.")
    return {
        "finance": "중립적입니다. 매출 회복은 긍정적이지만 수익성·부채 부담을 함께 봐야 합니다.",
        "market": "중립적입니다. 성장 산업 기대와 단기 변동성 리스크가 함께 있습니다.",
        "tech": "긍정적이지만 관망이 필요합니다. 기술 위치는 우호적이나 사업화 연결 확인이 중요합니다.",
        "valuation": "중립적입니다. 일부 저평가 신호는 있지만 강한 안전마진은 제한적입니다.",
        "issue": "중립적입니다. 우호적 뉴스와 단기 과열 부담이 함께 있습니다.",
        "macro": "중립에서 다소 부담입니다. 거시환경은 방향성이 엇갈립니다.",
    }.get(agent, "중립적입니다.")


def _agent_investor_block(agent: str, packet: dict[str, Any]) -> str:
    """Render specialist compact packets without changing any specialist JSON.

    The block intentionally follows the user's preferred shape:
    요약 / 핵심 thesis / 주요 risk / 비고 / 다음 확인 포인트.
    Raw count metrics such as news_count/rss_count and scorecard JSON are not shown.
    Useful natural-language numbers already present in each agent's summary/thesis/risk
    are preserved.
    """
    ko = AGENT_KO.get(agent, agent)
    recommendation = _normalize_recommendation(packet.get("auditor_recommendation"))
    summary = _clean_investor_sentence(agent, packet.get("summary"), kind="summary", limit=520)
    if not summary or summary == "요약 정보 확인 제한":
        summary = _default_bullet(agent, "thesis")

    positives = _investor_bullets(agent, packet.get("key_thesis"), kind="thesis", limit=4)
    risks = _investor_bullets(agent, packet.get("key_risks"), kind="risk", limit=4)

    # Macro ECOS raw dictionaries should become a sentence, not a raw 대표 지표 block.
    if agent == "macro":
        metrics = packet.get("metrics") if isinstance(packet.get("metrics"), dict) else {}
        for key in ("ecos_daily", "ecos daily", "daily_ecos"):
            if key in metrics and metrics.get(key) not in (None, ""):
                ecos_line = _format_ecos_daily(metrics.get(key))
                if ecos_line and ecos_line not in positives:
                    positives.append(ecos_line)
                break

    notes = _note_lines(agent, packet)
    watch = _watch_points(agent)
    lines = [
        f"### {ko}",
        f"- **투자자 관점:** {_view_phrase(agent, recommendation)}",
        f"- **요약:** {summary}",
        "- **핵심 thesis:**",
    ]
    lines.extend(f"  - {item}" for item in positives)
    lines.append("- **주요 risk:**")
    lines.extend(f"  - {item}" for item in risks)
    if notes:
        lines.append("- **비고:**")
        lines.extend(f"  - {item}" for item in notes)
    lines.append("- **다음 확인 포인트:**")
    lines.extend(f"  - {item}" for item in watch)
    return "\n".join(lines)


def _watch_points(agent: str) -> list[str]:
    return {
        "finance": [
            "매출 회복이 영업이익 개선으로 이어지는지",
            "자유현금흐름이 안정적으로 유지되는지",
            "부채와 운전자본 부담이 낮아지는지",
        ],
        "market": [
            "AI·고성능 반도체 수요가 후공정 패키징 주문으로 이어지는지",
            "동종 후공정 기업 대비 주가 흐름이 유지되는지",
            "단기 급등락이 실수요인지 단기 수급인지",
        ],
        "tech": [
            "고객 채택, 양산, 매출 전환의 직접 근거가 나오는지",
            "특허의 청구항, 인용, 패밀리, 존속 상태가 보강되는지",
            "기술이 마진, 원가, 현금흐름 개선으로 이어지는지",
        ],
        "valuation": [
            "동종기업 대비 낮은 가격 지표가 정당한 할인인지",
            "현금흐름 기반 적정가와 기준 주가의 차이가 충분히 벌어지는지",
            "자본비용과 장기 성장률 가정 변화에 얼마나 민감한지",
        ],
        "issue": [
            "뉴스 기대감이 실제 수주, 실적, 공시로 이어지는지",
            "자회사·관계사 이슈가 본사 실적에 미치는 영향이 있는지",
            "단기 과열 또는 부정 키워드가 확산되는지",
        ],
        "macro": [
            "원달러 환율과 금리 방향이 성장주 부담을 키우는지",
            "신용스프레드와 위험선호가 자금조달 환경을 악화시키는지",
            "반도체 수출 규제와 글로벌 수요 변화가 업황에 영향을 주는지",
        ],
    }.get(agent, ["최신 공시와 원천 데이터를 다시 확인해야 합니다."])


def _compact_block(agent: str, packet: dict[str, Any]) -> str:
    # Backward-compatible name; final report uses investor-friendly block.
    return _agent_investor_block(agent, packet)


def _decision_from_quantitative(qd: dict[str, Any], packets: list[dict[str, Any]]) -> tuple[str, float, str, list[str]]:
    if isinstance(qd, dict) and qd.get("final_recommendation"):
        final = _normalize_recommendation(qd.get("final_recommendation"))
        weighted = _safe_float(qd.get("weighted_signal"), 0.0)
        base = _normalize_recommendation(qd.get("base_recommendation") or final)
        reasons = _list_text(qd.get("adjustment_reasons"), 5)
        return final, weighted, base, reasons

    available_packets: dict[str, dict[str, Any]] = {}
    signal_by_agent: dict[str, float] = {}
    for packet in packets:
        agent = _agent_name(packet)
        if not agent:
            continue
        signal = packet.get("auditor_signal")
        if signal is None:
            rec = _normalize_recommendation(packet.get("auditor_recommendation"))
            signal = {"매수": 1.0, "보유": 0.0, "매도": -1.0}.get(rec, 0.0)
        available_packets[agent] = packet
        signal_by_agent[agent] = _safe_float(signal, 0.0)

    if not signal_by_agent:
        return "보유", 0.0, "보유", ["사용 가능한 에이전트 신호가 없어 보유로 처리"]

    if compute_dma_weights is not None:
        dma_result = compute_dma_weights(available_packets, signals=signal_by_agent)
        weights = dma_result.get("weights_adjusted") or dma_result.get("weights") or {}
    else:
        weights = {}

    if not weights:
        weights = {agent: 1.0 / len(signal_by_agent) for agent in signal_by_agent}

    total_weight = sum(float(weights.get(a, 0.0) or 0.0) for a in signal_by_agent) or 1.0
    weights = {a: float(weights.get(a, 0.0) or 0.0) / total_weight for a in signal_by_agent}
    weighted = sum(signal_by_agent[a] * weights.get(a, 0.0) for a in signal_by_agent)

    agent_decisions = {}
    for packet in packets:
        agent = _agent_name(packet)
        if agent not in signal_by_agent:
            continue
        label = _normalize_recommendation(
            packet.get("auditor_recommendation")
            or packet.get("recommendation")
            or packet.get("final_recommendation")
            or packet.get("opinion")
        )
        agent_decisions[agent] = {"signal": signal_by_agent[agent], "recommendation": label}

    final = "보유"
    if compute_dma_label_posterior is not None and agent_decisions:
        try:
            label_model = compute_dma_label_posterior(agent_decisions, weights)
            final = _normalize_recommendation(label_model.get("final_recommendation"))
        except Exception:
            final = "보유"
    return final, weighted, final, ["Auditor 정량결과가 없어 Chair fallback에서도 signal cutoff 없이 DMA categorical posterior/current labels로 계산"]



def _format_signal_value(value: Any) -> str:
    """Format a Chair/Auditor signal value while keeping the report compact."""
    try:
        num = float(value)
    except Exception:
        num = 0.0
    return f"{num:+.3f}"


def _signal_direction(value: Any) -> str:
    try:
        num = float(value)
    except Exception:
        num = 0.0
    if num > 0.0:
        return "연속 신호 양(+) 방향"
    if num < 0.0:
        return "연속 신호 음(-) 방향"
    return "연속 신호 중립"




def _signal_word(value: Any) -> str:
    """Interpret DMA weighted_signal as direction only, not as a label cutoff."""
    try:
        num = float(value)
    except Exception:
        num = 0.0
    if num > 0.0:
        return "에이전트 가중평균 양(+) 방향"
    if num < 0.0:
        return "에이전트 가중평균 음(-) 방향"
    return "에이전트 가중평균 중립(0)"


def _format_number(value: Any, decimals: int = 1) -> str:
    try:
        num = float(value)
    except Exception:
        return _to_text(value)
    if abs(num - round(num)) < 1e-9:
        return f"{int(round(num)):,}"
    return f"{num:,.{decimals}f}"


def _format_percent_value(value: Any) -> str:
    try:
        num = float(value)
    except Exception:
        return _to_text(value)
    pct = num * 100 if abs(num) <= 1 else num
    return f"{pct:+.1f}%"


def _money_krw(value: Any) -> str:
    try:
        num = float(value)
    except Exception:
        return _to_text(value)
    return f"{int(round(num)):,}원"


def _status_text(value: Any) -> str:
    text = _replace_labels(value)
    # Remove exact score fragments but preserve the qualitative status.
    text = re.sub(r"[-+]?\d+(?:\.\d+)?\s*(?:%|점|/100|배|원|억원|조원|건)", "", text)
    text = re.sub(r"\b[-+]?\d+(?:\.\d+)?\b", "", text)
    text = re.sub(r"\s{2,}", " ", text).strip(" ,;:/·-")
    return text or _replace_labels(value)


_METRIC_LABELS: dict[str, str] = {
    "sales_growth_%": "매출 성장 방향",
    "operating_margin_%": "영업수익성",
    "ROE_%": "자본 효율성",
    "fcf": "자유현금흐름",
    "debt_ratio_%": "부채 부담",
    "annual_return_%": "최근 주가 흐름",
    "annual_mdd_%": "주가 낙폭 위험",
    "market_total_score": "시장 종합 판단",
    "current_price_krw": "기준 주가",
    "current_price": "기준 주가",
    "change_krw": "당일 가격 변화",
    "change_rate_pct": "단기 가격 변화",
    "upside_downside_pct": "적정가 대비 가격 여력",
    "implied_price_krw": "현금흐름 기준 적정가",
    "intrinsic_price": "현금흐름 기준 적정가",
    "peer_psr": "동종기업 대비 매출가치 위치",
    "target_psr": "대상 기업 매출가치 지표",
    "peer_median_psr": "비교기업 매출가치 중앙값",
    "original_agent_view_reference": "기존 에이전트 참고 의견",
    "news_count": "확인한 뉴스 수",
    "rss_count": "확인한 RSS 수",
    "related_keyword_count": "관련 키워드 수",
    "df_news_rows": "구조화 뉴스 행 수",
    "macro_signal": "거시 방향성",
    "risk_level": "거시 부담 수준",
    "warning_stock": "투자경고 여부",
    "ecos_daily": "국내 금리·환율·신용 환경",
    "ecos daily": "국내 금리·환율·신용 환경",
    "daily_ecos": "국내 금리·환율·신용 환경",
    "peer_composite_percentile": "동종기업 내 기술 위치",
    "peer_percentile_band": "동종기업 내 위치 구간",
    "ip_evidence_bridge_signal": "특허 품질 신호",
    "ip_evidence_composite_bridge_signal": "특허 품질 신호",
}

_SCORE_LIKE_KEYS = {
    "ip_evidence_composite_score",
    "final_tech_investor_score",
    "base_bridge_score",
    "final_bridge_score_after_ip_evidence",
    "peer_adjusted_bridge_score_before_ip_evidence",
    "valuation_score",
    "valuation_scorecard",
    "macro_score",
    "score",
    "total_score",
}




def _parse_jsonish(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            # Some logs contain blanks after colon. Keep zone fields by regex.
            zones = re.findall(r'"([^"{}]+_zone)"\s*:\s*"([^"]+)"', text)
            return {k: v for k, v in zones}
    return {}


def _zone_ko(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text == "high":
        return "높은 구간"
    if text == "low":
        return "낮은 구간"
    if text == "neutral":
        return "중립 구간"
    if text == "medium":
        return "중간 구간"
    return _replace_labels(value)


def _format_ecos_daily(value: Any) -> str:
    data = _parse_jsonish(value)
    if not data:
        return "국내 금리·환율·신용 환경: 세부 수치 확인은 제한적이지만, 성장주 부담 변수로 계속 확인해야 합니다."
    def zone(name: str) -> str:
        return _zone_ko(data.get(f"{name}_zone")) if data.get(f"{name}_zone") not in (None, "") else "확인 제한"
    k10 = zone("국고채_10년")
    k3 = zone("국고채_3년")
    usd = zone("원달러")
    bbb = zone("신용스프레드_bbb-")
    aa = zone("신용스프레드_aa-")
    cd = zone("cd금리_91일")
    call = zone("콜금리")
    parts: list[str] = []
    if k10 != "확인 제한" or k3 != "확인 제한":
        if "높" in k10 or "높" in k3:
            parts.append("국고채 금리는 높은 구간으로 성장주 할인율에 부담입니다")
        elif "낮" in k10 or "낮" in k3:
            parts.append("국고채 금리는 낮은 구간으로 유동성 부담이 상대적으로 완화됩니다")
        else:
            parts.append("국고채 금리는 중립 구간입니다")
    if usd != "확인 제한":
        parts.append("원달러 환율은 높은 구간이라 원화 약세와 외국인 수급 부담을 확인해야 합니다" if "높" in usd else f"원달러 환율은 {usd}입니다")
    if bbb != "확인 제한":
        parts.append("BBB- 신용스프레드는 높은 구간이라 중소형 성장기업의 자금조달 부담을 키울 수 있습니다" if "높" in bbb else f"BBB- 신용스프레드는 {bbb}입니다")
    if aa != "확인 제한":
        parts.append("AA- 신용스프레드는 낮은 구간으로 우량 신용시장 부담은 상대적으로 제한적입니다" if "낮" in aa else f"AA- 신용스프레드는 {aa}입니다")
    if cd != "확인 제한" or call != "확인 제한":
        parts.append(f"단기금리는 CD금리 {cd}, 콜금리 {call}으로 해석됩니다")
    return "국내 금리·환율·신용 환경: " + "; ".join(parts[:4]) + "."


def _format_nested_metric_line(agent: str, key: str, value: Any) -> str:
    lower_key = str(key).lower()
    if "ecos" in lower_key:
        return _format_ecos_daily(value)
    if agent == "macro":
        return _qualitative_from_metric(agent, f"{key}: {value}", kind="thesis")
    if agent == "tech":
        return _qualitative_from_metric(agent, f"{key}: {value}", kind="thesis")
    if agent == "valuation":
        return _qualitative_from_metric(agent, f"{key}: {value}", kind="thesis")
    return ""


def _format_metric_line(agent: str, key: str, value: Any) -> str:
    if value in (None, ""):
        return ""
    lower_key = str(key).lower()
    label = _METRIC_LABELS.get(key) or _METRIC_LABELS.get(lower_key) or key.replace("_", " ")

    if isinstance(value, dict) or "ecos" in lower_key:
        nested = _format_nested_metric_line(agent, key, value)
        if nested:
            return nested

    if lower_key in {"peer_composite_percentile", "peer_percentile", "tech_peer_percentile"}:
        return "동종기업 내 기술 위치: 후공정·패키징 비교군 안에서 중상위권으로 해석됩니다."
    if lower_key in {"peer_percentile_band"}:
        return f"{label}: {_status_text(value)}"

    # Scores are not displayed as scores in the final investor report.
    if lower_key in _SCORE_LIKE_KEYS or lower_key.endswith("_score") or "score" in lower_key:
        if agent == "tech":
            return "기술 판정: 기술의 사업화 가능성은 우호적이지만, 고객 채택·양산·매출 전환 확인이 필요합니다."
        if agent == "valuation":
            return "가치평가 판정: 상대적 매력은 일부 있지만, 강한 안전마진으로 단정하기는 어렵습니다."
        if agent == "macro":
            return "거시 판정: 성장주에 부담이 되는 변수와 완화 요인이 함께 있습니다."
        return ""

    if "price" in lower_key or lower_key.endswith("_krw") or lower_key in {"fcf", "change_krw", "current_price"}:
        if lower_key == "fcf":
            try:
                return f"{label}: {_format_number(float(value) / 100_000_000, 1)}억원 수준"
            except Exception:
                return f"{label}: {_to_text(value)}"
        return f"{label}: {_money_krw(value)}"

    if "pct" in lower_key or lower_key.endswith("_%") or "margin" in lower_key or "ratio" in lower_key or "roe" in lower_key:
        return f"{label}: {_format_percent_value(value)}"

    if lower_key in {"news_count", "rss_count", "related_keyword_count", "df_news_rows"}:
        return f"{label}: {_format_number(value, 0)}건"

    if lower_key in {"original_agent_view_reference", "macro_signal", "risk_level", "warning_stock"}:
        return f"{label}: {_status_text(value)}"

    if isinstance(value, (int, float)):
        return f"{label}: {_format_number(value, 2)}"
    text = _status_text(value)
    return f"{label}: {text}" if text else ""


def _representative_metric_lines(agent: str, packet: dict[str, Any], limit: int = 4) -> list[str]:
    metrics = packet.get("metrics")
    if not isinstance(metrics, dict):
        return []
    preferred_by_agent = {
        "finance": ["sales_growth_%", "operating_margin_%", "ROE_%", "fcf", "debt_ratio_%", "annual_mdd_%"],
        "market": ["current_price_krw", "current_price", "change_krw", "change_rate_pct", "market_total_score"],
        "tech": ["original_agent_view_reference", "peer_percentile_band", "peer_composite_percentile", "final_tech_investor_score", "ip_evidence_composite_score", "base_bridge_score"],
        "valuation": ["upside_downside_pct", "implied_price_krw", "current_price_krw", "original_agent_view_reference", "peer_psr", "peer_median_psr"],
        "issue": ["news_count", "rss_count", "related_keyword_count", "df_news_rows"],
        "macro": ["macro_signal", "risk_level", "macro_score", "ecos_daily", "ecos daily", "daily_ecos"],
    }
    keys = preferred_by_agent.get(agent, []) + [k for k in metrics.keys() if k not in preferred_by_agent.get(agent, [])]
    out: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key not in metrics or key in seen:
            continue
        seen.add(key)
        line = _format_metric_line(agent, key, metrics.get(key))
        if line and line not in out:
            out.append(line)
        if len(out) >= limit:
            break
    return out


def _note_lines(agent: str, packet: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    raw_signal = packet.get("auditor_signal")
    if raw_signal is not None:
        notes.append(f"영역별 방향성 신호(signal): {_signal_word(raw_signal)}")
    rec = packet.get("auditor_recommendation")
    if rec:
        notes.append(f"요약 판단: {_normalize_recommendation(rec)}")
    metrics = packet.get("metrics") if isinstance(packet.get("metrics"), dict) else {}
    for key in ("grade", "label", "risk_level", "macro_signal", "ip_evidence_bridge_signal", "ip_evidence_composite_bridge_signal", "original_agent_view_reference"):
        if key in metrics and metrics.get(key) not in (None, ""):
            label = _METRIC_LABELS.get(key, _METRIC_LABELS.get(key.lower(), key.replace("_", " ")))
            notes.append(f"{label}: {_status_text(metrics.get(key))}")
    # Deduplicate and keep short.
    out: list[str] = []
    for n in notes:
        if n and n not in out:
            out.append(n)
        if len(out) >= 3:
            break
    return out


def _signal_summary_block(weighted_signal: float, by_agent: dict[str, dict[str, Any]]) -> str:
    """Expose signal / weighted_signal, but translate them into Korean investor language."""
    lines = [
        "## 2. 방향성 신호 요약",
        "최종 보고서에서는 내부 검증 점수표는 제외하고, 투자 방향을 이해하는 데 필요한 신호만 남깁니다.",
        f"- **종합 방향성 신호(weighted_signal):** {_signal_word(weighted_signal)}입니다. 이 값은 전체 분석 영역의 방향을 합친 참고 신호입니다.",
        "- **영역별 방향성 신호(signal):** 각 분석 영역이 최종 판단에 우호적인지, 부담인지를 보여주는 보조 신호입니다.",
    ]
    agent_parts: list[str] = []
    for agent in AGENT_ORDER:
        packet = by_agent.get(agent, {})
        if not packet:
            continue
        raw_signal = packet.get("auditor_signal")
        if raw_signal is None:
            rec = _normalize_recommendation(packet.get("auditor_recommendation"))
            raw_signal = {"매수": 1.0, "보유": 0.0, "매도": -1.0}.get(rec, 0.0)
        agent_parts.append(f"{AGENT_KO.get(agent, agent)}: {_signal_word(raw_signal)}")
    if agent_parts:
        lines.append("  - " + " / ".join(agent_parts))
    lines.append("- 비고: 양수·음수 같은 원천 신호는 내부 계산용이며, 투자자용 보고서에서는 우호·중립·부담의 의미로 해석합니다.")
    return "\n".join(lines)


def _one_line_conclusion(final_decision: str, by_agent: dict[str, dict[str, Any]]) -> str:
    recs = {a: _normalize_recommendation(p.get("auditor_recommendation")) for a, p in by_agent.items()}
    tech_positive = recs.get("tech") == "매수"
    issue_positive = recs.get("issue") == "매수"
    macro_negative = recs.get("macro") == "매도"
    valuation_hold = recs.get("valuation") == "보유"
    finance_not_buy = recs.get("finance") != "매수"
    if final_decision == "매수":
        return "기술·가격·재무 신호가 함께 우호적으로 맞물릴 때 편입을 검토할 수 있는 구간입니다."
    if final_decision == "매도":
        return "기술 기대보다 재무·가격·거시 부담이 더 커 보이는 구간입니다."
    if tech_positive or issue_positive:
        if macro_negative or valuation_hold or finance_not_buy:
            return "기술과 업황 기대는 있지만 가격 안전마진, 수익성, 거시 부담을 함께 보면 관망이 더 적절한 구간입니다."
    return "긍정 신호와 부담 요인이 엇갈려, 추가 확인 전에는 관망이 더 적절한 구간입니다."


def _core_summary(final_decision: str, by_agent: dict[str, dict[str, Any]]) -> list[str]:
    bullets: list[str] = []
    valuation = by_agent.get("valuation", {})
    tech = by_agent.get("tech", {})
    market = by_agent.get("market", {})
    finance = by_agent.get("finance", {})
    macro = by_agent.get("macro", {})
    issue = by_agent.get("issue", {})

    bullets.append("최종 의견은 단기 상승 재료보다 재무 체력, 가격 안전마진, 기술 사업화 가능성을 함께 본 결과입니다.")
    bullets.append(_investor_bullets("valuation", valuation.get("key_thesis") or valuation.get("summary"), kind="thesis", limit=1)[0])
    bullets.append(_investor_bullets("tech", tech.get("key_thesis") or tech.get("summary"), kind="thesis", limit=1)[0])
    bullets.append(_investor_bullets("market", market.get("key_thesis") or market.get("summary"), kind="thesis", limit=1)[0])
    bullets.append(_investor_bullets("finance", finance.get("key_risks") or finance.get("summary"), kind="risk", limit=1)[0])
    if _normalize_recommendation(macro.get("auditor_recommendation")) == "매도":
        bullets.append(_investor_bullets("macro", macro.get("key_risks") or macro.get("summary"), kind="risk", limit=1)[0])
    elif issue:
        bullets.append(_investor_bullets("issue", issue.get("key_thesis") or issue.get("summary"), kind="thesis", limit=1)[0])
    # Deduplicate and keep concise
    out: list[str] = []
    for b in bullets:
        if b and b not in out:
            out.append(b)
        if len(out) >= 5:
            break
    return out


def _relative_interpretation(by_agent: dict[str, dict[str, Any]]) -> list[str]:
    tech = by_agent.get("tech", {})
    valuation = by_agent.get("valuation", {})
    market = by_agent.get("market", {})
    lines = [
        _investor_bullets("tech", tech.get("key_thesis") or tech.get("summary"), kind="thesis", limit=1)[0],
        _investor_bullets("valuation", valuation.get("key_thesis") or valuation.get("summary"), kind="thesis", limit=1)[0],
        _investor_bullets("market", market.get("key_thesis") or market.get("summary"), kind="thesis", limit=1)[0],
        "동종기업 대비 싸 보이는 지표가 있더라도, 그 이유가 성장성 부족·수익성 부진·재무 리스크 때문인지 함께 봐야 합니다.",
        "기술 위치가 좋아도 실제 고객 채택, 양산, 매출, 현금흐름으로 이어질 때 투자 매력이 더 커집니다.",
    ]
    out: list[str] = []
    for line in lines:
        cleaned = _clean_investor_sentence("valuation" if "싸" in line else "tech", line, kind="thesis", limit=220)
        if cleaned and cleaned not in out:
            out.append(cleaned)
    return out


def _deeptech_ib_framework_lines() -> list[str]:
    return [
        "딥테크 기업은 기술검증, 파일럿, 첫 상업계약, 초기 상업화, 대규모 양산으로 이어질 때 가치평가 가산이 커집니다.",
        "R&D는 노력 신호이고, 특허·청구항·인용·패밀리는 기술 산출물 신호입니다. 최종적으로는 고객 채택, 양산, 매출, 현금흐름 전환이 확인되어야 합니다.",
        "현금흐름 기반 가치평가와 동종기업 멀티플은 가격을 보는 도구입니다. 기술이 좋아도 현재 가격이 이미 기대를 많이 반영했다면 보수적으로 볼 수 있습니다.",
        "CB/BW, 메자닌, 유상증자, 차입 확대는 성장자금일 수도 있지만 기존 주주에게는 희석과 오버행 리스크가 될 수 있습니다.",
        "정부과제나 정책 수혜는 긍정 신호지만, 실제 제품화·수주·매출로 이어지는지 확인해야 합니다.",
    ]


def _conflict_interpretation_lines(final_decision: str, by_agent: dict[str, dict[str, Any]]) -> list[str]:
    rec = {agent: _normalize_recommendation(packet.get("auditor_recommendation")) for agent, packet in by_agent.items()}
    lines: list[str] = []
    if rec.get("tech") == "매수" and rec.get("valuation") != "매수":
        lines.append("기술 분석은 우호적이지만, 가치평가에서는 강한 가격 안전마진이 확인되지 않아 최종 판단을 보수적으로 낮췄습니다.")
    if rec.get("issue") == "매수" and rec.get("finance") != "매수":
        lines.append("뉴스·이슈 흐름은 우호적이지만, 재무 분석에서는 수익성 정상화와 부채 부담을 더 확인해야 한다는 신호가 남아 있습니다.")
    if rec.get("market") == "매수" and rec.get("macro") == "매도":
        lines.append("산업 성장성은 좋지만 환율·금리·신용환경 같은 거시 변수는 성장주 밸류에이션에 부담을 줄 수 있습니다.")
    if rec.get("valuation") == "매수" and rec.get("finance") == "매도":
        lines.append("상대적으로 싸 보이는 가격 신호가 있더라도, 재무 체력이 약하면 저평가가 아니라 정당한 할인일 수 있습니다.")
    if not lines:
        lines.append("각 분석 영역의 방향이 완전히 한쪽으로 쏠리지는 않아, 최종 의견은 우호 신호와 부담 신호를 함께 반영한 결과입니다.")
    lines.append(f"따라서 최종 의견은 **{final_decision}**으로 정리하되, 이후 수주·양산·실적·현금흐름 확인 여부에 따라 판단이 달라질 수 있습니다.")
    return lines


def _performance_label_summary_lines(final_decision: str, weighted_signal: float, by_agent: dict[str, dict[str, Any]]) -> list[str]:
    buy_rule = "final_label 또는 최종 의견이 매수인 종목만 성과평가 포트폴리오에 동일가중으로 편입합니다."
    if final_decision != "매수":
        buy_rule = "이번 종목은 최종 의견이 매수가 아니므로, 기본 성과평가 포트폴리오에는 편입하지 않고 관찰 대상으로 둡니다."
    return [
        f"성과평가용 최종 라벨은 **{final_decision}**입니다.",
        f"종합 방향성 신호는 {_signal_word(weighted_signal)}로 해석하며, 임계값을 임의로 바꾸는 대신 보조 민감도 분석에 사용합니다.",
        buy_rule,
        "실제 성과는 기준월 말 종가 대비 다음 달 말 종가의 1개월 보유수익률로 계산하고, 반도체 후보군 동일가중 평균 또는 자기 자신을 제외한 peer 평균 대비 초과수익률을 함께 확인합니다.",
    ]


def _build_compact_report(company: str, company_dir: str, packets: list[dict[str, Any]], audit_result: dict[str, Any]) -> str:
    qd = _extract_quantitative_decision(audit_result, company_dir)
    final_decision, weighted_signal, base_decision, adjust_reasons = _decision_from_quantitative(qd, packets)
    by_agent = _latest_by_agent(packets)

    one_line = _one_line_conclusion(final_decision, by_agent)
    core_items = _core_summary(final_decision, by_agent)
    relative_lines = _relative_interpretation(by_agent)
    framework_lines = _deeptech_ib_framework_lines()

    blocks = [
        f"# {company} 개인투자자용 종합 투자 보고서",
        "",
        "## 1. 최종 의견",
        f"**{final_decision}**",
        "",
        f"**한 줄 결론:** {one_line}",
        "",
        _signal_summary_block(weighted_signal, by_agent),
        "",
        "## 3. 투자 판단 핵심",
        "이 보고서는 각 전문 에이전트가 만든 결과를 Chair 단계에서 개인투자자용 언어로 풀어쓴 보고서입니다. 원천 JSON은 바꾸지 않고, 영어 필드명과 점수 중심 표현만 쉬운 해석으로 정리했습니다.",
        "",
        "핵심적으로는 다음을 함께 봅니다.",
        "- **재무 체력:** 기술 사업화까지 버틸 수 있는 현금흐름, 수익성, 부채 부담",
        "- **가치평가:** 현재 가격이 동종기업과 현금흐름 기준으로 과도하게 비싼지 또는 싼지",
        "- **기술 사업화:** 특허 수 자체보다 고객 채택, 양산, 매출, 현금흐름으로 이어질 가능성",
        "- **시장·이슈·거시:** 산업 성장성, 단기 촉매, 환율·금리·신용환경의 부담",
        "",
        "## 4. 핵심 판단 요약",
        "\n".join(f"{i}. {item}" for i, item in enumerate(core_items, 1)),
        "",
        "## 5. 분석 영역별 쉬운 해석",
    ]
    for agent in AGENT_ORDER:
        packet = by_agent.get(agent, {"agent": agent, "summary": "요약 정보 확인 제한"})
        blocks.append(_agent_investor_block(agent, packet))
        blocks.append("")

    conflict_lines = _conflict_interpretation_lines(final_decision, by_agent)
    performance_lines = _performance_label_summary_lines(final_decision, weighted_signal, by_agent)
    blocks.extend([
        "## 6. 충돌 지점 및 해석",
        "\n".join(f"- {line}" for line in conflict_lines),
        "",
        "## 7. 동종기업 대비 해석",
        "\n".join(f"- {line}" for line in relative_lines),
        "",
        "## 8. 딥테크·IB 관점에서 꼭 봐야 할 점",
        "\n".join(f"- {line}" for line in framework_lines),
        "",
        "## 9. 투자 전 체크포인트",
        "- **가격:** 동종기업 대비 싸 보이는 이유가 성장성 부족, 수익성 부담, 재무 리스크 때문인지 확인해야 합니다.",
        "- **재무:** 매출 회복보다 영업수익성, 현금창출력, 부채 부담의 개선 여부를 우선 확인해야 합니다.",
        "- **기술:** 특허 수보다 고객 채택, 양산, 매출 전환, 현금흐름 개선이 확인되어야 합니다.",
        "- **자금조달:** CB/BW, 유상증자, 차입 확대는 성장자금인 동시에 주주가치 희석 위험이 될 수 있습니다.",
        "- **거시:** 환율, 금리, 신용환경이 나빠지면 반도체 성장주의 적정가치가 낮아질 수 있습니다.",
        "",
        "## 10. 성능평가용 라벨 요약",
        "\n".join(f"- {line}" for line in performance_lines),
        "",
        "## 11. 종합 의견",
        f"{company}의 최종 의견은 **{final_decision}**입니다. 기술과 업황 기대는 분명히 존재하지만, 가격 안전마진과 재무·거시 부담을 함께 보면 아직은 관망이 더 적절합니다. 특히 딥테크 기업은 특허 수나 기술 키워드만으로 판단하기보다, 그 기술이 고객 채택·양산·매출·현금흐름으로 이어지는지를 확인해야 합니다. 동종기업 대비 싸 보이는 지표가 있더라도 그 이유가 성장성 부족이나 재무 부담 때문일 수 있으므로, 최신 공시와 수주·양산 근거, 자금조달 이력을 함께 확인하는 것이 좋습니다.",
    ])
    report = "\n".join(blocks).strip()
    # Final guardrail: remove leftover raw JSON/scorecard fragments without deleting useful Korean numbers.
    report = re.sub(r"^[ \t]*- [^\n]*(?:news_count|rss_count|related_keyword_count|df_news_rows|scoring:|scorecard|raw_passed|min_actual_match|avg_actual_match)[^\n]*\n?", "", report, flags=re.IGNORECASE | re.MULTILINE)
    report = re.sub(r"^[ \t]*- [^\n]*\{[^\n]*\}[^\n]*\n?", "", report, flags=re.MULTILINE)
    report = re.sub(r"\b(?:raw_passed|min_actual_match|avg_actual_match|score=|label=|grade=|PASS)\b", "", report, flags=re.IGNORECASE)
    report = re.sub(r"\(\s*\)", "", report)
    report = re.sub(r"\n{3,}", "\n\n", report)
    return report.strip()


def _normalize_openai_base_url(base_url: str) -> str:
    return (base_url or "https://integrate.api.nvidia.com/v1").strip().rstrip("/")


def _make_llm():
    if _env_bool("CHAIR_DISABLE_LLM", True):
        return None
    try:
        from langchain_openai import ChatOpenAI
    except Exception as exc:
        print(f"[Chair] langchain_openai 로드 실패 → deterministic 보고서 사용: {exc}")
        return None

    api_key = _env_first("CHAIR_LLM_API_KEY", "NVIDIA_PARALLEL_API_KEY", "NVIDIA_API_KEY", "OPENAI_API_KEY")
    if not api_key:
        return None
    base_url = _env_first("CHAIR_LLM_BASE_URL", "NVIDIA_PARALLEL_BASE_URL", "NVIDIA_BASE_URL", "OPENAI_BASE_URL", default="https://integrate.api.nvidia.com/v1")
    model = _env_first("CHAIR_LLM_MODEL", "NVIDIA_PARALLEL_MODEL", "OPENAI_MODEL", default="qwen/qwen3.5-122b-a10b")
    timeout = _safe_int(os.getenv("CHAIR_LLM_TIMEOUT") or os.getenv("REQUEST_TIMEOUT"), 60)
    try:
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=_normalize_openai_base_url(base_url),
            temperature=0,
            max_tokens=REPORT_MAX_TOKENS,
            timeout=timeout,
        )
    except TypeError:
        return ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=_normalize_openai_base_url(base_url),
            temperature=0,
            max_tokens=REPORT_MAX_TOKENS,
        )


def _invoke_llm(llm: Any, prompt: str) -> str:
    result = llm.invoke(prompt)
    content = getattr(result, "content", result)
    if isinstance(content, list):
        return "\n".join(str(item.get("text") or item.get("content") or item) if isinstance(item, dict) else str(item) for item in content).strip()
    return str(content).strip()


def _strip_end_marker(report: str) -> str:
    return (report or "").replace(END_MARKER, "").strip()


def _sanitize_public_report_text(report: str) -> str:
    """Keep the Chair markdown investor-facing and close to the reference format."""

    text = str(report or "")
    replacements = {
        "LLM 호출 오류가 발생해 fallback 결과를 반환합니다.": "자동 분석 결과가 제한되어 가격·시장 데이터 중심으로 보수적으로 해석합니다.",
        "fallback 결과를 반환합니다.": "보수적 대체 분석 결과를 사용했습니다.",
        "Gemini API error": "외부 LLM 보조 분석 오류",
        "Qwen 3.5 fallback": "보조 분석 경로",
        "NVIDIA-compatible fallback": "보조 분석 경로",
        "Gateway Timeout": "외부 분석 지연",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove raw API/debug fragments that should not appear in the investor report.
    text = re.sub(r"\\[?\\d{3}\\]?\\s*Gateway Timeout[^\\n]*", "외부 분석 지연으로 로컬 검증 데이터를 우선 사용했습니다.", text)
    text = re.sub(r"Gemini API error status=\\d+[^\\n]*", "외부 LLM 보조 분석 오류가 있어 로컬 검증 데이터를 우선 사용했습니다.", text)
    text = re.sub(r"\\{['_]content['_].*?\\}", "", text, flags=re.DOTALL)
    text = re.sub(r"^[ \\t]*- [^\\n]*(?:raw_passed|min_actual_match|avg_actual_match|debug_policy|receipt_path)[^\\n]*\\n?", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"\\n{3,}", "\\n\\n", text)
    return text.strip()



def _extract_final_recommendation(report: str) -> str:
    head = str(report or "")[:2000]
    for label in ("매수", "보유", "매도"):
        if re.search(rf"(최종\s*의견|최종\s*추천|final_label|최종\s*판단)[^\n]{{0,100}}{label}", head):
            return label
    for label in ("매수", "보유", "매도"):
        if label in head:
            return label
    return "보유"


def _write_report(company_dir: str, report: str) -> Path:
    path = agent_output_path(company_dir, "chair", f"{company_dir}_chair_report.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    return path


def _write_chair_json(
    company_dir: str,
    payload: dict[str, Any],
    *,
    debug_payload: dict[str, Any] | None = None,
) -> dict[str, str]:
    primary = agent_output_path(company_dir, "chair", f"{company_dir}_chair.json")
    packet = agent_output_path(company_dir, "chair", f"{company_dir}_chair_agent_packet.json")
    debug_packet = agent_output_path(company_dir, "chair", f"{company_dir}_chair_debug_packet.json")
    payload = dict(payload)
    payload.setdefault("output_files", {}).update({
        "chair_json": rel_project_path(primary),
        "chair_agent_packet_json": rel_project_path(packet),
    })
    output_paths = {
        "chair_json": rel_project_path(primary),
        "chair_agent_packet_json": rel_project_path(packet),
    }
    if debug_payload is not None:
        payload["output_files"]["chair_debug_packet_json"] = rel_project_path(debug_packet)
        debug_payload = dict(debug_payload)
        debug_payload["output_files"] = dict(payload["output_files"])
        write_json(debug_packet, debug_payload)
        output_paths["chair_debug_packet_json"] = rel_project_path(debug_packet)
    write_json(primary, payload)
    write_json(packet, payload)
    return output_paths


def _sheets_history_result_mode() -> bool:
    """Return True when Chair/Auditor outputs should be stored in Google Sheets.

    In historical replay runs this mode is enabled by
    ALPHAPROVE_HISTORY_BACKEND=sheets and ALPHAPROVE_SHEETS_DB_ONLY=1.
    The input agent snapshots are read from Google Sheets and Chair/Auditor
    run results are appended back to Google Sheets.
    """
    return using_google_sheets_history() and _env_bool("ALPHAPROVE_SHEETS_DB_ONLY", True)


def _history_local_write_disabled() -> bool:
    """Chair keeps local MD/JSON by default even when a Sheets backend exists."""

    if not _sheets_history_result_mode():
        return False
    return _env_bool("CHAIR_ALLOW_SHEETS_ONLY_OUTPUT", False)


def _history_run_id() -> str:
    raw = os.getenv("ALPHAPROVE_HISTORY_RUN_ID", "").strip()
    if raw:
        return raw
    as_of = _history_result_as_of_date()
    return f"chair_sheets_{as_of}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _coerce_as_of_date(value: Any) -> str:
    text = str(value or "").strip()
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text


def _history_result_as_of_date() -> str:
    for name in (
        "ALPHAPROVE_AS_OF_DATE",
        "ALPHAPROVE_HISTORY_AS_OF_DATE",
        "ALPHAPROVE_DATA_AS_OF_DATE",
        "CHAIR_AS_OF_DATE",
        "MARKET_AS_OF_DATE",
        "MACRO_AS_OF_DATE",
        "FINANCE_AS_OF_DATE",
        "ISSUE_AS_OF_DATE",
        "VALUATION_AS_OF_DATE",
    ):
        value = _coerce_as_of_date(os.getenv(name, ""))
        if value:
            return value
    return datetime.now().strftime("%Y-%m-%d")


def _save_history_run_result(
    *,
    company_dir: str,
    company: str,
    agent: str,
    output_kind: str,
    payload: Any,
) -> dict[str, Any] | None:
    if not _sheets_history_result_mode():
        return None

    as_of_date = _history_result_as_of_date()
    field = _agent_history_field()
    run_id = _history_run_id()

    result = save_run_result(
        run_id=run_id,
        as_of_date=as_of_date,
        field=field,
        company_dir=company_dir,
        company_name=company,
        agent=agent,
        output_kind=output_kind,
        payload=payload,
    )
    print(
        f"[Chair] Google Sheets 저장 완료 → run_id={run_id}, "
        f"agent={agent}, output_kind={output_kind}, chunks={result.get('chunk_count') if isinstance(result, dict) else ''}",
        flush=True,
    )
    return result if isinstance(result, dict) else None


def _chair_csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [chunk.strip() for chunk in str(raw).replace(";", ",").split(",") if chunk.strip()]


def _agent_history_replay_enabled() -> bool:
    """Return True when Chair should use stored agent snapshots instead of live intake."""
    return _env_bool("ALPHAPROVE_USE_AGENT_HISTORY", False)


def _agent_history_as_of_date() -> str:
    as_of_date = os.getenv("ALPHAPROVE_AS_OF_DATE", "").strip()
    if not as_of_date:
        raise RuntimeError(
            "ALPHAPROVE_USE_AGENT_HISTORY=1 이지만 ALPHAPROVE_AS_OF_DATE가 없습니다. "
            "예: $env:ALPHAPROVE_AS_OF_DATE='2025-05-01'"
        )
    return as_of_date


def _agent_history_field() -> str:
    raw = os.getenv("ALPHAPROVE_FIELD", os.getenv("CHAIR_DATA_INTAKE_FIELD", "반도체"))
    return normalize_field_name(raw)


def _agent_history_required_agents() -> list[str]:
    """Agents required for a historical Chair replay.

    Data Intake itself is not removed from the pipeline. In replay mode, this node
    becomes an input-readiness check against the configured history backend so that latest
    live intake files are not regenerated before the Chair run.
    """
    default = ",".join([agent for agent in AGENT_ORDER if agent in {"finance", "market", "tech", "valuation", "issue", "macro"}])
    return _chair_csv_env("ALPHAPROVE_HISTORY_REQUIRED_AGENTS", default)


def _validate_agent_history_snapshots(
    *,
    company_dir: str,
    company: str,
    field: str,
    as_of_date: str,
    agents: list[str],
) -> dict[str, Any]:
    """Validate that all required historical agent snapshots exist.

    This deliberately checks only the stored snapshot presence. It does not run
    live Data Intake and does not regenerate any agent files. Missing snapshots
    fail fast to prevent mixing current/live data with historical replay data.
    """
    found: list[str] = []
    missing: list[str] = []

    for agent in agents:
        payload = load_agent_snapshot(
            as_of_date=as_of_date,
            field=field,
            company_dir=company_dir,
            agent=agent,
        )
        if payload is None:
            missing.append(agent)
        else:
            found.append(agent)

    if missing:
        raise RuntimeError(
            "[Chair] Agent History Replay snapshot 누락: "
            f"field={field}, as_of_date={as_of_date}, company_dir={company_dir}, "
            f"company={company}, missing={missing}. "
            "먼저 scripts/archive_agent_outputs_to_google_sheets.py 또는 as_of_date 생성 파이프라인으로 저장하세요."
        )

    return {
        "status": "HISTORY_REPLAY_READY",
        "mode": "AGENT_HISTORY_REPLAY",
        "reason": "latest live Data Intake was not rerun; stored agent snapshots were validated",
        "field": field,
        "as_of_date": as_of_date,
        "company_dir": company_dir,
        "company": company,
        "required_agents": agents,
        "found_agents": found,
        "missing_agents": missing,
        "source": history_source_label(),
    }


def data_intake_node(state: ChairState) -> dict[str, Any]:
    """Prepare Chair inputs.

    Normal/live mode:
        Run Data Intake before specialist agents, as before.

    Agent-history replay mode:
        Do not regenerate latest Data Intake files. Instead, validate that
        Google Sheets history already contains the required as_of_date agent
        snapshots. This keeps Data Intake conceptually required for snapshot
        creation, while preventing current/live files from being mixed into a
        historical Chair replay.
    """
    if _agent_history_replay_enabled():
        as_of_date = _agent_history_as_of_date()
        field = _agent_history_field()
        agents = _agent_history_required_agents()

        print("[Chair] 입력 준비 모드: AGENT_HISTORY_REPLAY")
        print("[Chair] 최신 Data Intake 재실행하지 않음")
        source_label = history_source_label()
        print(
            f"[Chair] {source_label} snapshot 검증 중... "
            f"field={field}, as_of_date={as_of_date}, agents={agents}"
        )

        result = _validate_agent_history_snapshots(
            company_dir=state["company_dir"],
            company=state["company"],
            field=field,
            as_of_date=as_of_date,
            agents=agents,
        )

        print(f"[Chair] {history_source_label()} snapshot 검증 완료 → found={result['found_agents']}")
        return {"data_intake_result": result}

    # IMPORTANT: In full-pipeline mode, data_intake has already run before the
    # Chair graph is invoked. Older logic used
    #     explicit False was combined with an env default True
    # so an explicit False from pipeline_runner was overwritten when
    # CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS defaulted to True. That caused Chair to
    # call data_intake a second time. Here an explicit state value always wins.
    env_default = _env_bool("CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS", True)
    explicit_run_intake = state.get("run_data_intake", None)
    if explicit_run_intake is None:
        run_flag = env_default
    else:
        run_flag = bool(explicit_run_intake)

    if _env_bool("CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS", False):
        run_flag = False

    if not run_flag:
        existing_result = state.get("data_intake_result")
        if isinstance(existing_result, dict) and existing_result:
            reused_result = dict(existing_result)
            reused_result.setdefault("status", existing_result.get("status", "OK"))
            reused_result["chair_data_intake_mode"] = "REUSED_PREVIOUS_PIPELINE_STAGE"
            reused_result["chair_data_intake_rerun"] = False
            print("[Chair] Data Intake 선행 실행 생략: pipeline에서 이미 실행한 data_intake_result 재사용")
            return {"data_intake_result": reused_result}

        print("[Chair] Data Intake 선행 실행 생략: --no-intake 또는 CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS=1")
        return {
            "data_intake_result": {
                "status": "SKIPPED",
                "mode": "LIVE_DATA_INTAKE_DISABLED",
                "reason": "chair live data intake disabled by explicit flag",
                "chair_data_intake_rerun": False,
            }
        }

    agents = _chair_csv_env("CHAIR_DATA_INTAKE_AGENTS", "macro,market,issue,finance,tech,valuation")
    field = normalize_field_name(os.getenv("CHAIR_DATA_INTAKE_FIELD", "반도체"))
    print("[Chair] Data Intake 선행 실행 중...")
    print(f"[Chair] Data Intake agents={agents}")

    try:
        from data_intake.runner import run_data_intake

        try:
            result = run_data_intake(
                company_dir=state["company_dir"],
                company=state["company"],
                field=field,
                agents=agents,
                continue_on_error=True,
                skip_network=_env_bool("CHAIR_DATA_INTAKE_SKIP_NETWORK", False),
                tech_skip_agent=_env_bool("CHAIR_TECH_INTAKE_SKIP_AGENT", True),
                tech_skip_network=_env_bool("CHAIR_TECH_INTAKE_SKIP_NETWORK", _env_bool("TECH_INTAKE_SKIP_NETWORK", False)),
                tech_force_fetch=_env_bool("CHAIR_TECH_INTAKE_FORCE_FETCH", _env_bool("TECH_INTAKE_FORCE_FETCH", False)),
            )
        except TypeError:
            result = run_data_intake(
                company_dir=state["company_dir"],
                company=state["company"],
                agents=agents,
                continue_on_error=True,
            )

        print(f"[Chair] Data Intake 완료 → status={result.get('status') if isinstance(result, dict) else type(result).__name__}")
        return {"data_intake_result": result}

    except Exception as exc:
        print(f"[Chair] Data Intake 실패 → 에이전트 실행은 계속 진행: {exc}")
        return {"data_intake_result": {"status": "FAILED", "error": str(exc)}}


def _agent_input_log_message(agent: str) -> str:
    if _agent_history_replay_enabled():
        return f"[Chair] {agent} 저장 snapshot 입력 패킷 준비 중..."
    return f"[Chair] {agent} 에이전트 실행 중..."


def _agent_history_strict_enabled() -> bool:
    """Replay mode에서는 기본적으로 fallback packet을 금지한다.

    Google Sheets/History snapshot을 읽지 못했는데 fallback packet으로 Chair가 계속 돌면,
    사용자가 원하는 "과거 일자 agent JSON 기반 신호 추출"이 아니라 확인 제한/중립 신호가 섞인다.
    따라서 ALPHAPROVE_USE_AGENT_HISTORY=1이면 기본값을 strict=True로 둔다.
    필요할 때만 ALPHAPROVE_HISTORY_STRICT=0으로 완화한다.
    """
    if not _agent_history_replay_enabled():
        return False
    return _env_bool("ALPHAPROVE_HISTORY_STRICT", True)


def _run_agent_node(state: ChairState, agent: str, runner) -> dict[str, Any]:
    print(_agent_input_log_message(agent))
    try:
        packet = runner(state["company_dir"], state["company"])
    except Exception as exc:
        if _agent_history_strict_enabled():
            raise RuntimeError(
                f"[Chair] {agent} history replay 입력 패킷 로드 실패. "
                f"fallback packet을 만들지 않고 중단합니다: {exc}"
            ) from exc
        print(f"[Chair] {agent} 실패 → Auditor fallback packet 생성: {exc}")
        packet = {
            "agent": agent,
            "company_name": state.get("company"),
            "summary": f"{agent} 실행 실패: {exc}",
            "key_risks": [f"{agent} 산출물 확인 제한"],
            "status": "FAILED",
        }
    tagged = _tag_raw_packet(agent, packet)
    print(f"[Chair] {agent} 완료 → Auditor 입력용 raw packet 수집")
    return {"opinions": [tagged]}


def finance_node(state: ChairState) -> dict[str, Any]:
    return _run_agent_node(state, "finance", run_finance_for_chair)


def issue_node(state: ChairState) -> dict[str, Any]:
    return _run_agent_node(state, "issue", run_issue_for_chair)


def macro_node(state: ChairState) -> dict[str, Any]:
    return _run_agent_node(state, "macro", run_macro_for_chair)


def market_node(state: ChairState) -> dict[str, Any]:
    return _run_agent_node(state, "market", run_market_for_chair)


def tech_node(state: ChairState) -> dict[str, Any]:
    return _run_agent_node(state, "tech", run_tech_for_chair)


def valuation_node(state: ChairState) -> dict[str, Any]:
    return _run_agent_node(state, "valuation", run_valuation_for_chair)


def auditor_hook_node(state: ChairState) -> dict[str, Any]:
    raw_packets = [o for o in list(state.get("opinions") or []) if isinstance(o, dict)]
    print(f"[Chair] First Auditor 3차 검증 시작 - raw packets: {[_agent_name(o) for o in raw_packets]}")
    try:
        from auditor_agent.first_gate import run_first_auditor

        result = run_first_auditor(
            company_dir=state["company_dir"],
            company=state["company"],
            opinions=raw_packets,
            max_rounds=1,
        )
    except Exception as exc:
        print("[Chair] First Auditor 실행 오류")
        print(traceback.format_exc())
        raise RuntimeError(f"First Auditor 실행 실패: {exc}") from exc

    if not isinstance(result, dict):
        result = _as_dict(result)

    if not result.get("passed"):
        failed_agents = result.get("failed_agents") or []
        if _env_bool("AUDITOR_FIRST_FAIL_OPEN", False):
            print(f"\n⚠️  [Chair] First Auditor 검증 FAIL-OPEN 진행: failed_agents={failed_agents}")
            print(f"   Receipt: {result.get('receipt_path')}")
            print(f"   Min Match: {result.get('min_actual_match', 'N/A')}, Threshold: 75%")
            print(f"   → 검증 실패했으나 fail-open 모드 활성화로 진행합니다.\n")
        else:
            raise RuntimeError(
                "First Auditor 3차 검증 실패: "
                f"failed_agents={failed_agents}, receipt={result.get('receipt_path')}"
            )

    compact_packets = _extract_compact_packets(result, state["company_dir"])
    print(f"[Chair] Auditor compact packet 수신: {[_agent_name(p) for p in compact_packets]}")

    auditor_chair_packet_payload = {
        "agent": "auditor",
        "company": state.get("company"),
        "company_dir": state.get("company_dir"),
        "as_of_date": _history_result_as_of_date(),
        "field": _agent_history_field(),
        "run_id": _history_run_id() if _sheets_history_result_mode() else "",
        "auditor_result": result,
        "compact_agent_packets": compact_packets,
        "packet_agents": [_agent_name(p) for p in compact_packets],
    }
    _save_history_run_result(
        company_dir=state["company_dir"],
        company=state["company"],
        agent="auditor",
        output_kind="auditor_chair_packet_json",
        payload=auditor_chair_packet_payload,
    )

    return {"audited_opinions": compact_packets, "auditor_result": result}


def final_report_node(state: ChairState) -> dict[str, Any]:
    company = state["company"]
    company_dir = state["company_dir"]
    audit_result = state.get("auditor_result") or {}
    compact_packets = [p for p in list(state.get("audited_opinions") or []) if isinstance(p, dict)]
    if not compact_packets:
        compact_packets = _extract_compact_packets(audit_result, company_dir)

    audit_summary = _build_auditor_summary(audit_result, company_dir)
    print(f"[Chair] 최종 보고서 생성 중... Auditor compact packets={len(compact_packets)}")
    for packet in compact_packets:
        print(
            f"  - [{_agent_name(packet)}] auditor_recommendation={packet.get('auditor_recommendation')} "
            f"signal={packet.get('auditor_signal')}"
        )

    report = ""
    force_template = _env_bool("CHAIR_FORCE_TEMPLATE_REPORT", True)
    llm = None if force_template else _make_llm()
    if llm is not None:
        prompt = build_chair_prompt(company=company, opinions=compact_packets, auditor_summary=audit_summary)
        for attempt in range(1, REPORT_MAX_RETRIES + 2):
            try:
                candidate = _invoke_llm(llm, prompt)
                candidate = _strip_end_marker(candidate)
                if len(candidate) >= MIN_REPORT_CHARS and ("## 1. 최종 의견" in candidate or "## 1. 최종 추천" in candidate):
                    report = candidate
                    break
            except Exception as exc:
                print(f"[Chair] LLM 보고서 생성 실패 attempt={attempt}: {exc}")
                break

    if not report:
        report = _build_compact_report(company, company_dir, compact_packets, audit_result)

    report = _sanitize_public_report_text(report)

    # 중요: v3에서는 Tech/Valuation 상세 섹션 재주입을 하지 않는다.
    # Chair는 Auditor compact packet만 사용하며, 장문 원천 표/항목은 각 agent 산출물에만 보관한다.
    chair_payload = {
        "agent": "chair",
        "company": company,
        "company_dir": company_dir,
        "opinion": _extract_final_recommendation(report),
        "chair_report": report,
        "auditor_receipt_path": audit_result.get("receipt_path"),
        "auditor_summary": audit_summary,
        "auditor_compact_packets": compact_packets,
        "handoff_policy": "Chair consumes Auditor compact packets only; raw specialist opinion/confidence/evidence-heavy fields are not used in the final report.",
    }
    chair_debug_payload = dict(chair_payload)
    chair_debug_payload.update({
        "auditor_result": audit_result,
        "debug_policy": "Full auditor_result is stored only in the debug packet to keep chair_agent_packet_json compact.",
    })

    if _sheets_history_result_mode():
        _save_history_run_result(
            company_dir=company_dir,
            company=company,
            agent="chair",
            output_kind="chair_agent_packet_json",
            payload=chair_payload,
        )
        _save_history_run_result(
            company_dir=company_dir,
            company=company,
            agent="chair",
            output_kind="chair_report_md",
            payload={
                "agent": "chair",
                "company": company,
                "company_dir": company_dir,
                "opinion": chair_payload.get("opinion"),
                "chair_report": report,
            },
        )
        if _history_local_write_disabled():
            print("[Chair] Google Sheets 저장 완료: history 모드이므로 로컬 chair JSON/MD 저장을 건너뜁니다")
            chair_payload["output_files"] = {
                "storage": "google_sheets_run_results",
                "local_write_disabled": True,
                "run_id": _history_run_id(),
                "as_of_date": _history_result_as_of_date(),
            }
            print(f"[Chair] 보고서 생성 완료 ({len(report)} chars)")
            print(report)
            return {"chair_report": report}

        print("[Chair] Google Sheets 저장 완료: 로컬 chair JSON/MD도 계속 저장합니다")

    path = _write_report(company_dir, report)
    chair_payload["output_files"] = {"chair_report_md": rel_project_path(path)}
    chair_debug_payload["output_files"] = {"chair_report_md": rel_project_path(path)}
    chair_json_files = _write_chair_json(company_dir, chair_payload, debug_payload=chair_debug_payload)
    print(f"[Chair] 보고서 생성 완료 ({len(report)} chars)")
    print(f"[Chair] JSON 저장 완료: {chair_json_files.get('chair_json')}")
    print("\n" + "=" * 60)
    print(f" 최종 보고서 저장 완료: {path}")
    print("=" * 60 + "\n")
    print(report)
    return {"chair_report": report}


def build_chair_graph():
    graph = StateGraph(ChairState)
    graph.add_node("data_intake", data_intake_node)
    graph.add_node("finance", finance_node)
    graph.add_node("issue", issue_node)
    graph.add_node("macro", macro_node)
    graph.add_node("market", market_node)
    graph.add_node("tech", tech_node)
    graph.add_node("valuation", valuation_node)
    graph.add_node("auditor_hook", auditor_hook_node)
    graph.add_node("final_report", final_report_node)

    graph.add_edge(START, "data_intake")
    for node in ("finance", "issue", "macro", "market", "tech", "valuation"):
        graph.add_edge("data_intake", node)
        graph.add_edge(node, "auditor_hook")
    graph.add_edge("auditor_hook", "final_report")
    graph.add_edge("final_report", END)
    return graph.compile()
