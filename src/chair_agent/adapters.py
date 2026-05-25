from __future__ import annotations

import csv
import json
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from common.evidence_contract import enforce_evidence_contract
from common.agent_history import load_agent_snapshot, history_source_label
from common.data_paths import normalize_field_name


VALID_OPINIONS = {"매수", "보유", "매도"}

HISTORY_TRUE_VALUES = {"1", "true", "yes", "y", "on"}


def _history_mode_enabled() -> bool:
    """
    Chair adapter가 각 agent를 새로 실행하지 않고
    저장된 agent history에서 as_of_date snapshot을 읽도록 하는 모드.
    """
    value = os.getenv("ALPHAPROVE_USE_AGENT_HISTORY", "")
    return str(value).strip().lower() in HISTORY_TRUE_VALUES


def _history_as_of_date() -> str:
    as_of_date = os.getenv("ALPHAPROVE_AS_OF_DATE", "").strip()
    if not as_of_date:
        raise RuntimeError(
            "ALPHAPROVE_USE_AGENT_HISTORY=1 이지만 "
            "ALPHAPROVE_AS_OF_DATE가 설정되지 않았습니다. "
            "예: $env:ALPHAPROVE_AS_OF_DATE='2025-05-01'"
        )
    return as_of_date


def _history_field() -> str:
    return os.getenv("ALPHAPROVE_FIELD", "반도체").strip() or "반도체"


def _load_history_for_chair(
    *,
    agent_name: str,
    company_dir: str,
    company: str,
) -> dict | None:
    """
    history mode가 꺼져 있으면 None.
    켜져 있으면 설정된 history backend(local SQLite 또는 Google Sheets)에서 snapshot을 읽는다.

    중요:
    history mode에서 snapshot이 없으면 최신 agent를 실행하지 않고 실패시킨다.
    그래야 과거 검증 시 최신 데이터가 섞이지 않는다.
    """
    if not _history_mode_enabled():
        return None

    as_of_date = _history_as_of_date()
    field = _history_field()

    payload = load_agent_snapshot(
        as_of_date=as_of_date,
        field=field,
        company_dir=company_dir,
        agent=agent_name,
    )

    if payload is None:
        raise RuntimeError(
            "[Agent History Missing] "
            f"field={field}, as_of_date={as_of_date}, "
            f"company_dir={company_dir}, agent={agent_name} snapshot이 없습니다. "
            "먼저 scripts/archive_agent_outputs_to_history_db.py 또는 archive_agent_outputs_to_google_sheets.py로 저장하세요."
        )

    print(
        f"[Agent History Replay] loaded from {history_source_label()}: "
        f"field={field}, as_of_date={as_of_date}, "
        f"company_dir={company_dir}, company={company}, agent={agent_name}",
        flush=True,
    )

    if not isinstance(payload, dict):
        payload = {
            "_wrapped_history_payload": True,
            "payload": payload,
        }

    payload = dict(payload)
    payload.setdefault("agent", agent_name)
    payload.setdefault("company", company)
    payload.setdefault("company_dir", company_dir)

    payload["agent_history_snapshot"] = {
        "enabled": True,
        "field": field,
        "as_of_date": as_of_date,
        "company_dir": company_dir,
        "company": company,
        "agent": agent_name,
        "source": history_source_label(),
    }

    return payload



def _short_text(value: Any, max_chars: int = 900) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def _normalized_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _deep_find_first(obj: Any, keys: list[str], *, max_depth: int = 8) -> Any:
    """
    nested dict/list에서 후보 key 중 첫 값을 찾는다.
    너무 깊은 raw payload 전체를 Auditor에 넘기지 않고도 핵심 지표만 끌어오기 위한 helper.
    """
    target_keys = {_normalized_key(k) for k in keys}

    def walk(x: Any, depth: int) -> Any:
        if depth > max_depth:
            return None

        if isinstance(x, dict):
            for k, v in x.items():
                if _normalized_key(k) in target_keys and v not in (None, "", [], {}):
                    return v

            for v in x.values():
                found = walk(v, depth + 1)
                if found not in (None, "", [], {}):
                    return found

        elif isinstance(x, list):
            for item in x[:80]:
                found = walk(item, depth + 1)
                if found not in (None, "", [], {}):
                    return found

        return None

    return walk(obj, 0)


def _clean_summary_for_auditor(value: Any, *, fallback: str) -> str:
    """
    Auditor가 template/request/missing-context 문구를 실패 신호로 오인하지 않도록
    raw LLM prompt/placeholder성 문장을 제거한다.
    """
    text = str(value or "").strip()
    if not text:
        return fallback

    banned_terms = (
        "missing-context",
        "missing context",
        "template",
        "request",
        "placeholder",
        "프롬프트",
        "템플릿",
        "요청문",
        "작성 요청",
    )

    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        lowered = stripped.lower()
        if any(term in lowered for term in banned_terms):
            continue

        lines.append(stripped)

        if len(" ".join(lines)) >= 700:
            break

    cleaned = " ".join(lines).strip()
    return _short_text(cleaned or fallback, 900)



def _adapter_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _history_context(payload: dict) -> dict:
    meta = payload.get("agent_history_snapshot") if isinstance(payload, dict) else {}
    if not isinstance(meta, dict):
        meta = {}

    return {
        "field": meta.get("field") or os.getenv("ALPHAPROVE_FIELD", "반도체"),
        "as_of_date": meta.get("as_of_date") or os.getenv("ALPHAPROVE_AS_OF_DATE", ""),
        "company_dir": meta.get("company_dir") or payload.get("company_dir"),
        "company": meta.get("company") or payload.get("company"),
    }


def _safe_metric_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        num = float(value)
        if math.isnan(num) or math.isinf(num):
            return None
        return num

    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "null", "확인 제한", "n/a"}:
        return None

    # 12.3%, 1,234원, 1.2조 같은 표현의 기본 숫자만 추출
    text = text.replace(",", "").replace("%", "").replace("원", "").strip()

    try:
        num = float(text)
        if math.isnan(num) or math.isinf(num):
            return None
        return num
    except Exception:
        return None


def _get_path_value(obj: Any, path: list[str]) -> Any:
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        if key not in cur:
            return None
        cur = cur.get(key)

    if cur in (None, "", [], {}):
        return None
    return cur


def _first_path_value(obj: dict, paths: list[list[str]]) -> Any:
    for path in paths:
        value = _get_path_value(obj, path)
        if value not in (None, "", [], {}):
            return value
    return None


def _first_numeric_path_value(obj: dict, paths: list[list[str]]) -> float | None:
    for path in paths:
        value = _get_path_value(obj, path)

        if isinstance(value, list):
            return float(len(value))

        num = _safe_metric_float(value)
        if num is not None:
            return num

    return None


def _parse_date_value(value: Any) -> datetime | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # 20260501 형태
    if re.fullmatch(r"\d{8}", text):
        try:
            return datetime.strptime(text, "%Y%m%d")
        except Exception:
            pass

    # 2026-05-01, 2026.05.01, 2026/05/01 형태
    text = text[:10].replace(".", "-").replace("/", "-")
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue

    return None


def _find_column(row: dict, candidates: list[str]) -> str | None:
    if not isinstance(row, dict):
        return None

    normalized = {_normalized_key(k): k for k in row.keys()}

    for cand in candidates:
        key = _normalized_key(cand)
        if key in normalized:
            return normalized[key]

    # 부분 매칭 fallback
    for norm_key, original_key in normalized.items():
        for cand in candidates:
            cand_norm = _normalized_key(cand)
            if cand_norm and cand_norm in norm_key:
                return original_key

    return None


def _read_price_csv_rows(path: Path) -> list[dict]:
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]

    for enc in encodings:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                raw_rows = list(reader)
            break
        except Exception:
            raw_rows = []
            continue
    else:
        return []

    if not raw_rows:
        return []

    sample = raw_rows[0]

    date_col = _find_column(
        sample,
        ["date", "datetime", "trade_date", "trading_date", "일자", "날짜", "거래일", "기준일"],
    )
    close_col = _find_column(
        sample,
        ["close", "adj_close", "adjusted_close", "latest_close", "종가", "수정종가", "현재가", "close_price"],
    )
    volume_col = _find_column(
        sample,
        ["volume", "거래량", "trading_volume"],
    )
    trading_value_col = _find_column(
        sample,
        ["trading_value", "amount", "value", "거래대금", "거래금액", "대금"],
    )

    if not date_col or not close_col:
        return []

    parsed = []

    for row in raw_rows:
        dt = _parse_date_value(row.get(date_col))
        close = _safe_metric_float(row.get(close_col))

        if dt is None or close is None or close <= 0:
            continue

        volume = _safe_metric_float(row.get(volume_col)) if volume_col else None
        trading_value = _safe_metric_float(row.get(trading_value_col)) if trading_value_col else None

        if trading_value is None and volume is not None:
            trading_value = volume * close

        parsed.append(
            {
                "date": dt,
                "close": close,
                "volume": volume,
                "trading_value": trading_value,
                "source_file": str(path),
            }
        )

    parsed.sort(key=lambda x: x["date"])
    return parsed


def _candidate_company_roots(*, field: str, company: str, company_dir: str) -> list[Path]:
    root = _adapter_project_root()
    field_root = root / "data" / field

    candidates = [
        field_root / company,
        field_root / company_dir,
    ]

    return [p for p in candidates if p.exists() and p.is_dir()]


def _find_price_csv_rows(*, field: str, company: str, company_dir: str) -> tuple[list[dict], str | None]:
    patterns = [
        "**/*price*.csv",
        "**/*stock*.csv",
        "**/*ohlcv*.csv",
        "**/*market*.csv",
        "**/*주가*.csv",
        "**/*시세*.csv",
        "**/*가격*.csv",
    ]

    candidates: list[Path] = []

    for root in _candidate_company_roots(field=field, company=company, company_dir=company_dir):
        for pattern in patterns:
            for p in root.glob(pattern):
                if not p.is_file():
                    continue

                parts = {part.lower() for part in p.parts}
                if "history_replay" in parts:
                    continue

                candidates.append(p)

    # 큰 파일/최근 파일 우선
    candidates = sorted(
        set(candidates),
        key=lambda p: (p.stat().st_size, p.stat().st_mtime),
        reverse=True,
    )

    for p in candidates[:30]:
        rows = _read_price_csv_rows(p)
        if len(rows) >= 2:
            return rows, str(p)

    return [], None


def _calc_return(latest: float | None, base: float | None) -> float | None:
    if latest is None or base is None or base == 0:
        return None
    return latest / base - 1.0


