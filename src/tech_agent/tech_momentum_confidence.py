from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
from typing import Any, Dict, Iterable, List, Optional, Tuple

from common.output_paths import agent_output_path, output_candidates, read_json_first, read_text_first, shared_output_dir

DEFAULT_COMPANY_NAMES: Dict[str, str] = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "엘티씨",
}

# Tech-to-Value 연결 체크 4개 축.
DIMENSION_KEYWORDS: Dict[str, List[str]] = {
    "customer_adoption": [
        "고객", "고객사", "채택", "수주", "계약", "공급", "납품", "거래처", "주요 고객",
        "vendor", "customer", "client", "adoption", "design win", "design-in", "purchase order", "order",
    ],
    "mass_production": [
        "양산", "상업생산", "대량생산", "생산라인", "생산 라인", "공정", "라인", "CAPA", "capa",
        "capacity", "mass production", "commercial production", "ramp-up", "ramp up", "volume production",
    ],
    "revenue_conversion": [
        "매출", "매출액", "매출 기여", "실적", "수익", "판매", "제품 매출", "인식", "revenue",
        "sales", "commercial revenue", "monetization", "top line",
    ],
    "fcf_cashflow": [
        "FCF", "free cash flow", "현금흐름", "영업현금", "영업활동현금", "잉여현금", "현금창출", "CAPEX",
        "cash flow", "operating cash flow", "free-cash-flow", "cashflow",
    ],
}

DIMENSION_LABELS: Dict[str, str] = {
    "customer_adoption": "고객 채택",
    "mass_production": "양산",
    "revenue_conversion": "매출 전환",
    "fcf_cashflow": "FCF/현금흐름",
}

# First Auditor/Chair에서 과대해석을 막기 위한 보수적 source taxonomy.
DIRECT_SOURCE_TYPES = {
    "dart",
    "opendart",
    "annual_report",
    "business_report",
    "quarterly_report",
    "semiannual_report",
    "company_ir",
    "ir",
    "company_disclosure",
    "disclosure",
    "official_filing",
    "finance_csv",
    "financial_csv",
    "stock_csv",
}

SECONDARY_OR_GENERATED_SOURCE_TYPES = {
    "agent_output",
    "agent_output_unverified",
    "self_generated",
    "report_output_self_check",
    "tech_agent_report",
    "company_ir_report_generated",
    "generated_report",
    "llm_summary",
    "chair_report",
    "tech_report",
    "analysis_report",
}

INDIRECT_SOURCE_TYPES = {
    "news",
    "rss",
    "article",
    "company_homepage",
    "homepage",
    "web",
    "kipris",
    "patent",
    "patent_csv",
    "unknown",
}

DIRECT_SOURCE_WEIGHT = {
    "dart": 0.98,
    "opendart": 0.98,
    "annual_report": 0.98,
    "business_report": 0.98,
    "quarterly_report": 0.94,
    "semiannual_report": 0.94,
    "company_ir": 0.88,
    "ir": 0.88,
    "company_disclosure": 0.95,
    "disclosure": 0.95,
    "official_filing": 0.95,
    "finance_csv": 0.96,
    "financial_csv": 0.96,
    "stock_csv": 0.90,
}

INDIRECT_SOURCE_WEIGHT = {
    "news": 0.48,
    "rss": 0.42,
    "article": 0.48,
    "company_homepage": 0.55,
    "homepage": 0.50,
    "web": 0.45,
    "kipris": 0.38,
    "patent": 0.38,
    "patent_csv": 0.38,
    "unknown": 0.25,
}

NUMBER_RE = re.compile(
    r"[-+]?\d[\d,]*(?:\.\d+)?\s*(?:%|원|억원|조원|건|개|회|년|분기|배|십억|million|billion|KRW|USD)?",
    re.I,
)
URL_RE = re.compile(r"https?://[^\s)\]>'\"]+")
YEAR_RE = re.compile(r"(?:19|20)\d{2}")

# 문서 첫머리/목차/생성 보고서 헤더는 대표 근거로 쓰지 않음.
HEADER_OR_BOILERPLATE_PATTERNS = [
    r"^\s*#\s+.*보고서",
    r"^\s*##\s+",
    r"종합\s*투자\s*보고서",
    r"하위\s*에이전트\s*의견\s*요약",
    r"최종\s*추천",
    r"목차",
    r"본\s*보고서는",
    r"테스트용",
    r"확인\s*제한",
    r"문서\s*첫머리",
]


def root() -> Path:
    return Path.cwd()


def read_json(path: Path) -> Optional[Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return None


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return default
        return float(value)
    s = str(value).replace(",", "").strip()
    s = re.sub(r"[^0-9.\-+]", "", s)
    if s in ("", ".", "-", "+"):
        return default
    try:
        return float(s)
    except Exception:
        return default


def clamp(x: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, x))


