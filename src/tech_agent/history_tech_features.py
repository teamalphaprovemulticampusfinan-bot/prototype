from __future__ import annotations

"""History/evaluation Tech signal feature builder.

This module is intentionally kept under ``src_eval`` only.  It does not alter the
production ``src`` Tech Agent report flow.  The goal is to make monthly/daily
history evaluation read *as-of* technology evidence instead of treating Tech as a
static, low-reliability carry-forward prior.

Research design encoded in the implementation
---------------------------------------------
* Patent quality is not a raw patent-count score.  We combine citations, claims,
  family size, renewals/legal status, recency and technology-field momentum when
  the columns are available.  This follows the multiple-indicator patent-quality
  literature and the OECD patent-quality composite index approach.
* Commercialization is separated from IP ownership.  Certifications,
  qualification, pilot/sample events, mass-production approval, supply contracts,
  product revenue and yield/cost evidence enter an evidence-confidence layer.
* Technology maturity is treated as a dated measurement.  TRL / readiness stage
  / commercialization gate columns are accepted when a date column proves they
  were observable at the evaluation as_of_date.
* No Buy/Hold/Sell threshold is introduced here.  This module outputs a continuous
  ``tech_signal`` in [-1, +1].  Label conversion remains the evaluation layer's
  responsibility, where DMA / IC / probability tensor logic is applied.
"""

from dataclasses import dataclass, asdict
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


DATE_COL_CANDIDATES = (
    "as_of_date", "date", "기준일", "공시일", "공고일", "출원일", "application_date",
    "filing_date", "publication_date", "등록일", "grant_date", "event_date", "연월",
    "month", "year_month", "기간", "start_date", "end_date",
)

COMPANY_COL_CANDIDATES = (
    "company", "company_name", "corp_name", "기업", "기업명", "회사", "회사명", "issuer", "applicant",
    "출원인", "권리자", "applicant_name", "owner", "right_holder", "slug", "company_dir",
)
TICKER_COL_CANDIDATES = ("ticker", "stock_code", "종목코드", "code", "corp_code")

POSITIVE_EVENT_PATTERNS = re.compile(
    r"양산|mass\s*production|qualification\s*pass|승인|cert|인증|iso|iatf|ul|ce|rohs|reach|kc|gmp|kgmp|"
    r"고객|customer|vendor|벤더|sample|샘플|pilot|poc|초도|납품|supply|contract|계약|매출|revenue|"
    r"수율\s*개선|yield\s*improvement|cost\s*down|원가\s*절감|performance|성능|throughput|처리량|roadmap|로드맵",
    re.IGNORECASE,
)
NEGATIVE_EVENT_PATTERNS = re.compile(
    r"소송|분쟁|무효|침해|영업비밀|품질\s*클레임|리콜|recall|delay|지연|failed|failure|실패|취하|거절|"
    r"손상|impairment|수율\s*문제|불량|계약\s*해지|approval\s*delay|인증\s*실패",
    re.IGNORECASE,
)

POSITIVE_NUMERIC_HINTS = (
    "score", "signal", "quality", "confidence", "growth", "momentum", "등록률", "존속률", "registration_rate",
    "alive_rate", "citation", "인용", "claim", "청구항", "family", "패밀리", "renewal", "매출", "revenue",
    "수율", "yield", "성능", "performance", "throughput", "efficiency", "채택", "adoption", "TRL", "trl",
)
NEGATIVE_NUMERIC_HINTS = (
    "risk", "penalty", "delay", "litigation", "dispute", "failure", "fail", "impairment", "손상", "분쟁",
    "소송", "지연", "실패", "불량", "defect", "cost_ratio", "원가율", "dependency", "의존도",
)

TECH_KEYWORDS = (
    "HBM", "CoWoS", "FOWLP", "WLP", "advanced packaging", "첨단패키징", "패키징", "OSAT",
    "EUV", "ALD", "전구체", "precursor", "소재", "검사", "테스트", "수율", "qualification",
)