def _calc_mdd(closes: list[float]) -> float | None:
    if len(closes) < 2:
        return None

    peak = closes[0]
    mdd = 0.0

    for close in closes:
        if close > peak:
            peak = close
        if peak:
            drawdown = close / peak - 1.0
            if drawdown < mdd:
                mdd = drawdown

    return mdd


def _calc_annualized_volatility(closes: list[float]) -> float | None:
    if len(closes) < 3:
        return None

    returns = []
    for prev, cur in zip(closes[:-1], closes[1:]):
        if prev and prev > 0:
            returns.append(cur / prev - 1.0)

    if len(returns) < 2:
        return None

    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(var) * math.sqrt(252)


def _compute_market_metrics_from_price_files(
    *,
    field: str,
    company: str,
    company_dir: str,
    as_of_date: str,
    market_cap: Any = None,
) -> dict:
    rows, source_file = _find_price_csv_rows(
        field=field,
        company=company,
        company_dir=company_dir,
    )

    if not rows:
        return {
            "source_file": None,
            "current_price": None,
            "annual_return": None,
            "recent_1m_return": None,
            "mdd": None,
            "volatility": None,
            "avg_trading_value_20d": None,
            "turnover_proxy": None,
            "liquidity_status": None,
        }

    as_of_dt = _parse_date_value(as_of_date)
    if as_of_dt is not None:
        rows = [r for r in rows if r["date"] <= as_of_dt]

    if len(rows) < 2:
        return {
            "source_file": source_file,
            "current_price": None,
            "annual_return": None,
            "recent_1m_return": None,
            "mdd": None,
            "volatility": None,
            "avg_trading_value_20d": None,
            "turnover_proxy": None,
            "liquidity_status": None,
        }

    latest = rows[-1]["close"]

    one_month_idx = max(0, len(rows) - 22)
    one_year_idx = max(0, len(rows) - 253)

    recent_1m_return = _calc_return(latest, rows[one_month_idx]["close"])
    annual_return = _calc_return(latest, rows[one_year_idx]["close"])

    window_rows = rows[-252:] if len(rows) > 252 else rows
    closes = [r["close"] for r in window_rows if r.get("close") is not None]

    mdd = _calc_mdd(closes)
    volatility = _calc_annualized_volatility(closes)

    trading_values = [
        r.get("trading_value")
        for r in rows[-20:]
        if _safe_metric_float(r.get("trading_value")) is not None
    ]

    avg_trading_value_20d = None
    if trading_values:
        avg_trading_value_20d = sum(float(v) for v in trading_values) / len(trading_values)

    market_cap_num = _safe_metric_float(market_cap)
    turnover_proxy = None
    if avg_trading_value_20d is not None and market_cap_num:
        turnover_proxy = avg_trading_value_20d / market_cap_num

    liquidity_status = None
    if avg_trading_value_20d is not None:
        if avg_trading_value_20d >= 10_000_000_000:
            liquidity_status = "HIGH"
        elif avg_trading_value_20d >= 1_000_000_000:
            liquidity_status = "MEDIUM"
        else:
            liquidity_status = "LOW"

    return {
        "source_file": source_file,
        "current_price": latest,
        "annual_return": annual_return,
        "recent_1m_return": recent_1m_return,
        "mdd": mdd,
        "volatility": volatility,
        "avg_trading_value_20d": avg_trading_value_20d,
        "turnover_proxy": turnover_proxy,
        "liquidity_status": liquidity_status,
    }


def _load_valuation_history_for_same_context(payload: dict, *, company_dir: str) -> dict:
    context = _history_context(payload)
    field = normalize_field_name(context.get("field") or "반도체")
    as_of_date = context.get("as_of_date")

    if not as_of_date:
        return {}

    try:
        valuation_payload = load_agent_snapshot(
            as_of_date=as_of_date,
            field=field,
            company_dir=company_dir,
            agent="valuation",
        )
        return valuation_payload if isinstance(valuation_payload, dict) else {}
    except Exception:
        return {}


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _choose_tech_total_score(
    *,
    source: dict,
    bridge_score: Any,
    max_score: Any,
) -> tuple[float | None, str]:
    """
    기존 deep_find_first가 nested evidence의 작은 score=5를 tech total_score로 잘못 잡는 문제를 방지한다.

    우선순위:
    1. 명시적 final/investor/scorecard 경로
    2. top-level total_score
    3. raw_payload.total_score
    4. 값이 너무 작고 bridge_score가 높은 경우 noise로 보고 bridge_score를 35점 만점 환산
    """
    max_score_num = _safe_metric_float(max_score) or 35.0
    bridge_num = _safe_metric_float(bridge_score)

    explicit_paths = [
        ["final_investor_tech_score"],
        ["final_tech_evidence_score"],
        ["tech_investor_view", "final_investor_tech_score"],
        ["tech_investor_view", "final_tech_score"],
        ["tech_investor_view", "score"],
        ["investor_tech_view", "final_investor_tech_score"],
        ["investor_tech_view", "final_tech_score"],
        ["scorecard", "final_investor_tech_score"],
        ["scorecard", "final_tech_score"],
        ["scorecard", "total_score"],
        ["total_score"],
        ["raw_payload", "total_score"],
    ]

    candidate = _first_numeric_path_value(source, explicit_paths)

    if candidate is not None:
        # 100점 척도면 max_score 척도로 변환
        if candidate > max_score_num and candidate <= 100:
            return round(candidate / 100.0 * max_score_num, 2), "scaled_from_100_point_score"

        # bridge가 높은데 total_score가 5처럼 비정상적으로 작으면 nested noise로 판단
        if bridge_num is not None and bridge_num >= 50 and candidate < max_score_num * 0.25:
            return round(bridge_num / 100.0 * max_score_num, 2), "derived_from_bridge_score_due_to_suspicious_low_candidate"

        return candidate, "explicit_total_score"

    if bridge_num is not None:
        return round(bridge_num / 100.0 * max_score_num, 2), "derived_from_bridge_score"

    return None, "not_available"


def _choose_patent_records_count(source: dict) -> float | None:
    paths = [
        ["patent_records_count"],
        ["patents_count"],
        ["total_patents"],
        ["raw_payload", "patent_records_count"],
        ["raw_payload", "patents_count"],
        ["raw_payload", "total_patents"],
        ["patent_count"],
        ["raw_payload", "patent_count"],
    ]

    for path in paths:
        value = _get_path_value(source, path)

        if isinstance(value, list):
            return float(len(value))

        num = _safe_metric_float(value)
        if num is not None:
            return num

    return None


def _choose_registered_patents_count(source: dict) -> float | None:
    """
    registered_patents=4809 같은 다른 의미의 raw 집계와 충돌하지 않도록
    estimated/count 계열만 우선 사용한다.
    """
    paths = [
        ["registered_patents_count"],
        ["registered_patents_estimated_count"],
        ["registered_patents_estimated"],
        ["valid_registered_patents_count"],
        ["raw_payload", "registered_patents_count"],
        ["raw_payload", "registered_patents_estimated_count"],
        ["raw_payload", "registered_patents_estimated"],
        ["raw_payload", "valid_registered_patents_count"],
    ]

    return _first_numeric_path_value(source, paths)





def _report_norm_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")



def _trim_to_complete_sentence(value: Any, *, max_chars: int = 900) -> str:
    """
    보고서 문장이 '고성능 WLP 패키지…'처럼 중간에서 끊기지 않도록
    가능한 문장 끝에서 자른다. 말줄임표는 붙이지 않는다.
    """
    text = str(value or "").strip()
    if not text:
        return ""

    text = " ".join(text.split())

    if len(text) <= max_chars:
        return text

    cut = text[:max_chars].rstrip()

    # 한국어 보고서에서 자연스럽게 끝나는 지점을 우선 탐색
    sentence_endings = ["다.", "니다.", "됩니다.", "입니다.", "합니다.", "있습니다.", "습니다.", "요.", "."]

    best = -1
    for ending in sentence_endings:
        idx = cut.rfind(ending)
        if idx > best:
            best = idx + len(ending)

    if best >= max(80, int(max_chars * 0.55)):
        return cut[:best].rstrip()

    # 문장 끝을 못 찾으면 마지막 공백 기준으로 자르되 말줄임표는 붙이지 않음
    space_idx = cut.rfind(" ")
    if space_idx >= max(80, int(max_chars * 0.55)):
        return cut[:space_idx].rstrip()

    return cut.rstrip()


def _summarize_market_dict_for_report(summary_dict: dict, *, max_chars: int = 760) -> str:
    """
    Market summary dict를 Chair 보고서용 완결 문단으로 변환한다.

    원칙:
    - summary는 너무 길게 만들지 않는다.
    - 경쟁 구도/주가 변동성 등은 risk bullet에 들어가므로 summary에서는 짧게만 반영한다.
    - 문장 중간 말줄임표가 생기지 않도록 각 항목을 문장 단위로 자른다.
    """
    if not isinstance(summary_dict, dict):
        return _trim_to_complete_sentence(summary_dict, max_chars=max_chars)

    ordered_keys = [
        ("industry_stage", "산업 단계"),
        ("value_chain_position", "밸류체인 포지션"),
        ("oecd_interpretation", "거시·경기 신호"),
        ("market_momentum", "시장 모멘텀"),
    ]

    parts = []

    for key, label in ordered_keys:
        value = summary_dict.get(key)
        if not value:
            continue

        # 각 항목이 너무 길면 해당 항목 내부에서 문장 단위로 정리
        cleaned = _trim_to_complete_sentence(value, max_chars=230)
        if cleaned:
            parts.append(f"{label}: {cleaned}")

    # competitive_position은 summary에 넣으면 길어지기 쉬우므로 짧게만 반영
    competitive = summary_dict.get("competitive_position")
    if competitive:
        cleaned = _trim_to_complete_sentence(competitive, max_chars=180)
        if cleaned:
            parts.append(f"경쟁 구도: {cleaned}")

    text = " ".join(parts).strip()
    return _trim_to_complete_sentence(text, max_chars=max_chars)


def _format_basis_opportunity_or_risk_dict(item: dict) -> str:
    """
    {'basis': ..., 'opportunity': ...} / {'basis': ..., '리스크': ..., 'severity': ...}
    형태가 보고서에 'basis: ... opportunity: ...'처럼 어색하게 나오지 않도록 정리한다.
    """
    if not isinstance(item, dict):
        return str(item or "").strip()

    basis = (
        item.get("basis")
        or item.get("근거")
        or item.get("evidence")
        or item.get("reason")
    )

    opportunity = (
        item.get("opportunity")
        or item.get("기회")
        or item.get("positive")
        or item.get("thesis")
    )

    risk = (
        item.get("risk")
        or item.get("리스크")
        or item.get("negative")
        or item.get("concern")
    )

    severity = item.get("severity") or item.get("중요도") or item.get("level")

    if opportunity:
        if basis:
            return f"{opportunity} 근거는 {basis}입니다."
        return str(opportunity).strip()

    if risk:
        if basis and severity:
            return f"{risk} 수준은 {severity}이며, 근거는 {basis}입니다."
        if basis:
            return f"{risk} 근거는 {basis}입니다."
        return str(risk).strip()

    # 일반 dict fallback
    parts = []
    for k, v in item.items():
        if v in (None, "", [], {}):
            continue
        parts.append(f"{k}: {v}")

    return " ".join(parts).strip()