def compact_text(text: Any, limit: int = 5000) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()[:limit]


def deep_find(obj: Any, keys: Iterable[str]) -> Any:
    key_set = {str(k) for k in keys}
    if isinstance(obj, dict):
        for k in key_set:
            if k in obj and obj[k] not in (None, ""):
                return obj[k]
        for v in obj.values():
            found = deep_find(v, key_set)
            if found not in (None, ""):
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = deep_find(item, key_set)
            if found not in (None, ""):
                return found
    return None


def load_company_item_from_all(path: Path, company_dir: str) -> Optional[Dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, dict):
        companies = data.get("companies")
        if isinstance(companies, dict) and isinstance(companies.get(company_dir), dict):
            return companies[company_dir]
        for key in ("items", "results", "rows", "companies"):
            rows = data.get(key)
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict) and str(row.get("company_dir") or row.get("slug") or "") == company_dir:
                        return row
        if str(data.get("company_dir") or data.get("slug") or "") == company_dir:
            return data
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict) and str(row.get("company_dir") or row.get("slug") or "") == company_dir:
                return row
    return None


def load_payload(company_dir: str, stem: str, all_name: str) -> Optional[Dict[str, Any]]:
    base = root()
    candidates = [company_agent_dir(company_dir, "tech") / f"{stem}.json"]
    candidates.extend(output_candidates(company_dir, "tech", f"{company_dir}_{stem}.json", root=base))
    payload = read_json_first(candidates)
    if isinstance(payload, dict):
        return payload
    shared = shared_output_dir("tech", root=base) / all_name
    data = load_company_item_from_all(shared, company_dir)
    if data is not None:
        return data
    return load_company_item_from_all(field_agent_dir("tech") / all_name, company_dir)


def infer_source_type(item: Dict[str, Any], source_hint: str = "") -> str:
    raw = " ".join(
        str(item.get(k) or "")
        for k in ("source_type", "source", "url", "filename", "file", "evidence_id", "title", "metric")
    ).lower()
    raw += " " + str(source_hint).lower()

    # 2차 산출물/LLM output은 먼저 잡아야 한다.
    generated_markers = [
        "agent_output", "unverified", "self_generated", "self-check", "self_check", "chair_report",
        "tech_agent_report", "tech_report", "high_quality_report", "generated", "llm", "summary",
        "report_output", "company_ir_report_generated",
    ]
    if any(x in raw for x in generated_markers):
        return "agent_output" if "agent_output" in raw else "generated_report"

    if "finance_csv" in raw or "financial_csv" in raw or "재무.csv" in raw or "_재무" in raw:
        return "finance_csv"
    if "stock_csv" in raw or "주식.csv" in raw or "_주식" in raw:
        return "stock_csv"
    if "dart" in raw or "opendart" in raw or "사업보고서" in raw or "분기보고서" in raw or "반기보고서" in raw:
        return "dart"
    if "공시" in raw or "disclosure" in raw or "filing" in raw:
        return "company_disclosure"
    if "ir" in raw or "investor" in raw or "presentation" in raw:
        return "company_ir"
    if "kipris" in raw or "patent" in raw or "특허" in raw:
        return "kipris"
    if "homepage" in raw or "company" in raw or ".co.kr" in raw:
        return "company_homepage"
    if "news" in raw or "rss" in raw or "article" in raw or "기자" in raw:
        return "news"
    return str(item.get("source_type") or "unknown")


def evidence_snippet(item: Dict[str, Any]) -> str:
    for key in ("snippet", "text", "rationale", "claim", "claim_text", "summary", "detail", "content", "title"):
        val = item.get(key)
        if val not in (None, ""):
            return str(val)
    return json.dumps(item, ensure_ascii=False)[:700]


def is_boilerplate_or_header(text: str) -> bool:
    s = compact_text(text, 600)
    if not s:
        return True
    if len(s) < 35:
        return True
    for pattern in HEADER_OR_BOILERPLATE_PATTERNS:
        if re.search(pattern, s, flags=re.I):
            return True
    # 문서 맨 앞의 회사 소개성 문단은 수치·연결 이벤트가 없으면 대표근거에서 제외.
    first_page_markers = ["회사개요", "기업개요", "회사 소개", "기업 소개", "사업 개요", "overview"]
    if any(m.lower() in s.lower() for m in first_page_markers) and not NUMBER_RE.search(s):
        return True
    # 키워드가 지나치게 생성 보고서적이면 제외.
    generated_phrases = ["본 9단계", "본 10단계", "chair 반영", "기술 점수", "최종 판단", "좋은 기업/나쁜 기업"]
    if any(p in s for p in generated_phrases):
        return True
    return False


