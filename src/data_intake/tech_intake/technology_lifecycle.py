from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from common.data_paths import company_agent_dir, field_common_dir, normalize_field_name

DEFAULT_FIELD = "반도체"

DEFAULT_TECH_KEYWORD_ALIASES: dict[str, list[str]] = {
    "advanced_packaging": ["advanced packaging", "첨단패키징", "고급패키징", "패키징", "package", "packaging", "패키지"],
    "hbm_ai_memory": ["HBM", "고대역폭", "AI memory", "AI 메모리", "memory", "메모리"],
    "fan_out_wlp": ["fan-out", "fanout", "FOWLP", "WLP", "wafer level", "웨이퍼 레벨", "팬아웃"],
    "bump_rdl_interposer": ["bump", "범프", "RDL", "재배선", "interposer", "인터포저", "substrate", "기판"],
    "semiconductor_test": ["test", "테스트", "검사", "probe", "프로브", "socket", "소켓", "burn-in", "번인"],
    "semiconductor_materials": ["전구체", "precursor", "photoresist", "포토레지스트", "etchant", "식각", "CMP", "slurry", "슬러리", "소재"],
    "process_yield_quality": ["수율", "yield", "불량", "defect", "reliability", "신뢰성", "공정", "process"],
    "power_thermal_efficiency": ["전력", "power", "thermal", "열", "방열", "heat", "효율", "efficiency"],
}

EXTERNAL_SIGNAL_FILENAMES = [
    "technology_lifecycle_external_signals.csv",
    "tech_lifecycle_external_signals.csv",
    "keyword_report_trends.csv",
]


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return float(value)
    text = _clean(value).replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        out = float(text)
    except Exception:
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def _year(value: Any) -> int | None:
    n = _num(value)
    if n is not None:
        y = int(n)
        if 1900 <= y <= 2100:
            return y
    text = _clean(value)
    m = re.search(r"(19|20)\d{2}", text)
    if m:
        return int(m.group(0))
    return None