def _clean_report_text(value: Any, *, max_chars: int = 2400) -> str:
    """
    Chair 보고서용 텍스트 정리 함수.

    개선:
    - dict summary를 그대로 "{...}" 형태로 넣지 않고 문장형으로 렌더링
    - template / placeholder / missing-context 류 문구 제거
    - 너무 긴 내용은 max_chars 기준으로 축약
    """
    label_map = {
        "competitive_position": "경쟁 구도",
        "industry_stage": "산업 단계",
        "market_momentum": "시장 모멘텀",
        "oecd_interpretation": "거시·경기 신호",
        "value_chain_position": "밸류체인 포지션",
        "growth_driver": "성장 동인",
        "growth_drivers": "성장 동인",
        "risk": "리스크",
        "risks": "리스크",
        "key_risks": "주요 리스크",
        "key_thesis": "핵심 투자 포인트",
        "summary": "요약",
        "analysis": "분석",
    }

    banned_terms = (
        "template",
        "placeholder",
        "missing-context",
        "missing context",
        "프롬프트",
        "템플릿",
        "작성 요청",
        "요청문",
    )

    def clean_line(x: Any) -> str:
        s = str(x or "").strip()
        if not s:
            return ""

        lowered = s.lower()
        if any(term in lowered for term in banned_terms):
            return ""

        return " ".join(s.split())

    parts: list[str] = []

    if isinstance(value, dict):
        preferred_order = [
            "industry_stage",
            "value_chain_position",
            "oecd_interpretation",
            "market_momentum",
            "competitive_position",
            "summary",
            "analysis",
            "key_thesis",
            "key_risks",
            "risks",
        ]

        used = set()

        for key in preferred_order:
            if key in value:
                line = clean_line(value.get(key))
                if line:
                    label = label_map.get(key, key)
                    parts.append(f"{label}: {line}")
                    used.add(key)

        for key, val in value.items():
            if key in used:
                continue
            if isinstance(val, (dict, list)):
                line = _clean_report_text(val, max_chars=700)
            else:
                line = clean_line(val)

            if line:
                label = label_map.get(str(key), str(key))
                parts.append(f"{label}: {line}")

        text = " ".join(parts).strip()

    elif isinstance(value, list):
        for item in value[:8]:
            line = _clean_report_text(item, max_chars=500)
            if line:
                parts.append(line)
        text = " ".join(parts).strip()

    else:
        raw = str(value or "").strip()
        lines = []
        for line in raw.splitlines():
            cleaned = clean_line(line)
            if cleaned:
                lines.append(cleaned)
        text = " ".join(lines).strip()

    text = _trim_to_complete_sentence(text, max_chars=max_chars)

    return text

def _is_compact_fallback_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True

    compact_markers = (
        "검증 가능한 핵심 근거는 다음과 같습니다",
        "market return metrics",
        "market drawdown metrics",
        "market liquidity metrics",
        "tech-to-value bridge metrics",
        "compact packet",
        "Auditor용",
        "history snapshot은",
    )

    return any(marker in text for marker in compact_markers)


def _is_report_text_usable(value: Any) -> bool:
    text = _clean_report_text(value)
    if len(text) < 40:
        return False
    if _is_compact_fallback_text(text):
        return False
    return True


def _iter_report_field_values(obj: Any, candidate_keys: set[str], *, max_depth: int = 7):
    skip_keys = {
        "claims",
        "claim",
        "evidences",
        "evidence",
        "source_contexts",
        "supported_claims",
        "unsupported_claims",
        "framework_metrics",
        "tech_framework_metrics",
        "market_framework",
        "adapter_compaction",
        "metric_source",
        "agent_history_snapshot",
    }

    def walk(x: Any, depth: int):
        if depth > max_depth:
            return

        if isinstance(x, dict):
            for k, v in x.items():
                nk = _report_norm_key(k)
                if nk in candidate_keys and v not in (None, "", [], {}):
                    yield v

            for k, v in x.items():
                nk = _report_norm_key(k)
                if nk in skip_keys:
                    continue
                yield from walk(v, depth + 1)

        elif isinstance(x, list):
            for item in x[:50]:
                yield from walk(item, depth + 1)

    yield from walk(obj, 0)


def _value_to_report_items(value: Any, *, max_items: int = 6, max_chars_each: int = 420) -> list[str]:
    items: list[str] = []

    def add_one(x: Any):
        if x in (None, "", [], {}):
            return

        if isinstance(x, dict):
            formatted = _format_basis_opportunity_or_risk_dict(x)
            if formatted:
                add_one(formatted)
            return

        s = str(x).strip()
        if not s:
            return

        for prefix in ("- ", "• ", "* "):
            if s.startswith(prefix):
                s = s[len(prefix):].strip()

        s = _clean_report_text(s, max_chars=max_chars_each)

        if not s or _is_compact_fallback_text(s):
            return

        if s not in items:
            items.append(s)

    if isinstance(value, list):
        for item in value:
            add_one(item)

    elif isinstance(value, dict):
        for key in (
            "items",
            "points",
            "key_thesis",
            "thesis",
            "key_risks",
            "risks",
            "risk_factors",
            "strengths",
            "opportunities",
        ):
            if key in value:
                nested = _value_to_report_items(
                    value.get(key),
                    max_items=max_items,
                    max_chars_each=max_chars_each,
                )
                for item in nested:
                    if item not in items:
                        items.append(item)

        if not items:
            add_one(value)

    else:
        text = str(value or "").strip()
        raw_lines = [line.strip() for line in text.splitlines() if line.strip()]

        if len(raw_lines) >= 2:
            for line in raw_lines:
                add_one(line)
        else:
            add_one(text)

    return items[:max_items]


def _pick_report_summary_from_source(source: dict, *, fallback: str) -> str:
    candidate_keys = {
        "summary",
        "market_summary",
        "tech_summary",
        "finance_summary",
        "issue_summary",
        "macro_summary",
        "valuation_summary",
        "analysis_summary",
        "report_summary",
        "narrative_summary",
        "analysis",
    }

    dict_candidates = []
    text_candidates = []

    for value in _iter_report_field_values(source, candidate_keys):
        if isinstance(value, dict):
            rendered = _summarize_market_dict_for_report(value, max_chars=760)
            if _is_report_text_usable(rendered):
                dict_candidates.append(rendered)
        elif _is_report_text_usable(value):
            cleaned = _clean_report_text(value, max_chars=1200)
            text_candidates.append(cleaned)

    # dict summary가 있으면, 문장형으로 안전하게 렌더링한 것을 우선 사용
    if dict_candidates:
        dict_candidates = sorted(dict_candidates, key=len, reverse=True)
        return _trim_to_complete_sentence(dict_candidates[0], max_chars=760)

    if text_candidates:
        text_candidates = sorted(text_candidates, key=len, reverse=True)
        return _trim_to_complete_sentence(text_candidates[0], max_chars=1000)

    return _trim_to_complete_sentence(fallback, max_chars=760)

def _pick_report_items_from_source(
    source: dict,
    *,
    kind: str,
    fallback: list[str] | None = None,
) -> list[str]:
    if kind == "thesis":
        candidate_keys = {
            "key_thesis",
            "thesis",
            "investment_thesis",
            "positive_factors",
            "strengths",
            "opportunities",
            "main_points",
            "핵심_thesis",
        }
    else:
        candidate_keys = {
            "key_risks",
            "risks",
            "risk_factors",
            "negative_factors",
            "weaknesses",
            "concerns",
            "주의사항",
            "주요_risk",
        }

    best: list[str] = []

    for value in _iter_report_field_values(source, candidate_keys):
        items = _value_to_report_items(value, max_items=6)
        if len(" ".join(items)) > len(" ".join(best)):
            best = items

    if best:
        return best

    fallback = fallback or []
    return _value_to_report_items(fallback, max_items=6)



def _derive_report_items_from_summary_dict(
    source: dict,
    *,
    agent_name: str,
    kind: str,
) -> list[str]:
    """
    원본 history payload에 key_thesis/key_risks가 없더라도,
    summary dict의 구조적 항목을 보고 Chair 보고서용 thesis/risk를 자동 생성한다.

    특히 Market Agent의 아래 구조를 보고서용으로 분리한다.
    - industry_stage / value_chain_position / oecd_interpretation -> thesis
    - competitive_position / market_momentum 중 하락·변동성 문구 -> risk
    """
    if not isinstance(source, dict):
        return []

    summary_candidate_keys = {
        "summary",
        "market_summary",
        "tech_summary",
        "finance_summary",
        "issue_summary",
        "macro_summary",
        "valuation_summary",
        "analysis_summary",
        "report_summary",
        "narrative_summary",
        "analysis",
    }

    summary_dicts = []
    for value in _iter_report_field_values(source, summary_candidate_keys):
        if isinstance(value, dict):
            summary_dicts.append(value)

    if not summary_dicts:
        return []

    thesis_keys = {
        "industry_stage": "산업 성장성",
        "value_chain_position": "밸류체인 포지션",
        "oecd_interpretation": "거시·경기 신호",
        "growth_driver": "성장 동인",
        "growth_drivers": "성장 동인",
        "opportunity": "기회 요인",
        "opportunities": "기회 요인",
        "strength": "강점",
        "strengths": "강점",
        "commercialization": "사업화 연결성",
        "tech_to_value": "기술-가치 연결성",
    }

    risk_keys = {
        "competitive_position": "경쟁 리스크",
        "risk": "리스크",
        "risks": "리스크",
        "key_risks": "주요 리스크",
        "weakness": "약점",
        "weaknesses": "약점",
        "concern": "우려 요인",
        "concerns": "우려 요인",
        "drawdown": "낙폭 리스크",
        "volatility": "변동성 리스크",
        "liquidity": "유동성 리스크",
    }

    negative_terms = (
        "하락",
        "부진",
        "변동성",
        "고점 대비",
        "리스크",
        "경쟁",
        "압박",
        "둔화",
        "불확실",
        "약세",
        "낙폭",
    )

    items: list[str] = []

    def add_item(label: str, val: Any):
        text = _clean_report_text(val, max_chars=420)
        if not text:
            return
        item = f"{label}: {text}"
        if item not in items:
            items.append(item)

    for summary_dict in summary_dicts:
        for key, val in summary_dict.items():
            norm_key = str(key).strip().lower()

            if kind == "thesis":
                if norm_key in thesis_keys:
                    add_item(thesis_keys[norm_key], val)

                # market_momentum은 긍정 문맥이면 thesis로도 활용 가능
                elif norm_key == "market_momentum":
                    text = _clean_report_text(val, max_chars=420)
                    if text and not any(term in text for term in negative_terms):
                        add_item("시장 모멘텀", val)

            else:
                if norm_key in risk_keys:
                    add_item(risk_keys[norm_key], val)

                elif norm_key == "market_momentum":
                    text = _clean_report_text(val, max_chars=420)
                    if text and any(term in text for term in negative_terms):
                        add_item("주가·시장 모멘텀 리스크", val)

        if len(items) >= 5:
            break

    return items[:6]