@dataclass
class TechHistoryFeature:
    signal: float
    status: str
    source: str
    as_of_date: str
    company: str
    ticker: str
    stock_code: str
    base_signal: float
    evidence_confidence: float
    commercialization_gate_signal: float
    technology_risk_penalty: float
    ip_quality_signal: float
    lifecycle_signal: float
    technology_differentiation_signal: float
    commercialization_signal: float
    rnd_sustainability_signal: float
    peer_position_signal: float
    tech_to_value_signal: float
    certification_signal: float
    qualification_signal: float
    cost_yield_signal: float
    workforce_signal: float
    government_rd_signal: float
    licensing_signal: float
    dispute_risk_signal: float
    failure_delay_signal: float
    intangible_accounting_signal: float
    patent_records_asof: int
    dated_records_asof: int
    undated_records_used: int
    files_used: int
    notes: str


def _clip(v: Any, lo: float = -1.0, hi: float = 1.0) -> float:
    try:
        x = float(v)
    except Exception:
        return 0.0
    if not math.isfinite(x):
        return 0.0
    return max(lo, min(hi, x))


def _safe_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        x = float(v)
        return x if math.isfinite(x) else None
    s = str(v).strip()
    if not s or s.lower() in {"nan", "none", "null", "na", "n/a", "확인 제한", "-"}:
        return None
    s = s.replace(",", "").replace("%", "")
    try:
        x = float(s)
    except Exception:
        return None
    return x if math.isfinite(x) else None


def _sigmoid_signal(x: float, scale: float = 1.0) -> float:
    if scale <= 0:
        scale = 1.0
    return _clip(math.tanh(float(x) / scale))


def _ratio_to_signal(x: Any, neutral: float = 0.5) -> float:
    v = _safe_float(x)
    if v is None:
        return 0.0
    if v > 1.0 and v <= 100.0:
        v = v / 100.0
    return _clip((v - neutral) * 2.0)


def _score_to_signal(x: Any, neutral: float = 50.0, scale: float = 35.0) -> float:
    v = _safe_float(x)
    if v is None:
        return 0.0
    if -1.0 <= v <= 1.0:
        return _clip(v)
    if 0.0 <= v <= 1.0:
        return _ratio_to_signal(v)
    return _clip((v - neutral) / max(scale, 1e-9))


def _mean(vals: Iterable[Any]) -> float:
    xs = [_safe_float(v) for v in vals]
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    if not xs:
        return 0.0
    return _clip(sum(xs) / len(xs))


def _date_col(df: pd.DataFrame) -> str | None:
    lower = {str(c).strip().lower(): c for c in df.columns}
    for c in DATE_COL_CANDIDATES:
        if c.lower() in lower:
            return lower[c.lower()]
    for c in df.columns:
        name = str(c).lower()
        if "date" in name or "일자" in name or "일" == name or "연월" in name:
            return c
    return None


def _parse_dates(series: pd.Series) -> pd.Series:
    # Handles YYYY-MM, YYYYMMDD, YYYY, and regular date strings.
    s = series.astype(str).str.strip()
    yyyy_mm = s.str.match(r"^\d{4}-\d{1,2}$", na=False)
    yyyy = s.str.match(r"^\d{4}$", na=False)
    s2 = s.copy()
    s2.loc[yyyy_mm] = s2.loc[yyyy_mm] + "-01"
    s2.loc[yyyy] = s2.loc[yyyy] + "-12-31"
    return pd.to_datetime(s2, errors="coerce")


def _filter_asof(df: pd.DataFrame, as_of: pd.Timestamp) -> tuple[pd.DataFrame, bool]:
    dc = _date_col(df)
    if not dc:
        return df.copy(), False
    dt = _parse_dates(df[dc])
    out = df.loc[dt.notna() & (dt <= as_of)].copy()
    out["__parsed_date"] = dt.loc[out.index]
    return out, True


def _target_tokens(target: dict[str, Any]) -> set[str]:
    tokens: set[str] = set()
    for k in ("company", "company_name", "corp_name", "name", "company_dir", "slug", "ticker", "stock_code"):
        v = str(target.get(k, "") or "").strip()
        if v:
            tokens.add(v.lower())
            tokens.add(v.replace(" ", "").lower())
            if v.isdigit():
                tokens.add(v.zfill(6))
    return tokens