def extract_evidence_texts(obj: Any, source_hint: str = "") -> List[Tuple[str, str, str]]:
    """Extract structured evidence entries from arbitrary JSON.

    문자열 전체를 무차별 수집하면 generated report의 첫머리/요약문이 과도하게 잡히므로,
    evidence처럼 보이는 dict와 명확한 source가 있는 text만 수집한다.
    """
    out: List[Tuple[str, str, str]] = []

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            looks_like_evidence = any(
                k in x for k in (
                    "evidence_id", "source_type", "source", "url", "filename", "file",
                    "snippet", "rationale", "claim", "claim_text", "metric", "period", "value",
                )
            )
            if looks_like_evidence:
                st = infer_source_type(x, source_hint=source_hint)
                source = str(x.get("source") or x.get("url") or x.get("filename") or x.get("file") or source_hint)
                text = evidence_snippet(x)
                if text.strip() and not is_boilerplate_or_header(text):
                    out.append((st, source, text))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for item in x:
                walk(item)

    walk(obj)
    seen = set()
    uniq: List[Tuple[str, str, str]] = []
    for st, src, txt in out:
        compact = compact_text(txt, 350)
        if compact and compact not in seen:
            seen.add(compact)
            uniq.append((normalize_source_type(st), src, txt))
    return uniq


def parse_company_yaml(company_dir: str) -> Dict[str, str]:
    path = company_config_path(company_dir)
    if not path.exists():
        return {}
    result: Dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k:
                result[k] = v
    except Exception:
        pass
    return result


def load_csv_text(path: Path, limit_rows: int = 80) -> str:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            rows = []
            for i, row in enumerate(reader):
                rows.append(", ".join(str(x) for x in row))
                if i >= limit_rows:
                    break
            return "\n".join(rows)
    except UnicodeDecodeError:
        try:
            with path.open("r", encoding="cp949", newline="") as f:
                reader = csv.reader(f)
                rows = []
                for i, row in enumerate(reader):
                    rows.append(", ".join(str(x) for x in row))
                    if i >= limit_rows:
                        break
                return "\n".join(rows)
        except Exception:
            return ""
    except Exception:
        return ""


def load_finance_csv_evidence(company_dir: str, company_name: str = "") -> List[Tuple[str, str, str]]:
    """Finance CSV/stock CSV를 직접 수치 근거로 추가한다.

    FCF/현금흐름, 매출, 수익성처럼 기술-가치 연결에서 재무성과 확인이 필요한 항목은
    finance_agent의 LLM 요약보다 로컬 CSV가 Auditor-safe 하다.
    """
    base = root()
    cfg = parse_company_yaml(company_dir)
    data_dir = field_common_dir("data")
    candidates: List[Path] = []
    for key in ("finance_file", "financial_file", "stock_file"):
        filename = cfg.get(key)
        if filename:
            candidates.append(data_dir / filename)
    if company_name:
        candidates.extend(data_dir.glob(f"*{company_name}*재무*.csv"))
        candidates.extend(data_dir.glob(f"*{company_name}*주식*.csv"))
    candidates.extend(data_dir.glob(f"*{company_dir}*finance*.csv"))
    candidates.extend(data_dir.glob(f"*{company_dir}*stock*.csv"))

    out: List[Tuple[str, str, str]] = []
    seen = set()
    for path in candidates:
        if not path.exists() or path in seen:
            continue
        seen.add(path)
        text = load_csv_text(path)
        if not text.strip():
            continue
        st = "stock_csv" if "주식" in path.name or "stock" in path.name.lower() else "finance_csv"
        out.append((st, str(path), text[:12000]))
    return out


def load_text_candidates(company_dir: str, company_name: str = "") -> List[Tuple[str, str, str]]:
    """Return (source_type, source, text) candidates for evidence search."""
    base = root()
    result: List[Tuple[str, str, str]] = []

    json_paths = [
        company_agent_dir(company_dir, "tech") / "tech.json",
        company_agent_dir(company_dir, "tech") / "tech_packet.json",
        company_agent_dir(company_dir, "tech") / "tech_to_value_bridge.json",
        company_agent_dir(company_dir, "tech") / "tech_peer_percentile_bridge.json",
        company_agent_dir(company_dir, "tech") / "tech_differentiation.json",
        company_agent_dir(company_dir, "tech") / "tech_ip_ml.json",
        company_agent_dir(company_dir, "tech") / "finance.json",
        company_agent_dir(company_dir, "tech") / "finance_packet.json",
        *output_candidates(company_dir, "finance", f"{company_dir}_finance.json", root=base),
        *output_candidates(company_dir, "tech", f"{company_dir}_tech_to_value_bridge.json", root=base),
        *output_candidates(company_dir, "tech", f"{company_dir}_tech_evidence_harvest.json", root=base),
    ]
    for path in json_paths:
        payload = read_json(path)
        if payload is not None:
            result.extend(extract_evidence_texts(payload, source_hint=str(path)))

    # Generated markdown 보고서는 직접 근거가 아니라 self-check용 2차 산출물로만 반영한다.
    md_paths = [
        *output_candidates(company_dir, "tech", f"{company_dir}_tech_high_quality_report.md", root=base),
        *output_candidates(company_dir, "chair", f"{company_dir}_chair_report.md", root=base),
        field_agent_dir("tech") / f"{company_dir}_report.md",
    ]
    for path in md_paths:
        try:
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="ignore")
                if text.strip() and not is_boilerplate_or_header(text[:800]):
                    result.append(("generated_report", str(path), text[:6000]))
        except Exception:
            pass

    result.extend(load_finance_csv_evidence(company_dir, company_name=company_name))
    return dedupe_evidence(result)