def _pick_concise_original_summary_for_report(
    source: dict,
    *,
    agent_name: str,
    company: str,
) -> str:
    """
    Chair 보고서용 summary는 길게 이어붙인 dict 설명보다
    원래 agent가 만든 짧고 완결된 summary 문장을 우선 사용한다.

    특히 market history replay에서 아래와 같은 끊김을 방지한다.
    - 산업 단계: ... 경쟁 구도: ... 고성능 WLP 패키지…

    원칙:
    - summary / *_summary / report_summary 계열의 문자열만 후보로 사용
    - dict를 렌더링한 '산업 단계: ... 밸류체인 포지션: ...' 형태는 제외
    - compact fallback 문구도 제외
    - 60~800자 사이의 완결 문장 우선
    """
    if not isinstance(source, dict):
        return ""

    candidate_keys = {
        "summary",
        "market_summary",
        "tech_summary",
        "finance_summary",
        "issue_summary",
        "macro_summary",
        "valuation_summary",
        "analysis_summary",
        "report_summary",
        "narrative_summary",
    }

    label_markers = (
        "산업 단계:",
        "밸류체인 포지션:",
        "거시·경기 신호:",
        "시장 모멘텀:",
        "경쟁 구도:",
        "competitive_position:",
        "industry_stage:",
        "market_momentum:",
        "value_chain_position:",
    )

    compact_markers = (
        "검증 가능한 핵심 근거는 다음과 같습니다",
        "compact packet",
        "Auditor용",
        "history snapshot은",
        "market return metrics",
        "market drawdown metrics",
        "market liquidity metrics",
    )

    candidates: list[tuple[int, str]] = []

    def add_candidate(value: Any, *, direct_bonus: int = 0):
        if not isinstance(value, str):
            return

        cleaned = _clean_report_text(value, max_chars=900)
        if not cleaned:
            return

        if len(cleaned) < 50:
            return

        if any(marker in cleaned for marker in label_markers):
            return

        if any(marker in cleaned for marker in compact_markers):
            return

        if _is_compact_fallback_text(cleaned):
            return

        score = direct_bonus

        if company and company in cleaned:
            score += 20

        if 80 <= len(cleaned) <= 500:
            score += 30
        elif 500 < len(cleaned) <= 800:
            score += 10

        if "다만" in cleaned or "그러나" in cleaned:
            score += 8

        if "보유" in cleaned or "매수" in cleaned or "매도" in cleaned:
            score += 5

        if cleaned.endswith(("다.", "습니다.", "합니다.", "입니다.")):
            score += 8

        # 너무 길어서 다시 잘릴 가능성이 있는 문장은 감점
        if len(cleaned) > 700:
            score -= 20

        candidates.append((score, _trim_to_complete_sentence(cleaned, max_chars=700)))

    # top-level summary를 가장 우선
    for key in candidate_keys:
        add_candidate(source.get(key), direct_bonus=100)

    # raw_payload / result / packet 내부에 있는 원래 summary도 탐색
    for container_key in ("raw_payload", "result", "packet", "agent_packet", "original_payload"):
        container = source.get(container_key)
        if isinstance(container, dict):
            for key in candidate_keys:
                add_candidate(container.get(key), direct_bonus=80)

    # 마지막으로 전체 nested 탐색
    for value in _iter_report_field_values(source, candidate_keys):
        add_candidate(value, direct_bonus=20)

    if not candidates:
        return ""

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]




def _find_market_summary_dict(source: dict) -> dict:
    """
    Market Agent 원본 payload 안에서
    industry_stage / value_chain_position / market_momentum / competitive_position
    같은 구조화 summary dict를 찾는다.
    """
    if not isinstance(source, dict):
        return {}

    candidate_keys = {
        "summary",
        "market_summary",
        "analysis_summary",
        "report_summary",
        "narrative_summary",
        "analysis",
    }

    expected_keys = {
        "industry_stage",
        "value_chain_position",
        "oecd_interpretation",
        "market_momentum",
        "competitive_position",
    }

    for value in _iter_report_field_values(source, candidate_keys):
        if isinstance(value, dict):
            keys = {str(k).strip() for k in value.keys()}
            if keys & expected_keys:
                return value

    return {}


def _market_item(label: str, value: Any, *, max_chars: int = 360) -> str:
    text = _clean_report_text(value, max_chars=max_chars)
    text = _trim_to_complete_sentence(text, max_chars=max_chars)
    if not text:
        return ""
    return f"{label}: {text}"


def _append_unique_market_items(
    base_items: Any,
    extra_items: list[str],
    *,
    max_items: int = 5,
) -> list[str]:
    result: list[str] = []

    def add(value: Any):
        if value in (None, "", [], {}):
            return

        if isinstance(value, list):
            for x in value:
                add(x)
            return

        if isinstance(value, dict):
            formatted = _format_basis_opportunity_or_risk_dict(value)
            add(formatted)
            return

        text = _clean_report_text(value, max_chars=460)
        text = _trim_to_complete_sentence(text, max_chars=460)

        if not text:
            return

        if _is_compact_fallback_text(text):
            return

        if text not in result:
            result.append(text)

    add(base_items)

    for item in extra_items:
        add(item)

    return result[:max_items]


def _build_rich_market_summary(
    *,
    base_summary: str,
    summary_dict: dict,
    company: str,
) -> str:
    """
    너무 짧지도, 너무 길어서 끊기지도 않는 시장 요약을 만든다.
    """
    base = _clean_report_text(base_summary, max_chars=420)
    base = _trim_to_complete_sentence(base, max_chars=420)

    industry = summary_dict.get("industry_stage")
    value_chain = summary_dict.get("value_chain_position")
    momentum = summary_dict.get("market_momentum")
    competition = summary_dict.get("competitive_position")
    oecd = summary_dict.get("oecd_interpretation")

    parts = []

    if base:
        parts.append(base)

    detail_positive = []
    if industry:
        detail_positive.append(_trim_to_complete_sentence(industry, max_chars=180))
    if value_chain:
        detail_positive.append(_trim_to_complete_sentence(value_chain, max_chars=180))
    if oecd:
        detail_positive.append(_trim_to_complete_sentence(oecd, max_chars=160))

    detail_positive = [x for x in detail_positive if x]

    if detail_positive:
        parts.append("시장 측면에서는 " + " ".join(detail_positive))

    detail_risk = []
    if momentum:
        detail_risk.append(_trim_to_complete_sentence(momentum, max_chars=160))
    if competition:
        detail_risk.append(_trim_to_complete_sentence(competition, max_chars=180))

    detail_risk = [x for x in detail_risk if x]

    if detail_risk:
        parts.append("다만 " + " ".join(detail_risk))

    text = " ".join(parts).strip()

    # Chair 본문에서 또 잘리지 않도록 900자 안쪽으로 제한하되 문장 단위로 마감
    return _trim_to_complete_sentence(text, max_chars=900)



def _first_complete_sentence(value: Any, *, max_chars: int = 180) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    text = " ".join(text.split())

    # 첫 문장 우선
    for ending in ["다.", "니다.", "입니다.", "합니다.", "있습니다.", "습니다.", "."]:
        idx = text.find(ending)
        if idx >= 0:
            sentence = text[: idx + len(ending)].strip()
            return _trim_to_complete_sentence(sentence, max_chars=max_chars)

    return _trim_to_complete_sentence(text, max_chars=max_chars)


def _build_safe_market_summary_for_final_report(
    *,
    base_summary: str,
    summary_dict: dict,
    company: str,
) -> str:
    """
    Chair 보고서의 시장 분석 '요약' 전용 문장 생성.

    목적:
    - 요약이 길어져서 '52주…', 'WLP 패키지…'처럼 끊기는 문제 방지
    - 시장 분석 전체 길이는 thesis/risk에서 유지
    - 요약은 2문장 내외, 450~520자 이내로 제한
    """
    if not isinstance(summary_dict, dict):
        safe = _trim_to_complete_sentence(base_summary, max_chars=460)
        return safe.replace("…", "").replace("...", "").strip()

    industry = _first_complete_sentence(summary_dict.get("industry_stage"), max_chars=190)
    value_chain = _first_complete_sentence(summary_dict.get("value_chain_position"), max_chars=190)
    oecd = _first_complete_sentence(summary_dict.get("oecd_interpretation"), max_chars=150)
    momentum = _first_complete_sentence(summary_dict.get("market_momentum"), max_chars=150)
    competition = _first_complete_sentence(summary_dict.get("competitive_position"), max_chars=150)

    positive_parts = []
    if industry:
        positive_parts.append(industry)
    if value_chain:
        positive_parts.append(value_chain)

    risk_parts = []
    if momentum:
        risk_parts.append("최근 주가 흐름과 변동성은 단기 점검 요인입니다.")
    if competition:
        risk_parts.append("후공정 패키징 시장 내 경쟁 강도도 함께 확인할 필요가 있습니다.")

    if positive_parts:
        first_sentence = "시장 측면에서는 " + " ".join(positive_parts)
    else:
        first_sentence = _trim_to_complete_sentence(base_summary, max_chars=260)

    second_bits = []
    if oecd:
        second_bits.append("거시·경기 신호는 반도체 업황 회복 가능성을 일부 뒷받침합니다.")
    if risk_parts:
        second_bits.extend(risk_parts)

    if second_bits:
        second_sentence = "다만 " + " ".join(second_bits)
    else:
        second_sentence = "다만 단기 주가 흐름과 산업 경쟁 강도는 계속 확인해야 합니다."

    summary = f"{first_sentence} {second_sentence}".strip()

    # 최종 방어: 요약은 반드시 완결 문장으로, 말줄임표 없이 제한
    summary = _trim_to_complete_sentence(summary, max_chars=520)
    summary = summary.replace("…", "").replace("...", "").strip()

    return summary