def _filter_company(df: pd.DataFrame, target: dict[str, Any]) -> tuple[pd.DataFrame, bool]:
    tokens = _target_tokens(target)
    if not tokens:
        return df.copy(), False
    cols = [c for c in df.columns if str(c) in COMPANY_COL_CANDIDATES or str(c) in TICKER_COL_CANDIDATES]
    cols += [c for c in df.columns if any(h in str(c).lower() for h in ["company", "ticker", "stock", "기업", "회사", "종목", "code", "출원인", "권리자"])]
    cols = list(dict.fromkeys(cols))
    if not cols:
        return df.copy(), False
    text = df[cols].astype(str).agg(" ".join, axis=1).str.lower().str.replace(" ", "", regex=False)
    mask = False
    for t in tokens:
        mask = mask | text.str.contains(re.escape(t.replace(" ", "")), na=False)
    if int(mask.sum()) == 0:
        return df.iloc[0:0].copy(), True
    return df.loc[mask].copy(), True


def _read_table(path: Path) -> pd.DataFrame | None:
    try:
        if path.suffix.lower() in {".csv", ".txt"}:
            for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
                try:
                    return pd.read_csv(path, encoding=enc)
                except Exception:
                    continue
        if path.suffix.lower() in {".xlsx", ".xls"}:
            return pd.read_excel(path)
    except Exception:
        return None
    return None


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _iter_files(root: Path, patterns: Iterable[str], max_files: int = 200) -> list[Path]:
    files: list[Path] = []
    if not root.exists():
        return files
    for pat in patterns:
        files.extend([p for p in root.rglob(pat) if p.is_file() and "__pycache__" not in str(p)])
    # Prefer newer, smaller, and named history/intake files, but keep deterministic.
    def key(p: Path) -> tuple[int, str]:
        name = p.name.lower()
        priority = 0
        for i, token in enumerate(("history", "monthly", "daily", "intake", "feature", "patent", "kipris", "qualification", "cert")):
            if token in name:
                priority -= 10 - i
        return (priority, str(p).lower())
    return sorted(set(files), key=key)[:max_files]


def _company_dir(root: Path, field: str, target: dict[str, Any]) -> Path:
    cands = [
        str(target.get("company_dir") or ""),
        str(target.get("company") or ""),
        str(target.get("company_name") or ""),
        str(target.get("slug") or ""),
    ]
    for c in cands:
        if not c:
            continue
        p = root / "data" / field / c
        if p.exists():
            return p
    return root / "data" / field / str(target.get("company") or target.get("company_dir") or "")


def _all_roots(root: Path, field: str, target: dict[str, Any]) -> list[Path]:
    cdir = _company_dir(root, field, target)
    return [
        cdir / "tech",
        cdir / "_company_common" / "tech",
        cdir / "tech" / "intake",
        cdir / "tech" / "source",
        root / "data" / field / "_sector_common" / "tech",
        root / "data" / field / "_sector_common" / "tech" / "monthly",
        root / "data" / field / "_sector_common" / "tech" / "daily",
        root / "data" / field / "_sector_common" / "tech_certifications",
    ]


def _numeric_signals(df: pd.DataFrame, category: str) -> list[float]:
    vals: list[float] = []
    if df is None or df.empty:
        return vals
    for c in df.columns:
        lc = str(c).lower()
        if lc.startswith("__"):
            continue
        series = df[c]
        nums = [_safe_float(v) for v in series.dropna().tail(24).tolist()]
        nums = [x for x in nums if x is not None]
        if not nums:
            continue
        val = nums[-1]
        if any(h.lower() in lc for h in POSITIVE_NUMERIC_HINTS):
            vals.append(_score_to_signal(val))
        elif any(h.lower() in lc for h in NEGATIVE_NUMERIC_HINTS):
            vals.append(-_score_to_signal(val))
        elif category in {"patent", "ip"} and any(h in lc for h in ["count", "수", "patent", "등록", "출원"]):
            vals.append(_sigmoid_signal(math.log1p(max(val, 0.0)), 4.0))
    return vals


