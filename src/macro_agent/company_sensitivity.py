from __future__ import annotations

"""
F. 기업별 macro 민감도 기준
============================

목적
----
macro 공통 점수는 모든 기업에 같은 외부환경을 적용한다. 이 모듈은 같은 macro 충격이라도
기업의 매출 구조, 업종 역할, 손익/부채 구조에 따라 민감도가 다르다는 점을 Chair/Auditor가
객관적으로 볼 수 있게 만든다.

설계 원칙
---------
1. 외부 macro 충격 기준은 이전 패치의 A/B 기준을 재사용한다.
   - 수준 기준: 입력 시계열의 과거분포 20/80 분위 또는 공식 시계열 수준
   - 변화율 기준: 1/5/20/60영업일 변화율, rolling z-score, 과거분포 분위수 급등/급락 cutoff
2. 기업 노출도는 가능한 경우 숫자 데이터에서 읽고, 숫자가 없으면 company.yaml의 products/keywords/core_keywords
   같은 명시 입력값만 사용한다. LLM 추론이나 임의 보정값을 만들지 않는다.
3. 수치형 노출도 cutoff는 한 기업 단독 고정값이 아니라 같은 data/<field> universe의 최신값 cross-section
   분위수로 판단한다. 관측치가 부족하면 점수 반영을 하지 않고 data_insufficient로 남긴다.
4. 네트워크 호출이 없고, 이미 생성된 로컬 산출물만 읽는다. 따라서 전체 파이프라인 속도에 미치는 영향이 작다.
"""

import json
import math
import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd
import yaml

try:
    from common.data_paths import (
        DEFAULT_FIELD,
        company_agent_dir,
        company_config_path,
        company_field,
        company_name as canonical_company_name,
        company_slug,
        field_common_dir,
        field_dir,
    )
except Exception:  # pragma: no cover - standalone test fallback
    DEFAULT_FIELD = "반도체"  # type: ignore
    company_agent_dir = None  # type: ignore
    company_config_path = None  # type: ignore
    company_field = None  # type: ignore
    canonical_company_name = None  # type: ignore
    company_slug = None  # type: ignore
    field_common_dir = None  # type: ignore
    field_dir = None  # type: ignore


# ---------------------------------------------------------------------------
# 공식/객관 기준 메타데이터. 코드가 외부 문서를 호출하지는 않지만, 산출물에 어떤 기준을 썼는지 남긴다.
# ---------------------------------------------------------------------------
METHODOLOGY_BASIS: Dict[str, str] = {
    "macro_level": "한국은행 ECOS/FRED 등 공식 시계열의 과거분포 20/80 분위 기준",
    "macro_rolling": "rolling z-score ±2σ watch, ±3σ extreme 및 과거분포 5/95·1/99 분위 급등/급락 cutoff",
    "export_fx": "DART 사업보고서의 내수/수출·지역별 매출 또는 사용자가 입력한 외부 CSV export_ratio를 우선 사용",
    "raw_material": "DART 사업보고서 원재료/생산설비·원재료 가격 추이 또는 company.yaml의 명시 제품/소재 키워드 사용",
    "equipment_regulation": "BIS/수출통제 등 규제 뉴스 텍스트와 company.yaml의 반도체 장비 키워드 매칭",
    "memory_hbm_demand": "WSTS/SIA 등 반도체·메모리 수요 proxy 또는 로컬 시장/월별 데이터의 메모리/HBM/반도체 지표 변화율 사용",
    "rate_sensitivity": "DCF/현재가치 원리에 따라 미래 현금흐름 비중이 큰 딥테크·적자·FCF 음수 기업은 금리 충격에 민감하게 표시",
    "credit_spread": "회사채/신용스프레드 확대와 기업별 부채비율 cross-section 분위수 결합",
}

# 숫자 노출도를 직접 보강하고 싶을 때 쓰는 선택 CSV. 없으면 자동으로 건너뛴다.
EXTERNAL_SENSITIVITY_RELATIVE_PATH = (
    "macro_company_sensitivity" / Path("company_sensitivity_external.csv")
)

ROLE_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "material_company": (
        "소재", "화학", "케미칼", "전구체", "precursor", "고순도", "식각", "세정", "박리", "슬러리",
        "photoresist", "포토레지스트", "특수가스", "gas", "chemical", "material", "materials",
    ),
    "equipment_company": (
        "장비", "equipment", "본더", "bonder", "tc bonder", "비전", "placement", "테스터", "tester",
        "검사장비", "공정장비", "증착", "식각장비", "세정장비", "자동화", "handler", "probe",
    ),
    "backend_packaging_company": (
        "후공정", "패키징", "packaging", "package", "osat", "wlp", "plp", "bump", "bumping",
        "fan-out", "fanout", "테스트", "test", "probe", "socket", "소켓", "번인", "burn-in",
    ),
    "hbm_memory_linked": (
        "hbm", "메모리", "memory", "dram", "nand", "tc bonder", "본더", "advanced packaging",
        "첨단 패키징", "후공정", "패키징", "wlp", "fan-out", "plp",
    ),
    "deeptech_company": (
        "딥테크", "deeptech", "r&d", "연구개발", "특허", "patent", "기술", "소부장", "소재", "장비",
        "패키징", "fabless", "파운드리", "바이오", "전고체", "이차전지",
    ),
    "export_keyword_hint": (
        "수출", "export", "global", "overseas", "해외", "미국", "중국", "일본", "asia", "worldwide",
    ),
}