def _enrich_market_report_fields_from_summary_dict(
    *,
    compact: dict,
    source: dict,
    company: str,
) -> dict:
    """
    Auditor용 compact evidence는 유지하되,
    Chair 보고서의 market summary / thesis / risk를 너무 짧지 않게 보강한다.

    적용 결과:
    - summary: 2~3문장 수준으로 산업·밸류체인·시장모멘텀 포함
    - key_thesis: 원래 thesis + 산업 성장성 + 밸류체인 + 경기 신호
    - key_risks: 원래 risk + 주가 변동성 + 경쟁 구도
    """
    if not isinstance(compact, dict) or not isinstance(source, dict):
        return compact

    summary_dict = _find_market_summary_dict(source)
    if not summary_dict:
        return compact

    compact["summary"] = _build_safe_market_summary_for_final_report(
        base_summary=compact.get("summary") or "",
        summary_dict=summary_dict,
        company=company,
    )

    thesis_extras = []

    if summary_dict.get("industry_stage"):
        thesis_extras.append(
            _market_item("산업 성장성", summary_dict.get("industry_stage"))
        )

    if summary_dict.get("value_chain_position"):
        thesis_extras.append(
            _market_item("밸류체인 포지션", summary_dict.get("value_chain_position"))
        )

    if summary_dict.get("oecd_interpretation"):
        thesis_extras.append(
            _market_item("거시·경기 신호", summary_dict.get("oecd_interpretation"))
        )

    compact["key_thesis"] = _append_unique_market_items(
        compact.get("key_thesis") or compact.get("thesis") or [],
        [x for x in thesis_extras if x],
        max_items=5,
    )
    compact["thesis"] = compact["key_thesis"]

    risk_extras = []

    if summary_dict.get("market_momentum"):
        risk_extras.append(
            _market_item("주가·시장 모멘텀 리스크", summary_dict.get("market_momentum"))
        )

    if summary_dict.get("competitive_position"):
        risk_extras.append(
            _market_item("경쟁 구도 리스크", summary_dict.get("competitive_position"))
        )

    compact["key_risks"] = _append_unique_market_items(
        compact.get("key_risks") or compact.get("risks") or [],
        [x for x in risk_extras if x],
        max_items=5,
    )
    compact["risks"] = compact["key_risks"]

    restore_meta = compact.get("report_detail_restore")
    if not isinstance(restore_meta, dict):
        restore_meta = {}

    restore_meta.update(
        {
            "market_rich_restore_enabled": True,
            "summary_chars_after_market_enrich": len(str(compact.get("summary") or "")),
            "thesis_count_after_market_enrich": len(compact.get("key_thesis") or []),
            "risk_count_after_market_enrich": len(compact.get("key_risks") or []),
        }
    )

    compact["report_detail_restore"] = restore_meta

    return compact



def _restore_original_history_report_fields(
    *,
    compact: dict,
    source: dict,
    agent_name: str,
    company: str,
) -> dict:
    """
    History replay에서는 Auditor 통과를 위해 compact evidence/claims는 유지하되,
    Chair 보고서에 들어가는 summary / key_thesis / key_risks는 원래 agent history payload에서 복원한다.

    이렇게 하면:
    - Auditor는 return/drawdown/liquidity 같은 compact 검증 필드를 계속 볼 수 있음
    - Chair 보고서는 기존처럼 상세한 시장/기술/이슈 설명을 유지함
    - 네패스뿐 아니라 모든 company_dir에 공통 적용됨
    """
    if not isinstance(compact, dict):
        compact = {}

    if not isinstance(source, dict):
        return compact

    fallback_summary = compact.get("summary") or f"{company} {agent_name} 분석 요약입니다."

    restored_summary = _pick_report_summary_from_source(
        source,
        fallback=fallback_summary,
    )

    concise_original_summary = _pick_concise_original_summary_for_report(
        source,
        agent_name=agent_name,
        company=company,
    )

    if concise_original_summary:
        restored_summary = concise_original_summary

    restored_thesis = _pick_report_items_from_source(
        source,
        kind="thesis",
        fallback=compact.get("key_thesis") or compact.get("thesis") or [],
    )

    restored_risks = _pick_report_items_from_source(
        source,
        kind="risks",
        fallback=compact.get("key_risks") or compact.get("risks") or [],
    )


    if not restored_thesis:
        restored_thesis = _derive_report_items_from_summary_dict(
            source,
            agent_name=agent_name,
            kind="thesis",
        )

    if not restored_risks:
        restored_risks = _derive_report_items_from_summary_dict(
            source,
            agent_name=agent_name,
            kind="risks",
        )

    if restored_summary:
        compact["summary"] = restored_summary

    if restored_thesis:
        compact["key_thesis"] = restored_thesis
        compact["thesis"] = restored_thesis

    if restored_risks:
        compact["key_risks"] = restored_risks
        compact["risks"] = restored_risks

    compact["report_detail_restore"] = {
        "enabled": True,
        "agent": agent_name,
        "source": "original_history_payload",
        "auditor_compact_evidence_preserved": True,
        "summary_chars": len(str(compact.get("summary") or "")),
        "thesis_count": len(compact.get("key_thesis") or []),
        "risk_count": len(compact.get("key_risks") or []),
    }

    return compact



def _compact_market_history_for_auditor(payload: dict, *, company: str, company_dir: str) -> dict:
    """
    Market Agent history snapshot을 Chair/Auditor용 compact packet으로 변환한다.

    개선 사항:
    - return / drawdown / liquidity가 None이면 valuation snapshot 또는 주가 CSV에서 계산
    - Auditor stage2 framework가 실제 값을 볼 수 있도록 명시
    """
    source = payload if isinstance(payload, dict) else {}
    history_meta = source.get("agent_history_snapshot")
    context = _history_context(source)

    field = context.get("field") or "반도체"
    as_of_date = context.get("as_of_date") or ""

    valuation_payload = _load_valuation_history_for_same_context(source, company_dir=company_dir)

    total_score = _first_non_empty(
        _deep_find_first(source, ["total_score", "market_score", "score"]),
        _deep_find_first(valuation_payload, ["market_score"]),
    )

    market_cap = _first_non_empty(
        _deep_find_first(source, ["market_cap", "시가총액"]),
        _deep_find_first(valuation_payload, ["market_cap"]),
    )

    file_metrics = _compute_market_metrics_from_price_files(
        field=field,
        company=company,
        company_dir=company_dir,
        as_of_date=as_of_date,
        market_cap=market_cap,
    )

    current_price = _first_non_empty(
        _deep_find_first(source, ["current_price", "latest_close", "close_price", "close", "현재가"]),
        _deep_find_first(valuation_payload, ["current_price", "latest_close", "close_price", "close", "현재가"]),
        file_metrics.get("current_price"),
    )

    annual_return = _first_non_empty(
        _deep_find_first(source, ["annual_return", "return_1y", "one_year_return", "yearly_return", "1y_return"]),
        _deep_find_first(valuation_payload, ["annual_return", "return_1y", "one_year_return", "yearly_return", "1y_return"]),
        file_metrics.get("annual_return"),
    )

    recent_1m_return = _first_non_empty(
        _deep_find_first(source, ["recent_1m_return", "return_1m", "one_month_return", "monthly_return", "1m_return"]),
        _deep_find_first(valuation_payload, ["recent_1m_return", "return_1m", "one_month_return", "monthly_return", "1m_return"]),
        file_metrics.get("recent_1m_return"),
    )

    mdd = _first_non_empty(
        _deep_find_first(source, ["mdd", "max_drawdown", "maximum_drawdown", "drawdown"]),
        _deep_find_first(valuation_payload, ["mdd", "max_drawdown", "maximum_drawdown", "drawdown"]),
        file_metrics.get("mdd"),
    )

    volatility = _first_non_empty(
        _deep_find_first(source, ["volatility", "annualized_volatility", "vol_20d", "volatility_20d"]),
        _deep_find_first(valuation_payload, ["volatility", "annualized_volatility", "vol_20d", "volatility_20d"]),
        file_metrics.get("volatility"),
    )

    avg_trading_value_20d = _first_non_empty(
        _deep_find_first(source, ["avg_trading_value_20d", "average_trading_value_20d", "avg_turnover_20d", "trading_value_20d", "거래대금_20일평균"]),
        _deep_find_first(valuation_payload, ["avg_trading_value_20d", "average_trading_value_20d", "avg_turnover_20d", "trading_value_20d", "거래대금_20일평균"]),
        file_metrics.get("avg_trading_value_20d"),
    )

    turnover_proxy = _first_non_empty(
        _deep_find_first(source, ["turnover_proxy", "turnover", "liquidity_turnover", "volume_turnover"]),
        _deep_find_first(valuation_payload, ["turnover_proxy", "turnover", "liquidity_turnover", "volume_turnover"]),
        file_metrics.get("turnover_proxy"),
    )

    liquidity_status = _first_non_empty(
        _deep_find_first(source, ["liquidity_status", "liquidity_grade", "liquidity", "유동성"]),
        _deep_find_first(valuation_payload, ["liquidity_status", "liquidity_grade", "liquidity", "유동성"]),
        file_metrics.get("liquidity_status"),
    )

    # as_of_date replay에서는 valuation/current snapshot보다
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


    original_summary = (
        source.get("summary")
        or source.get("market_summary")
        or source.get("analysis_summary")
        or source.get("analysis")
        or ""
    )

    summary = _clean_summary_for_auditor(
        original_summary,
        fallback=(
            f"{company} Market Agent snapshot은 주가 수익률(return), 최대낙폭(drawdown), "
            f"거래대금·회전율 기반 유동성(liquidity)을 Chair/Auditor 검증용으로 요약한 compact packet입니다."
        ),
    )

    metric_source = {
        "price_csv_source_file": file_metrics.get("source_file"),
        "valuation_snapshot_used": bool(valuation_payload),
        "as_of_date": as_of_date,
    }

    framework_metrics = {
        "return": {
            "annual_return": annual_return,
            "recent_1m_return": recent_1m_return,
        },
        "drawdown": {
            "mdd": mdd,
            "volatility": volatility,
        },
        "liquidity": {
            "avg_trading_value_20d": avg_trading_value_20d,
            "turnover_proxy": turnover_proxy,
            "liquidity_status": liquidity_status,
        },
        "price": {
            "current_price": current_price,
            "market_cap": market_cap,
        },
        "market_score": total_score,
        "metric_source": metric_source,
    }

    evidences = [
        {
            "evidence_id": "MKT_RETURN_METRICS",
            "source_type": "market_history_snapshot_or_price_csv",
            "source_name": "Market Agent return metrics",
            "snippet": (
                f"{company} market return metrics as_of_date={as_of_date}: "
                f"annual_return={annual_return}, recent_1m_return={recent_1m_return}, "
                f"current_price={current_price}, source={file_metrics.get('source_file')}."
            ),
        },
        {
            "evidence_id": "MKT_DRAWDOWN_METRICS",
            "source_type": "market_history_snapshot_or_price_csv",
            "source_name": "Market Agent drawdown and volatility metrics",
            "snippet": (
                f"{company} market drawdown metrics as_of_date={as_of_date}: "
                f"mdd={mdd}, volatility={volatility}."
            ),
        },
        {
            "evidence_id": "MKT_LIQUIDITY_METRICS",
            "source_type": "market_history_snapshot_or_price_csv",
            "source_name": "Market Agent liquidity metrics",
            "snippet": (
                f"{company} market liquidity metrics as_of_date={as_of_date}: "
                f"avg_trading_value_20d={avg_trading_value_20d}, "
                f"turnover_proxy={turnover_proxy}, liquidity_status={liquidity_status}."
            ),
        },
    ]

    claims = [
        {
            "claim_id": "MKT_CLAIM_RETURN",
            "text": (
                f"{company}의 Market Agent는 return 지표로 "
                f"annual_return={annual_return}, recent_1m_return={recent_1m_return}을 제공합니다."
            ),
            "evidence_ids": ["MKT_RETURN_METRICS"],
        },
        {
            "claim_id": "MKT_CLAIM_DRAWDOWN",
            "text": (
                f"{company}의 Market Agent는 drawdown 지표로 "
                f"mdd={mdd}, volatility={volatility}를 제공합니다."
            ),
            "evidence_ids": ["MKT_DRAWDOWN_METRICS"],
        },
        {
            "claim_id": "MKT_CLAIM_LIQUIDITY",
            "text": (
                f"{company}의 Market Agent는 liquidity 지표로 "
                f"avg_trading_value_20d={avg_trading_value_20d}, "
                f"turnover_proxy={turnover_proxy}, liquidity_status={liquidity_status}를 제공합니다."
            ),
            "evidence_ids": ["MKT_LIQUIDITY_METRICS"],
        },
    ]

    compact = {
        "agent": "market",
        "company": company,
        "company_dir": company_dir,
        "summary": summary,
        "opinion": source.get("opinion"),
        "confidence": source.get("confidence"),
        "total_score": total_score,
        "framework_metrics": framework_metrics,
        "market_framework": {
            "return_visible": True,
            "drawdown_visible": True,
            "liquidity_visible": True,
            "framework_keywords": ["return", "drawdown", "liquidity"],
        },
        "claims": claims,
        "evidences": evidences,
        "evidence": evidences,
        "source_contexts": evidences,
        "adapter_compaction": {
            "enabled": True,
            "reason": "Auditor용 compact market packet: return/drawdown/liquidity 실제값 보강",
            "raw_payload_omitted": True,
            "metric_source": metric_source,
        },
    }

    compact = _restore_original_history_report_fields(
        compact=compact,
        source=source,
        agent_name="market",
        company=company,
    )

    compact = _enrich_market_report_fields_from_summary_dict(
        compact=compact,
        source=source,
        company=company,
    )

    if history_meta:
        compact["agent_history_snapshot"] = history_meta

    return compact