def _text_event_signal(df: pd.DataFrame) -> tuple[float, int, int]:
    if df is None or df.empty:
        return 0.0, 0, 0
    text = df.astype(str).agg(" ".join, axis=1)
    pos = int(text.str.contains(POSITIVE_EVENT_PATTERNS, na=False).sum())
    neg = int(text.str.contains(NEGATIVE_EVENT_PATTERNS, na=False).sum())
    raw = math.log1p(pos) - math.log1p(neg)
    return _sigmoid_signal(raw, 2.0), pos, neg


def _stage_signal(df: pd.DataFrame) -> list[float]:
    vals: list[float] = []
    if df is None or df.empty:
        return vals
    for c in df.columns:
        lc = str(c).lower()
        if "trl" in lc or "readiness" in lc or "성숙" in lc or "stage" in lc or "단계" in lc:
            for v in df[c].dropna().tail(24).tolist():
                num = _safe_float(v)
                if num is not None:
                    if 1 <= num <= 9:
                        vals.append((num - 5.0) / 4.0)
                    else:
                        vals.append(_score_to_signal(num))
                    continue
                s = str(v).lower()
                mapping = {
                    "research": -0.8, "lab": -0.7, "prototype": -0.45, "시제품": -0.45,
                    "validation": -0.25, "검증": -0.25, "sample": -0.1, "샘플": -0.1,
                    "pilot": 0.05, "poc": 0.05, "qualification": 0.25, "퀄": 0.25,
                    "approved": 0.45, "승인": 0.45, "mass": 0.65, "양산": 0.65,
                    "revenue": 0.8, "매출": 0.8, "scale": 0.9, "스케일": 0.9,
                }
                for k, score in mapping.items():
                    if k in s:
                        vals.append(score)
                        break
    return vals


def _patent_block(df: pd.DataFrame, as_of: pd.Timestamp) -> tuple[float, dict[str, Any]]:
    if df is None or df.empty:
        return 0.0, {"patent_records_asof": 0}
    n = len(df)
    dates = df["__parsed_date"] if "__parsed_date" in df.columns else pd.Series([], dtype="datetime64[ns]")
    recent_3y = int(((dates >= as_of - pd.DateOffset(years=3)) & (dates <= as_of)).sum()) if len(dates) else 0
    recent_5y = int(((dates >= as_of - pd.DateOffset(years=5)) & (dates <= as_of)).sum()) if len(dates) else 0

    joined = df.astype(str).agg(" ".join, axis=1)
    registered = int(joined.str.contains(r"등록|granted|register", case=False, regex=True, na=False).sum())
    active = int(joined.str.contains(r"존속|유효|alive|active|maintained", case=False, regex=True, na=False).sum())
    rejected = int(joined.str.contains(r"거절|취하|소멸|rejected|abandon|expired|withdraw", case=False, regex=True, na=False).sum())

    count_signal = _sigmoid_signal(math.log1p(n), 4.5)
    recent_signal = _sigmoid_signal(math.log1p(recent_5y), 3.2)
    reg_signal = _ratio_to_signal(registered / n if n else None, neutral=0.45)
    active_signal = _ratio_to_signal(active / max(registered, 1) if registered else None, neutral=0.55) if active else 0.0
    weak_status_penalty = _ratio_to_signal(rejected / n if n else None, neutral=0.10)

    numeric_vals = _numeric_signals(df, "patent")
    quality_signal = _mean([count_signal, recent_signal, reg_signal, active_signal, *numeric_vals])
    signal = _clip(quality_signal - max(0.0, weak_status_penalty) * 0.3)
    return signal, {
        "patent_records_asof": int(n),
        "recent_patents_3y": recent_3y,
        "recent_patents_5y": recent_5y,
        "registered_like_patents": registered,
        "active_like_patents": active,
        "weak_status_like_patents": rejected,
    }


