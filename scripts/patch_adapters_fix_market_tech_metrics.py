from pathlib import Path
import re

path = Path(r".\src\chair_agent\adapters.py")
text = path.read_text(encoding="utf-8")

# ---------------------------------------------------------------------
# 1) imports 보강
# ---------------------------------------------------------------------
old_imports = """import json
import os
from typing import Any
"""

new_imports = """import csv
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any
"""

if "import csv" not in text:
    if old_imports not in text:
        raise RuntimeError("import block not found. adapters.py 상단 import 구조를 확인하세요.")
    text = text.replace(old_imports, new_imports, 1)


# ---------------------------------------------------------------------
# 2) helper 추가
# ---------------------------------------------------------------------
helper_marker = "def _compute_market_metrics_from_price_files"
insert_before = "def _compact_market_history_for_auditor"

helper_code = r'''
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
    field = context.get("field") or "반도체"
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


'''

if helper_marker not in text:
    if insert_before not in text:
        raise RuntimeError("insert marker not found: def _compact_market_history_for_auditor")
    text = text.replace(insert_before, helper_code + "\n\n" + insert_before, 1)


# ---------------------------------------------------------------------
# 3) market compact 함수 교체
# ---------------------------------------------------------------------
market_pattern = r'''def _compact_market_history_for_auditor\(payload: dict, \*, company: str, company_dir: str\) -> dict:\n.*?\n\n(?=def _compact_tech_history_for_auditor)'''

new_market_func = r'''def _compact_market_history_for_auditor(payload: dict, *, company: str, company_dir: str) -> dict:
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

    if history_meta:
        compact["agent_history_snapshot"] = history_meta

    return compact
'''

text, count = re.subn(market_pattern, new_market_func + "\n\n", text, count=1, flags=re.S)
if count != 1:
    raise RuntimeError(f"market compact function replace failed. count={count}")


# ---------------------------------------------------------------------
# 4) tech compact 함수 교체
# ---------------------------------------------------------------------
tech_pattern = r'''def _compact_tech_history_for_auditor\(payload: dict, \*, company: str, company_dir: str\) -> dict:\n.*?\n\n(?=POSITIVE_TERMS = \[)'''

new_tech_func = r'''def _compact_tech_history_for_auditor(payload: dict, *, company: str, company_dir: str) -> dict:
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

    if history_meta:
        compact["agent_history_snapshot"] = history_meta

    return compact
'''

text, count = re.subn(tech_pattern, new_tech_func + "\n\n", text, count=1, flags=re.S)
if count != 1:
    raise RuntimeError(f"tech compact function replace failed. count={count}")

path.write_text(text, encoding="utf-8")
print("[OK] adapters.py patched: market metrics calculation + tech total_score correction.")