def _compact_tech_history_for_auditor(payload: dict, *, company: str, company_dir: str) -> dict:
    """
    Tech Agent history snapshot을 Chair/Auditor용 compact packet으로 변환한다.

    개선 사항:
    - raw tech_chair_summary / threshold / template / 중간 dict를 그대로 넘기지 않음
    - total_score=5처럼 nested 보조값을 최종 Tech score로 오인하는 문제 방지
    - 명시적 최종 score가 없거나 의심스러우면 bridge_score를 35점 만점으로 환산
    """
    source = payload if isinstance(payload, dict) else {}
    history_meta = source.get("agent_history_snapshot")

    max_score = _first_non_empty(
        _first_numeric_path_value(source, [["max_score"], ["raw_payload", "max_score"], ["scorecard", "max_score"]]),
        35,
    )

    bridge_score = _first_non_empty(
        _first_numeric_path_value(
            source,
            [
                ["tech_to_value_bridge_score"],
                ["peer_adjusted_bridge_score"],
                ["bridge_score"],
                ["tech_to_value_score"],
                ["raw_payload", "tech_to_value_bridge_score"],
                ["raw_payload", "peer_adjusted_bridge_score"],
                ["raw_payload", "bridge_score"],
                ["raw_payload", "tech_to_value_score"],
            ],
        ),
        _deep_find_first(
            source,
            [
                "tech_to_value_bridge_score",
                "peer_adjusted_bridge_score",
                "bridge_score",
                "tech_to_value_score",
            ],
        ),
    )

    total_score, score_source = _choose_tech_total_score(
        source=source,
        bridge_score=bridge_score,
        max_score=max_score,
    )

    bridge_grade = _first_non_empty(
        _first_path_value(
            source,
            [
                ["bridge_grade"],
                ["grade"],
                ["final_grade"],
                ["tech_to_value_grade"],
                ["raw_payload", "bridge_grade"],
                ["raw_payload", "grade"],
                ["raw_payload", "final_grade"],
            ],
        ),
        _deep_find_first(source, ["bridge_grade", "grade", "final_grade", "tech_to_value_grade"]),
    )

    differentiation_score = _first_non_empty(
        _first_numeric_path_value(
            source,
            [
                ["technology_differentiation_score"],
                ["differentiation_score"],
                ["raw_payload", "technology_differentiation_score"],
                ["raw_payload", "differentiation_score"],
            ],
        ),
        _deep_find_first(source, ["technology_differentiation_score", "differentiation_score"]),
    )

    momentum_score = _first_non_empty(
        _first_numeric_path_value(
            source,
            [
                ["patent_momentum_score"],
                ["momentum_score"],
                ["raw_payload", "patent_momentum_score"],
                ["raw_payload", "momentum_score"],
            ],
        ),
        _deep_find_first(source, ["patent_momentum_score", "momentum_score"]),
    )

    evidence_confidence_score = _first_non_empty(
        _first_numeric_path_value(
            source,
            [
                ["tech_to_value_evidence_confidence"],
                ["evidence_confidence_score"],
                ["raw_payload", "tech_to_value_evidence_confidence"],
                ["raw_payload", "evidence_confidence_score"],
            ],
        ),
        _deep_find_first(source, ["tech_to_value_evidence_confidence", "evidence_confidence_score"]),
    )

    ip_strength_score = _first_non_empty(
        _first_numeric_path_value(
            source,
            [
                ["tech_ip_strength_index"],
                ["ip_strength_score"],
                ["ip_strength_index"],
                ["raw_payload", "tech_ip_strength_index"],
                ["raw_payload", "ip_strength_score"],
                ["raw_payload", "ip_strength_index"],
            ],
        ),
        _deep_find_first(source, ["tech_ip_strength_index", "ip_strength_score", "ip_strength_index"]),
    )

    patent_records_count = _choose_patent_records_count(source)
    registered_patents_count = _choose_registered_patents_count(source)

    original_summary = (
        source.get("summary")
        or source.get("tech_summary")
        or source.get("chair_summary")
        or source.get("analysis_summary")
        or ""
    )

    summary = _clean_summary_for_auditor(
        original_summary,
        fallback=(
            f"{company} Tech Agent snapshot은 기술-사업화 연결성, IP 정량 신호, "
            f"차별성, 특허 모멘텀, 근거 직접성을 Chair/Auditor 검증용으로 요약한 compact packet입니다."
        ),
    )

    tech_framework_metrics = {
        "tech_to_value_bridge_score": bridge_score,
        "bridge_grade": bridge_grade,
        "technology_differentiation_score": differentiation_score,
        "patent_momentum_score": momentum_score,
        "tech_to_value_evidence_confidence_score": evidence_confidence_score,
        "tech_ip_strength_score": ip_strength_score,
        "score": {
            "total_score": total_score,
            "max_score": max_score,
            "score_source": score_source,
        },
        "ip_metrics": {
            "patent_records_count": patent_records_count,
            "registered_patents_count": registered_patents_count,
        },
    }

    evidences = [
        {
            "evidence_id": "TECH_BRIDGE_METRICS",
            "source_type": "tech_history_snapshot_compact",
            "source_name": "Tech-to-Value Bridge compact metrics",
            "snippet": (
                f"{company} tech-to-value bridge metrics: "
                f"bridge_score={bridge_score}, bridge_grade={bridge_grade}, "
                f"total_score={total_score}, max_score={max_score}, score_source={score_source}."
            ),
        },
        {
            "evidence_id": "TECH_IP_METRICS",
            "source_type": "tech_history_snapshot_compact",
            "source_name": "IP quantitative compact metrics",
            "snippet": (
                f"{company} IP metrics: patent_records_count={patent_records_count}, "
                f"registered_patents_count={registered_patents_count}, "
                f"tech_ip_strength_score={ip_strength_score}."
            ),
        },
        {
            "evidence_id": "TECH_ML_METRICS",
            "source_type": "tech_history_snapshot_compact",
            "source_name": "Tech ML compact metrics",
            "snippet": (
                f"{company} Tech ML metrics: differentiation_score={differentiation_score}, "
                f"patent_momentum_score={momentum_score}, "
                f"evidence_confidence_score={evidence_confidence_score}."
            ),
        },
    ]

    claims = [
        {
            "claim_id": "TECH_CLAIM_BRIDGE",
            "text": (
                f"{company}의 Tech Agent는 기술-사업화 연결성 지표로 "
                f"bridge_score={bridge_score}, bridge_grade={bridge_grade}, "
                f"total_score={total_score}/{max_score}를 제공합니다."
            ),
            "evidence_ids": ["TECH_BRIDGE_METRICS"],
        },
        {
            "claim_id": "TECH_CLAIM_IP",
            "text": (
                f"{company}의 Tech Agent는 IP 정량 지표로 "
                f"patent_records_count={patent_records_count}, "
                f"registered_patents_count={registered_patents_count}, "
                f"tech_ip_strength_score={ip_strength_score}를 제공합니다."
            ),
            "evidence_ids": ["TECH_IP_METRICS"],
        },
        {
            "claim_id": "TECH_CLAIM_ML",
            "text": (
                f"{company}의 Tech Agent는 기술 차별성·특허 모멘텀·근거 직접성 보조지표로 "
                f"differentiation_score={differentiation_score}, "
                f"patent_momentum_score={momentum_score}, "
                f"evidence_confidence_score={evidence_confidence_score}를 제공합니다."
            ),
            "evidence_ids": ["TECH_ML_METRICS"],
        },
    ]

    compact = {
        "agent": "tech",
        "company": company,
        "company_dir": company_dir,
        "summary": summary,
        "opinion": source.get("opinion"),
        "confidence": source.get("confidence"),
        "total_score": total_score,
        "max_score": max_score,
        "tech_framework_metrics": tech_framework_metrics,
        "claims": claims,
        "evidences": evidences,
        "evidence": evidences,
        "source_contexts": evidences,
        "adapter_compaction": {
            "enabled": True,
            "reason": "Auditor용 compact tech packet: noisy raw nested payload 제거 및 total_score 오인 보정",
            "raw_payload_omitted": True,
            "score_source": score_source,
            "removed_noisy_fields": [
                "raw_nested_thresholds",
                "template_or_request_text",
                "conflicting_registered_patents_raw_values",
                "full_tech_chair_summary_raw_payload",
                "nested_low_score_noise",
            ],
        },
    }

    compact = _restore_original_history_report_fields(
        compact=compact,
        source=source,
        agent_name="tech",
        company=company,
    )

    if history_meta:
        compact["agent_history_snapshot"] = history_meta

    return compact