def dedupe_evidence(items: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
    seen = set()
    out: List[Tuple[str, str, str]] = []
    for st, src, txt in items:
        if not txt or is_boilerplate_or_header(txt):
            continue
        key = (normalize_source_type(st), compact_text(txt, 280))
        if key in seen:
            continue
        seen.add(key)
        out.append((normalize_source_type(st), src, txt))
    return out


def normalize_source_type(source_type: str) -> str:
    s = str(source_type or "unknown").lower()
    if s in SECONDARY_OR_GENERATED_SOURCE_TYPES:
        return "generated_report" if s != "agent_output_unverified" else "agent_output"
    if s in DIRECT_SOURCE_TYPES or s in INDIRECT_SOURCE_TYPES:
        return s
    if "finance" in s and "csv" in s:
        return "finance_csv"
    if "stock" in s and "csv" in s:
        return "stock_csv"
    if "dart" in s:
        return "dart"
    if "ir" in s:
        return "company_ir"
    if "kipris" in s or "patent" in s:
        return "kipris"
    if "news" in s or "rss" in s:
        return "news"
    if "agent" in s or "generated" in s or "report" in s:
        return "generated_report"
    return "unknown"


def metric_values(ip_payload: Optional[Dict[str, Any]], diff_payload: Optional[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    src = ip_payload or {}
    diff_raw = (diff_payload or {}).get("raw_metrics") or {}

    def get(keys: Iterable[str]) -> Optional[float]:
        for source in (src, diff_raw, diff_payload or {}):
            val = deep_find(source, keys)
            if val not in (None, ""):
                parsed = safe_float(val)
                if parsed is not None:
                    return parsed
        return None

    return {
        "base_patent_momentum_score": get(["patent_momentum_score", "momentum_score", "recent_momentum_score"]),
        "normalized_patent_records": get(["normalized_patent_records", "normalized_records", "total_patents", "patent_records"]),
        "company_matched_patents": get(["company_matched_patents", "matched_applicant_patents", "matched_patents"]),
        "registered_patents": get(["registered_patents", "registered_count", "registration_count"]),
        "alive_patents": get(["alive_patents", "active_patents", "valid_patents", "surviving_patents"]),
        "recent_5y_patents": get(["recent_5y_patents", "recent_5_year_patents", "recent_patents_5y", "recent_patents"]),
        "ipc_cpc_classes": get(["ipc_cpc_classes", "ipc_cpc_count", "ipc_cpc_diversity"]),
        "core_ipc_h01l_patents": get(["core_ipc_h01l_patents", "h01l_patents", "core_ipc_patents"]),
        "patent_keyword_matches": get(["patent_keyword_matches", "keyword_matches", "tech_keyword_matches"]),
    }


def infer_year_span(ip_payload: Optional[Dict[str, Any]], diff_payload: Optional[Dict[str, Any]], evidence_texts: List[Tuple[str, str, str]]) -> Dict[str, Optional[int]]:
    years: List[int] = []
    for payload in (ip_payload, diff_payload):
        if not payload:
            continue
        for key in ("patent_year_start", "patent_year_end", "start_year", "end_year", "min_year", "max_year"):
            val = deep_find(payload, [key])
            parsed = safe_float(val)
            if parsed:
                years.append(int(parsed))
        text = json.dumps(payload, ensure_ascii=False)[:20000]
        years.extend(int(x) for x in YEAR_RE.findall(text))
    for _, _, text in evidence_texts[:30]:
        years.extend(int(x) for x in YEAR_RE.findall(text[:1000]))
    years = [y for y in years if 1990 <= y <= 2030]
    if not years:
        return {"start_year": None, "end_year": None, "span_years": None}
    return {"start_year": min(years), "end_year": max(years), "span_years": max(years) - min(years) + 1}


def calculate_patent_momentum(metrics: Dict[str, Optional[float]], span: Dict[str, Optional[int]]) -> Dict[str, Any]:
    matched = metrics.get("company_matched_patents") or metrics.get("normalized_patent_records") or 0.0
    registered = metrics.get("registered_patents") or 0.0
    alive = metrics.get("alive_patents") or 0.0
    recent = metrics.get("recent_5y_patents") or 0.0
    ipc = metrics.get("ipc_cpc_classes") or 0.0
    core = metrics.get("core_ipc_h01l_patents") or 0.0

    def ratio(n: float, d: float) -> Optional[float]:
        if d <= 0:
            return None
        return n / d

    recent_ratio = ratio(recent, matched)
    active_ratio = ratio(alive, matched)
    registered_ratio = ratio(registered, matched)
    core_ipc_ratio = ratio(core, matched)

    recent_activity_score = 50.0 if recent_ratio is None else clamp((recent_ratio / 0.25) * 100.0)
    active_continuity_score = 50.0 if active_ratio is None else clamp((active_ratio / 0.65) * 100.0)
    registration_quality_score = 50.0 if registered_ratio is None else clamp((registered_ratio / 0.60) * 100.0)

    span_years = span.get("span_years")
    if span_years is None:
        sustained_activity_score = 50.0
    elif span_years >= 20:
        sustained_activity_score = 90.0
    elif span_years >= 12:
        sustained_activity_score = 75.0
    elif span_years >= 6:
        sustained_activity_score = 60.0
    else:
        sustained_activity_score = 40.0

    ipc_score = clamp((ipc / 120.0) * 100.0) if ipc else 40.0
    core_score = 50.0 if core_ipc_ratio is None else clamp((core_ipc_ratio / 0.05) * 100.0)
    technology_continuity_score = 0.65 * ipc_score + 0.35 * core_score

    recalibrated = (
        0.40 * recent_activity_score
        + 0.22 * active_continuity_score
        + 0.18 * registration_quality_score
        + 0.10 * sustained_activity_score
        + 0.10 * technology_continuity_score
    )

    base = metrics.get("base_patent_momentum_score")
    final = 0.60 * base + 0.40 * recalibrated if base is not None else recalibrated

    if final >= 75:
        grade = "HIGH_MOMENTUM"
        grade_kr = "최근 특허 모멘텀 강함"
    elif final >= 55:
        grade = "MODERATE_MOMENTUM"
        grade_kr = "최근 특허 모멘텀 보통"
    elif final >= 35:
        grade = "WATCH_MOMENTUM"
        grade_kr = "최근 특허 모멘텀 추적 필요"
    else:
        grade = "LOW_OR_STALE_MOMENTUM"
        grade_kr = "최근 특허 모멘텀 약함"

    return {
        "patent_momentum_score": round(final, 2),
        "baseline_step9_momentum_score": None if base is None else round(float(base), 2),
        "recalibrated_momentum_signal": round(recalibrated, 2),
        "grade": grade,
        "grade_kr": grade_kr,
        "component_scores": {
            "recent_activity_score": round(recent_activity_score, 2),
            "active_continuity_score": round(active_continuity_score, 2),
            "registration_quality_score": round(registration_quality_score, 2),
            "sustained_activity_score": round(sustained_activity_score, 2),
            "technology_continuity_score": round(technology_continuity_score, 2),
        },
        "raw_signals": {
            **metrics,
            "recent_5y_ratio": None if recent_ratio is None else round(recent_ratio * 100.0, 2),
            "active_patent_ratio": None if active_ratio is None else round(active_ratio * 100.0, 2),
            "registered_patent_ratio": None if registered_ratio is None else round(registered_ratio * 100.0, 2),
            "core_ipc_ratio": None if core_ipc_ratio is None else round(core_ipc_ratio * 100.0, 2),
            **span,
        },
        "interpretation": (
            "Patent Momentum Score는 최근 특허 활동, 존속 특허 비중, 등록 특허 비중, 포트폴리오 지속 기간, "
            "IPC/CPC 기반 기술 지속성을 결합한 보조 지표입니다. 이 점수는 미래 수익률 예측이 아니라 기술 활동의 "
            "현재성·지속성을 설명합니다."
        ),
    }


def source_bucket(source_type: str) -> str:
    st = normalize_source_type(source_type)
    if st in DIRECT_SOURCE_TYPES:
        return "direct"
    if st in SECONDARY_OR_GENERATED_SOURCE_TYPES or st in {"agent_output", "generated_report"}:
        return "limited"
    return "indirect"


def source_quality_score(source_type: str, source: str, dim: str, text: str) -> float:
    st = normalize_source_type(source_type)
    bucket = source_bucket(st)
    has_url = bool(URL_RE.search(source or "") or URL_RE.search(text or ""))
    has_numeric = bool(NUMBER_RE.search(text or ""))

    if bucket == "direct":
        base = DIRECT_SOURCE_WEIGHT.get(st, 0.85) * 100.0
        if has_numeric:
            base += 8.0
        if has_url:
            base += 2.0
        # FCF는 재무 CSV/DART 직접 수치가 아니면 강한 근거로 보지 않는다.
        if dim == "fcf_cashflow" and st not in {"finance_csv", "financial_csv", "dart", "opendart", "business_report", "annual_report"}:
            base = min(base, 52.0)
        return clamp(base, 0.0, 92.0)

    if bucket == "indirect":
        base = INDIRECT_SOURCE_WEIGHT.get(st, 0.30) * 100.0
        if has_numeric:
            base += 5.0
        if has_url:
            base += 2.0
        # KIPRIS/특허는 기술성 근거이지 고객 채택·양산·매출·FCF의 직접 근거는 아님.
        if st in {"kipris", "patent", "patent_csv"}:
            base = min(base, 42.0)
        return clamp(base, 0.0, 49.0)

    # Generated / agent output / unknown limited evidence.
    base = 18.0
    if has_numeric:
        base += 4.0
    return clamp(base, 0.0, 28.0)


def classify_evidence_level(source_type: str, source: str, text: str, dim: str) -> Tuple[str, str]:
    st = normalize_source_type(source_type)
    bucket = source_bucket(st)
    s = compact_text(text, 1000)
    has_numeric = bool(NUMBER_RE.search(s))
    if is_boilerplate_or_header(s):
        return "확인 제한", "문서 첫머리·목차·생성 보고서성 문단은 대표 근거에서 제외"
    if bucket == "direct":
        if dim == "fcf_cashflow" and st not in {"finance_csv", "financial_csv", "dart", "opendart", "business_report", "annual_report"}:
            return "간접 근거", "FCF/현금흐름은 DART 또는 재무 CSV 직접 수치가 아니므로 간접 근거로 제한"
        if has_numeric or st in {"dart", "opendart", "business_report", "annual_report", "company_disclosure"}:
            return "직접 근거", "DART/IR/공시/재무 CSV 등 1차 출처 기반 근거"
        return "간접 근거", "1차 출처이나 수치·기간·단위가 부족해 간접 근거로 분류"
    if bucket == "indirect":
        return "간접 근거", "뉴스·홈페이지·KIPRIS 등은 연결 항목의 보조 근거로만 반영"
    return "확인 제한", "agent_output·generated report 등 2차 산출물은 통과 점수에서 강한 근거로 인정하지 않음"


def score_dimension(dim: str, evidence_texts: List[Tuple[str, str, str]]) -> Dict[str, Any]:
    keywords = [kw.lower() for kw in DIMENSION_KEYWORDS[dim]]
    hits: List[Dict[str, Any]] = []

    for source_type, source, text in evidence_texts:
        if is_boilerplate_or_header(text):
            continue
        low = str(text).lower()
        matched_keywords = [kw for kw in keywords if kw in low]
        if not matched_keywords:
            continue
        st = normalize_source_type(source_type)
        level, reason = classify_evidence_level(st, source, text, dim)
        numeric = bool(NUMBER_RE.search(text))
        url = bool(URL_RE.search(source) or URL_RE.search(text))
        q_score = source_quality_score(st, source, dim, text)
        hits.append(
            {
                "source_type": st,
                "source": source,
                "matched_keywords": matched_keywords[:6],
                "has_numeric_signal": numeric,
                "has_url_signal": url,
                "evidence_level": level,
                "level_reason": reason,
                "hit_score": round(q_score, 2),
                "snippet": compact_text(text, 260),
            }
        )

    # 직접 근거 우선, 그다음 간접 근거, 확인 제한은 맨 뒤.
    level_rank = {"직접 근거": 0, "간접 근거": 1, "확인 제한": 2}
    hits.sort(key=lambda x: (level_rank.get(x["evidence_level"], 9), -float(x["hit_score"])))

    direct_hits = [h for h in hits if h["evidence_level"] == "직접 근거"]
    indirect_hits = [h for h in hits if h["evidence_level"] == "간접 근거"]
    limited_hits = [h for h in hits if h["evidence_level"] == "확인 제한"]

    if direct_hits:
        top_scores = [float(h["hit_score"]) for h in direct_hits[:3]]
        score = sum(top_scores) / len(top_scores)
        score += min(8.0, max(0, len(direct_hits) - 1) * 2.5)
        score += min(4.0, len({h["source_type"] for h in direct_hits}) * 1.5)
        score = clamp(score, 50.0, 88.0)
    elif indirect_hits:
        top_scores = [float(h["hit_score"]) for h in indirect_hits[:3]]
        score = sum(top_scores) / len(top_scores)
        score += min(4.0, max(0, len(indirect_hits) - 1) * 1.0)
        score = clamp(score, 30.0, 49.0)
    elif limited_hits:
        top_scores = [float(h["hit_score"]) for h in limited_hits[:3]]
        score = sum(top_scores) / len(top_scores)
        score = clamp(score, 15.0, 28.0)
    else:
        score = 15.0

    if direct_hits and score >= 72:
        status = "DIRECT_CONFIRMED"
        status_kr = "직접 근거"
    elif direct_hits:
        status = "DIRECT_BUT_LIMITED"
        status_kr = "직접 근거 일부"
    elif indirect_hits:
        status = "INDIRECT_ONLY"
        status_kr = "간접 근거"
    else:
        status = "NOT_CONFIRMED"
        status_kr = "확인 제한"

    return {
        "dimension": dim,
        "dimension_label": DIMENSION_LABELS.get(dim, dim),
        "score": round(score, 2),
        "status": status,
        "status_kr": status_kr,
        "evidence_hit_count": len(hits),
        "direct_evidence_count": len(direct_hits),
        "indirect_evidence_count": len(indirect_hits),
        "limited_evidence_count": len(limited_hits),
        "top_direct_evidence": direct_hits[:3],
        "top_indirect_evidence": indirect_hits[:3],
        "top_limited_evidence": limited_hits[:2],
        "top_evidence": (direct_hits + indirect_hits + limited_hits)[:3],
    }


def calculate_evidence_confidence(evidence_texts: List[Tuple[str, str, str]]) -> Dict[str, Any]:
    dimensions = {dim: score_dimension(dim, evidence_texts) for dim in DIMENSION_KEYWORDS}
    weights = {
        "customer_adoption": 0.30,
        "mass_production": 0.25,
        "revenue_conversion": 0.25,
        "fcf_cashflow": 0.20,
    }
    raw_score = sum(dimensions[k]["score"] * w for k, w in weights.items())

    direct_dimension_count = sum(1 for d in dimensions.values() if d.get("direct_evidence_count", 0) > 0)
    indirect_only_count = sum(1 for d in dimensions.values() if d.get("direct_evidence_count", 0) == 0 and d.get("indirect_evidence_count", 0) > 0)

    # Direct evidence가 부족하면 점수를 보수적으로 cap한다.
    if direct_dimension_count == 0:
        score = min(raw_score, 38.0)
    elif direct_dimension_count == 1:
        score = min(raw_score, 52.0)
    elif direct_dimension_count == 2:
        score = min(raw_score, 64.0)
    else:
        score = raw_score
    score = round(clamp(score), 2)

    if score >= 75:
        grade = "EVIDENCE_STRONG"
        grade_kr = "기술-가치 연결 직접 근거 강함"
    elif score >= 55:
        grade = "EVIDENCE_PARTIAL_DIRECT"
        grade_kr = "기술-가치 연결 직접 근거 일부 확인"
    elif score >= 40:
        grade = "EVIDENCE_INDIRECT_OR_WEAK"
        grade_kr = "기술-가치 연결 간접/약한 근거"
    else:
        grade = "EVIDENCE_NOT_CONFIRMED"
        grade_kr = "기술-가치 연결 확인 제한"

    return {
        "tech_to_value_evidence_confidence_score": score,
        "raw_weighted_score_before_direct_cap": round(raw_score, 2),
        "grade": grade,
        "grade_kr": grade_kr,
        "direct_dimension_count": direct_dimension_count,
        "indirect_only_dimension_count": indirect_only_count,
        "dimensions": dimensions,
        "scoring_policy": {
            "direct_sources": sorted(DIRECT_SOURCE_TYPES),
            "secondary_sources_penalized": sorted(SECONDARY_OR_GENERATED_SOURCE_TYPES),
            "direct_evidence_cap_rule": "직접 근거가 확인된 연결 항목 수가 0/1/2개이면 전체 Evidence Confidence를 각각 38/52/64점으로 cap합니다.",
            "strong_evidence_rule": "DART/IR/공시/재무 CSV의 직접 수치·기간·단위가 있는 경우만 강한 근거로 인정합니다.",
        },
        "interpretation": (
            "Tech-to-Value Evidence Confidence는 기술성 자체가 아니라 고객 채택, 양산, 매출 전환, FCF/현금흐름 "
            "개선 근거가 얼마나 직접 확인되는지를 평가합니다. agent_output, company_ir_report_generated, "
            "tech_agent_report 같은 2차 산출물은 감점하며, DART/IR/공시/재무 CSV 직접 수치만 강한 근거로 인정합니다."
        ),
    }


def analyze_company(company_dir: str, company_name: Optional[str] = None) -> Dict[str, Any]:
    company = company_name or DEFAULT_COMPANY_NAMES.get(company_dir, company_dir)
    ip_payload = load_payload(company_dir, "tech_ip_ml", "tech_ip_strength_all.json")
    diff_payload = load_payload(company_dir, "tech_differentiation", "tech_differentiation_all.json")
    evidence_texts = load_text_candidates(company_dir, company_name=company)

    metrics = metric_values(ip_payload, diff_payload)
    span = infer_year_span(ip_payload, diff_payload, evidence_texts)
    patent_momentum = calculate_patent_momentum(metrics, span)
    evidence_confidence = calculate_evidence_confidence(evidence_texts)

    return {
        "company_dir": company_dir,
        "company_name": company,
        "method": "Patent Momentum Score + Conservative Tech-to-Value Evidence Confidence",
        "patent_momentum": patent_momentum,
        "tech_to_value_evidence_confidence": evidence_confidence,
        "source_files_checked": {
            "tech_ip_ml": bool(ip_payload),
            "tech_differentiation": bool(diff_payload),
            "evidence_text_units": len(evidence_texts),
        },
        "chair_policy": (
            "Patent Momentum은 기술 활동의 현재성·지속성을 보조하고, Evidence Confidence는 기술 점수를 "
            "최종 가치판단에 얼마나 반영할지 조절하는 보수 게이트로 사용한다."
        ),
    }


def render_markdown(results: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("# Patent Momentum & Conservative Tech-to-Value Evidence Confidence")
    lines.append("")
    lines.append("## 1. 기업별 요약")
    lines.append("| 기업 | Patent Momentum | Momentum 등급 | Evidence Confidence | Evidence 등급 | 직접 근거 항목 수 |")
    lines.append("|---|---:|---|---:|---|---:|")
    for r in results:
        pm = r["patent_momentum"]
        ev = r["tech_to_value_evidence_confidence"]
        lines.append(
            f"| {r['company_name']}({r['company_dir']}) | {pm['patent_momentum_score']:.2f}/100 | {pm['grade_kr']} | "
            f"{ev['tech_to_value_evidence_confidence_score']:.2f}/100 | {ev['grade_kr']} | {ev.get('direct_dimension_count', 0)}/4 |"
        )
    lines.append("")
    lines.append("## 2. 해석 원칙")
    lines.append("- Patent Momentum Score는 최근 특허 활동의 현재성·지속성을 보는 보조 지표이며, 미래 수익률 예측 지표가 아닙니다.")
    lines.append("- Evidence Confidence는 고객 채택·양산·매출 전환·FCF 개선 근거를 직접 근거/간접 근거/확인 제한으로 나누어 평가합니다.")
    lines.append("- DART/IR/공시/재무 CSV 직접 수치만 강한 근거로 인정하고, agent output·생성 보고서는 감점합니다.")
    lines.append("- Evidence Confidence가 낮으면 기술/IP 점수가 높더라도 Chair는 최종 추천을 보수적으로 반영해야 합니다.")
    return "\n".join(lines) + "\n"


def save_company_packet(result: Dict[str, Any]) -> None:
    company_dir = result["company_dir"]
    path = company_agent_dir(company_dir, "tech") / "tech_momentum_confidence.json"
    write_json(path, result)
    write_json(agent_output_path(company_dir, "tech", f"{company_dir}_tech_momentum_confidence.json", root=root()), result)


def run(company_dirs: List[str], company_names: Optional[List[str]] = None, save: bool = True) -> List[Dict[str, Any]]:
    names = company_names or []
    results = []
    for i, company_dir in enumerate(company_dirs):
        company = names[i] if i < len(names) else DEFAULT_COMPANY_NAMES.get(company_dir, company_dir)
        result = analyze_company(company_dir, company)
        results.append(result)
        if save:
            save_company_packet(result)

    if save:
        out_dir = shared_output_dir("tech", root=root())
        out_json = out_dir / "tech_momentum_confidence_all.json"
        out_md = out_dir / "tech_momentum_confidence.md"
        write_json(out_json, {"companies": {r["company_dir"]: r for r in results}, "items": results})
        write_text(out_md, render_markdown(results))
        print(f"[Tech Momentum Confidence] 저장 완료: {out_json}")
        print(f"[Tech Momentum Confidence] 저장 완료: {out_md}")
        print(f"[Tech Momentum Confidence] companies={len(results)}")
        for r in results:
            ev = r["tech_to_value_evidence_confidence"]
            print(
                f"  - {r['company_name']}({r['company_dir']}): "
                f"momentum={r['patent_momentum']['patent_momentum_score']}/100, "
                f"evidence={ev['tech_to_value_evidence_confidence_score']}/100, "
                f"direct_dims={ev.get('direct_dimension_count', 0)}/4, "
                f"grade={ev['grade']}"
            )
    return results


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Patent Momentum Score + Conservative Tech-to-Value Evidence Confidence")
    parser.add_argument("--company-dir", action="append", dest="company_dirs", help="Company slug, e.g. nepes. Can be repeated.")
    parser.add_argument("--company-name", action="append", dest="company_names", help="Display company name. Optional, repeat in same order.")
    parser.add_argument("--all", action="store_true", help="Run default five focal companies.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.all or not args.company_dirs:
        company_dirs = ["nepes", "hanmi", "hansol", "duksan", "ltc"]
    else:
        company_dirs = args.company_dirs
    run(company_dirs, company_names=args.company_names, save=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