MACRO_INDICATOR_ALIASES: Dict[str, Tuple[str, ...]] = {
    "fx_krw_usd": ("원달러", "usdkrw", "krw", "환율"),
    "dxy": ("달러인덱스_dxy", "dxy", "dollar_index", "달러인덱스"),
    "raw_oil": ("유가_평균", "유가_wti", "유가_brent", "wti", "brent", "oil", "유가"),
    "natural_gas": ("천연가스", "natural_gas", "gas"),
    "copper": ("구리", "copper"),
    "rare_earth": ("희토류", "rare_earth", "rareearth"),
    "kr_rates": ("국고채_10년", "국고채_3년", "콜금리", "cd금리_91일", "회사채_aa-", "회사채_bbb-"),
    "credit_spreads": ("신용스프레드_aa-", "신용스프레드_bbb-", "회사채_bbb-", "회사채_aa-"),
    "us_rates": ("미국_국채_10년", "미국_국채_13주", "dgs10", "tb3ms"),
    "memory_hbm_demand": (
        "hbm", "memory", "메모리", "dram", "nand", "반도체_수출", "semiconductor_export",
        "sox", "필라델피아", "semiconductor", "반도체",
    ),
}


@dataclass
class CompanyContext:
    slug: str
    company_name: str
    field: str
    config_path: str | None
    finance_csv_path: str | None
    external_sensitivity_path: str | None
    role_flags: Dict[str, bool]
    role_evidence: Dict[str, List[str]]
    metrics: Dict[str, Any]
    metric_percentiles: Dict[str, Any]


def _safe_slug(value: Any, default: str = "unknown_company") -> str:
    if company_slug is not None:
        try:
            return str(company_slug(value, default=default))
        except Exception:
            pass
    return re.sub(r"[^0-9A-Za-z가-힣_\-]+", "_", str(value or default)).strip("_") or default


def _safe_company_name(slug: str, fallback: str | None = None) -> str:
    if canonical_company_name is not None:
        try:
            return str(canonical_company_name(slug))
        except Exception:
            pass
    return str(fallback or slug)


def _safe_field(slug: str) -> str:
    if company_field is not None:
        try:
            return str(company_field(slug))
        except Exception:
            pass
    return str(DEFAULT_FIELD or "반도체")


def _read_yaml(path: Path | None) -> Dict[str, Any]:
    if not path or not path.exists():
        return {}
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return yaml.safe_load(path.read_text(encoding=enc)) or {}
        except Exception:
            continue
    return {}


def _read_json(path: Path | None) -> Any | None:
    if not path or not path.exists():
        return None
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return None


def _flatten_text(value: Any) -> List[str]:
    out: List[str] = []
    if value is None:
        return out
    if isinstance(value, dict):
        for v in value.values():
            out.extend(_flatten_text(v))
    elif isinstance(value, (list, tuple, set)):
        for v in value:
            out.extend(_flatten_text(v))
    else:
        s = str(value).strip()
        if s:
            out.append(s)
    return out


def _selected_company_text(meta: Dict[str, Any]) -> str:
    keys = [
        "corp_name", "corp_name_en", "aliases", "keywords", "core_keywords", "products", "tech_keywords",
        "business", "business_area", "vc_role", "industry", "sector", "notes",
    ]
    parts: List[str] = []
    for key in keys:
        if key in meta:
            parts.extend(_flatten_text(meta.get(key)))
    return " \n".join(parts).lower()


def _detect_role_flags(meta: Dict[str, Any]) -> Tuple[Dict[str, bool], Dict[str, List[str]]]:
    text = _selected_company_text(meta)
    flags: Dict[str, bool] = {}
    evidence: Dict[str, List[str]] = {}
    for role, keywords in ROLE_KEYWORDS.items():
        hits = [kw for kw in keywords if kw.lower() in text]
        flags[role] = bool(hits)
        evidence[role] = hits[:12]
    return flags, evidence