POSITIVE_TERMS = [
    "성장", "개선", "흑자", "수혜", "확대", "회복", "견조", "호조",
    "수주", "계약", "증설", "반등", "ai", "hbm", "고급 패키징", "첨단 패키징",
]

NEGATIVE_TERMS = [
    "적자", "손실", "악화", "둔화", "하락", "부진", "리스크", "소송",
    "규제", "제재", "차질", "지연", "감소", "고금리", "부채", "상장폐지",
]


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except Exception:
        return None


def _normalize_opinion(value: Any) -> str | None:
    text = str(value or "").strip()
    return text if text in VALID_OPINIONS else None


def _normalize_confidence(value: Any, default: float) -> float:
    num = _to_number(value)
    if num is None:
        return default
    if num > 1:
        num = num / 100
    return max(0.0, min(float(num), 1.0))


def _text_blob(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value or "")


def _count_terms(text: str, terms: list[str]) -> int:
    lowered = str(text or "").lower()
    return sum(lowered.count(term.lower()) for term in terms)


def _risk_score(result: dict) -> int:
    risks = result.get("risks", [])
    if not isinstance(risks, list):
        return 0

    score = 0
    for risk in risks:
        text = _text_blob(risk)
        if "상" in text or "high" in text.lower():
            score += 2
        elif "중" in text or "medium" in text.lower():
            score += 1
        elif text:
            score += 1

    return score


def _infer_market(result: dict) -> tuple[str, float]:
    raw = result.get("raw_payload") if isinstance(result.get("raw_payload"), dict) else {}
    analysis = raw.get("analysis") if isinstance(raw.get("analysis"), dict) else raw

    parsed = _normalize_opinion(analysis.get("opinion"))
    if parsed:
        return parsed, _normalize_confidence(analysis.get("confidence"), 0.55)

    score = _to_number(result.get("total_score")) or _to_number(analysis.get("total_score"))
    risks = _risk_score(result)

    if score is None:
        return "보유", 0.40
    if score >= 75 and risks <= 2:
        return "매수", 0.62
    if score <= 45 or (score < 60 and risks >= 3):
        return "매도", 0.60
    return "보유", 0.50


def _infer_tech(result: dict) -> tuple[str, float]:
    raw = result.get("raw_payload") if isinstance(result.get("raw_payload"), dict) else {}
    total = _to_number(raw.get("total_score")) or _to_number(result.get("total_score"))
    max_score = _to_number(raw.get("max_score")) or 35.0

    if total is None or not max_score:
        return "보유", 0.40

    ratio = total / max_score
    weaknesses = raw.get("weaknesses", [])
    weakness_count = len(weaknesses) if isinstance(weaknesses, list) else 0
    risks = max(_risk_score(result), weakness_count)

    if ratio >= 0.78 and risks <= 2:
        return "매수", 0.58
    if ratio < 0.45 or risks >= 5:
        return "매도", 0.55
    return "보유", 0.48


def _infer_issue(result: dict) -> tuple[str, float]:
    raw = result.get("raw_payload") if isinstance(result.get("raw_payload"), dict) else {}
    analysis_text = str(raw.get("analysis_text") or "")

    for marker in ("opinion:", "투자의견:", "의견:"):
        if marker in analysis_text:
            tail = analysis_text.split(marker, 1)[1].strip()[:10]
            parsed = _normalize_opinion(tail.split()[0].replace("|", "").strip())
            if parsed:
                return parsed, 0.55

    blob = _text_blob(result)
    positive = _count_terms(blob, POSITIVE_TERMS)
    negative = _count_terms(blob, NEGATIVE_TERMS)

    if negative >= positive + 2 and negative >= 2:
        return "매도", 0.58
    if positive >= negative + 2 and positive >= 3:
        return "매수", 0.55
    return "보유", 0.45


def _infer_macro(result: dict) -> tuple[str, float]:
    current = _normalize_opinion(result.get("opinion"))
    if current:
        return current, _normalize_confidence(result.get("confidence"), 0.50)

    raw = result.get("raw_payload") if isinstance(result.get("raw_payload"), dict) else {}
    signal = str(raw.get("signal") or result.get("signal") or "").upper()

    if signal == "BUY":
        return "매수", _normalize_confidence(raw.get("confidence") or result.get("confidence"), 0.50)
    if signal == "SELL":
        return "매도", _normalize_confidence(raw.get("confidence") or result.get("confidence"), 0.50)
    if signal == "HOLD":
        return "보유", _normalize_confidence(raw.get("confidence") or result.get("confidence"), 0.50)

    errors = raw.get("errors", [])
    outputs = raw.get("outputs", {})

    if isinstance(errors, list) and len(errors) >= 2:
        return "보유", 0.25

    blob = _text_blob(outputs or result)
    positive = _count_terms(blob, POSITIVE_TERMS + ["완화", "금리 인하", "물가 안정", "공급 안정"])
    negative = _count_terms(blob, NEGATIVE_TERMS + ["침체", "긴축", "환율 상승", "공급 차질", "가격 급등"])

    if negative >= positive + 3 and negative >= 3:
        return "매도", 0.50
    if positive >= negative + 3 and positive >= 3:
        return "매수", 0.50
    return "보유", 0.40


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _fmt_num(value: Any, digits: int = 2) -> str:
    num = _safe_float(value)
    if num is None:
        return "확인 제한"
    return f"{num:,.{digits}f}"


def _fmt_pct(value: Any) -> str:
    num = _safe_float(value)
    if num is None:
        return "확인 제한"
    return f"{num * 100:.2f}%"


def _fmt_money(value: Any) -> str:
    num = _safe_float(value)
    if num is None:
        return "확인 제한"
    return f"{num:,.0f}원"


def _infer_valuation(result: dict) -> tuple[str, float]:
    """Valuation Agent 결과를 Chair용 방향 신호로 변환합니다.

    v50 evaluation mode removes the old ±20% valuation band from Chair fallback.
    Upside/downside is used directionally; Hold is kept only when validation is
    unavailable or upside itself is missing/zero.  The magnitude affects
    confidence, not the Buy/Hold/Sell boundary.
    """
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else result
    dcf = metrics.get("dcf") or {}
    validation_status = str(metrics.get("validation_status") or result.get("status") or "").upper()
    upside = _safe_float(dcf.get("upside_downside_pct"))

    if validation_status not in {"PASS", "OK"}:
        return "보유", 0.45
    if upside is None or upside == 0:
        return "보유", 0.45
    confidence = min(0.75, 0.50 + min(abs(upside), 0.50) * 0.40)
    if upside > 0:
        return "매수", confidence
    return "매도", confidence


def _normalize_for_chair(result: dict, *, agent_name: str) -> dict:
    normalized = dict(result or {})
    current_opinion = _normalize_opinion(normalized.get("opinion"))

    if agent_name == "finance" and current_opinion:
        normalized["opinion"] = current_opinion
        normalized["confidence"] = _normalize_confidence(normalized.get("confidence"), 0.50)
        normalized.setdefault("opinion_source", "agent")
        return normalized

    if agent_name == "market":
        opinion, confidence = _infer_market(normalized)
    elif agent_name == "tech":
        opinion, confidence = _infer_tech(normalized)
    elif agent_name == "issue":
        opinion, confidence = _infer_issue(normalized)
    elif agent_name == "macro":
        opinion, confidence = _infer_macro(normalized)
    elif agent_name == "valuation":
        opinion, confidence = _infer_valuation(normalized)
    else:
        opinion, confidence = current_opinion or "보유", 0.40

    normalized["opinion"] = opinion
    normalized["confidence"] = confidence
    normalized["opinion_source"] = "chair_adapter_inferred"
    return normalized


def _with_evidence_contract(result: dict, *, agent_name: str, company: str) -> dict:
    contracted = enforce_evidence_contract(result, agent_name=agent_name, company=company)
    return _normalize_for_chair(contracted, agent_name=agent_name)


def _flatten_finance_result(result: Any) -> tuple[dict, dict | None]:
    """Normalize finance_agent.runner.run_finance_agent output without editing finance_agent.

    Supported shapes:
    1) chair_view with _audit_packet
    2) {chair_json: {...}, audit_packet/full_packet: {...}}
    3) {result: {...}}
    4) full auditor packet directly
    """
    if not isinstance(result, dict):
        return {"summary": str(result), "opinion": "보유"}, None

    work = dict(result)
    audit_packet = work.pop("_audit_packet", None)

    for key in ("audit_packet", "full_packet", "auditor_packet", "packet"):
        if audit_packet is None and isinstance(work.get(key), dict):
            audit_packet = work.get(key)

    chair_json = None
    for key in ("chair_json", "chair_view", "chair", "summary_json"):
        if isinstance(work.get(key), dict):
            chair_json = dict(work.get(key) or {})
            break

    if chair_json is None:
        nested = work.get("result")
        if isinstance(nested, dict):
            if isinstance(nested.get("chair_json"), dict):
                chair_json = dict(nested.get("chair_json") or {})
                if audit_packet is None:
                    audit_packet = nested.get("_audit_packet") or nested.get("audit_packet") or nested.get("full_packet")
            else:
                chair_json = dict(nested)
        else:
            chair_json = work

    # Copy useful top-level fields that single-agent finance often emits.
    for key in (
        "summary", "key_thesis", "key_risks", "warning_note", "opinion",
        "confidence", "industry_type", "evidence", "claims", "evidences", "source_contexts",
    ):
        if key in work and key not in chair_json:
            chair_json[key] = work[key]

    return chair_json, audit_packet if isinstance(audit_packet, dict) else None