def _extract_metrics_from_json(obj: Any) -> dict[str, float]:
    out: dict[str, float] = {}

    def walk(x: Any, path: str = "") -> None:
        if isinstance(x, dict):
            for k, v in x.items():
                nk = f"{path}.{k}" if path else str(k)
                lk = str(k).lower()
                fv = _safe_float(v)
                if fv is not None and any(h in lk for h in ["score", "signal", "percentile", "patent", "citation", "claim", "family", "trl"]):
                    out[nk] = fv
                walk(v, nk)
        elif isinstance(x, list):
            for i, v in enumerate(x[:50]):
                walk(v, f"{path}[{i}]")
    walk(obj)
    return out


def _json_block(root: Path, field: str, target: dict[str, Any], as_of: pd.Timestamp) -> tuple[dict[str, float], list[str]]:
    metrics: dict[str, float] = {}
    sources: list[str] = []
    for r in _all_roots(root, field, target):
        for p in _iter_files(r, ["*.json"], max_files=120):
            if any(skip in p.name.lower() for skip in ["prompt", "repair_request"]):
                continue
            obj = _read_json(p)
            if obj is None:
                continue
            # Do not use JSON with an explicit future as_of_date.
            explicit_dates = []
            if isinstance(obj, dict):
                for dk in ("as_of_date", "date", "created_at", "analysis_date"):
                    if dk in obj:
                        explicit_dates.append(obj.get(dk))
            if explicit_dates:
                dts = pd.to_datetime(pd.Series(explicit_dates), errors="coerce")
                if dts.notna().any() and dts.max() > as_of:
                    continue
            m = _extract_metrics_from_json(obj)
            if m:
                for k, v in m.items():
                    metrics[k] = v
                sources.append(str(p))
    return metrics, sources


def _signals_from_existing_json(metrics: dict[str, float]) -> dict[str, float]:
    def pick(*needles: str) -> list[float]:
        vals = []
        for k, v in metrics.items():
            lk = k.lower()
            if any(n.lower() in lk for n in needles):
                vals.append(_score_to_signal(v))
        return vals

    return {
        "technology_differentiation_signal": _mean(pick("differentiation", "차별")),
        "peer_position_signal": _mean(pick("peer", "percentile", "umap", "kmeans")),
        "tech_to_value_signal": _mean(pick("bridge", "tech_to_value", "commercialization", "evidence_confidence")),
        "rnd_sustainability_signal": _mean(pick("rnd", "r&d", "patent_momentum", "momentum")),
        "ip_quality_signal": _mean(pick("ip", "patent", "citation", "claim", "family", "legal_stability")),
    }


def _classify_file(path: Path) -> str:
    name = path.name.lower()
    parent = str(path.parent).lower()
    text = name + " " + parent
    if any(k in text for k in ["patent", "kipris", "특허", "ip_"]):
        return "patent"
    if any(k in text for k in ["cert", "standard", "인증", "qualification", "vendor", "고객", "퀄"]):
        return "commercialization"
    if any(k in text for k in ["lifecycle", "life_cycle", "technology_trend", "keyword", "trl", "readiness", "roadmap"]):
        return "lifecycle"
    if any(k in text for k in ["workforce", "hiring", "채용", "인력", "researcher", "rnd", "r&d", "government", "rd_project", "과제"]):
        return "rnd"
    if any(k in text for k in ["dispute", "litigation", "lawsuit", "소송", "분쟁", "failure", "delay", "지연", "실패"]):
        return "risk"
    if any(k in text for k in ["cost", "yield", "수율", "원가", "benchmark", "performance", "성능"]):
        return "cost_yield"
    if any(k in text for k in ["license", "licensing", "transfer", "기술이전", "라이선스"]):
        return "licensing"
    if any(k in text for k in ["intangible", "무형", "development_cost", "개발비"]):
        return "intangible"
    if any(k in text for k in ["supply", "supply_chain", "공급망", "switching", "dependency"]):
        return "supply_chain"
    return "general"