def _possible_company_paths(slug: str, company: str | None = None) -> List[Path]:
    paths: List[Path] = []
    if company_agent_dir is not None:
        for value in [slug, company]:
            if not value:
                continue
            try:
                paths.append(company_agent_dir(value, "finance", create=False).parent)
            except Exception:
                continue
    # fallback for standalone tests
    root = Path(__file__).resolve().parents[2]
    for field_name in [DEFAULT_FIELD, "반도체", "바이오", "이차전지"]:
        if company:
            paths.append(root / "data" / str(field_name) / str(company))
        paths.append(root / "data" / str(field_name) / slug)
    # de-dup
    seen = set()
    uniq = []
    for p in paths:
        k = str(p)
        if k not in seen:
            uniq.append(p)
            seen.add(k)
    return uniq


def _find_first_existing(paths: Iterable[Path]) -> Path | None:
    for p in paths:
        try:
            if p.exists():
                return p
        except Exception:
            continue
    return None


def _find_company_config(slug: str) -> Path | None:
    if company_config_path is not None:
        try:
            p = company_config_path(slug, create_parent=False)
            if p.exists():
                return p
        except Exception:
            pass
    return None


def _find_finance_csv(slug: str, company: str | None = None) -> Path | None:
    candidates: List[Path] = []
    for root in _possible_company_paths(slug, company):
        candidates.extend((root / "finance").glob("*.csv") if (root / "finance").exists() else [])
    # 재무 파일 우선, stock 파일 제외
    ranked = []
    for p in candidates:
        name = p.name.lower()
        if "stock" in name or "주식" in name:
            continue
        weight = 0
        if "재무" in name or "finance" in name:
            weight -= 10
        if "standardize" in name or "manifest" in name:
            weight += 20
        ranked.append((weight, p))
    ranked.sort(key=lambda x: (x[0], str(x[1])))
    return ranked[0][1] if ranked else None


def _read_csv_safely(path: Path | None) -> pd.DataFrame | None:
    if path is None or not path.exists():
        return None
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return None


def _latest_valid_row(df: pd.DataFrame | None) -> pd.Series | None:
    if df is None or df.empty:
        return None
    frame = df.copy()
    if "year" in frame.columns:
        frame["__year"] = pd.to_numeric(frame["year"], errors="coerce")
        frame = frame.sort_values("__year")
    frame = frame.dropna(how="all")
    if frame.empty:
        return None
    return frame.iloc[-1]


def _num(value: Any) -> float | None:
    try:
        if isinstance(value, str):
            value = value.replace(",", "").replace("%", "").strip()
        out = float(value)
        if math.isfinite(out):
            return out
    except Exception:
        return None
    return None


def _extract_finance_metrics(finance_csv: Path | None) -> Dict[str, Any]:
    df = _read_csv_safely(finance_csv)
    latest = _latest_valid_row(df)
    metrics: Dict[str, Any] = {}
    if latest is None:
        return metrics

    candidates = {
        "sales": ["sales", "매출", "매출액"],
        "operating_income": ["operating_income", "영업이익"],
        "net_income": ["net_income", "순이익", "당기순이익"],
        "fcf": ["fcf", "잉여현금흐름", "free_cash_flow"],
        "debt_ratio_pct": ["debt_ratio_%", "debt_ratio", "부채비율", "부채비율_%"],
        "operating_margin_pct": ["operating_margin_%", "영업이익률", "영업이익률_%"],
        "net_margin_pct": ["net_margin_%", "순이익률", "net_margin"],
        "current_ratio_pct": ["current_ratio_%", "유동비율"],
    }
    lower_map = {str(c).lower(): c for c in latest.index}
    for out_key, cols in candidates.items():
        for c in cols:
            real = lower_map.get(c.lower())
            if real is not None:
                v = _num(latest.get(real))
                if v is not None:
                    metrics[out_key] = v
                    break

    metrics["loss_making"] = bool(
        (metrics.get("operating_income") is not None and metrics["operating_income"] < 0)
        or (metrics.get("net_income") is not None and metrics["net_income"] < 0)
        or (metrics.get("operating_margin_pct") is not None and metrics["operating_margin_pct"] < 0)
        or (metrics.get("net_margin_pct") is not None and metrics["net_margin_pct"] < 0)
    )
    metrics["fcf_negative"] = bool(metrics.get("fcf") is not None and metrics["fcf"] < 0)
    return metrics


def _external_sensitivity_paths(slug: str, field: str) -> List[Path]:
    paths: List[Path] = []
    if field_common_dir is not None:
        try:
            paths.append(field_common_dir("macro_company_sensitivity", field=field, create=False) / "company_sensitivity_external.csv")
        except Exception:
            pass
    root = Path(__file__).resolve().parents[2]
    paths.extend([
        root / "data" / field / "_sector_common" / "macro_company_sensitivity" / "company_sensitivity_external.csv",
        root / "data" / field / "macro_company_sensitivity" / "company_sensitivity_external.csv",
        root / "data" / "macro_company_sensitivity" / "company_sensitivity_external.csv",
    ])
    return paths