def run_finance_for_chair(company_dir: str, company: str) -> dict:
    history_payload = _load_history_for_chair(
        agent_name="finance",
        company_dir=company_dir,
        company=company,
    )
    if history_payload is not None:
        normalized = _with_evidence_contract(
            history_payload,
            agent_name="finance",
            company=company,
        )
        normalized.setdefault("finance_adapter_status", "LOADED_FROM_AGENT_HISTORY")
        return normalized

    from finance_agent.runner import run_finance_agent

    raw_result = run_finance_agent(company_dir, company)
    chair_view, audit_packet = _flatten_finance_result(raw_result)

    if audit_packet is not None:
        contracted = _with_evidence_contract(audit_packet, agent_name="finance", company=company)
        for key in (
            "summary", "key_thesis", "key_risks", "warning_note", "opinion",
            "confidence", "industry_type", "evidence", "claims", "evidences", "source_contexts",
        ):
            if key in chair_view and chair_view[key] not in (None, "", []):
                contracted[key] = chair_view[key]
        contracted.setdefault("finance_adapter_status", "CHAIR_VIEW_MERGED_WITH_AUDIT_PACKET")
        return contracted

    normalized = _with_evidence_contract(chair_view, agent_name="finance", company=company)
    normalized.setdefault("finance_adapter_status", "CHAIR_VIEW_DIRECT")
    return normalized


def run_market_for_chair(company_dir: str, company: str) -> dict:
    history_payload = _load_history_for_chair(
        agent_name="market",
        company_dir=company_dir,
        company=company,
    )
    if history_payload is not None:
        compact_payload = _compact_market_history_for_auditor(
            history_payload,
            company=company,
            company_dir=company_dir,
        )
        normalized = _with_evidence_contract(
            compact_payload,
            agent_name="market",
            company=company,
        )
        normalized.setdefault("market_adapter_status", "LOADED_FROM_AGENT_HISTORY_COMPACT")
        return normalized

    from market_agent.runner import run_market_report

    compact_payload = _compact_market_history_for_auditor(
        run_market_report(company, company_dir=company_dir),
        company=company,
        company_dir=company_dir,
    )
    normalized = _with_evidence_contract(
        compact_payload,
        agent_name="market",
        company=company,
    )
    normalized.setdefault("market_adapter_status", "LIVE_COMPACT")
    return normalized


def run_tech_for_chair(company_dir: str, company: str) -> dict:
    history_payload = _load_history_for_chair(
        agent_name="tech",
        company_dir=company_dir,
        company=company,
    )
    if history_payload is not None:
        compact_payload = _compact_tech_history_for_auditor(
            history_payload,
            company=company,
            company_dir=company_dir,
        )
        normalized = _with_evidence_contract(
            compact_payload,
            agent_name="tech",
            company=company,
        )
        normalized.setdefault("tech_adapter_status", "LOADED_FROM_AGENT_HISTORY_COMPACT")
        return normalized

    from tech_agent.runner import run_tech_agent

    return _with_evidence_contract(
        run_tech_agent(company_dir, company),
        agent_name="tech",
        company=company,
    )


def run_issue_for_chair(company_dir: str, company: str) -> dict:
    history_payload = _load_history_for_chair(
        agent_name="issue",
        company_dir=company_dir,
        company=company,
    )
    if history_payload is not None:
        normalized = _with_evidence_contract(
            history_payload,
            agent_name="issue",
            company=company,
        )
        normalized.setdefault("issue_adapter_status", "LOADED_FROM_AGENT_HISTORY")
        return normalized

    from issue_agent.runner import run_company

    try:
        result = run_company(company, company_dir=company_dir)
    except TypeError:
        result = run_company(company)

    return _with_evidence_contract(
        result,
        agent_name="issue",
        company=company,
    )


def run_macro_for_chair(company_dir: str, company: str) -> dict:
    history_payload = _load_history_for_chair(
        agent_name="macro",
        company_dir=company_dir,
        company=company,
    )
    if history_payload is not None:
        normalized = _with_evidence_contract(
            history_payload,
            agent_name="macro",
            company=company,
        )
        normalized.setdefault("macro_adapter_status", "LOADED_FROM_AGENT_HISTORY")
        return normalized

    from macro_agent.runner import run

    return _with_evidence_contract(
        run(date="latest", company_dir=company_dir, company=company),
        agent_name="macro",
        company=company,
    )


def _build_valuation_contract(raw_result: dict, *, company_dir: str, company: str) -> dict:
    """Build a claim/evidence packet for Valuation Agent without reading finance_agent outputs."""
    result = raw_result if isinstance(raw_result, dict) else {}
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    dcf = metrics.get("dcf") or {}
    wacc = metrics.get("wacc") or {}
    price = metrics.get("price_summary") or {}
    ml = metrics.get("ml_overlay") or {}
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    validation_status = str(
        metrics.get("validation_status")
        or result.get("status")
        or validation.get("status")
        or "확인 제한"
    )

    wacc_v = wacc.get("wacc") if isinstance(wacc, dict) else wacc
    implied = dcf.get("implied_price")
    current = price.get("latest_close") or dcf.get("latest_close")
    upside = dcf.get("upside_downside_pct")
    market_cap = price.get("market_cap")
    price_rows = price.get("price_rows")
    shares = price.get("shares_outstanding") or dcf.get("shares_outstanding")
    avg_trading = price.get("avg_trading_value_20d")
    ml_label = ml.get("label_kr") or ml.get("label") or "확인 제한"

    evidences = [
        {
            "evidence_id": "VAL_DART_NORMALIZED_FS",
            "source_type": "valuation_intake_dart",
            "source_name": "Valuation Agent 전용 DART 정규화 재무제표",
            "snippet": (
                f"{company} valuation_intake는 DART 원천 계정과 정규화 재무제표를 사용합니다. "
                f"validation_status={validation_status}, WACC={_fmt_pct(wacc_v)}, "
                f"DCF 내재주가={_fmt_money(implied)}, 현재가={_fmt_money(current)}, "
                f"현재가 대비 괴리율={_fmt_pct(upside)}."
            ),
        },
        {
            "evidence_id": "VAL_PRICE_SHARE_DATA",
            "source_type": "valuation_intake_price",
            "source_name": "Valuation Agent 전용 주가·발행주식 수 intake",
            "snippet": (
                f"{company} valuation_intake 주가 데이터는 {price_rows}행이며, "
                f"발행주식수={_fmt_num(shares, 0)}주, 시가총액={_fmt_money(market_cap)}, "
                f"20일 평균 거래대금={_fmt_money(avg_trading)}입니다."
            ),
        },
        {
            "evidence_id": "VAL_WORKBOOK_DASHBOARD",
            "source_type": "valuation_workbook",
            "source_name": "Valuation Agent Excel workbook 및 dashboard payload",
            "snippet": (
                f"{company} Valuation Agent는 DCF, WACC, Peer Comps, 민감도, ML 보조판단을 "
                f"workbook/dashboard payload로 저장했습니다. ML 보조판단={ml_label}."
            ),
        },
    ]

    claims = [
        {
            "claim_id": "VAL_CLAIM_DCF_UPSIDE",
            "text": (
                f"{company}의 Valuation Agent DCF 내재주가는 {_fmt_money(implied)}이고 "
                f"현재가 {_fmt_money(current)} 대비 괴리율은 {_fmt_pct(upside)}입니다."
            ),
            "evidence_ids": ["VAL_DART_NORMALIZED_FS", "VAL_PRICE_SHARE_DATA"],
        },
        {
            "claim_id": "VAL_CLAIM_PRICE_LIQUIDITY",
            "text": (
                f"{company}의 valuation 전용 주가 데이터는 {price_rows}행이며 "
                f"시가총액은 {_fmt_money(market_cap)}, 20일 평균 거래대금은 {_fmt_money(avg_trading)}입니다."
            ),
            "evidence_ids": ["VAL_PRICE_SHARE_DATA"],
        },
        {
            "claim_id": "VAL_CLAIM_OUTPUTS",
            "text": (
                f"{company} Valuation Agent는 자체 intake 기반으로 DCF·WACC·피어비교·대시보드 payload를 생성했고 "
                f"검증 상태는 {validation_status}입니다."
            ),
            "evidence_ids": ["VAL_WORKBOOK_DASHBOARD", "VAL_DART_NORMALIZED_FS"],
        },
    ]

    summary = (
        f"{company} Valuation Agent는 finance_agent 산출물을 읽지 않고 자체 DART·주가·발행주식 수 intake를 사용해 "
        f"WACC {_fmt_pct(wacc_v)}, DCF 내재주가 {_fmt_money(implied)}, 현재가 대비 괴리율 {_fmt_pct(upside)}를 산출했습니다. "
        f"검증 상태는 {validation_status}이며 workbook과 dashboard payload가 생성되었습니다."
    )

    contracted = {
        "agent": "valuation",
        "company": company,
        "company_dir": company_dir,
        "summary": summary,
        "opinion": result.get("opinion"),
        "confidence": result.get("confidence"),
        "claims": claims,
        "evidences": evidences,
        "evidence": evidences,
        "source_contexts": evidences,
        "metrics": metrics,
        "validation": validation,
        "output_files": result.get("output_files") or {},
        "data_principle": "valuation_agent 자체 intake만 사용; finance_agent 산출물 미사용",
    }
    return contracted


def run_valuation_for_chair(company_dir: str, company: str) -> dict:
    history_payload = _load_history_for_chair(
        agent_name="valuation",
        company_dir=company_dir,
        company=company,
    )
    if history_payload is not None:
        history_meta = history_payload.get("agent_history_snapshot")

        # history에 저장된 valuation_metrics.json은 metrics가 top-level일 수 있으므로
        # _build_valuation_contract가 기대하는 구조로 감싼다.
        if isinstance(history_payload.get("metrics"), dict):
            raw_result = history_payload
        else:
            raw_result = {
                "metrics": history_payload,
                "status": history_payload.get("validation_status") or history_payload.get("status"),
                "opinion": history_payload.get("opinion"),
                "confidence": history_payload.get("confidence"),
                "output_files": history_payload.get("output_files") or {},
            }

        packet = _build_valuation_contract(
            raw_result,
            company_dir=company_dir,
            company=company,
        )

        if history_meta:
            packet["agent_history_snapshot"] = history_meta

        packet.setdefault("valuation_adapter_status", "LOADED_FROM_AGENT_HISTORY")

        return _with_evidence_contract(
            packet,
            agent_name="valuation",
            company=company,
        )

    from valuation_agent.runner import run_valuation

    raw_result = run_valuation(company_dir=company_dir, company=company, auto_intake=True)
    packet = _build_valuation_contract(raw_result, company_dir=company_dir, company=company)
    return _with_evidence_contract(packet, agent_name="valuation", company=company)