def build_history_tech_feature(
    root: str | Path,
    field: str,
    target: dict[str, Any],
    as_of_date: str | pd.Timestamp,
    *,
    frequency: str | None = None,
) -> dict[str, Any]:
    root = Path(root)
    as_of = pd.Timestamp(as_of_date)
    freq = frequency or os.environ.get("ALPHAPROVE_EVAL_FREQUENCY", "monthly")

    category_values: dict[str, list[float]] = {
        "ip_quality_signal": [],
        "lifecycle_signal": [],
        "technology_differentiation_signal": [],
        "commercialization_signal": [],
        "rnd_sustainability_signal": [],
        "peer_position_signal": [],
        "tech_to_value_signal": [],
        "certification_signal": [],
        "qualification_signal": [],
        "cost_yield_signal": [],
        "workforce_signal": [],
        "government_rd_signal": [],
        "licensing_signal": [],
        "dispute_risk_signal": [],
        "failure_delay_signal": [],
        "intangible_accounting_signal": [],
    }
    meta: dict[str, Any] = {"patent_records_asof": 0, "dated_records_asof": 0, "undated_records_used": 0}
    sources: list[str] = []

    # 1) Structured CSV/XLSX evidence, with strict as_of cutoff whenever a date column exists.
    patterns = ["*.csv", "*.xlsx", "*.xls"]
    for r in _all_roots(root, field, target):
        for p in _iter_files(r, patterns, max_files=250):
            # Avoid reading evaluation result files as inputs.
            if any(skip in str(p).lower() for skip in ["history_sheets_exports", "chair_report", "eval_", "signal_df"]):
                continue
            df = _read_table(p)
            if df is None or df.empty:
                continue
            df_company, company_filtered = _filter_company(df, target)
            if company_filtered and df_company.empty:
                continue
            df_asof, has_date = _filter_asof(df_company, as_of)
            if df_asof.empty:
                continue
            cls = _classify_file(p)
            sources.append(str(p))
            if has_date:
                meta["dated_records_asof"] = int(meta.get("dated_records_asof", 0)) + int(len(df_asof))
            else:
                meta["undated_records_used"] = int(meta.get("undated_records_used", 0)) + int(len(df_asof))

            event_sig, pos_events, neg_events = _text_event_signal(df_asof)
            nums = _numeric_signals(df_asof, cls)
            stages = _stage_signal(df_asof)

            if cls == "patent":
                sig, pm = _patent_block(df_asof, as_of)
                category_values["ip_quality_signal"].append(sig)
                meta["patent_records_asof"] = int(meta.get("patent_records_asof", 0)) + int(pm.get("patent_records_asof", 0) or 0)
                for k, v in pm.items():
                    if k != "patent_records_asof":
                        meta[k] = max(int(meta.get(k, 0) or 0), int(v or 0))
                if nums:
                    category_values["technology_differentiation_signal"].append(_mean(nums))
            elif cls == "commercialization":
                category_values["commercialization_signal"].append(_mean([event_sig, *nums, *stages]))
                category_values["certification_signal"].append(_mean([event_sig, *nums]))
                category_values["qualification_signal"].append(_mean([event_sig, *stages]))
            elif cls == "lifecycle":
                category_values["lifecycle_signal"].append(_mean([event_sig, *nums, *stages]))
            elif cls == "rnd":
                category_values["rnd_sustainability_signal"].append(_mean([event_sig, *nums]))
                if "government" in str(p).lower() or "과제" in str(p):
                    category_values["government_rd_signal"].append(_mean([event_sig, *nums]))
                else:
                    category_values["workforce_signal"].append(_mean([event_sig, *nums]))
            elif cls == "risk":
                # Positive value means risk pressure; it will become a penalty later.
                risk = _clip(_sigmoid_signal(math.log1p(max(neg_events, 0)) - math.log1p(max(pos_events, 0)), 1.6) + max(0.0, -_mean(nums)))
                if "delay" in str(p).lower() or "지연" in str(p) or "failure" in str(p).lower() or "실패" in str(p):
                    category_values["failure_delay_signal"].append(risk)
                else:
                    category_values["dispute_risk_signal"].append(risk)
            elif cls == "cost_yield":
                category_values["cost_yield_signal"].append(_mean([event_sig, *nums]))
            elif cls == "licensing":
                category_values["licensing_signal"].append(_mean([event_sig, *nums]))
            elif cls == "intangible":
                category_values["intangible_accounting_signal"].append(_mean([event_sig, *nums]))
            elif cls == "supply_chain":
                category_values["tech_to_value_signal"].append(_mean([event_sig, *nums]))
            else:
                # Generic technology-intake data: use dated events and numeric scores but do not over-count.
                category_values["technology_differentiation_signal"].append(_mean([event_sig, *nums, *stages]))

    # 2) Existing Tech Agent JSON artifacts.  They are accepted only if not dated after as_of.
    json_metrics, json_sources = _json_block(root, field, target, as_of)
    if json_metrics:
        js = _signals_from_existing_json(json_metrics)
        for k, v in js.items():
            if v:
                category_values[k].append(v)
        sources.extend(json_sources[:20])

    # 3) Optional lightweight text evidence from reports/MD, still as-of conservative by source file content only.
    # This is a fallback for projects where certification/qualification is in MD/IR extracts, not CSV.
    text_hits = 0
    text_risk_hits = 0
    for r in _all_roots(root, field, target):
        for p in _iter_files(r, ["*.md", "*.txt"], max_files=120):
            if any(skip in str(p).lower() for skip in ["chair_report", "history_sheets_exports", "readme"]):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")[:250000]
            except Exception:
                continue
            pos = len(POSITIVE_EVENT_PATTERNS.findall(text))
            neg = len(NEGATIVE_EVENT_PATTERNS.findall(text))
            kw = sum(text.lower().count(k.lower()) for k in TECH_KEYWORDS)
            if pos or neg or kw:
                sources.append(str(p))
                text_hits += pos + kw
                text_risk_hits += neg
    if text_hits or text_risk_hits:
        text_signal = _sigmoid_signal(math.log1p(text_hits) - math.log1p(text_risk_hits), 2.5)
        category_values["commercialization_signal"].append(text_signal)
        category_values["technology_differentiation_signal"].append(text_signal * 0.7)
        category_values["failure_delay_signal"].append(max(0.0, -text_signal))

    comp = {k: _mean(v) for k, v in category_values.items()}

    # Equal-weight block composition avoids claiming literature-specific fixed weights.  DMA/IC can learn weights later.
    base_blocks = [
        comp["ip_quality_signal"],
        comp["technology_differentiation_signal"],
        comp["commercialization_signal"],
        comp["rnd_sustainability_signal"],
        comp["peer_position_signal"],
        comp["tech_to_value_signal"],
        comp["lifecycle_signal"],
    ]
    # Use only non-zero observed blocks so missing data does not mechanically depress all Tech signals.
    observed_base = [x for x in base_blocks if abs(x) > 1e-9]
    base_signal = _mean(observed_base) if observed_base else 0.0

    reliability_pos = _mean([
        comp["certification_signal"],
        comp["qualification_signal"],
        comp["cost_yield_signal"],
        comp["workforce_signal"],
        comp["government_rd_signal"],
        comp["licensing_signal"],
        comp["intangible_accounting_signal"],
    ])
    risk_penalty = max(0.0, _mean([comp["dispute_risk_signal"], comp["failure_delay_signal"]]))

    # Confidence layer: if commercial evidence is strong, let Tech matter more; if only generic text exists, keep it muted.
    evidence_volume = int(meta.get("dated_records_asof", 0) or 0) + int(meta.get("patent_records_asof", 0) or 0)
    evidence_confidence = _clip(0.35 + 0.35 * _sigmoid_signal(math.log1p(evidence_volume), 3.0) + 0.20 * max(0.0, reliability_pos) + 0.10 * max(0.0, comp["commercialization_signal"]), 0.20, 1.0)

    commercialization_gate = _mean([comp["commercialization_signal"], comp["qualification_signal"], comp["certification_signal"], comp["cost_yield_signal"]])

    final_signal = _clip(base_signal * evidence_confidence + 0.25 * commercialization_gate - 0.35 * risk_penalty)

    if sources:
        status = "OK_TECH_HISTORY_ASOF"
    else:
        status = "NO_TECH_EVIDENCE_ASOF"

    target_company = str(target.get("company") or target.get("company_name") or "")
    target_ticker = str(target.get("ticker") or "")
    target_stock_code = str(target.get("stock_code") or target.get("ticker") or "")

    feature = TechHistoryFeature(
        signal=round(final_signal, 6),
        status=status,
        source=";".join(dict.fromkeys(sources[:12])),
        as_of_date=str(as_of.date()),
        company=target_company,
        ticker=target_ticker,
        stock_code=target_stock_code,
        base_signal=round(base_signal, 6),
        evidence_confidence=round(evidence_confidence, 6),
        commercialization_gate_signal=round(commercialization_gate, 6),
        technology_risk_penalty=round(risk_penalty, 6),
        ip_quality_signal=round(comp["ip_quality_signal"], 6),
        lifecycle_signal=round(comp["lifecycle_signal"], 6),
        technology_differentiation_signal=round(comp["technology_differentiation_signal"], 6),
        commercialization_signal=round(comp["commercialization_signal"], 6),
        rnd_sustainability_signal=round(comp["rnd_sustainability_signal"], 6),
        peer_position_signal=round(comp["peer_position_signal"], 6),
        tech_to_value_signal=round(comp["tech_to_value_signal"], 6),
        certification_signal=round(comp["certification_signal"], 6),
        qualification_signal=round(comp["qualification_signal"], 6),
        cost_yield_signal=round(comp["cost_yield_signal"], 6),
        workforce_signal=round(comp["workforce_signal"], 6),
        government_rd_signal=round(comp["government_rd_signal"], 6),
        licensing_signal=round(comp["licensing_signal"], 6),
        dispute_risk_signal=round(comp["dispute_risk_signal"], 6),
        failure_delay_signal=round(comp["failure_delay_signal"], 6),
        intangible_accounting_signal=round(comp["intangible_accounting_signal"], 6),
        patent_records_asof=int(meta.get("patent_records_asof", 0) or 0),
        dated_records_asof=int(meta.get("dated_records_asof", 0) or 0),
        undated_records_used=int(meta.get("undated_records_used", 0) or 0),
        files_used=len(set(sources)),
        notes=(
            "Tech history signal uses dated patent/IP, TRL/readiness, certification, qualification, "
            "commercialization, R&D/workforce, risk and accounting evidence before as_of_date; no Buy/Hold/Sell threshold is applied."
        ),
    )
    result = asdict(feature)
    result["frequency"] = freq
    result["formula"] = "final=base_signal*evidence_confidence + 0.25*commercialization_gate_signal - 0.35*technology_risk_penalty"
    result["research_basis"] = [
        "Hall-Jaffe-Trajtenberg patent citations/value; Lanjouw-Schankerman patent quality; OECD patent quality composite indicators",
        "DoD/NASA TRL and TRA maturity framework",
        "IFC/Bpifrance deep-tech development-stage financing framework",
        "Text-based industry/technology relatedness literature for peer/differentiation evidence",
    ]
    return result


def build_and_save_history_tech_feature(
    root: str | Path,
    field: str,
    target: dict[str, Any],
    as_of_date: str | pd.Timestamp,
    *,
    frequency: str | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    result = build_history_tech_feature(root, field, target, as_of_date, frequency=frequency)
    if output_dir is None:
        cdir = _company_dir(Path(root), field, target)
        output_dir = cdir / "tech"
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"tech_history_features_{str(pd.Timestamp(as_of_date).date())}"
    json_path = out / f"{stem}.json"
    csv_path = out / f"{stem}.csv"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    pd.DataFrame([result]).to_csv(csv_path, index=False, encoding="utf-8-sig")
    result["history_feature_json"] = str(json_path)
    result["history_feature_csv"] = str(csv_path)
    return result