def _load_external_sensitivity(slug: str, company: str | None, field: str) -> Tuple[Dict[str, Any], str | None]:
    path = _find_first_existing(_external_sensitivity_paths(slug, field))
    if not path:
        return {}, None
    df = _read_csv_safely(path)
    if df is None or df.empty:
        return {}, str(path)
    cols = {str(c).lower(): c for c in df.columns}
    masks = []
    for key in ("slug", "company_dir", "company", "corp_name", "stock_code"):
        c = cols.get(key)
        if c is None:
            continue
        masks.append(df[c].astype(str).str.strip().str.lower().isin({slug.lower(), str(company or "").lower()}))
    if not masks:
        return {}, str(path)
    mask = masks[0]
    for m in masks[1:]:
        mask = mask | m
    if not mask.any():
        return {}, str(path)
    row = df.loc[mask].iloc[0]
    out: Dict[str, Any] = {}
    for c in df.columns:
        val = row.get(c)
        if pd.isna(val):
            continue
        out[str(c).strip()] = val.item() if hasattr(val, "item") else val
    return out, str(path)


def _merge_external_metrics(metrics: Dict[str, Any], external: Dict[str, Any]) -> Dict[str, Any]:
    aliases = {
        "export_ratio_pct": ["export_ratio_pct", "export_ratio", "수출비중", "수출비중_%", "해외매출비중"],
        "raw_material_ratio_pct": ["raw_material_ratio_pct", "raw_material_ratio", "원재료비중", "원재료매입비중"],
        "china_revenue_ratio_pct": ["china_revenue_ratio_pct", "china_revenue_ratio", "중국매출비중"],
        "foreign_currency_debt_ratio_pct": ["foreign_currency_debt_ratio_pct", "외화부채비중"],
        "interest_bearing_debt_ratio_pct": ["interest_bearing_debt_ratio_pct", "차입금의존도", "유이자부채비중"],
    }
    lower = {str(k).lower(): k for k in external.keys()}
    merged = dict(metrics)
    for out_key, keys in aliases.items():
        for key in keys:
            real = lower.get(key.lower())
            if real is not None:
                v = _num(external.get(real))
                if v is not None:
                    # 0~1 입력이면 %로 변환
                    if 0 <= v <= 1 and "pct" in out_key:
                        v *= 100.0
                    merged[out_key] = v
                    break
    return merged


def _iter_universe_finance_csvs(field: str) -> List[Path]:
    roots: List[Path] = []
    if field_dir is not None:
        try:
            roots.append(field_dir(field, create=False))
        except Exception:
            pass
    root = Path(__file__).resolve().parents[2]
    roots.append(root / "data" / field)
    paths: List[Path] = []
    for base in roots:
        if not base.exists():
            continue
        for p in base.glob("*/finance/*.csv"):
            name = p.name.lower()
            if "stock" in name or "주식" in name or "manifest" in name:
                continue
            if "재무" in name or "finance" in name:
                paths.append(p)
    seen = set()
    uniq = []
    for p in paths:
        k = str(p.resolve())
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def _latest_metric_from_csv(path: Path, metric_key: str) -> float | None:
    df = _read_csv_safely(path)
    latest = _latest_valid_row(df)
    if latest is None:
        return None
    aliases = {
        "debt_ratio_pct": ["debt_ratio_%", "debt_ratio", "부채비율", "부채비율_%"],
        "operating_margin_pct": ["operating_margin_%", "영업이익률", "영업이익률_%"],
        "fcf": ["fcf", "잉여현금흐름", "free_cash_flow"],
    }.get(metric_key, [metric_key])
    lower = {str(c).lower(): c for c in latest.index}
    for c in aliases:
        real = lower.get(c.lower())
        if real is not None:
            return _num(latest.get(real))
    return None


