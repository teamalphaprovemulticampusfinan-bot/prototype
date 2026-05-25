from __future__ import annotations

import csv
import json
import math
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from common.data_paths import company_agent_dir, company_common_dir, field_common_dir
from statistics import mean, median, pstdev
from typing import Any

from .sources import ROOT


_NUMERIC_CANDIDATES = {
    "sales",
    "operating_income",
    "net_income",
    "total_assets",
    "total_liabilities",
    "total_equity",
    "current_assets",
    "current_liabilities",
    "ocf",
    "capex",
    "fcf",
    "sales_growth_%",
    "operating_margin_%",
    "net_margin_%",
    "debt_ratio_%",
    "current_ratio_%",
    "ROE_%",
    "Open",
    "High",
    "Low",
    "Close",
    "Volume",
    "Change",
    "VIX",
    "VKOSPI",
    "일수익률_%",
    "드로다운_%",
    "기간MDD_%",
}

_CREDIT_NEGATIVE_TERMS = [
    "적자",
    "손실",
    "영업손실",
    "순손실",
    "현금흐름 악화",
    "부채비율",
    "유동성",
    "차입",
    "재무 부담",
    "자본잠식",
    "계속기업",
    "리파이낸싱",
    "만기",
    "상환",
]

_TECH_COMMERCIALIZATION_TERMS = [
    "양산",
    "수주",
    "고객사",
    "공급",
    "매출 전환",
    "상용화",
    "CAPA",
    "증설",
    "로드맵",
    "특허",
    "공정",
]

_VALUATION_TERMS = [
    "DCF",
    "FCF",
    "WACC",
    "terminal",
    "멀티플",
    "PER",
    "PBR",
    "PSR",
    "EV/EBITDA",
    "가치평가",
    "밸류에이션",
    "할인율",
]

# Auditor-only trained proxy ML artifacts.
# These files are intentionally loaded from src/auditor_agent/resources so Chair,
# other agents, and environment files remain untouched. The artifacts were built
# from the semiconductor deeptech feature matrix and exclude the 20-trading-day
# excess-return target. They are proxy labels, not official credit ratings or
# investment recommendations.
_ML_RESOURCE_FILES = {
    "overlay_json": "valuation_credit_ml_overlay.json",
    "overlay_candidate_csv": "valuation_credit_ml_overlay_candidate.csv",
    "quality_summary_csv": "ml_quality_summary.csv",
}


@dataclass
class FinancialSnapshot:
    company_dir: str
    company: str | None
    latest_year: int | None
    sales: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    total_equity: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None
    ocf: float | None = None
    capex: float | None = None
    fcf: float | None = None
    sales_growth_pct: float | None = None
    operating_margin_pct: float | None = None
    net_margin_pct: float | None = None
    debt_ratio_pct: float | None = None
    current_ratio_pct: float | None = None
    roe_pct: float | None = None
    financial_source_file: str | None = None


@dataclass
class MarketSnapshot:
    latest_date: str | None = None
    latest_close: float | None = None
    return_volatility_pct: float | None = None
    mean_daily_return_pct: float | None = None
    max_drawdown_pct: float | None = None
    period_mdd_pct: float | None = None
    stock_source_file: str | None = None


def _clean_key(key: Any) -> str:
    return str(key or "").replace("\ufeff", "").strip()


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            if math.isnan(float(value)) or math.isinf(float(value)):
                return None
        except Exception:
            return None
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text or text.lower() in {"nan", "none", "null", "-"}:
        return None
    text = re.sub(r"[^0-9.\-+eE]", "", text)
    if text in {"", "+", "-", "."}:
        return None
    try:
        val = float(text)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except Exception:
        return None


def _safe_int(value: Any) -> int | None:
    val = _safe_float(value)
    if val is None:
        return None
    try:
        return int(val)
    except Exception:
        return None


def _clamp(value: float | None, lo: float = 0.0, hi: float = 1.0, default: float = 0.0) -> float:
    if value is None:
        value = default
    return max(lo, min(hi, float(value)))


def _sigmoid(x: float) -> float:
    if x > 35:
        return 1.0
    if x < -35:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cleaned = {_clean_key(k): v for k, v in row.items() if _clean_key(k)}
                if cleaned:
                    rows.append(cleaned)
    except UnicodeDecodeError:
        try:
            with path.open("r", encoding="cp949", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cleaned = {_clean_key(k): v for k, v in row.items() if _clean_key(k)}
                    if cleaned:
                        rows.append(cleaned)
        except Exception:
            return []
    except Exception:
        return []
    return rows


def _resource_dir() -> Path:
    return Path(__file__).resolve().parent / "resources"


def _existing_ml_artifact_dirs() -> list[Path]:
    """Return candidate directories for Auditor ML artifact files.

    Canonical team-a data layout keeps field-level ML assets under:
        data/<field>/_sector_common/ml_universe/

    Older builds stored the same files under src/auditor_agent/resources/.
    We search the canonical data location first and keep resources/ as a
    compatibility fallback so existing teammates' runs do not break.
    """
    candidates = [
        field_common_dir("ml_universe", create=False),
        field_common_dir("data", create=False),
        _resource_dir(),
        ROOT / "src" / "auditor_agent" / "resources",
        ROOT / "workspace" / "ml_universe",
        ROOT / "workspace" / "outputs",
        ROOT / "workspace" / "data",
        ROOT,
    ]

    out: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except Exception:
            resolved = path
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if path.exists():
            out.append(path)
    return out


def _find_ml_artifact(filename: str) -> Path | None:
    for directory in _existing_ml_artifact_dirs():
        path = directory / filename
        if path.exists():
            return path

    # Last-resort recursive search is intentionally narrow to avoid scanning
    # virtual environments or unrelated cache folders.
    for root in (field_common_dir("ml_universe", create=False).parent, _resource_dir().parent, ROOT / "data"):
        if not root.exists():
            continue
        try:
            hits = sorted(p for p in root.rglob(filename) if ".venv" not in p.parts and "__pycache__" not in p.parts)
        except Exception:
            hits = []
        if hits:
            return hits[0]
    return None


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}
    except Exception:
        return {}


def _normalize_lookup_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[^0-9a-z가-힣]", "", text)
    return text