def _load_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def find_patent_csv(tech_dir: Path, slug: str) -> Path | None:
    candidates = [
        tech_dir / f"{slug}_kipris_bibliographic_normalized.csv",
        tech_dir / f"{slug}_kipris_patents_normalized.csv",
        tech_dir / f"{slug}_tech_patent_normalized.csv",
        tech_dir / "kipris_bibliographic_normalized.csv",
        tech_dir / "kipris_patents_normalized.csv",
        tech_dir / "tech_patent_normalized.csv",
        tech_dir / "source" / f"{slug}_kipris_bibliographic_normalized.csv",
        tech_dir / "source" / f"{slug}_kipris_patents_normalized.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    found = sorted(tech_dir.glob("*kipris*bibliographic*normalized*.csv"))
    if found:
        return found[0]
    found = sorted(tech_dir.glob("*patent*normalized*.csv"))
    return found[0] if found else None


def _keyword_aliases_from_arg(raw: str | None) -> dict[str, list[str]]:
    if not raw:
        return dict(DEFAULT_TECH_KEYWORD_ALIASES)
    out: dict[str, list[str]] = {}
    for token in re.split(r"[,;|]", raw):
        word = token.strip()
        if not word:
            continue
        key = re.sub(r"[^0-9A-Za-z가-힣]+", "_", word).strip("_").lower() or word
        out[key] = [word]
    return out or dict(DEFAULT_TECH_KEYWORD_ALIASES)


def _row_text(row: pd.Series) -> str:
    cols = [
        "invention_title", "title", "abstract", "claim_text", "claims",
        "ipc_number", "ipc", "cpc_number", "cpc", "legal_status",
    ]
    return " ".join(_clean(row.get(c)) for c in cols if c in row.index).lower()


def _contains_alias(text: str, aliases: Iterable[str]) -> bool:
    lower_aliases = [a.lower().strip() for a in aliases if str(a).strip()]
    return any(alias in text for alias in lower_aliases)


def _classify_keyword_stage(
    *,
    first_year: int | None,
    latest_year: int | None,
    total_count: int,
    recent_count: int,
    baseline_count: int,
    recent_avg: float,
    baseline_avg: float,
    trend_ratio: float | None,
) -> tuple[str, str, float]:
    if total_count <= 0:
        return "NO_DATA", "특허 출원 추세 데이터가 없습니다.", 0.0

    age = (latest_year - first_year + 1) if first_year and latest_year else None
    recent_share = recent_count / total_count if total_count else 0.0

    if total_count <= 2:
        return "INTRODUCTION_OR_SPARSE", "출원 수가 적어 도입기 또는 확인 제한으로 분류합니다.", 35.0
    if baseline_count == 0 and recent_count > 0:
        return "INTRODUCTION_TO_GROWTH", "과거 구간 대비 최근 출원이 새로 확인되어 도입기에서 성장기로 넘어가는 신호입니다.", 65.0
    if trend_ratio is not None and trend_ratio >= 1.35 and recent_count >= 3:
        return "GROWTH", "최근 출원 밀도가 과거 구간보다 뚜렷하게 높아 성장기 신호로 분류합니다.", min(90.0, 60.0 + (trend_ratio - 1.0) * 20.0)
    if trend_ratio is not None and trend_ratio <= 0.65 and baseline_count >= 3:
        return "DECLINE_OR_SHIFT", "과거 대비 최근 출원 밀도가 약해져 쇠퇴 또는 기술 전환 신호로 분류합니다.", 30.0
    if age is not None and age >= 7 and recent_share >= 0.15:
        return "MATURITY", "장기간 출원이 누적되고 최근 출원도 유지되어 성숙기 신호로 분류합니다.", 55.0
    if trend_ratio is not None and 0.65 < trend_ratio < 1.35:
        return "STABLE_MATURITY", "최근과 과거 출원 밀도가 유사해 안정적 성숙기 신호로 분류합니다.", 50.0
    return "UNCERTAIN", "출원 추세만으로 수명주기 단계를 단정하기 어렵습니다.", 40.0


def _find_external_signal_files(*, field: str, tech_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for name in EXTERNAL_SIGNAL_FILENAMES:
        candidates.append(tech_dir / "source" / name)
        candidates.append(tech_dir / name)
    try:
        common = field_common_dir("tech_lifecycle", field=field, create=True)
        for name in EXTERNAL_SIGNAL_FILENAMES:
            candidates.append(common / name)
    except Exception:
        pass
    return [p for p in candidates if p.exists()]


def _load_external_signals(*, field: str, tech_dir: Path, keyword_aliases: dict[str, list[str]]) -> dict[str, Any]:
    files = _find_external_signal_files(field=field, tech_dir=tech_dir)
    if not files:
        return {
            "status": "NOT_PROVIDED",
            "files": [],
            "summary": "논문/보고서 증가 추세, 산업 리포트 채택 단계, 고객 산업 채택 속도는 외부 CSV가 없어 확인 제한입니다.",
            "by_keyword": {},
        }

    records: list[dict[str, Any]] = []
    for p in files:
        try:
            df = _load_csv(p)
        except Exception as exc:
            records.append({"source_file": str(p), "error": repr(exc)})
            continue
        for _, row in df.iterrows():
            rec = {str(k): row.get(k) for k in df.columns}
            rec["source_file"] = str(p)
            records.append(rec)

    by_keyword: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rec in records:
        text = " ".join(_clean(v) for v in rec.values()).lower()
        explicit = _clean(rec.get("keyword") or rec.get("tech_keyword") or rec.get("technology") or "")
        matched = False
        for key, aliases in keyword_aliases.items():
            if explicit and (explicit.lower() == key.lower() or explicit.lower() in [a.lower() for a in aliases]):
                by_keyword[key].append(rec)
                matched = True
            elif _contains_alias(text, aliases):
                by_keyword[key].append(rec)
                matched = True
        if not matched:
            by_keyword["unmatched"].append(rec)

    return {
        "status": "LOADED",
        "files": [str(p) for p in files],
        "record_count": len(records),
        "by_keyword": {k: v[:20] for k, v in by_keyword.items()},
        "summary": "외부 수명주기 CSV를 로드했습니다. stage/adoption/report_count/paper_count 컬럼이 있으면 Chair 해석에 보조 근거로 사용할 수 있습니다.",
    }


def _safe_round(value: float | None, ndigits: int = 4) -> float | None:
    if value is None or math.isnan(value) or math.isinf(value):
        return None
    return round(float(value), ndigits)


def build_technology_lifecycle_features(
    *,
    company_dir: str,
    company: str | None = None,
    field: str = DEFAULT_FIELD,
    keywords: str | None = None,
    recent_window: int = 3,
    baseline_window: int = 5,
    write: bool = True,
) -> dict[str, Any]:
    field = normalize_field_name(field)
    slug = company_dir
    display = company or slug
    tech_dir = company_agent_dir(slug, "tech", create=True)
    patent_csv = find_patent_csv(tech_dir, slug)
    keyword_aliases = _keyword_aliases_from_arg(keywords)

    result: dict[str, Any] = {
        "feature_name": "technology_lifecycle",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "field": field,
        "company_dir": slug,
        "company": display,
        "source_patent_csv": str(patent_csv) if patent_csv else None,
        "recent_window_years": recent_window,
        "baseline_window_years": baseline_window,
        "keyword_aliases": keyword_aliases,
        "status": "INIT",
    }

    if not patent_csv or not patent_csv.exists():
        result.update({
            "status": "NO_PATENT_CSV",
            "overall_lifecycle_stage": "UNKNOWN",
            "overall_lifecycle_score": 0.0,
            "summary": "정규화된 KIPRIS 특허 CSV가 없어 기술 수명주기 추세를 계산하지 못했습니다.",
            "keyword_trends": [],
            "external_signals": _load_external_signals(field=field, tech_dir=tech_dir, keyword_aliases=keyword_aliases),
        })
        if write:
            _persist_outputs(result, tech_dir, slug)
        return result

    df = _load_csv(patent_csv)
    if df.empty:
        result.update({
            "status": "EMPTY_PATENT_CSV",
            "overall_lifecycle_stage": "UNKNOWN",
            "overall_lifecycle_score": 0.0,
            "summary": "특허 CSV는 존재하지만 행이 없어 기술 수명주기 추세를 계산하지 못했습니다.",
            "keyword_trends": [],
            "external_signals": _load_external_signals(field=field, tech_dir=tech_dir, keyword_aliases=keyword_aliases),
        })
        if write:
            _persist_outputs(result, tech_dir, slug)
        return result

    year_col = "application_year" if "application_year" in df.columns else None
    if year_col is None:
        for cand in ["application_date", "open_date", "publication_date", "register_date", "registration_date"]:
            if cand in df.columns:
                year_col = cand
                break
    if year_col is None:
        years = pd.Series([None] * len(df))
    else:
        years = df[year_col].apply(_year)
    df = df.copy()
    df["_application_year_norm"] = years
    df = df[df["_application_year_norm"].notna()].copy()
    df["_application_year_norm"] = df["_application_year_norm"].astype(int)

    if df.empty:
        result.update({
            "status": "NO_VALID_PATENT_YEAR",
            "overall_lifecycle_stage": "UNKNOWN",
            "overall_lifecycle_score": 0.0,
            "summary": "특허 데이터에서 유효한 출원연도를 찾지 못했습니다.",
            "keyword_trends": [],
            "external_signals": _load_external_signals(field=field, tech_dir=tech_dir, keyword_aliases=keyword_aliases),
        })
        if write:
            _persist_outputs(result, tech_dir, slug)
        return result

    latest_year = int(df["_application_year_norm"].max())
    recent_start = latest_year - max(1, recent_window) + 1
    baseline_end = recent_start - 1
    baseline_start = baseline_end - max(1, baseline_window) + 1

    trends: list[dict[str, Any]] = []
    annual_rows: list[dict[str, Any]] = []
    for key, aliases in keyword_aliases.items():
        mask = df.apply(lambda row: _contains_alias(_row_text(row), aliases), axis=1)
        sub = df[mask].copy()
        annual = sub.groupby("_application_year_norm").size().to_dict() if not sub.empty else {}
        for y, cnt in sorted(annual.items()):
            annual_rows.append({"keyword": key, "year": int(y), "patent_application_count": int(cnt)})

        total_count = int(len(sub))
        first_year = int(sub["_application_year_norm"].min()) if total_count else None
        key_latest = int(sub["_application_year_norm"].max()) if total_count else None
        recent_count = int(((sub["_application_year_norm"] >= recent_start) & (sub["_application_year_norm"] <= latest_year)).sum()) if total_count else 0
        baseline_count = int(((sub["_application_year_norm"] >= baseline_start) & (sub["_application_year_norm"] <= baseline_end)).sum()) if total_count else 0
        recent_avg = recent_count / max(1, recent_window)
        baseline_avg = baseline_count / max(1, baseline_window)
        trend_ratio = (recent_avg / baseline_avg) if baseline_avg > 0 else None
        stage, reason, score = _classify_keyword_stage(
            first_year=first_year,
            latest_year=key_latest,
            total_count=total_count,
            recent_count=recent_count,
            baseline_count=baseline_count,
            recent_avg=recent_avg,
            baseline_avg=baseline_avg,
            trend_ratio=trend_ratio,
        )
        top_titles = []
        if total_count:
            sort_cols = ["_application_year_norm"]
            sub_sorted = sub.sort_values(sort_cols, ascending=False)
            for _, r in sub_sorted.head(5).iterrows():
                top_titles.append({
                    "year": int(r.get("_application_year_norm")),
                    "title": _clean(r.get("invention_title") or r.get("title")),
                    "application_number": _clean(r.get("application_number") or r.get("application_no")),
                })
        trends.append({
            "keyword": key,
            "aliases": aliases,
            "total_patent_count": total_count,
            "first_application_year": first_year,
            "latest_application_year": key_latest,
            "recent_count": recent_count,
            "baseline_count": baseline_count,
            "recent_avg_per_year": _safe_round(recent_avg, 3),
            "baseline_avg_per_year": _safe_round(baseline_avg, 3),
            "trend_ratio_recent_vs_baseline": _safe_round(trend_ratio, 3) if trend_ratio is not None else None,
            "lifecycle_stage": stage,
            "lifecycle_score": _safe_round(score, 2),
            "reason": reason,
            "recent_patent_examples": top_titles,
        })

    nonzero = [t for t in trends if t["total_patent_count"] > 0]
    if nonzero:
        weighted_score = sum(float(t["lifecycle_score"] or 0) * int(t["total_patent_count"] or 0) for t in nonzero) / sum(int(t["total_patent_count"] or 0) for t in nonzero)
        stage_counts: dict[str, int] = defaultdict(int)
        for t in nonzero:
            stage_counts[str(t["lifecycle_stage"])] += int(t["total_patent_count"] or 0)
        overall_stage = max(stage_counts.items(), key=lambda x: x[1])[0]
        top_keywords = sorted(nonzero, key=lambda t: (int(t["recent_count"] or 0), int(t["total_patent_count"] or 0)), reverse=True)[:5]
        summary = _make_summary(overall_stage, weighted_score, top_keywords)
        status = "OK"
    else:
        weighted_score = 0.0
        overall_stage = "NO_KEYWORD_MATCH"
        top_keywords = []
        summary = "특허 데이터는 있으나 설정된 기술 키워드와 매칭되는 출원 추세가 확인되지 않았습니다. 키워드 사전 보강이 필요합니다."
        status = "NO_KEYWORD_MATCH"

    result.update({
        "status": status,
        "patent_row_count": int(len(df)),
        "year_range": {"start": int(df["_application_year_norm"].min()), "end": latest_year},
        "recent_window": {"start": recent_start, "end": latest_year},
        "baseline_window": {"start": baseline_start, "end": baseline_end},
        "overall_lifecycle_stage": overall_stage,
        "overall_lifecycle_score": _safe_round(weighted_score, 2),
        "summary": summary,
        "top_lifecycle_keywords": top_keywords,
        "keyword_trends": trends,
        "annual_trend_rows": annual_rows,
        "external_signals": _load_external_signals(field=field, tech_dir=tech_dir, keyword_aliases=keyword_aliases),
        "interpretation_policy": {
            "patent_trend": "기술 키워드별 연도별 출원 추세로 도입/성장/성숙/쇠퇴 또는 전환을 추정합니다.",
            "external_reports": "논문/보고서 증가 추세, 산업 리포트 채택 단계, 고객 산업 채택 속도는 선택 CSV가 있을 때만 반영합니다.",
            "missing_data_rule": "외부 데이터 없음은 부정이 아니라 확인 제한으로 처리합니다.",
        },
    })
    if write:
        _persist_outputs(result, tech_dir, slug)
    return result


def _make_summary(stage: str, score: float, top_keywords: list[dict[str, Any]]) -> str:
    names = [str(t.get("keyword")) for t in top_keywords[:3]]
    joined = ", ".join(names) if names else "핵심 키워드"
    if stage in {"GROWTH", "INTRODUCTION_TO_GROWTH"}:
        return f"{joined} 중심의 최근 특허 출원 밀도가 높아 기술 수명주기는 성장기 신호에 가깝습니다. 다만 논문/산업 리포트/고객 채택 속도 데이터가 없으면 확정이 아니라 특허 기반 추정입니다."
    if stage in {"MATURITY", "STABLE_MATURITY"}:
        return f"{joined} 관련 출원이 장기간 누적되고 최근에도 유지되어 기술 수명주기는 성숙기 또는 안정화 단계로 해석됩니다. 차별화 강도는 제품 성능·고객 채택 근거와 함께 확인해야 합니다."
    if stage in {"DECLINE_OR_SHIFT"}:
        return f"{joined} 관련 최근 출원 밀도가 약해져 쇠퇴 또는 차세대 기술 전환 가능성을 점검해야 합니다."
    if stage in {"INTRODUCTION_OR_SPARSE"}:
        return f"{joined} 관련 출원 수가 적어 도입기 또는 확인 제한으로 보는 것이 안전합니다."
    return f"기술 수명주기 점수는 {score:.1f}점이며, 특허 출원 추세만으로는 단계를 단정하기 어렵습니다."


def render_lifecycle_md(feature: dict[str, Any]) -> str:
    lines = [
        "# Technology Lifecycle Features",
        "",
        f"- company: {feature.get('company')}",
        f"- status: {feature.get('status')}",
        f"- overall_lifecycle_stage: {feature.get('overall_lifecycle_stage')}",
        f"- overall_lifecycle_score: {feature.get('overall_lifecycle_score')}",
        f"- source_patent_csv: `{feature.get('source_patent_csv')}`",
        "",
        "## Summary",
        str(feature.get("summary") or ""),
        "",
        "## Keyword Trends",
        "| keyword | stage | score | total | recent | baseline | trend_ratio | reason |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for t in feature.get("keyword_trends") or []:
        lines.append(
            f"| {t.get('keyword')} | {t.get('lifecycle_stage')} | {t.get('lifecycle_score')} | "
            f"{t.get('total_patent_count')} | {t.get('recent_count')} | {t.get('baseline_count')} | "
            f"{t.get('trend_ratio_recent_vs_baseline')} | {str(t.get('reason') or '').replace('|', '/')} |"
        )
    lines.extend([
        "",
        "## External Signals",
        f"- status: {(feature.get('external_signals') or {}).get('status')}",
        f"- summary: {(feature.get('external_signals') or {}).get('summary')}",
    ])
    return "\n".join(lines).rstrip() + "\n"


def merge_lifecycle_into_summary(summary: dict[str, Any], feature: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return summary
    compact = {
        "status": feature.get("status"),
        "overall_lifecycle_stage": feature.get("overall_lifecycle_stage"),
        "overall_lifecycle_score": feature.get("overall_lifecycle_score"),
        "summary": feature.get("summary"),
        "top_lifecycle_keywords": [
            {
                "keyword": t.get("keyword"),
                "stage": t.get("lifecycle_stage"),
                "score": t.get("lifecycle_score"),
                "recent_count": t.get("recent_count"),
                "trend_ratio": t.get("trend_ratio_recent_vs_baseline"),
            }
            for t in (feature.get("top_lifecycle_keywords") or [])[:5]
        ],
        "external_signal_status": (feature.get("external_signals") or {}).get("status"),
    }
    summary["technology_lifecycle"] = compact
    selected = dict(summary.get("selected_ml_signals") or {})
    selected["technology_lifecycle"] = compact
    selected["technology_lifecycle_score"] = compact.get("overall_lifecycle_score")
    selected["technology_lifecycle_stage"] = compact.get("overall_lifecycle_stage")
    summary["selected_ml_signals"] = selected
    return summary


def _persist_outputs(feature: dict[str, Any], tech_dir: Path, slug: str) -> None:
    tech_dir.mkdir(parents=True, exist_ok=True)
    json_path = tech_dir / "tech_lifecycle_features.json"
    md_path = tech_dir / "tech_lifecycle_features.md"
    csv_path = tech_dir / "tech_lifecycle_keyword_trends.csv"
    annual_path = tech_dir / "tech_lifecycle_annual_trends.csv"

    json_path.write_text(json.dumps(feature, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md_path.write_text(render_lifecycle_md(feature), encoding="utf-8")

    trends = feature.get("keyword_trends") or []
    if trends:
        pd.json_normalize(trends).to_csv(csv_path, index=False, encoding="utf-8-sig")
    annual = feature.get("annual_trend_rows") or []
    if annual:
        pd.DataFrame(annual).to_csv(annual_path, index=False, encoding="utf-8-sig")

    # Optional aggregate packet for future tech_extra_intake overlays.
    packet_path = tech_dir / "tech_extra_intake_packet.json"
    packet: dict[str, Any] = {}
    if packet_path.exists():
        try:
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
        except Exception:
            packet = {}
    packet.update({
        "company_dir": feature.get("company_dir"),
        "company": feature.get("company"),
        "field": feature.get("field"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    })
    packet["technology_lifecycle"] = {
        "status": feature.get("status"),
        "overall_lifecycle_stage": feature.get("overall_lifecycle_stage"),
        "overall_lifecycle_score": feature.get("overall_lifecycle_score"),
        "summary": feature.get("summary"),
        "source_file": "tech_lifecycle_features.json",
    }
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