def _cross_section_percentiles(field: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    universe = _iter_universe_finance_csvs(field)
    for metric_key in ["debt_ratio_pct", "operating_margin_pct", "fcf"]:
        current = _num(metrics.get(metric_key))
        if current is None:
            continue
        vals: List[float] = []
        for path in universe:
            v = _latest_metric_from_csv(path, metric_key)
            if v is not None:
                vals.append(v)
        if len(vals) < 5:
            out[metric_key] = {"available": False, "reason": "cross_section_observations_lt_5", "observations": len(vals)}
            continue
        ser = pd.Series(vals, dtype="float64").dropna()
        percentile = float((ser <= current).mean())
        out[metric_key] = {
            "available": True,
            "observations": int(len(ser)),
            "current": float(current),
            "pctl_rank": round(percentile, 4),
            "q20": float(ser.quantile(0.20)),
            "q50": float(ser.quantile(0.50)),
            "q80": float(ser.quantile(0.80)),
            "method": "same_field_cross_section_percentile_latest_finance_csv",
        }
    return out


def load_company_context(company_dir: str | None = None, company: str | None = None) -> CompanyContext:
    slug = _safe_slug(company_dir or company or "macro")
    name = _safe_company_name(slug, company)
    field = _safe_field(slug)

    cfg_path = _find_company_config(slug)
    meta = _read_yaml(cfg_path)
    role_flags, role_evidence = _detect_role_flags(meta)

    finance_csv = _find_finance_csv(slug, company)
    metrics = _extract_finance_metrics(finance_csv)

    external, external_path = _load_external_sensitivity(slug, company, field)
    if external:
        metrics = _merge_external_metrics(metrics, external)
        role_flags["export_keyword_hint"] = role_flags.get("export_keyword_hint", False) or any(
            _num(metrics.get(k)) is not None and float(metrics[k]) > 0
            for k in ("export_ratio_pct", "china_revenue_ratio_pct")
        )

    metric_percentiles = _cross_section_percentiles(field, metrics)

    return CompanyContext(
        slug=slug,
        company_name=name,
        field=field,
        config_path=str(cfg_path) if cfg_path else None,
        finance_csv_path=str(finance_csv) if finance_csv else None,
        external_sensitivity_path=external_path,
        role_flags=role_flags,
        role_evidence=role_evidence,
        metrics=metrics,
        metric_percentiles=metric_percentiles,
    )


def _canonical_col(col: str) -> str:
    return str(col or "").strip().lower()


def _match_alias(col: str, aliases: Iterable[str]) -> bool:
    c = _canonical_col(col)
    for alias in aliases:
        a = _canonical_col(alias)
        if not a:
            continue
        if c == a or a in c:
            return True
    return False


def _latest_feature(df: pd.DataFrame, base_col: str, contains: str) -> Any | None:
    base = _canonical_col(base_col)
    target = contains.lower()
    candidates = []
    for col in df.columns:
        c = _canonical_col(str(col))
        if base in c and target in c:
            candidates.append(col)
    if not candidates:
        return None
    latest = df.iloc[-1]
    for col in candidates:
        val = latest.get(col)
        if pd.notna(val):
            return val
    return None


def _collect_indicator_events(feature_data: Dict[str, pd.DataFrame], aliases: Iterable[str]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for dataset_name, df in (feature_data or {}).items():
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            continue
        frame = df.copy()
        frame.columns = [str(c).strip().lower() for c in frame.columns]
        latest = frame.iloc[-1]
        for col in frame.columns:
            if col == "date" or not _match_alias(col, aliases):
                continue
            try:
                value = _num(latest.get(col))
            except Exception:
                value = None
            if value is None:
                continue
            diff = _num(latest.get(f"{col}_diff"))
            if diff is None:
                diff = _num(_latest_feature(frame, col, "diff_1"))
            chg1 = _num(_latest_feature(frame, col, "chg_1"))
            chg20 = _num(_latest_feature(frame, col, "chg_20"))
            z_alert = _num(_latest_feature(frame, col, "z_alert"))
            shock_flag = _num(_latest_feature(frame, col, "shock_flag"))
            zscore = _num(_latest_feature(frame, col, "zscore"))
            # 원천 컬럼만 중복 수집하고 생성 feature 컬럼 자체는 제외한다.
            if any(
                token in col
                for token in [
                    "_diff", "_pct_change", "_chg_", "_bp_change", "_zscore", "_z_alert",
                    "_shock", "_ma5", "_ma20", "_trend", "_rolling_", "_mean_reversion",
                ]
            ):
                continue
            events.append({
                "dataset": dataset_name,
                "indicator": col,
                "latest": value,
                "diff": diff,
                "chg1_pct": chg1,
                "chg20_pct": chg20,
                "z_alert": int(z_alert) if z_alert is not None else 0,
                "shock_flag": int(shock_flag) if shock_flag is not None else 0,
                "zscore": zscore,
            })
    return events


def _event_pressure(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """양수=상승/확대 압력, 음수=하락/축소 압력."""
    if not events:
        return {"available": False, "pressure": 0, "events": []}
    scored = []
    pressure = 0
    for ev in events:
        p = 0
        diff = _num(ev.get("diff"))
        chg1 = _num(ev.get("chg1_pct"))
        z_alert = int(ev.get("z_alert") or 0)
        shock = int(ev.get("shock_flag") or 0)
        if diff is not None:
            p += 1 if diff > 0 else (-1 if diff < 0 else 0)
        elif chg1 is not None:
            p += 1 if chg1 > 0 else (-1 if chg1 < 0 else 0)
        if z_alert > 0 or shock > 0:
            p += 1
        elif z_alert < 0 or shock < 0:
            p -= 1
        pressure += p
        item = dict(ev)
        item["pressure_component"] = p
        scored.append(item)
    pressure = max(-3, min(3, pressure))
    scored = sorted(scored, key=lambda x: abs(x.get("pressure_component", 0)), reverse=True)
    return {"available": True, "pressure": int(pressure), "events": scored[:8]}




def _join_recent_text_frame(df: pd.DataFrame, text_cols: list[str], *, tail_rows: int = 30) -> str:
    if df is None or df.empty or not text_cols:
        return ""
    existing: list[str] = []
    seen: set[str] = set()
    for col in text_cols:
        if col in df.columns and col not in seen:
            existing.append(col)
            seen.add(col)
    if not existing:
        return ""
    try:
        frame = df.tail(tail_rows).loc[:, existing].copy()
        if getattr(frame.columns, "duplicated", None) is not None:
            frame = frame.loc[:, ~frame.columns.duplicated()]
        frame = frame.fillna("").astype(str)
        row_text = frame.apply(lambda row: " ".join(x for x in row.tolist() if x), axis=1)
        return " ".join(row_text.tolist()).lower()
    except Exception:
        pieces: list[str] = []
        try:
            for _, row in df.tail(tail_rows).iterrows():
                for col in existing:
                    value = row.get(col, "")
                    if pd.notna(value):
                        pieces.append(str(value))
        except Exception:
            return ""
        return " ".join(pieces).lower()

def _regulation_pressure(feature_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    df = feature_data.get("규제") if isinstance(feature_data, dict) else None
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return {"available": False, "pressure": 0, "keyword_count": 0, "method": "no_regulation_frame"}
    text_cols = [c for c in df.columns if str(c).lower() in {"title", "summary", "description", "content"}]
    if not text_cols:
        return {"available": False, "pressure": 0, "keyword_count": 0, "method": "no_text_columns"}
    recent = _join_recent_text_frame(df, text_cols, tail_rows=30)
    if not recent:
        return {"available": False, "pressure": 0, "keyword_count": 0, "method": "empty_recent_regulation_text"}
    keywords = [
        "export control", "restriction", "sanction", "tariff", "ban", "entity list", "bis",
        "semiconductor manufacturing equipment", "advanced computing", "advanced semiconductor",
        "수출통제", "제재", "관세", "규제", "장비", "반도체",
    ]
    count = sum(recent.count(k.lower()) for k in keywords)
    pressure = 2 if count >= 5 else (1 if count > 0 else 0)
    return {"available": True, "pressure": pressure, "keyword_count": int(count), "method": "recent_regulation_keyword_count_tail30"}


def _is_high_percentile(context: CompanyContext, metric_key: str, threshold: float = 0.80) -> bool:
    p = context.metric_percentiles.get(metric_key) or {}
    if not p.get("available"):
        return False
    try:
        return float(p.get("pctl_rank")) >= threshold
    except Exception:
        return False


def _is_low_percentile(context: CompanyContext, metric_key: str, threshold: float = 0.20) -> bool:
    p = context.metric_percentiles.get(metric_key) or {}
    if not p.get("available"):
        return False
    try:
        return float(p.get("pctl_rank")) <= threshold
    except Exception:
        return False


def _numeric_exposure_level(context: CompanyContext, metric_key: str) -> str:
    value = _num(context.metrics.get(metric_key))
    if value is None:
        return "unknown"
    # 외부 CSV 값은 현재 universe percentile이 없을 수 있어 값만 기록하고, 임계 판단은 보수적으로 unknown 처리한다.
    p = context.metric_percentiles.get(metric_key) or {}
    if p.get("available"):
        rank = float(p.get("pctl_rank"))
        if rank >= 0.80:
            return "high_by_cross_section_p80"
        if rank <= 0.20:
            return "low_by_cross_section_p20"
        return "middle_by_cross_section"
    return "observed_no_cross_section_cutoff"


def score_company_macro_sensitivity(
    feature_data: Dict[str, pd.DataFrame],
    *,
    company_dir: str | None = None,
    company: str | None = None,
    sector: str = "default",
) -> Tuple[int, List[str], Dict[str, Any]]:
    """기업별 macro 민감도 점수와 근거를 반환한다.

    반환 점수는 macro 총점을 과도하게 흔들지 않도록 최종 caller에서 cap하는 것을 전제로 한다.
    양수는 해당 기업에 우호, 음수는 비우호다.
    """
    context = load_company_context(company_dir=company_dir, company=company)
    flags = context.role_flags
    metrics = context.metrics

    fx_pressure = _event_pressure(
        _collect_indicator_events(feature_data, MACRO_INDICATOR_ALIASES["fx_krw_usd"])
        + _collect_indicator_events(feature_data, MACRO_INDICATOR_ALIASES["dxy"])
    )
    raw_pressure = _event_pressure(
        _collect_indicator_events(feature_data, MACRO_INDICATOR_ALIASES["raw_oil"])
        + _collect_indicator_events(feature_data, MACRO_INDICATOR_ALIASES["natural_gas"])
        + _collect_indicator_events(feature_data, MACRO_INDICATOR_ALIASES["copper"])
        + _collect_indicator_events(feature_data, MACRO_INDICATOR_ALIASES["rare_earth"])
    )
    rate_pressure = _event_pressure(
        _collect_indicator_events(feature_data, MACRO_INDICATOR_ALIASES["kr_rates"])
        + _collect_indicator_events(feature_data, MACRO_INDICATOR_ALIASES["us_rates"])
    )
    credit_pressure = _event_pressure(_collect_indicator_events(feature_data, MACRO_INDICATOR_ALIASES["credit_spreads"]))
    demand_pressure = _event_pressure(_collect_indicator_events(feature_data, MACRO_INDICATOR_ALIASES["memory_hbm_demand"]))
    regulation_pressure = _regulation_pressure(feature_data)

    raw_score = 0
    reasons: List[str] = []
    axes: Dict[str, Any] = {}

    # 1. 수출기업 환율 민감도
    export_level = _numeric_exposure_level(context, "export_ratio_pct")
    export_exposed = export_level.startswith("high") or bool(flags.get("export_keyword_hint"))
    fx_p = int(fx_pressure.get("pressure") or 0)
    fx_score = 0
    if export_exposed and fx_pressure.get("available"):
        # 원달러 상승은 수출 매출의 원화 환산에는 우호적일 수 있지만, DXY/위험회피도 함께 들어오므로
        # 확정 매수/매도 요인이 아니라 민감도 보정으로만 작게 반영한다.
        fx_score = 1 if fx_p > 0 else (-1 if fx_p < 0 else 0)
        raw_score += fx_score
        if fx_score > 0:
            reasons.append("수출/해외 매출 노출 기업 + 원달러·달러 지표 상승 → 원화 환산 매출 민감도 우호")
        elif fx_score < 0:
            reasons.append("수출/해외 매출 노출 기업 + 원달러·달러 지표 하락 → 환율 tailwind 약화")
    axes["export_fx_sensitivity"] = {
        "score": fx_score,
        "exposure_level": export_level,
        "exposure_metric": metrics.get("export_ratio_pct"),
        "role_keyword_hint": bool(flags.get("export_keyword_hint")),
        "macro_pressure": fx_pressure,
        "basis": METHODOLOGY_BASIS["export_fx"],
    }

    # 2. 소재기업 원자재 민감도
    raw_p = int(raw_pressure.get("pressure") or 0)
    material_exposed = bool(flags.get("material_company")) or _numeric_exposure_level(context, "raw_material_ratio_pct").startswith("high")
    raw_score_axis = 0
    if material_exposed and raw_pressure.get("available"):
        raw_score_axis = -1 if raw_p > 0 else (1 if raw_p < 0 else 0)
        raw_score += raw_score_axis
        if raw_score_axis < 0:
            reasons.append("소재/화학 기업 + 유가·가스·구리·희토류 상승 압력 → 원재료비 민감도 부담")
        elif raw_score_axis > 0:
            reasons.append("소재/화학 기업 + 원자재 가격 하락 압력 → 원가 부담 완화")
    axes["raw_material_sensitivity"] = {
        "score": raw_score_axis,
        "material_role": bool(flags.get("material_company")),
        "role_evidence": context.role_evidence.get("material_company", []),
        "raw_material_ratio_pct": metrics.get("raw_material_ratio_pct"),
        "raw_material_ratio_level": _numeric_exposure_level(context, "raw_material_ratio_pct"),
        "macro_pressure": raw_pressure,
        "basis": METHODOLOGY_BASIS["raw_material"],
    }

    # 3. 장비기업 규제 민감도
    reg_p = int(regulation_pressure.get("pressure") or 0)
    reg_score = 0
    if flags.get("equipment_company") and regulation_pressure.get("available") and reg_p > 0:
        reg_score = -2 if reg_p >= 2 else -1
        raw_score += reg_score
        reasons.append("반도체 장비 기업 + 수출통제/규제 키워드 증가 → 규제 민감도 부담")
    axes["equipment_regulation_sensitivity"] = {
        "score": reg_score,
        "equipment_role": bool(flags.get("equipment_company")),
        "role_evidence": context.role_evidence.get("equipment_company", []),
        "macro_pressure": regulation_pressure,
        "basis": METHODOLOGY_BASIS["equipment_regulation"],
    }

    # 4. 후공정기업 HBM/메모리 수요 민감도
    demand_p = int(demand_pressure.get("pressure") or 0)
    demand_exposed = bool(flags.get("backend_packaging_company") or flags.get("hbm_memory_linked"))
    demand_score = 0
    if demand_exposed and demand_pressure.get("available"):
        demand_score = 1 if demand_p > 0 else (-1 if demand_p < 0 else 0)
        raw_score += demand_score
        if demand_score > 0:
            reasons.append("후공정/HBM·메모리 연계 기업 + 메모리/반도체 수요 proxy 개선 → 수요 민감도 우호")
        elif demand_score < 0:
            reasons.append("후공정/HBM·메모리 연계 기업 + 메모리/반도체 수요 proxy 약화 → 수요 민감도 부담")
    axes["backend_hbm_memory_demand_sensitivity"] = {
        "score": demand_score,
        "backend_role": bool(flags.get("backend_packaging_company")),
        "hbm_memory_linked": bool(flags.get("hbm_memory_linked")),
        "role_evidence": sorted(set(context.role_evidence.get("backend_packaging_company", []) + context.role_evidence.get("hbm_memory_linked", [])))[:12],
        "macro_pressure": demand_pressure,
        "basis": METHODOLOGY_BASIS["memory_hbm_demand"],
    }

    # 5. 딥테크/적자기업 금리 민감도
    rate_p = int(rate_pressure.get("pressure") or 0)
    rate_sensitive = bool(flags.get("deeptech_company") or metrics.get("loss_making") or metrics.get("fcf_negative"))
    rate_score = 0
    if rate_sensitive and rate_pressure.get("available"):
        rate_score = -2 if rate_p > 1 else (-1 if rate_p > 0 else (1 if rate_p < 0 else 0))
        raw_score += rate_score
        rate_labels: List[str] = []
        if flags.get("deeptech_company"):
            rate_labels.append("딥테크/장기 성장")
        if metrics.get("loss_making"):
            rate_labels.append("적자")
        if metrics.get("fcf_negative"):
            rate_labels.append("FCF 음수")
        rate_label = "·".join(rate_labels) if rate_labels else "금리 민감"
        if rate_score < 0:
            reasons.append(f"{rate_label} 기업 + 금리 상승 압력 → 할인율·자금조달 민감도 부담")
        elif rate_score > 0:
            reasons.append(f"{rate_label} 기업 + 금리 하락 압력 → 할인율·자금조달 부담 완화")
    axes["deeptech_loss_rate_sensitivity"] = {
        "score": rate_score,
        "deeptech_role": bool(flags.get("deeptech_company")),
        "loss_making": bool(metrics.get("loss_making")),
        "fcf_negative": bool(metrics.get("fcf_negative")),
        "operating_margin_pct": metrics.get("operating_margin_pct"),
        "net_margin_pct": metrics.get("net_margin_pct"),
        "fcf": metrics.get("fcf"),
        "macro_pressure": rate_pressure,
        "basis": METHODOLOGY_BASIS["rate_sensitivity"],
    }

    # 6. 부채 많은 기업 신용스프레드 민감도
    debt_high = _is_high_percentile(context, "debt_ratio_pct", 0.80)
    credit_p = int(credit_pressure.get("pressure") or 0)
    credit_score = 0
    if debt_high and credit_pressure.get("available"):
        credit_score = -2 if credit_p > 1 else (-1 if credit_p > 0 else (1 if credit_p < 0 else 0))
        raw_score += credit_score
        if credit_score < 0:
            reasons.append("부채비율 상위 20% 기업 + 신용스프레드 확대 압력 → 차입/신용 민감도 부담")
        elif credit_score > 0:
            reasons.append("부채비율 상위 20% 기업 + 신용스프레드 축소 압력 → 차입/신용 부담 완화")
    axes["high_debt_credit_spread_sensitivity"] = {
        "score": credit_score,
        "debt_ratio_pct": metrics.get("debt_ratio_pct"),
        "debt_ratio_percentile": context.metric_percentiles.get("debt_ratio_pct"),
        "high_debt_by_same_field_p80": debt_high,
        "macro_pressure": credit_pressure,
        "basis": METHODOLOGY_BASIS["credit_spread"],
    }

    capped_score = max(-4, min(4, raw_score))
    details = {
        "company": context.company_name,
        "company_dir": context.slug,
        "field": context.field,
        "method": "company_exposure_from_local_disclosures_and_yaml + macro_shock_from_official_timeseries_rolling_criteria",
        "score_raw": raw_score,
        "score_capped": capped_score,
        "basis": METHODOLOGY_BASIS,
        "context": asdict(context),
        "axes": axes,
        "note": "숫자 노출도가 없으면 임의 수치를 만들지 않고 company.yaml 명시 키워드와 로컬 산출물만 사용합니다.",
    }
    return int(capped_score), reasons[:10], details


def build_company_sensitivity_snapshot(
    feature_data: Dict[str, pd.DataFrame],
    *,
    company_dir: str | None = None,
    company: str | None = None,
    sector: str = "default",
) -> Dict[str, Any]:
    score, reasons, details = score_company_macro_sensitivity(
        feature_data,
        company_dir=company_dir,
        company=company,
        sector=sector,
    )
    return {"score": score, "reasons": reasons, "details": details}