def _format_ticker6(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    text = re.sub(r"\.0$", "", text)
    digits = re.sub(r"[^0-9]", "", text)
    if not digits:
        return None
    return digits.zfill(6)[-6:]


def _quality_rows_to_dict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for row in rows:
        section = _normalize_lookup_text(row.get("section")) or "summary"
        metric = str(row.get("metric") or "").strip()
        if not metric:
            continue
        key = f"{section}.{metric}"
        raw_value = row.get("value")
        value = _safe_float(raw_value)
        out[key] = value if value is not None else raw_value
    return out


def _load_trained_ml_artifacts() -> dict[str, Any]:
    """Load Auditor-only trained proxy ML artifacts.

    The canonical location is now:
        data/<field>/_sector_common/ml_universe/

    For backward compatibility this loader also accepts:
        src/auditor_agent/resources/
        workspace/ml_universe/
        workspace/outputs/

    Missing files simply disable the trained ML layer while preserving the older
    deterministic overlay.
    """
    overlay_path = _find_ml_artifact(_ML_RESOURCE_FILES["overlay_json"])
    candidate_path = _find_ml_artifact(_ML_RESOURCE_FILES["overlay_candidate_csv"])
    quality_path = _find_ml_artifact(_ML_RESOURCE_FILES["quality_summary_csv"])

    overlay = _read_json_file(overlay_path) if overlay_path and overlay_path.exists() else {}
    records = overlay.get("records") if isinstance(overlay, dict) else None
    if not isinstance(records, list):
        records = []

    quality_rows = _read_csv_rows(quality_path) if quality_path and quality_path.exists() else []
    candidate_rows = _read_csv_rows(candidate_path) if candidate_path and candidate_path.exists() else []

    missing = []
    if overlay_path is None:
        missing.append(_ML_RESOURCE_FILES["overlay_json"])
    if candidate_path is None:
        missing.append(_ML_RESOURCE_FILES["overlay_candidate_csv"])
    if quality_path is None:
        missing.append(_ML_RESOURCE_FILES["quality_summary_csv"])

    return {
        "available": bool(records),
        "overlay_path": str(overlay_path) if overlay_path and overlay_path.exists() else None,
        "candidate_path": str(candidate_path) if candidate_path and candidate_path.exists() else None,
        "quality_path": str(quality_path) if quality_path and quality_path.exists() else None,
        "missing_files": missing,
        "project": overlay.get("project") if isinstance(overlay, dict) else None,
        "version": overlay.get("version") if isinstance(overlay, dict) else None,
        "row_count": overlay.get("row_count") if isinstance(overlay, dict) else None,
        "notes": overlay.get("notes") if isinstance(overlay, dict) else [],
        "records": records,
        "candidate_rows": candidate_rows,
        "quality_summary": _quality_rows_to_dict(quality_rows),
    }


def _candidate_ticker_from_company_files(company_dir: str) -> str | None:
    company_path = company_common_dir(company_dir)
    for csv_path in sorted(company_path.glob("*.csv")):
        rows = _read_csv_rows(csv_path)
        for row in rows[:5]:
            for key in ("ticker", "ticker6", "종목코드", "code", "stock_code"):
                ticker = _format_ticker6(row.get(key))
                if ticker:
                    return ticker
    return None


def _select_trained_ml_record(artifacts: dict[str, Any], company_dir: str, company: str | None) -> tuple[dict[str, Any] | None, str | None]:
    records = artifacts.get("records") or []
    if not isinstance(records, list) or not records:
        return None, None

    target_ticker = _candidate_ticker_from_company_files(company_dir)
    if target_ticker:
        for rec in records:
            if _format_ticker6(rec.get("ticker") or rec.get("ticker6")) == target_ticker:
                return rec, "ticker"

    target_names = [
        _normalize_lookup_text(company),
        _normalize_lookup_text(company_dir),
    ]
    target_names = [name for name in target_names if name]
    if not target_names:
        return None, None

    for rec in records:
        rec_name = _normalize_lookup_text(rec.get("company_name"))
        if rec_name and rec_name in target_names:
            return rec, "company_name_exact"

    for rec in records:
        rec_name = _normalize_lookup_text(rec.get("company_name"))
        if not rec_name:
            continue
        for target in target_names:
            if target and (target in rec_name or rec_name in target):
                return rec, "company_name_partial"

    return None, None


def _bucket_from_confidence(value: Any) -> str:
    val = _safe_float(value)
    if val is None:
        return "UNKNOWN"
    if val >= 0.75:
        return "HIGH"
    if val >= 0.55:
        return "MEDIUM"
    return "LOW"


def _run_trained_proxy_ml_layer(company_dir: str, company: str | None) -> dict[str, Any]:
    artifacts = _load_trained_ml_artifacts()
    if not artifacts.get("available"):
        return {
            "available": False,
            "reason": "trained ML artifact files were not found in src/auditor_agent/resources",
            "required_files": list(_ML_RESOURCE_FILES.values()),
        }

    rec, matched_by = _select_trained_ml_record(artifacts, company_dir, company)
    if not isinstance(rec, dict):
        return {
            "available": False,
            "reason": "no matching company in trained ML overlay artifacts",
            "project": artifacts.get("project"),
            "version": artifacts.get("version"),
            "row_count": artifacts.get("row_count"),
            "matched_by": None,
            "quality_summary": artifacts.get("quality_summary", {}),
        }

    valuation_ml = rec.get("valuation_ml") if isinstance(rec.get("valuation_ml"), dict) else {}
    credit_ml = rec.get("credit_ml") if isinstance(rec.get("credit_ml"), dict) else {}
    checks = rec.get("auditor_checks") if isinstance(rec.get("auditor_checks"), dict) else {}
    quality = artifacts.get("quality_summary", {})

    val_conf = valuation_ml.get("confidence_score")
    cred_conf = credit_ml.get("confidence_score")
    valuation_label = valuation_ml.get("signal") or valuation_ml.get("proxy_label")
    credit_label = credit_ml.get("risk_label") or credit_ml.get("proxy_label")
    anomaly_flag = bool(credit_ml.get("anomaly_flag_top15pct"))

    if credit_label == "HIGH_RISK" or anomaly_flag or checks.get("requires_human_review"):
        decision_hint = "ml_risk_guardrail"
        interpretation = "학습형 신용 proxy 또는 이상치 탐지가 보수적 검토를 요구합니다."
    elif valuation_label == "ATTRACTIVE" and credit_label in {"LOW_RISK", "MEDIUM_RISK"}:
        decision_hint = "ml_supportive_but_proxy_only"
        interpretation = "학습형 가치평가 proxy는 우호적이나, 공식 투자의견이 아니므로 Auditor 근거 검증과 함께만 사용합니다."
    elif valuation_label == "EXPENSIVE":
        decision_hint = "ml_valuation_caution"
        interpretation = "학습형 가치평가 proxy가 고평가/부담 신호를 보입니다."
    else:
        decision_hint = "ml_balanced_watch"
        interpretation = "학습형 가치평가·신용 proxy가 혼재되어 중립 보조 신호로 사용합니다."

    return {
        "available": True,
        "project": artifacts.get("project"),
        "version": artifacts.get("version"),
        "row_count": artifacts.get("row_count"),
        "source_files": {
            "overlay_json": artifacts.get("overlay_path"),
            "overlay_candidate_csv": artifacts.get("candidate_path"),
            "quality_summary_csv": artifacts.get("quality_path"),
        },
        "matched_by": matched_by,
        "company_match": {
            "ticker": _format_ticker6(rec.get("ticker") or rec.get("ticker6")),
            "company_name": rec.get("company_name"),
            "peer_group": rec.get("peer_group"),
            "semiconductor_tag": rec.get("semiconductor_tag"),
        },
        "trained_model_family": {
            "valuation_selected_model": quality.get("valuation.selected_model"),
            "credit_selected_model": quality.get("credit.selected_model"),
            "valuation_holdout_balanced_accuracy": quality.get("valuation.holdout_balanced_accuracy"),
            "valuation_holdout_f1_weighted": quality.get("valuation.holdout_f1_weighted"),
            "credit_holdout_balanced_accuracy": quality.get("credit.holdout_balanced_accuracy"),
            "credit_holdout_f1_weighted": quality.get("credit.holdout_f1_weighted"),
        },
        "valuation_ml": {
            "signal": valuation_label,
            "proxy_label": valuation_ml.get("proxy_label"),
            "proxy_score": _round_or_none(valuation_ml.get("proxy_score"), 4),
            "confidence": valuation_ml.get("confidence") or _bucket_from_confidence(val_conf),
            "confidence_score": _round_or_none(val_conf, 4),
            "class_probabilities": valuation_ml.get("class_probabilities", {}),
            "global_top_features": valuation_ml.get("global_top_features", [])[:10],
        },
        "credit_ml": {
            "risk_label": credit_label,
            "proxy_label": credit_ml.get("proxy_label"),
            "proxy_score": _round_or_none(credit_ml.get("proxy_score"), 4),
            "confidence": credit_ml.get("confidence") or _bucket_from_confidence(cred_conf),
            "confidence_score": _round_or_none(cred_conf, 4),
            "class_probabilities": credit_ml.get("class_probabilities", {}),
            "anomaly_score": _round_or_none(credit_ml.get("anomaly_score"), 4),
            "anomaly_flag_top15pct": anomaly_flag,
            "global_top_features": credit_ml.get("global_top_features", [])[:10],
        },
        "auditor_checks": checks,
        "decision_hint": decision_hint,
        "interpretation": interpretation,
        "governance": {
            "proxy_label_only": True,
            "not_official_credit_rating": True,
            "not_investment_recommendation": True,
            "human_in_the_loop": True,
            "chair_override": False,
            "pass_fail_override": False,
            "auditor_original_role_preserved": True,
            "no_20_trading_day_target": True,
        },
        "artifact_notes": artifacts.get("notes", []),
    }


def _trained_ml_summary_text(overlay: dict[str, Any]) -> str:
    trained = overlay.get("ml_trained_proxy_ensemble") or {}
    if isinstance(trained, dict) and trained.get("available"):
        val = trained.get("valuation_ml") or {}
        cred = trained.get("credit_ml") or {}
        fam = trained.get("trained_model_family") or {}
        return (
            "Auditor trained ML overlay: "
            f"valuation={val.get('signal', 'N/A')}, "
            f"credit={cred.get('risk_label', 'N/A')}, "
            f"credit_anomaly={_format_num(cred.get('anomaly_score'))}, "
            f"valuation_model={fam.get('valuation_selected_model', 'N/A')}, "
            f"credit_model={fam.get('credit_selected_model', 'N/A')}; "
            "proxy-only, no 20거래일 target, Chair/pass-fail 미변경."
        )

    ml = overlay.get("ml_interpretable_ensemble") or {}
    model_outputs = ml.get("model_outputs") or {}
    return (
        f"Auditor ML overlay label={model_outputs.get('ml_overlay_label', '확인 제한')}, "
        f"downside_score={_format_num(model_outputs.get('downside_risk_score'))}, "
        f"upside_score={_format_num(model_outputs.get('upside_support_score'))}; "
        "이 값은 Chair를 대체하지 않는 보조 scorecard입니다."
    )


def _trained_ml_source_lines(overlay: dict[str, Any]) -> list[str]:
    trained = overlay.get("ml_trained_proxy_ensemble") or {}
    if not isinstance(trained, dict) or not trained.get("available"):
        return []
    files = trained.get("source_files") if isinstance(trained.get("source_files"), dict) else {}
    lines = []
    for key in ("overlay_json", "overlay_candidate_csv", "quality_summary_csv"):
        val = files.get(key)
        if val:
            lines.append(f"trained_ml_{key}={val}")
    model = trained.get("trained_model_family") or {}
    if model:
        lines.append(
            "trained_ml_quality="
            f"valuation_model={model.get('valuation_selected_model')}, "
            f"valuation_holdout_bal_acc={model.get('valuation_holdout_balanced_accuracy')}, "
            f"credit_model={model.get('credit_selected_model')}, "
            f"credit_holdout_bal_acc={model.get('credit_holdout_balanced_accuracy')}"
        )
    return lines


def _ml_value_label_for_chair(overlay: dict[str, Any]) -> tuple[str, str]:
    trained = overlay.get("ml_trained_proxy_ensemble") or {}
    val = trained.get("valuation_ml") or {} if isinstance(trained, dict) else {}
    cred = trained.get("credit_ml") or {} if isinstance(trained, dict) else {}
    valuation_signal = str(
        val.get("signal")
        or val.get("proxy_label")
        or (overlay.get("valuation_assessment") or {}).get("valuation_signal")
        or "확인 제한"
    )
    credit_label = str(
        cred.get("risk_label")
        or cred.get("proxy_label")
        or (overlay.get("credit_assessment") or {}).get("watch_grade")
        or "확인 제한"
    )
    return valuation_signal, credit_label


def _mandatory_ml_chair_section(overlay: dict[str, Any]) -> str:
    company = str(overlay.get("company") or "해당 기업")
    valuation_signal, credit_label = _ml_value_label_for_chair(overlay)

    if valuation_signal == "ATTRACTIVE" and credit_label == "MEDIUM_RISK":
        interpretation = (
            f"{company}는 반도체 딥테크 peer universe 내에서 상대가치 매력은 있으나, "
            "신용위험은 LOW_RISK가 아닌 MEDIUM_RISK로 분류된다."
        )
    elif valuation_signal == "ATTRACTIVE" and credit_label not in {"LOW_RISK", "확인 제한"}:
        interpretation = (
            f"{company}는 반도체 딥테크 peer universe 내에서 상대가치 매력은 있으나, "
            f"신용위험은 LOW_RISK가 아닌 {credit_label}로 분류된다."
        )
    else:
        interpretation = (
            f"{company}는 반도체 딥테크 peer universe 내에서 가치평가 ML 판단은 {valuation_signal}, "
            f"신용위험 ML 판단은 {credit_label}로 분류된다."
        )

    return "\n".join(
        [
            "## ML 기반 신용·가치평가 교차검증",
            f"- 가치평가 ML 판단: {valuation_signal}",
            f"- 신용위험 ML 판단: {credit_label}",
            f"- 해석: {interpretation}",
            "- Auditor 판단: 최종 보고서에서는 성장성·저평가 가능성뿐 아니라 수익성, 현금흐름, 재무안정성 리스크도 함께 검토해야 한다.",
        ]
    )


def _mandatory_ml_chair_claims(overlay: dict[str, Any]) -> list[str]:
    valuation_signal, credit_label = _ml_value_label_for_chair(overlay)
    company = str(overlay.get("company") or "해당 기업")
    return [
        f"ML 기반 신용·가치평가 교차검증: 가치평가 ML 판단={valuation_signal}, 신용위험 ML 판단={credit_label}.",
        f"Auditor ML 해석: {company}는 반도체 딥테크 peer universe 기준으로 상대가치와 신용위험을 분리해 보아야 하며, 최종 보고서에는 수익성·현금흐름·재무안정성 리스크를 반드시 병기해야 합니다.",
    ]


def _prepend_unique_text(base: Any, additions: list[str], limit: int = 12) -> list[Any]:
    original = list(base) if isinstance(base, list) else ([] if base is None else [base])
    items: list[Any] = []
    seen: set[str] = set()
    for item in list(additions) + original:
        cleaned = str(item).strip()
        if cleaned and cleaned not in seen:
            items.append(item)
            seen.add(cleaned)
    return items[:limit]


def _prepend_summary_text(base: Any, prefix: str, limit_chars: int = 2400) -> str:
    base_text = str(base).strip() if base is not None else ""
    prefix = str(prefix).strip()
    if not prefix:
        return base_text
    if base_text.startswith(prefix):
        return base_text[:limit_chars]
    combined = f"{prefix}\n\n{base_text}" if base_text else prefix
    return combined[:limit_chars]



def _score_operating_margin_bridge(value: float | None) -> float:
    if value is None:
        return 50.0
    if value >= 15:
        return 85.0
    if value >= 5:
        return 70.0
    if value >= 0:
        return 58.0
    if value >= -5:
        return 38.0
    return 25.0


def _score_current_ratio_bridge(value: float | None) -> float:
    if value is None:
        return 50.0
    if value >= 150:
        return 85.0
    if value >= 100:
        return 65.0
    if value >= 70:
        return 42.0
    return 25.0


def _score_debt_ratio_bridge(value: float | None) -> float:
    if value is None:
        return 50.0
    if value < 80:
        return 85.0
    if value < 150:
        return 65.0
    if value < 250:
        return 42.0
    return 25.0


def _score_valuation_signal_bridge(signal: Any, confidence: Any = None) -> float:
    label = str(signal or "").upper()
    conf = str(confidence or "").upper()
    if "ATTRACTIVE" in label or "VALUATION_SUPPORTIVE" in label or "저평가" in label:
        score = 85.0
    elif "FAIR" in label or "NEUTRAL" in label or "중립" in label:
        score = 60.0
    elif "EXPENSIVE" in label or "CAUTION" in label or "고평가" in label:
        score = 35.0
    else:
        score = 50.0
    if "HIGH" in conf:
        score += 5.0
    elif "LOW" in conf:
        score -= 8.0
    return _clamp(score, 0, 100, 50)


def _score_credit_label_bridge(label: Any, confidence: Any = None) -> float:
    text = str(label or "").upper()
    conf = str(confidence or "").upper()
    if "LOW" in text or text in {"A", "STABLE"}:
        score = 85.0
    elif "MEDIUM" in text or text in {"B", "WATCH", "C", "CAUTION"}:
        score = 55.0
    elif "HIGH" in text or text in {"D", "HIGH_RISK"}:
        score = 25.0
    else:
        score = 50.0
    if "HIGH" in conf:
        score += 3.0
    elif "LOW" in conf:
        score -= 5.0
    return _clamp(score, 0, 100, 50)


def _tech_score_from_text_bridge(text: str, hits: dict[str, Any] | None = None) -> tuple[float, dict[str, Any]]:
    """Estimate technical strength without modifying Tech Agent.

    If Tech Agent left a 28/35 style score in packets/reports, use it. Otherwise,
    fall back to technology/commercialization keyword evidence. This is intentionally
    conservative because the bridge score asks whether technology becomes value,
    not whether the technology sounds impressive.
    """
    patterns = [
        r"총점\s*[:：]?\s*(\d+(?:\.\d+)?)\s*/\s*35",
        r"기술\s*경쟁력[^\n]{0,40}?(\d+(?:\.\d+)?)\s*/\s*35",
        r"(\d+(?:\.\d+)?)\s*/\s*35",
    ]
    for pattern in patterns:
        m = re.search(pattern, text or "")
        if m:
            raw = _safe_float(m.group(1))
            if raw is not None:
                return _clamp(raw / 35.0 * 100.0, 0, 100, 50), {"method": "text_regex_35", "raw_35_score": raw}

    tech_terms = ["기술 경쟁력", "핵심 기술", "특허", "R&D", "연구개발", "진입장벽", "양산", "첨단", "패키징", "공정", "수율", "고객사"]
    negative_terms = ["확인 제한", "근거 부족", "미확인", "검증 제한", "추정", "불확실", "제한적", "과장"]
    pos = _keyword_hits(text or "", tech_terms)
    neg = _keyword_hits(text or "", negative_terms)
    commercialization_hits = []
    if isinstance(hits, dict):
        raw_hits = hits.get("commercialization_terms") or []
        if isinstance(raw_hits, list):
            commercialization_hits = [str(x) for x in raw_hits]
    score = 50.0 + min(len(pos), 8) * 4.0 + min(len(commercialization_hits), 5) * 3.0 - min(len(neg), 6) * 4.0
    return _clamp(score, 30, 85, 50), {
        "method": "keyword_fallback",
        "positive_tech_hits": pos,
        "commercialization_hits": commercialization_hits,
        "negative_evidence_hits": neg,
    }


def _commercialization_score_bridge(text: str, hits: dict[str, Any] | None = None) -> tuple[float, dict[str, Any]]:
    terms = ["양산", "고객사", "고객", "수주", "납품", "공급", "채택", "계약", "매출", "상용화", "레퍼런스", "공동개발", "생산", "라인", "증설", "인증", "qualification", "shipment", "revenue"]
    negative_terms = ["확인 제한", "근거 부족", "미확인", "검증 제한", "추정", "불확실", "제한적"]
    pos = _keyword_hits(text or "", terms)
    neg = _keyword_hits(text or "", negative_terms)
    if isinstance(hits, dict):
        raw = hits.get("commercialization_terms") or []
        if isinstance(raw, list):
            for item in raw:
                s = str(item)
                if s and s not in pos:
                    pos.append(s)
    url_count = len(re.findall(r"https?://[^\s\]\)\"']+", text or ""))
    score = 40.0 + min(len(pos), 10) * 5.5 + min(url_count, 4) * 3.0 - min(len(neg), 6) * 4.5
    return _clamp(score, 15, 90, 50), {
        "positive_commercialization_hits": pos[:15],
        "negative_evidence_hits": neg[:10],
        "url_count": url_count,
    }


def _financial_conversion_score_bridge(fin: FinancialSnapshot | None) -> tuple[float, dict[str, Any]]:
    if fin is None:
        return 50.0, {"method": "missing_financial_snapshot"}
    op = _score_operating_margin_bridge(fin.operating_margin_pct)
    cur = _score_current_ratio_bridge(fin.current_ratio_pct)
    debt = _score_debt_ratio_bridge(fin.debt_ratio_pct)
    fcf_score = 50.0
    if fin.fcf is not None:
        fcf_score = 70.0 if fin.fcf > 0 else 30.0
    score = 0.40 * op + 0.20 * cur + 0.25 * debt + 0.15 * fcf_score
    return _clamp(score, 0, 100, 50), {
        "operating_margin_pct": fin.operating_margin_pct,
        "current_ratio_pct": fin.current_ratio_pct,
        "debt_ratio_pct": fin.debt_ratio_pct,
        "fcf": fin.fcf,
        "component_scores": {
            "operating_margin_score": round(op, 2),
            "current_ratio_score": round(cur, 2),
            "debt_ratio_score": round(debt, 2),
            "fcf_score": round(fcf_score, 2),
        },
    }


def _bridge_grade(score: float) -> str:
    if score >= 80:
        return "STRONG_VALUE_BRIDGE"
    if score >= 65:
        return "COMMERCIALIZATION_WATCH"
    if score >= 50:
        return "TECH_FINANCE_GAP"
    return "KEYWORD_OR_EARLY_STAGE_RISK"


def _compute_tech_to_value_bridge(
    *,
    company: str,
    fin: FinancialSnapshot | None,
    market: MarketSnapshot,
    valuation: dict[str, Any],
    credit: dict[str, Any],
    trained_ml_layer: dict[str, Any],
    evidence_score: float,
    text: str,
    text_feature_hits: dict[str, Any],
) -> dict[str, Any]:
    trained_val = trained_ml_layer.get("valuation_ml") if isinstance(trained_ml_layer, dict) else {}
    trained_cred = trained_ml_layer.get("credit_ml") if isinstance(trained_ml_layer, dict) else {}
    trained_checks = trained_ml_layer.get("auditor_checks") if isinstance(trained_ml_layer, dict) else {}

    valuation_signal = None
    valuation_conf = None
    if isinstance(trained_val, dict):
        valuation_signal = trained_val.get("signal") or trained_val.get("proxy_label")
        valuation_conf = trained_val.get("confidence")
    valuation_signal = valuation_signal or valuation.get("valuation_signal")

    credit_label = None
    credit_conf = None
    if isinstance(trained_cred, dict):
        credit_label = trained_cred.get("risk_label") or trained_cred.get("proxy_label")
        credit_conf = trained_cred.get("confidence")
    credit_label = credit_label or credit.get("credit_signal") or credit.get("watch_grade")

    tech_score, tech_debug = _tech_score_from_text_bridge(text, text_feature_hits)
    commercialization_score, comm_debug = _commercialization_score_bridge(text, text_feature_hits)
    financial_score, fin_debug = _financial_conversion_score_bridge(fin)
    valuation_score = _score_valuation_signal_bridge(valuation_signal, valuation_conf)
    credit_support_score = _score_credit_label_bridge(credit_label, credit_conf)
    evidence_quality_score = _clamp(evidence_score * 100.0, 0, 100, 50)

    raw_score = (
        0.25 * tech_score
        + 0.20 * commercialization_score
        + 0.20 * financial_score
        + 0.15 * valuation_score
        + 0.10 * credit_support_score
        + 0.10 * evidence_quality_score
    )
    flags: list[str] = []
    adjusted = raw_score

    if tech_score >= 70 and financial_score < 45:
        adjusted = min(adjusted, 64.0)
        flags.append("기술 점수 대비 재무 전환력 부족")
    if commercialization_score < 40:
        adjusted = min(adjusted, 59.0)
        flags.append("사업화 근거 부족")
    if str(credit_label or "").upper().startswith("HIGH"):
        adjusted = min(adjusted, 69.0)
        flags.append("신용위험 HIGH_RISK")
    if isinstance(trained_checks, dict) and trained_checks.get("requires_human_review") is True:
        flags.append("Auditor human review 필요")

    final_score = round(_clamp(adjusted, 0, 100, 50), 2)
    grade = _bridge_grade(final_score)

    if grade == "STRONG_VALUE_BRIDGE":
        interpretation = f"{company}은 기술 경쟁력과 사업화·재무 전환 근거가 비교적 균형적으로 확인되어 기술이 투자 가치로 연결될 가능성이 높은 구간입니다."
    elif grade == "COMMERCIALIZATION_WATCH":
        interpretation = f"{company}은 기술 및 사업화 가능성은 확인되지만, 수익성·현금흐름·재무안정성으로의 연결 여부를 추가 확인해야 하는 구간입니다."
    elif grade == "TECH_FINANCE_GAP":
        interpretation = f"{company}은 기술 경쟁력 또는 상대가치 매력은 있으나, 현재 수익성·현금흐름·재무안정성 측면에서 기술과 투자 가치 사이의 간극이 남아 있는 구간입니다."
    else:
        interpretation = f"{company}은 기술 키워드 또는 잠재력은 확인되지만, 사업화·재무성과·가치평가로 연결되는 근거가 아직 약한 구간입니다."

    return {
        "available": True,
        "module": "tech_to_value_bridge_score",
        "version": "v5_auditor_chair_visible_once",
        "purpose": "딥테크 기업의 기술 경쟁력이 사업화·재무성과·가치평가로 연결되는지 Auditor 보조 지표로 평가",
        "score": final_score,
        "raw_score_before_guardrail": round(raw_score, 2),
        "grade": grade,
        "components": {
            "technology_strength_score": round(tech_score, 2),
            "commercialization_evidence_score": round(commercialization_score, 2),
            "financial_conversion_score": round(financial_score, 2),
            "valuation_alignment_score": round(valuation_score, 2),
            "credit_support_score": round(credit_support_score, 2),
            "evidence_quality_score": round(evidence_quality_score, 2),
        },
        "weights": {
            "technology_strength_score": 0.25,
            "commercialization_evidence_score": 0.20,
            "financial_conversion_score": 0.20,
            "valuation_alignment_score": 0.15,
            "credit_support_score": 0.10,
            "evidence_quality_score": 0.10,
        },
        "signals": {
            "valuation_signal": valuation_signal,
            "valuation_confidence": valuation_conf,
            "credit_risk_label": credit_label,
            "credit_confidence": credit_conf,
            "market_volatility_pct": market.return_volatility_pct,
            "market_mdd_pct": market.period_mdd_pct or market.max_drawdown_pct,
        },
        "flags": flags,
        "interpretation": interpretation,
        "auditor_usage_rule": "공식 투자의견/목표주가가 아니라 기술 claim이 사업화·재무성과·가치평가로 연결되는지 점검하는 보조 검증 지표",
        "debug": {
            "technology_debug": tech_debug,
            "commercialization_debug": comm_debug,
            "financial_debug": fin_debug,
        },
    }


def _mandatory_tech_to_value_chair_section(overlay: dict[str, Any]) -> str:
    bridge = overlay.get("tech_to_value_bridge") if isinstance(overlay, dict) else {}
    if not isinstance(bridge, dict) or not bridge.get("available"):
        return ""
    score = bridge.get("score", "확인 제한")
    grade = bridge.get("grade", "확인 제한")
    interp = bridge.get("interpretation") or "기술-가치 연결 판단이 제한적입니다."
    comps = bridge.get("components") if isinstance(bridge.get("components"), dict) else {}
    return "\n".join([
        "## Tech-to-Value Bridge 검증",
        f"- Tech-to-Value Bridge Score: {score} / 100",
        f"- 판정: {grade}",
        f"- 핵심 구성: 기술경쟁력 {comps.get('technology_strength_score', 'N/A')}, 사업화근거 {comps.get('commercialization_evidence_score', 'N/A')}, 재무전환력 {comps.get('financial_conversion_score', 'N/A')}, 가치평가정합성 {comps.get('valuation_alignment_score', 'N/A')}, 신용위험보정 {comps.get('credit_support_score', 'N/A')}",
        f"- 해석: {interp}",
        "- Auditor 판단: 기술 우위는 고객사 채택, 양산, 매출 전환, FCF 개선 근거와 연결될 때만 가치평가 가산 요인으로 반영한다.",
    ])


def _mandatory_tech_to_value_claims(overlay: dict[str, Any]) -> list[str]:
    bridge = overlay.get("tech_to_value_bridge") if isinstance(overlay, dict) else {}
    if not isinstance(bridge, dict) or not bridge.get("available"):
        return []
    score = bridge.get("score", "확인 제한")
    grade = bridge.get("grade", "확인 제한")
    interp = bridge.get("interpretation") or "기술-가치 연결 판단이 제한적입니다."
    return [
        f"Tech-to-Value Bridge Score: {score}/100, 판정={grade}.",
        f"Auditor Tech-to-Value 해석: {interp}",
        "Auditor Tech-to-Value 원칙: 기술 우위는 고객사 채택, 양산, 매출 전환, FCF 개선 근거와 연결될 때만 가치평가 가산 요인으로 반영합니다.",
    ]


def _render_tech_to_value_markdown(bridge: dict[str, Any], company: str) -> str:
    if not isinstance(bridge, dict) or not bridge.get("available"):
        return f"# {company} Tech-to-Value Bridge Score\n\n- 생성 실패 또는 데이터 부족\n"
    lines = [
        f"# {company} Tech-to-Value Bridge Score",
        "",
        f"- **Score:** {bridge.get('score')} / 100",
        f"- **Grade:** {bridge.get('grade')}",
        f"- **Interpretation:** {bridge.get('interpretation')}",
        "",
        "## Component Scores",
        "",
        "| Component | Score |",
        "|---|---:|",
    ]
    comps = bridge.get("components") if isinstance(bridge.get("components"), dict) else {}
    for key, value in comps.items():
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Auditor Usage Rule", "", str(bridge.get("auditor_usage_rule") or "")])
    flags = bridge.get("flags") if isinstance(bridge.get("flags"), list) else []
    if flags:
        lines.extend(["", "## Flags", ""])
        lines.extend([f"- {flag}" for flag in flags])
    return "\n".join(lines) + "\n"


def _financial_csvs(company_path: Path) -> list[Path]:
    files: list[Path] = []
    for path in company_path.glob("*.csv"):
        rows = _read_csv_rows(path)
        if not rows:
            continue
        cols = set(rows[0].keys())
        if {"sales", "operating_income", "net_income"} & cols:
            files.append(path)
    return files


def _stock_csvs(company_path: Path) -> list[Path]:
    files: list[Path] = []
    for path in company_path.glob("*.csv"):
        rows = _read_csv_rows(path)
        if not rows:
            continue
        cols = set(rows[0].keys())
        if {"Date", "Close"} <= cols or {"일수익률_%", "드로다운_%"} & cols:
            files.append(path)
    return files


def _pick_latest_financial(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    sortable = []
    for i, row in enumerate(rows):
        year = _safe_int(row.get("year"))
        sortable.append((year if year is not None else -10_000 + i, i, row))
    sortable.sort(key=lambda x: (x[0], x[1]))
    return sortable[-1][2]


def _snapshot_from_company_dir(company_dir: str) -> tuple[FinancialSnapshot | None, MarketSnapshot]:
    # Finance Agent owns both financial CSV and local stock-price CSV in the
    # reorganized layout: data/<field>/<company>/finance/.
    # company/common is kept as a fallback for older migrated folders.
    finance_path = company_agent_dir(company_dir, "finance", create=True)
    common_path = company_common_dir(company_dir)
    candidate_paths = [finance_path, common_path]

    fin_snapshot: FinancialSnapshot | None = None
    market_snapshot = MarketSnapshot()

    for csv_path in [p for base in candidate_paths for p in _financial_csvs(base)]:
        rows = _read_csv_rows(csv_path)
        latest = _pick_latest_financial(rows)
        if not latest:
            continue
        company_name = latest.get("company") or latest.get("회사명")
        fin_snapshot = FinancialSnapshot(
            company_dir=company_dir,
            company=str(company_name) if company_name else None,
            latest_year=_safe_int(latest.get("year")),
            sales=_safe_float(latest.get("sales")),
            operating_income=_safe_float(latest.get("operating_income")),
            net_income=_safe_float(latest.get("net_income")),
            total_assets=_safe_float(latest.get("total_assets")),
            total_liabilities=_safe_float(latest.get("total_liabilities")),
            total_equity=_safe_float(latest.get("total_equity")),
            current_assets=_safe_float(latest.get("current_assets")),
            current_liabilities=_safe_float(latest.get("current_liabilities")),
            ocf=_safe_float(latest.get("ocf")),
            capex=_safe_float(latest.get("capex")),
            fcf=_safe_float(latest.get("fcf")),
            sales_growth_pct=_safe_float(latest.get("sales_growth_%")),
            operating_margin_pct=_safe_float(latest.get("operating_margin_%")),
            net_margin_pct=_safe_float(latest.get("net_margin_%")),
            debt_ratio_pct=_safe_float(latest.get("debt_ratio_%")),
            current_ratio_pct=_safe_float(latest.get("current_ratio_%")),
            roe_pct=_safe_float(latest.get("ROE_%")),
            financial_source_file=csv_path.name,
        )
        break

    for csv_path in [p for base in candidate_paths for p in _stock_csvs(base)]:
        rows = _read_csv_rows(csv_path)
        if not rows:
            continue
        closes: list[float] = []
        returns: list[float] = []
        drawdowns: list[float] = []
        mdds: list[float] = []
        latest_row = rows[-1]
        for row in rows:
            close = _safe_float(row.get("Close"))
            if close is not None:
                closes.append(close)
            ret = _safe_float(row.get("일수익률_%"))
            if ret is None:
                change = _safe_float(row.get("Change"))
                ret = change * 100 if change is not None else None
            if ret is not None:
                returns.append(ret)
            dd = _safe_float(row.get("드로다운_%"))
            if dd is not None:
                drawdowns.append(dd)
            mdd = _safe_float(row.get("기간MDD_%"))
            if mdd is not None:
                mdds.append(mdd)
        market_snapshot = MarketSnapshot(
            latest_date=str(latest_row.get("Date")) if latest_row.get("Date") else None,
            latest_close=_safe_float(latest_row.get("Close")) or (closes[-1] if closes else None),
            return_volatility_pct=round(pstdev(returns), 4) if len(returns) >= 2 else None,
            mean_daily_return_pct=round(mean(returns), 4) if returns else None,
            max_drawdown_pct=round(min(drawdowns), 4) if drawdowns else None,
            period_mdd_pct=round(min(mdds), 4) if mdds else None,
            stock_source_file=csv_path.name,
        )
        break

    return fin_snapshot, market_snapshot


def _peer_snapshots() -> list[FinancialSnapshot]:
    base = field_common_dir("companies")
    peers: list[FinancialSnapshot] = []
    if not base.exists():
        return peers
    for path in base.iterdir():
        if not path.is_dir():
            continue
        snapshot, _ = _snapshot_from_company_dir(path.name)
        if snapshot is not None:
            peers.append(snapshot)
    return peers


def _z_score(value: float | None, values: list[float]) -> float | None:
    if value is None or len(values) < 3:
        return None
    mu = mean(values)
    sd = pstdev(values)
    if sd <= 1e-12:
        return None
    return (value - mu) / sd


def _peer_anomaly(fin: FinancialSnapshot | None, peers: list[FinancialSnapshot]) -> dict[str, Any]:
    if fin is None:
        return {"available": False, "reason": "financial snapshot missing"}
    metrics = [
        "sales_growth_pct",
        "operating_margin_pct",
        "net_margin_pct",
        "debt_ratio_pct",
        "current_ratio_pct",
        "roe_pct",
    ]
    zscores: dict[str, float] = {}
    for metric in metrics:
        value = getattr(fin, metric)
        peer_vals = [getattr(peer, metric) for peer in peers if getattr(peer, metric) is not None]
        z = _z_score(value, [float(v) for v in peer_vals if v is not None])
        if z is not None:
            zscores[metric] = round(z, 4)
    abs_z = [abs(v) for v in zscores.values()]
    anomaly_score = _clamp(mean(abs_z) / 3.0 if abs_z else None, 0, 1, 0)
    return {
        "available": bool(zscores),
        "peer_count": len(peers),
        "z_scores": zscores,
        "anomaly_score": round(anomaly_score, 4),
        "interpretation": _peer_anomaly_text(zscores, anomaly_score),
    }


def _peer_anomaly_text(zscores: dict[str, float], anomaly_score: float) -> str:
    if not zscores:
        return "동종 샘플이 부족해 peer anomaly는 제한적으로만 해석합니다."
    high = [f"{k} z={v:+.2f}" for k, v in zscores.items() if abs(v) >= 1.0]
    if anomaly_score >= 0.55:
        return "동종 샘플 대비 이례값이 커서 Auditor가 재무/가치평가 수치를 보수적으로 검토해야 합니다: " + ", ".join(high[:4])
    if high:
        return "일부 재무지표가 동종 샘플 대비 차이가 있으나 단독 결론 근거로 쓰기보다는 보조 위험 신호로 활용합니다: " + ", ".join(high[:4])
    return "동종 샘플 대비 극단적 이례값은 제한적입니다."


def _load_kb() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "resources" / "valuation_credit_kb.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "kb_version": "fallback",
            "default_assumptions": {"wacc": 0.11, "terminal_growth": 0.02, "projection_years": 5},
            "auditor_design_principles": [],
        }


def _recent_growth(fin: FinancialSnapshot | None, fallback: float = 0.02) -> float:
    if fin is None:
        return fallback
    raw = fin.sales_growth_pct
    if raw is None:
        return fallback
    return _clamp(raw / 100.0, -0.25, 0.25, fallback)


def _dcf_proxy(fin: FinancialSnapshot | None, kb: dict[str, Any]) -> dict[str, Any]:
    if fin is None:
        return {"available": False, "reason": "financial snapshot missing"}
    assumptions = kb.get("default_assumptions") or {}
    wacc = float(assumptions.get("wacc", 0.11))
    terminal_growth = float(assumptions.get("terminal_growth", 0.02))
    years = int(assumptions.get("projection_years", 5))
    fcf = fin.fcf
    if fcf is None:
        return {"available": False, "reason": "FCF missing"}
    if wacc <= terminal_growth:
        wacc = terminal_growth + 0.05
    growth = _recent_growth(fin, fallback=0.02)
    projected: list[float] = []
    current = fcf
    for _ in range(max(1, years)):
        current *= 1.0 + growth
        projected.append(current)
    discounted = [val / ((1.0 + wacc) ** (i + 1)) for i, val in enumerate(projected)]
    terminal_value = projected[-1] * (1.0 + terminal_growth) / max(0.01, wacc - terminal_growth)
    discounted_terminal = terminal_value / ((1.0 + wacc) ** years)
    ev_proxy = sum(discounted) + discounted_terminal
    sales_multiple_proxy = ev_proxy / fin.sales if fin.sales not in (None, 0) else None
    asset_multiple_proxy = ev_proxy / fin.total_assets if fin.total_assets not in (None, 0) else None
    equity_multiple_proxy = ev_proxy / fin.total_equity if fin.total_equity not in (None, 0) else None
    return {
        "available": True,
        "method": "FCF DCF proxy; not a target price because shares outstanding / market cap may be unavailable",
        "latest_fcf": round(fcf, 2),
        "growth_assumption": round(growth, 4),
        "wacc": round(wacc, 4),
        "terminal_growth": round(terminal_growth, 4),
        "projection_years": years,
        "enterprise_value_proxy": round(ev_proxy, 2),
        "ev_proxy_to_sales": round(sales_multiple_proxy, 4) if sales_multiple_proxy is not None else None,
        "ev_proxy_to_assets": round(asset_multiple_proxy, 4) if asset_multiple_proxy is not None else None,
        "ev_proxy_to_equity": round(equity_multiple_proxy, 4) if equity_multiple_proxy is not None else None,
        "warning": "FCF가 일회성 개선/악화일 수 있으므로 원천 재무제표와 사업화 단계 확인이 필요합니다.",
    }


def _score_credit(fin: FinancialSnapshot | None, market: MarketSnapshot, evidence_score: float) -> dict[str, Any]:
    if fin is None:
        return {
            "available": False,
            "credit_signal": "insufficient_data",
            "pd_proxy": None,
            "watch_grade": "N/A",
            "risk_drivers": ["financial CSV snapshot missing"],
        }
    risk = 0.0
    drivers: list[str] = []
    positives: list[str] = []

    debt = fin.debt_ratio_pct
    if debt is not None:
        if debt >= 250:
            risk += 0.24
            drivers.append(f"부채비율 {debt:.2f}%로 레버리지 부담이 큼")
        elif debt >= 150:
            risk += 0.16
            drivers.append(f"부채비율 {debt:.2f}%로 차입 부담 점검 필요")
        elif debt <= 80:
            risk -= 0.06
            positives.append(f"부채비율 {debt:.2f}%로 상대적으로 완충 여지")

    current_ratio = fin.current_ratio_pct
    if current_ratio is not None:
        if current_ratio < 80:
            risk += 0.17
            drivers.append(f"유동비율 {current_ratio:.2f}%로 단기 유동성 압력")
        elif current_ratio < 120:
            risk += 0.08
            drivers.append(f"유동비율 {current_ratio:.2f}%로 운전자본 점검 필요")
        elif current_ratio >= 180:
            risk -= 0.04
            positives.append(f"유동비율 {current_ratio:.2f}%로 단기 지급능력 완충")

    if fin.operating_margin_pct is not None:
        if fin.operating_margin_pct < 0:
            risk += 0.16
            drivers.append(f"영업이익률 {fin.operating_margin_pct:.2f}%로 사업 수익성 미흡")
        elif fin.operating_margin_pct >= 10:
            risk -= 0.05
            positives.append(f"영업이익률 {fin.operating_margin_pct:.2f}%")

    if fin.net_margin_pct is not None:
        if fin.net_margin_pct < 0:
            risk += 0.11
            drivers.append(f"순이익률 {fin.net_margin_pct:.2f}%로 손실 흡수력 점검 필요")
        elif fin.net_margin_pct >= 5:
            risk -= 0.04
            positives.append(f"순이익률 {fin.net_margin_pct:.2f}%")

    if fin.fcf is not None:
        if fin.fcf < 0:
            risk += 0.13
            drivers.append("FCF가 음수라 내부 현금창출 기반 상환능력 확인 필요")
        else:
            risk -= 0.08
            positives.append("FCF가 양수라 현금창출 측면의 완충 요인 존재")

    if fin.roe_pct is not None:
        if fin.roe_pct < 0:
            risk += 0.07
            drivers.append(f"ROE {fin.roe_pct:.2f}%로 자본효율성 부진")
        elif fin.roe_pct >= 8:
            risk -= 0.04
            positives.append(f"ROE {fin.roe_pct:.2f}%")

    if market.period_mdd_pct is not None and market.period_mdd_pct <= -60:
        risk += 0.07
        drivers.append(f"기간 MDD {market.period_mdd_pct:.2f}%로 시장 신용/자본조달 리스크 확대")
    if market.return_volatility_pct is not None and market.return_volatility_pct >= 4.0:
        risk += 0.04
        drivers.append(f"일수익률 변동성 {market.return_volatility_pct:.2f}%로 자본시장 리스크 큼")

    if evidence_score < 0.65:
        risk += 0.07
        drivers.append("Auditor evidence score가 낮아 재무·신용 판단의 검증 리스크 존재")

    # Convert monotonic risk points into an interpretable PD proxy.
    pd_proxy = _sigmoid(-1.2 + 3.0 * _clamp(risk, 0, 1, 0))
    if pd_proxy >= 0.55:
        signal, grade = "high_risk", "D"
    elif pd_proxy >= 0.38:
        signal, grade = "caution", "C"
    elif pd_proxy >= 0.22:
        signal, grade = "watch", "B"
    else:
        signal, grade = "stable", "A"

    return {
        "available": True,
        "method": "resource-informed monotonic credit ensemble; proxy only, not an external credit rating",
        "pd_proxy": round(pd_proxy, 4),
        "watch_grade": grade,
        "credit_signal": signal,
        "risk_points": round(_clamp(risk, 0, 1, 0), 4),
        "risk_drivers": drivers[:8],
        "positive_factors": positives[:6],
    }


def _score_valuation(fin: FinancialSnapshot | None, market: MarketSnapshot, dcf: dict[str, Any], peer: dict[str, Any]) -> dict[str, Any]:
    if fin is None:
        return {"available": False, "valuation_signal": "insufficient_data", "drivers": ["financial snapshot missing"]}
    score = 0.50
    drivers: list[str] = []
    cautions: list[str] = []

    if fin.fcf is not None:
        if fin.fcf > 0:
            score += 0.10
            drivers.append("양의 FCF 기반 DCF proxy 산정 가능")
        else:
            score -= 0.12
            cautions.append("FCF가 음수라 DCF의 안정성이 낮음")

    if fin.sales_growth_pct is not None:
        if fin.sales_growth_pct >= 15:
            score += 0.08
            drivers.append(f"매출 성장률 {fin.sales_growth_pct:.2f}%")
        elif fin.sales_growth_pct < 0:
            score -= 0.08
            cautions.append(f"매출 성장률 {fin.sales_growth_pct:.2f}%")

    if fin.operating_margin_pct is not None:
        if fin.operating_margin_pct >= 8:
            score += 0.08
            drivers.append(f"영업이익률 {fin.operating_margin_pct:.2f}%")
        elif fin.operating_margin_pct < 0:
            score -= 0.12
            cautions.append(f"영업이익률 {fin.operating_margin_pct:.2f}%")

    ev_sales = dcf.get("ev_proxy_to_sales") if dcf.get("available") else None
    if isinstance(ev_sales, (int, float)):
        if ev_sales < 0:
            score -= 0.12
            cautions.append("DCF proxy가 음수라 가치평가 결론을 보수적으로 제한")
        elif ev_sales <= 1.0:
            score += 0.07
            drivers.append(f"DCF proxy/sales {ev_sales:.2f}배")
        elif ev_sales >= 4.0 and (fin.operating_margin_pct or 0) < 5:
            score -= 0.10
            cautions.append(f"수익성 대비 DCF proxy/sales {ev_sales:.2f}배로 부담 가능성")

    anomaly = peer.get("anomaly_score") if isinstance(peer, dict) else None
    if isinstance(anomaly, (int, float)) and anomaly >= 0.55:
        score -= 0.06
        cautions.append("peer anomaly가 높아 단일 지표 가치평가를 보수적으로 해석")

    if market.period_mdd_pct is not None and market.period_mdd_pct <= -60:
        score -= 0.05
        cautions.append(f"기간 MDD {market.period_mdd_pct:.2f}%로 시장 할인 요인 존재")

    score = _clamp(score, 0, 1, 0.5)
    if score >= 0.68:
        signal = "valuation_supportive"
    elif score <= 0.38:
        signal = "valuation_risky"
    else:
        signal = "valuation_neutral"

    return {
        "available": True,
        "method": "DCF proxy + profitability/growth + peer anomaly sanity-check",
        "valuation_score": round(score, 4),
        "valuation_signal": signal,
        "supportive_drivers": drivers[:8],
        "cautions": cautions[:8],
    }


def _text_blob(opinions: list[dict[str, Any]], source_context: str) -> str:
    parts: list[str] = [source_context or ""]
    for op in opinions:
        if isinstance(op, dict):
            try:
                parts.append(json.dumps(op, ensure_ascii=False))
            except Exception:
                parts.append(str(op))
    return "\n".join(parts)


def _keyword_hits(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    hits: list[str] = []
    for term in terms:
        if term.lower() in low and term not in hits:
            hits.append(term)
    return hits


def _evidence_quality(agent_results: list[dict[str, Any]] | None) -> float:
    scores: list[float] = []
    for row in agent_results or []:
        if not isinstance(row, dict):
            continue
        val = row.get("actual_match_ratio")
        try:
            scores.append(float(val))
        except Exception:
            pass
    if not scores:
        return 0.70
    return _clamp(mean(scores), 0, 1, 0.70)


def _final_overlay_decision(valuation: dict[str, Any], credit: dict[str, Any]) -> dict[str, Any]:
    val_signal = valuation.get("valuation_signal")
    credit_signal = credit.get("credit_signal")
    if credit_signal in {"high_risk", "caution"} and val_signal != "valuation_supportive":
        stance = "conservative_hold_or_sell_bias"
        reason = "신용/상환능력 리스크가 가치평가 보조 신호보다 우선합니다."
    elif val_signal == "valuation_supportive" and credit_signal in {"stable", "watch"}:
        stance = "valuation_credit_supportive"
        reason = "가치평가 보조 신호와 신용 리스크가 동시에 악화되지는 않았습니다."
    elif val_signal == "valuation_risky":
        stance = "valuation_caution"
        reason = "DCF/수익성/peer sanity-check에서 가치평가 부담이 확인됩니다."
    else:
        stance = "neutral_overlay"
        reason = "가치평가와 신용평가 보조 신호가 명확하게 한쪽으로 쏠리지 않았습니다."
    return {"stance": stance, "reason": reason}



def _round_or_none(value: Any, digits: int = 4) -> float | None:
    val = _safe_float(value)
    return round(val, digits) if val is not None else None


def _format_pct(value: Any) -> str:
    val = _safe_float(value)
    return "확인 제한" if val is None else f"{val:.2f}%"


def _format_num(value: Any, suffix: str = "") -> str:
    val = _safe_float(value)
    if val is None:
        return "확인 제한"
    return f"{val:,.2f}{suffix}"


def _first_items(items: Any, limit: int = 3) -> str:
    if not isinstance(items, list):
        return "확인 제한"
    cleaned = [str(x).strip() for x in items if str(x).strip()]
    return "; ".join(cleaned[:limit]) if cleaned else "확인 제한"


def _build_ml_feature_vector(
    fin: FinancialSnapshot | None,
    market: MarketSnapshot,
    evidence_score: float,
    valuation: dict[str, Any],
    credit: dict[str, Any],
    peer: dict[str, Any],
) -> dict[str, Any]:
    """Create a compact auditable feature vector for the Auditor-only ML layer.

    Values are deliberately simple and deterministic. The purpose is not to
    claim a production-grade rating model, but to make the valuation/credit
    overlay behave like a transparent ML scorecard that can be shown to a mentor
    without changing Chair or the other agents.
    """
    fcf_positive = None
    if fin is not None and fin.fcf is not None:
        fcf_positive = 1.0 if fin.fcf > 0 else 0.0

    mdd = market.period_mdd_pct if market.period_mdd_pct is not None else market.max_drawdown_pct
    mdd_risk = _clamp(abs(mdd) / 80.0 if mdd is not None and mdd < 0 else 0.0, 0, 1, 0)
    vol_risk = _clamp((market.return_volatility_pct or 0.0) / 8.0, 0, 1, 0)

    op_margin = fin.operating_margin_pct if fin is not None else None
    sales_growth = fin.sales_growth_pct if fin is not None else None
    current_ratio = fin.current_ratio_pct if fin is not None else None
    debt_ratio = fin.debt_ratio_pct if fin is not None else None

    return {
        "raw": {
            "sales_growth_pct": _round_or_none(sales_growth, 4),
            "operating_margin_pct": _round_or_none(op_margin, 4),
            "debt_ratio_pct": _round_or_none(debt_ratio, 4),
            "current_ratio_pct": _round_or_none(current_ratio, 4),
            "fcf": _round_or_none(fin.fcf if fin is not None else None, 2),
            "return_volatility_pct": _round_or_none(market.return_volatility_pct, 4),
            "period_mdd_pct": _round_or_none(mdd, 4),
            "auditor_evidence_quality": round(_clamp(evidence_score, 0, 1, 0.7), 4),
            "valuation_score": _round_or_none(valuation.get("valuation_score"), 4),
            "credit_risk_points": _round_or_none(credit.get("risk_points"), 4),
            "peer_anomaly_score": _round_or_none(peer.get("anomaly_score"), 4),
        },
        "normalized_for_ml": {
            "growth_support": _clamp(((sales_growth or 0.0) + 25.0) / 50.0, 0, 1, 0.5),
            "profitability_support": _clamp(((op_margin or 0.0) + 20.0) / 40.0, 0, 1, 0.5),
            "leverage_risk": _clamp((debt_ratio or 0.0) / 300.0, 0, 1, 0.5 if debt_ratio is None else 0),
            "liquidity_support": _clamp((current_ratio or 0.0) / 250.0, 0, 1, 0.5 if current_ratio is None else 0),
            "fcf_positive": fcf_positive,
            "market_mdd_risk": round(mdd_risk, 4),
            "market_volatility_risk": round(vol_risk, 4),
            "evidence_risk": round(1.0 - _clamp(evidence_score, 0, 1, 0.7), 4),
        },
    }


def _run_interpretable_ml_layer(
    fin: FinancialSnapshot | None,
    market: MarketSnapshot,
    evidence_score: float,
    valuation: dict[str, Any],
    credit: dict[str, Any],
    peer: dict[str, Any],
) -> dict[str, Any]:
    features = _build_ml_feature_vector(fin, market, evidence_score, valuation, credit, peer)
    raw = features.get("raw", {})
    norm = features.get("normalized_for_ml", {})

    credit_risk = _clamp(raw.get("credit_risk_points"), 0, 1, 0.45 if not credit.get("available") else 0)
    valuation_score = _clamp(raw.get("valuation_score"), 0, 1, 0.5)
    peer_anomaly = _clamp(raw.get("peer_anomaly_score"), 0, 1, 0)
    mdd_risk = _clamp(norm.get("market_mdd_risk"), 0, 1, 0)
    vol_risk = _clamp(norm.get("market_volatility_risk"), 0, 1, 0)
    evidence_risk = _clamp(norm.get("evidence_risk"), 0, 1, 0.3)

    downside_risk_score = _clamp(
        0.34 * credit_risk
        + 0.20 * (1.0 - valuation_score)
        + 0.14 * peer_anomaly
        + 0.12 * mdd_risk
        + 0.08 * vol_risk
        + 0.12 * evidence_risk,
        0,
        1,
        0.5,
    )
    upside_support_score = _clamp(
        0.32 * valuation_score
        + 0.18 * _clamp(norm.get("growth_support"), 0, 1, 0.5)
        + 0.18 * _clamp(norm.get("profitability_support"), 0, 1, 0.5)
        + 0.12 * _clamp(norm.get("liquidity_support"), 0, 1, 0.5)
        + 0.10 * (1.0 - credit_risk)
        + 0.10 * (1.0 - evidence_risk),
        0,
        1,
        0.5,
    )

    if downside_risk_score >= 0.62:
        ml_label = "downside_guardrail"
        interpretation = "ML scorecard가 신용·시장·검증 리스크를 우선 경고하므로 Chair 결론을 보수적으로 해석해야 합니다."
    elif upside_support_score >= 0.64 and downside_risk_score < 0.46:
        ml_label = "upside_watch"
        interpretation = "성장·수익성·유동성 보조 신호가 있으나, Auditor evidence를 거친 범위에서만 긍정 요인으로 사용합니다."
    else:
        ml_label = "balanced_watch"
        interpretation = "상승/하락 보조 신호가 혼재되어 가치평가와 신용평가를 중립적 보조 근거로 사용합니다."

    return {
        "available": True,
        "model_family": "dependency-free interpretable ensemble + peer z-score anomaly detection",
        "why_it_counts_as_ml_method": [
            "financial/market/evidence features are transformed into a feature vector",
            "weighted ensemble produces downside and upside scores",
            "peer z-score anomaly detection adds an unsupervised ML-style control",
            "all coefficients are fixed for auditability and no external dependency is required",
        ],
        "feature_vector": features,
        "model_outputs": {
            "downside_risk_score": round(downside_risk_score, 4),
            "upside_support_score": round(upside_support_score, 4),
            "ml_overlay_label": ml_label,
            "interpretation": interpretation,
        },
        "governance": {
            "human_in_the_loop": True,
            "pass_fail_override": False,
            "chair_override": False,
            "auditor_original_role_preserved": True,
        },
    }


def _overlay_source_lines(overlay: dict[str, Any]) -> list[str]:
    fin = overlay.get("financial_snapshot") or {}
    market = overlay.get("market_snapshot") or {}
    sources: list[str] = []
    if isinstance(fin, dict) and fin.get("financial_source_file"):
        sources.append(f"financial_csv={fin.get('financial_source_file')}")
    if isinstance(market, dict) and market.get("stock_source_file"):
        sources.append(f"stock_csv={market.get('stock_source_file')}")
    artifact = overlay.get("artifact_path")
    if artifact:
        sources.append(f"auditor_overlay_artifact={artifact}")
    archives = [str(x) for x in overlay.get("source_archives_used", []) if x]
    if archives:
        sources.append("uploaded_kb_archives=" + ", ".join(archives))
    sources.extend(_trained_ml_source_lines(overlay))
    return sources


def _overlay_claims_for_agent(agent: str, overlay: dict[str, Any]) -> list[str]:
    credit = overlay.get("credit_assessment") or {}
    valuation = overlay.get("valuation_assessment") or {}
    dcf = overlay.get("dcf_proxy") or {}
    peer = overlay.get("peer_anomaly") or {}
    market = overlay.get("market_snapshot") or {}
    ml = (overlay.get("ml_interpretable_ensemble") or {}).get("model_outputs", {})
    fin = overlay.get("financial_snapshot") or {}

    common_ml = _trained_ml_summary_text(overlay)

    if agent == "finance":
        return [
            f"Auditor 신용평가 overlay: watch_grade={credit.get('watch_grade', 'N/A')}, credit_signal={credit.get('credit_signal', 'insufficient_data')}; 주요 위험요인={_first_items(credit.get('risk_drivers'), 3)}.",
            f"현금흐름·부채·유동성 기반 상환능력 proxy를 별도 점검했습니다. FCF={_format_num(fin.get('fcf'))}, 부채비율={_format_pct(fin.get('debt_ratio_pct'))}, 유동비율={_format_pct(fin.get('current_ratio_pct'))}.",
            common_ml,
        ]
    if agent == "market":
        return [
            f"Auditor 가치평가 overlay: valuation_signal={valuation.get('valuation_signal', 'insufficient_data')}, DCF proxy/sales={_format_num(dcf.get('ev_proxy_to_sales'), '배')}; 목표주가가 아니라 sanity-check입니다.",
            f"시장 리스크 overlay: 기간 MDD={_format_pct(market.get('period_mdd_pct'))}, 일수익률 변동성={_format_pct(market.get('return_volatility_pct'))}; valuation caution={_first_items(valuation.get('cautions'), 3)}.",
            common_ml,
        ]
    if agent == "tech":
        return [
            "Auditor 기술-가치평가 bridge: 기술 우위 claim은 양산·고객사·수주·매출전환·FCF 개선 근거와 연결될 때만 가치평가 가산 요인으로 사용합니다.",
            f"DCF proxy availability={dcf.get('available')}; 기술성만으로 매수 근거를 만들지 않고 commercialization evidence와 재무 snapshot을 함께 요구합니다.",
            common_ml,
        ]
    if agent == "issue":
        return [
            f"Auditor downside/event overlay: peer anomaly score={_format_num(peer.get('anomaly_score'))}; 해석={peer.get('interpretation', '확인 제한')}",
            f"신용/가치평가 이벤트 민감도: credit_signal={credit.get('credit_signal', 'insufficient_data')}, valuation_signal={valuation.get('valuation_signal', 'insufficient_data')}; 부정 이슈는 재무·시장 지표와 교차 확인합니다.",
            common_ml,
        ]
    if agent == "macro":
        return [
            f"Auditor macro-discount overlay: WACC={_format_num(dcf.get('wacc'))}, terminal_growth={_format_num(dcf.get('terminal_growth'))}; 거시요인은 할인율·자금조달 민감도 보조 신호로만 사용합니다.",
            "거시 긍정 신호가 있어도 개별기업의 매출·이익·현금흐름·신용위험 근거가 부족하면 최종 판단을 보수화합니다.",
            common_ml,
        ]
    return [common_ml]


def _overlay_evidences_for_agent(agent: str, overlay: dict[str, Any]) -> list[str]:
    focus = (overlay.get("agent_hints") or {}).get(agent, {}).get("auditor_overlay_focus", "valuation_credit_overlay")
    lines = [
        f"Auditor overlay focus={focus}; original Auditor evidence gate/pass-fail is preserved.",
        "Uploaded KB used: financial modeling materials for DCF/FCF/WACC sanity-check, distressed debt materials for repayment/recovery risk, fintech digital finance materials for explainability/model governance.",
    ]
    lines.extend(_overlay_source_lines(overlay))
    return lines


def _append_unique_text(base: Any, additions: list[str], limit: int = 12) -> list[Any]:
    items = list(base) if isinstance(base, list) else ([] if base is None else [base])
    seen = {str(x).strip() for x in items if str(x).strip()}
    for item in additions:
        cleaned = str(item).strip()
        if cleaned and cleaned not in seen:
            items.append(cleaned)
            seen.add(cleaned)
    return items[:limit]


def _write_overlay_markdown(overlay: dict[str, Any], audit_dir: Path) -> str | None:
    try:
        credit = overlay.get("credit_assessment") or {}
        valuation = overlay.get("valuation_assessment") or {}
        dcf = overlay.get("dcf_proxy") or {}
        peer = overlay.get("peer_anomaly") or {}
        ml = overlay.get("ml_interpretable_ensemble") or {}
        model_outputs = ml.get("model_outputs") or {}
        trained = overlay.get("ml_trained_proxy_ensemble") or {}
        trained_val = trained.get("valuation_ml") or {} if isinstance(trained, dict) else {}
        trained_cred = trained.get("credit_ml") or {} if isinstance(trained, dict) else {}
        trained_family = trained.get("trained_model_family") or {} if isinstance(trained, dict) else {}
        sources = _overlay_source_lines(overlay)
        lines = [
            f"# Auditor Valuation/Credit/ML Overlay - {overlay.get('company')}",
            "",
            "## Scope Control",
            "- Chair and non-Auditor agents are not modified.",
            "- Auditor's original evidence-contract and pass/fail gate are preserved.",
            "- This overlay is injected into audited opinions as front-loaded claims/evidence/source_contexts so the final report can visibly reflect valuation, credit, and ML methods.",
            "",
            _mandatory_ml_chair_section(overlay),
            "",
            "## Credit Assessment",
            f"- signal: {credit.get('credit_signal')}",
            f"- watch_grade: {credit.get('watch_grade')}",
            f"- risk_drivers: {_first_items(credit.get('risk_drivers'), 6)}",
            "",
            "## Valuation Assessment",
            f"- valuation_signal: {valuation.get('valuation_signal')}",
            f"- dcf_available: {dcf.get('available')}",
            f"- ev_proxy_to_sales: {dcf.get('ev_proxy_to_sales')}",
            f"- cautions: {_first_items(valuation.get('cautions'), 6)}",
            "",
            "## ML / Model-Risk Overlay",
            f"- trained_proxy_available: {trained.get('available') if isinstance(trained, dict) else False}",
            f"- trained_valuation_signal: {trained_val.get('signal')}",
            f"- trained_valuation_confidence: {trained_val.get('confidence_score')}",
            f"- trained_credit_label: {trained_cred.get('risk_label')}",
            f"- trained_credit_confidence: {trained_cred.get('confidence_score')}",
            f"- trained_credit_anomaly_score: {trained_cred.get('anomaly_score')}",
            f"- trained_models: valuation={trained_family.get('valuation_selected_model')}, credit={trained_family.get('credit_selected_model')}",
            f"- trained_quality: valuation_bal_acc={trained_family.get('valuation_holdout_balanced_accuracy')}, credit_bal_acc={trained_family.get('credit_holdout_balanced_accuracy')}",
            f"- fallback_model_family: {ml.get('model_family')}",
            f"- fallback_ml_overlay_label: {model_outputs.get('ml_overlay_label')}",
            f"- downside_risk_score: {model_outputs.get('downside_risk_score')}",
            f"- upside_support_score: {model_outputs.get('upside_support_score')}",
            f"- peer_anomaly: {peer.get('interpretation')}",
            "",
            "## Sources",
        ]
        lines.extend([f"- {src}" for src in sources] or ["- source 제한"])
        path = audit_dir / "valuation_credit_overlay.md"
        path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        return str(path)
    except Exception:
        return None

def _agent_hints(overlay: dict[str, Any]) -> dict[str, Any]:
    credit = overlay.get("credit_assessment") or {}
    valuation = overlay.get("valuation_assessment") or {}
    dcf = overlay.get("dcf_proxy") or {}
    peer = overlay.get("peer_anomaly") or {}
    market = overlay.get("market_snapshot") or {}
    trained = overlay.get("ml_trained_proxy_ensemble") or {}
    trained_val = trained.get("valuation_ml") or {} if isinstance(trained, dict) else {}
    trained_cred = trained.get("credit_ml") or {} if isinstance(trained, dict) else {}
    trained_common = {
        "trained_ml_available": trained.get("available") if isinstance(trained, dict) else False,
        "trained_valuation_signal": trained_val.get("signal"),
        "trained_credit_label": trained_cred.get("risk_label"),
        "trained_credit_anomaly_score": trained_cred.get("anomaly_score"),
        "trained_ml_interpretation": trained.get("interpretation") if isinstance(trained, dict) else None,
        "trained_ml_governance": trained.get("governance") if isinstance(trained, dict) else None,
    }
    return {
        "finance": {
            "auditor_overlay_focus": "credit_capacity_and_cash_flow",
            "credit_signal": credit.get("credit_signal"),
            "watch_grade": credit.get("watch_grade"),
            "risk_drivers": credit.get("risk_drivers", [])[:5],
            "positive_factors": credit.get("positive_factors", [])[:4],
            **trained_common,
        },
        "market": {
            "auditor_overlay_focus": "valuation_and_market_risk",
            "valuation_signal": valuation.get("valuation_signal"),
            "period_mdd_pct": market.get("period_mdd_pct"),
            "return_volatility_pct": market.get("return_volatility_pct"),
            "valuation_cautions": valuation.get("cautions", [])[:5],
            **trained_common,
        },
        "tech": {
            "auditor_overlay_focus": "commercialization_link_to_valuation",
            "required_connection": "기술 우위는 매출 성장률, FCF, 수익성, 고객사/양산 근거와 연결될 때만 가치평가 가산 요인으로 해석",
            "dcf_available": dcf.get("available"),
            **trained_common,
        },
        "issue": {
            "auditor_overlay_focus": "model_risk_and_downside_events",
            "credit_signal": credit.get("credit_signal"),
            "peer_anomaly_interpretation": peer.get("interpretation"),
            **trained_common,
        },
        "macro": {
            "auditor_overlay_focus": "discount_rate_and_refinancing_sensitivity",
            "wacc_used_in_proxy": dcf.get("wacc"),
            "macro_use_limit": "거시요인은 WACC/자본조달 민감도 보조 신호이며 개별기업 직접 근거로 과장하지 않음",
            **trained_common,
        },
    }


def attach_overlay_to_opinions(opinions: list[dict[str, Any]], overlay: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Attach valuation/credit ML overlay without polluting every Chair section.

    v3 intentionally front-loaded the ML overlay into every agent so that we could
    prove the data path reached Chair. That worked, but it repeated the same ML
    text across finance/market/tech/issue/macro and pushed markdown into the
    limitations section. v4 keeps the same non-blocking Auditor overlay, but makes
    it report-friendly:

    - Finance receives the main ML cross-check claims, so Chair can surface the
      section once in 핵심 근거 / 재무 분석.
    - Other agents keep structured overlay metadata only; their original claims
      are not overwritten by repeated ML text.
    - No markdown block is injected into evidences/source_contexts/limitations.
    - Chair/pass-fail/agent logic remains unchanged.
    """
    if not overlay or not isinstance(overlay, dict) or not overlay.get("enabled"):
        return opinions

    hints = overlay.get("agent_hints") or {}
    mandatory_section = overlay.get("mandatory_chair_section") or _mandatory_ml_chair_section(overlay)
    mandatory_claims = _mandatory_ml_chair_claims(overlay)
    bridge_section = overlay.get("mandatory_tech_to_value_chair_section") or _mandatory_tech_to_value_chair_section(overlay)
    bridge_claims = _mandatory_tech_to_value_claims(overlay)
    compact_prefix = "\n".join(mandatory_claims + bridge_claims)

    valuation_signal, credit_label = _ml_value_label_for_chair(overlay)
    company = str(overlay.get("company") or "해당 기업")
    governance_note = (
        "Auditor ML overlay는 반도체 딥테크 universe 기반 proxy-only 보조검증이며, "
        "공식 신용등급/목표주가/투자의견이 아닙니다. 20거래일 수익률 타깃은 사용하지 않았고, "
        "기존 Auditor evidence gate/pass-fail 역할은 유지됩니다."
    )
    one_line_reference = (
        f"Auditor ML cross-check 참고: {company}의 가치평가 ML={valuation_signal}, "
        f"신용위험 ML={credit_label}. 상세 내용은 재무 분석의 ML 기반 신용·가치평가 교차검증 섹션에 반영합니다."
    )

    attached: list[dict[str, Any]] = []
    main_inserted = False

    for op in opinions:
        if not isinstance(op, dict):
            continue

        cloned = dict(op)
        agent = str(
            cloned.get("agent")
            or cloned.get("agent_name")
            or cloned.get("name")
            or cloned.get("role")
            or ""
        ).lower().replace("_agent", "")

        if agent in hints:
            hint = dict(hints[agent]) if isinstance(hints.get(agent), dict) else {}
            hint["mandatory_chair_section"] = mandatory_section
            if bridge_section:
                hint["mandatory_tech_to_value_chair_section"] = bridge_section
            hint["chair_visibility_policy"] = "main_section_once_finance_and_tech_to_value_v5"
            cloned["auditor_valuation_credit_overlay"] = hint
            cloned["valuation_credit_overlay"] = hint
            cloned["auditor_mandatory_chair_section"] = mandatory_section
            cloned["auditor_ml_crosscheck_summary"] = compact_prefix

            # Put the main Chair-visible ML section only once. Prefer finance because
            # valuation/credit risk is closest to financial analysis, and Chair's
            # deterministic fallback tends to surface finance claims early.
            is_main_target = (agent == "finance") or (not main_inserted and agent in {"market", "tech", "issue", "macro"})

            if is_main_target and not main_inserted:
                overlay_claims = mandatory_claims + bridge_claims + _overlay_claims_for_agent(agent, overlay)
                # Evidence stays one-line/plain text to avoid markdown appearing in 한계.
                overlay_evidences = _overlay_evidences_for_agent(agent, overlay) + [governance_note]
                cloned["claims"] = _prepend_unique_text(cloned.get("claims"), overlay_claims, limit=18)
                cloned["evidences"] = _prepend_unique_text(cloned.get("evidences"), overlay_evidences, limit=18)
                cloned["source_contexts"] = _prepend_unique_text(cloned.get("source_contexts"), [governance_note], limit=12)

                for text_key in ("summary", "analysis_summary", "rationale", "recommendation", "conclusion"):
                    if text_key in cloned or text_key == "summary":
                        cloned[text_key] = _prepend_summary_text(cloned.get(text_key), compact_prefix)

                cloned["auditor_overlay_visible"] = True
                cloned["auditor_overlay_visibility_policy"] = "main_ml_crosscheck_and_tech_to_value_once_no_markdown_evidence_v5"
                main_inserted = True
            else:
                # Keep metadata for auditability, but do not front-load repeated ML
                # claims into every agent section. Add only a short non-invasive note
                # to source_contexts so downstream code can still trace the overlay.
                cloned["source_contexts"] = _prepend_unique_text(
                    cloned.get("source_contexts"),
                    [one_line_reference, governance_note],
                    limit=12,
                )
                cloned["auditor_overlay_visible"] = True
                cloned["auditor_overlay_visibility_policy"] = "metadata_only_reference_no_repeated_claims_v5"

        attached.append(cloned)

    return attached

def run_valuation_credit_overlay(
    *,
    company_dir: str,
    company: str,
    opinions: list[dict[str, Any]],
    source_context: str,
    agent_results: list[dict[str, Any]] | None = None,
    audit_dir: Path | None = None,
) -> dict[str, Any]:
    """Run a non-blocking valuation/credit/ML overlay inside Auditor.

    This module intentionally does not modify Chair or other agents. It keeps the
    original Auditor evidence gate intact and adds a structured, auditable
    second opinion that Chair can see through audited opinion JSON.
    """
    enabled = os.getenv("AUDITOR_ENABLE_VALUATION_CREDIT_OVERLAY", "1").strip().lower() not in {"0", "false", "no", "off"}
    if not enabled:
        return {"enabled": False, "reason": "AUDITOR_ENABLE_VALUATION_CREDIT_OVERLAY is disabled"}

    kb = _load_kb()
    fin, market = _snapshot_from_company_dir(company_dir)
    peers = _peer_snapshots()
    peer = _peer_anomaly(fin, peers)
    evidence_score = _evidence_quality(agent_results)
    dcf = _dcf_proxy(fin, kb)
    credit = _score_credit(fin, market, evidence_score)
    valuation = _score_valuation(fin, market, dcf, peer)
    ml_layer = _run_interpretable_ml_layer(fin, market, evidence_score, valuation, credit, peer)
    trained_ml_layer = _run_trained_proxy_ml_layer(company_dir, company)
    final = _final_overlay_decision(valuation, credit)
    text = _text_blob(opinions, source_context)

    overlay = {
        "enabled": True,
        "overlay_version": "auditor_valuation_credit_overlay_v3_trained_ml_proxy",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "company_dir": company_dir,
        "company": company,
        "source_archives_used": [item.get("archive") for item in kb.get("created_from_uploaded_archives", [])],
        "scope_control": {
            "chair_modified": False,
            "other_agents_modified": False,
            "auditor_original_evidence_gate_preserved": True,
            "pass_fail_override": False,
            "env_file_opened_or_required": False,
        },
        "knowledge_base_version": kb.get("kb_version"),
        "financial_snapshot": asdict(fin) if fin is not None else None,
        "market_snapshot": asdict(market),
        "dcf_proxy": dcf,
        "peer_anomaly": peer,
        "credit_assessment": credit,
        "valuation_assessment": valuation,
        "text_feature_hits": {
            "valuation_terms": _keyword_hits(text, _VALUATION_TERMS),
            "credit_negative_terms": _keyword_hits(text, _CREDIT_NEGATIVE_TERMS),
            "commercialization_terms": _keyword_hits(text, _TECH_COMMERCIALIZATION_TERMS),
        },
        "ml_interpretable_ensemble": {
            **ml_layer,
            "features": kb.get("feature_dictionary", {}),
            "evidence_quality_modifier": round(evidence_score, 4),
            "reason_for_auditor_layer": "ML-style risk scoring is added at Auditor so team members' existing agents and Chair remain unchanged.",
            "visible_injection_policy": "The overlay is appended to each audited opinion's claims/evidences/source_contexts so Chair can reflect it without code changes.",
            "limitations": [
                "This is not an external agency credit rating.",
                "DCF proxy is not a formal target price.",
                "The model is deterministic and interpretable so it can be audited without new package dependencies.",
            ],
        },
        "ml_trained_proxy_ensemble": trained_ml_layer,
        "overlay_decision": final,
    }
    overlay["tech_to_value_bridge"] = _compute_tech_to_value_bridge(
        company=company,
        fin=fin,
        market=market,
        valuation=valuation,
        credit=credit,
        trained_ml_layer=trained_ml_layer,
        evidence_score=evidence_score,
        text=text,
        text_feature_hits=overlay.get("text_feature_hits", {}),
    )
    overlay["mandatory_chair_section"] = _mandatory_ml_chair_section(overlay)
    overlay["mandatory_tech_to_value_chair_section"] = _mandatory_tech_to_value_chair_section(overlay)
    overlay["chair_required_claims"] = _mandatory_ml_chair_claims(overlay)
    overlay["chair_required_tech_to_value_claims"] = _mandatory_tech_to_value_claims(overlay)
    overlay["agent_hints"] = _agent_hints(overlay)

    if audit_dir is not None:
        try:
            audit_dir.mkdir(parents=True, exist_ok=True)
            path = audit_dir / "valuation_credit_overlay.json"
            overlay["artifact_path"] = str(path)
            md_path = _write_overlay_markdown(overlay, audit_dir)
            if md_path:
                overlay["artifact_markdown_path"] = md_path
            bridge = overlay.get("tech_to_value_bridge")
            if isinstance(bridge, dict):
                bridge_json_path = audit_dir / "tech_to_value_bridge.json"
                bridge_md_path = audit_dir / "tech_to_value_bridge.md"
                bridge_json_path.write_text(json.dumps(bridge, ensure_ascii=False, indent=2), encoding="utf-8")
                bridge_md_path.write_text(_render_tech_to_value_markdown(bridge, company), encoding="utf-8")
                overlay["tech_to_value_bridge"]["artifact_json_path"] = str(bridge_json_path)
                overlay["tech_to_value_bridge"]["artifact_markdown_path"] = str(bridge_md_path)
            path.write_text(json.dumps(overlay, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            overlay["artifact_write_error"] = str(exc)

    return overlay
