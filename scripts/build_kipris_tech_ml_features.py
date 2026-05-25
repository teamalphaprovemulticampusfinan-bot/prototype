from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from common.data_paths import normalize_field_name


DEFAULT_FIELD = "반도체"
DEFAULT_COMPANY_NAME = "네패스"
DEFAULT_COMPANY_SLUG = "nepes"


SEMICONDUCTOR_CORE_PREFIXES = [
    "H01L",
]

SEMICONDUCTOR_RELATED_PREFIXES = [
    "H01L",
    "H10B",
    "H10D",
    "H10F",
    "H10H",
    "H10K",
    "H10N",
    "H10W",
    "H05K",
    "G01R",
    "B81B",
    "B81C",
]

NEGATIVE_DISPOSAL_KEYWORDS = [
    "거절",
    "취하",
    "소멸",
    "포기",
    "무효",
]

TECH_KEYWORDS = [
    "반도체",
    "패키지",
    "패키징",
    "웨이퍼",
    "wafer",
    "wlp",
    "fowlp",
    "fan-out",
    "fanout",
    "테스트",
    "test",
    "소자",
    "chip",
    "칩",
    "substrate",
    "기판",
    "bump",
    "범프",
    "interposer",
    "인터포저",
    "probe",
    "프로브",
    "module",
    "모듈",
    "memory",
    "메모리",
    "quantum",
    "양자",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def num(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return float(value)
    text = clean_text(value).replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        out = float(text)
    except Exception:
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = clean_text(value).lower()
    return text in {"true", "1", "yes", "y", "등록", "registered"}


def rate(numerator: int | float, denominator: int | float) -> float | None:
    if denominator in (0, None):
        return None
    return round(float(numerator) / float(denominator), 4)


def score_from_rate(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(100.0, value * 100.0))


def cap_score(value: float, cap: float) -> float:
    if cap <= 0:
        return 0.0
    return max(0.0, min(100.0, value / cap * 100.0))


def normalize_ipc(value: Any) -> str:
    text = clean_text(value).upper()
    text = text.replace(";", ",")
    text = re.sub(r"\s+", " ", text)
    return text


def ipc_tokens(value: Any) -> list[str]:
    text = normalize_ipc(value)
    if not text:
        return []

    raw_parts = re.split(r"[,|;]", text)
    tokens: list[str] = []

    for part in raw_parts:
        part = part.strip()
        if not part:
            continue

        # 예: H10W 70/00, H01L 21/00
        m = re.match(r"([A-HY]\d{2}[A-Z])\s*(\d+)?", part)
        if m:
            base = m.group(1)
            group = m.group(2)
            if group:
                tokens.append(f"{base} {group}")
            tokens.append(base)
        else:
            tokens.append(part)

    # 순서 보존 중복 제거
    return list(dict.fromkeys(tokens))


def ipc_main_group(value: Any) -> str:
    tokens = ipc_tokens(value)
    if not tokens:
        return ""
    for token in tokens:
        if re.match(r"^[A-HY]\d{2}[A-Z]\s+\d+", token):
            return token
    return tokens[0]


def ipc_subclass(value: Any) -> str:
    tokens = ipc_tokens(value)
    if not tokens:
        return ""
    for token in tokens:
        if re.match(r"^[A-HY]\d{2}[A-Z]$", token):
            return token
    first = tokens[0]
    m = re.match(r"^([A-HY]\d{2}[A-Z])", first)
    return m.group(1) if m else ""


def has_prefix(value: Any, prefixes: list[str]) -> bool:
    text = normalize_ipc(value)
    return any(prefix in text for prefix in prefixes)


def has_negative_disposal(value: Any) -> bool:
    text = clean_text(value)
    return any(keyword in text for keyword in NEGATIVE_DISPOSAL_KEYWORDS)


def keyword_match_count(row: dict[str, Any]) -> int:
    joined = " ".join(
        [
            clean_text(row.get("invention_title")),
            clean_text(row.get("abstract")),
            clean_text(row.get("ipc_number")),
            clean_text(row.get("ipc_main")),
            clean_text(row.get("ipc_section")),
        ]
    ).lower()

    count = 0
    for keyword in TECH_KEYWORDS:
        if keyword.lower() in joined:
            count += 1
    return count


def find_normalized_csv(tech_dir: Path, slug: str) -> Path:
    preferred = tech_dir / f"{slug}_kipris_patents_normalized.csv"
    if preferred.exists():
        return preferred

    candidates = sorted(tech_dir.glob("*kipris*normalized*.csv"))
    if candidates:
        return candidates[0]

    candidates = sorted(tech_dir.glob("*patent*normalized*.csv"))
    if candidates:
        return candidates[0]

    raise FileNotFoundError(
        f"KIPRIS normalized CSV를 찾지 못했습니다: {tech_dir}\n"
        f"예상 파일명: {preferred.name}"
    )


def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "ipc_number" not in out.columns:
        out["ipc_number"] = ""

    out["ipc_subclass_refined"] = out["ipc_number"].apply(ipc_subclass)
    out["ipc_main_refined"] = out["ipc_number"].apply(ipc_main_group)

    out["has_h01l_refined"] = out["ipc_number"].apply(
        lambda x: has_prefix(x, SEMICONDUCTOR_CORE_PREFIXES)
    )
    out["has_semiconductor_related_ipc_refined"] = out["ipc_number"].apply(
        lambda x: has_prefix(x, SEMICONDUCTOR_RELATED_PREFIXES)
    )

    if "tech_keyword_match_count" not in out.columns:
        out["tech_keyword_match_count"] = 0

    out["tech_keyword_match_count_refined"] = out.apply(
        lambda row: keyword_match_count(row.to_dict()),
        axis=1,
    )

    if "is_registered" not in out.columns:
        out["is_registered"] = False
    out["is_registered_bool"] = out["is_registered"].apply(bool_value)

    if "is_alive_estimated" not in out.columns:
        out["is_alive_estimated"] = False
    out["is_alive_estimated_bool"] = out["is_alive_estimated"].apply(bool_value)

    if "final_disposal" not in out.columns:
        out["final_disposal"] = ""
    out["has_negative_disposal_estimated"] = out["final_disposal"].apply(has_negative_disposal)

    if "application_year" not in out.columns:
        out["application_year"] = None
    out["application_year_num"] = out["application_year"].apply(num)

    return out


def build_features(
    *,
    df: pd.DataFrame,
    source_csv: Path,
    enriched_csv: Path,
    field: str,
    company_name: str,
    company_slug: str,
) -> dict[str, Any]:
    total = len(df)

    registered_count = int(df["is_registered_bool"].fillna(False).sum()) if total else 0
    alive_count = int(df["is_alive_estimated_bool"].fillna(False).sum()) if total else 0
    negative_disposal_count = int(df["has_negative_disposal_estimated"].fillna(False).sum()) if total else 0

    h01l_count = int(df["has_h01l_refined"].fillna(False).sum()) if total else 0
    semiconductor_related_count = int(df["has_semiconductor_related_ipc_refined"].fillna(False).sum()) if total else 0

    application_years = [
        int(v)
        for v in df["application_year_num"].dropna().tolist()
        if int(v) > 0
    ]

    current_year = datetime.now().year
    recent_5y_threshold = current_year - 5
    recent_5y_count = int((df["application_year_num"].fillna(0) >= recent_5y_threshold).sum()) if total else 0

    application_year_min = min(application_years) if application_years else None
    application_year_max = max(application_years) if application_years else None
    application_year_span = (
        application_year_max - application_year_min + 1
        if application_year_min is not None and application_year_max is not None
        else None
    )

    ipc_subclass_count = int(df["ipc_subclass_refined"].replace("", pd.NA).dropna().nunique()) if total else 0
    ipc_main_count = int(df["ipc_main_refined"].replace("", pd.NA).dropna().nunique()) if total else 0

    keyword_total = int(df["tech_keyword_match_count_refined"].fillna(0).sum()) if total else 0
    keyword_avg = round(float(df["tech_keyword_match_count_refined"].fillna(0).mean()), 4) if total else 0.0

    registration_rate = rate(registered_count, total)
    alive_rate_total = rate(alive_count, total)
    alive_rate_registered = rate(alive_count, registered_count)
    recent_5y_rate = rate(recent_5y_count, total)
    h01l_rate = rate(h01l_count, total)
    semiconductor_related_rate = rate(semiconductor_related_count, total)
    negative_disposal_rate = rate(negative_disposal_count, total)

    legal_stability_score = round(
        score_from_rate(registration_rate) * 0.45
        + score_from_rate(alive_rate_registered) * 0.45
        + (100.0 - score_from_rate(negative_disposal_rate)) * 0.10,
        2,
    )

    portfolio_momentum_score = round(
        cap_score(recent_5y_count, 100) * 0.45
        + score_from_rate(recent_5y_rate) * 0.35
        + cap_score(float(application_year_span or 0), 20) * 0.20,
        2,
    )

    ip_technology_fit_score = round(
        score_from_rate(semiconductor_related_rate) * 0.35
        + score_from_rate(h01l_rate) * 0.20
        + cap_score(ipc_subclass_count, 30) * 0.25
        + cap_score(keyword_avg, 2.0) * 0.20,
        2,
    )

    kipris_tech_ml_score = round(
        legal_stability_score * 0.40
        + portfolio_momentum_score * 0.30
        + ip_technology_fit_score * 0.30,
        2,
    )

    if kipris_tech_ml_score >= 75:
        bridge_adjustment = 3.0
        bridge_signal = "IP_QUALITY_STRONG"
    elif kipris_tech_ml_score >= 65:
        bridge_adjustment = 2.0
        bridge_signal = "IP_QUALITY_POSITIVE"
    elif kipris_tech_ml_score >= 55:
        bridge_adjustment = 1.0
        bridge_signal = "IP_QUALITY_MODERATE"
    elif kipris_tech_ml_score >= 40:
        bridge_adjustment = 0.0
        bridge_signal = "IP_QUALITY_NEUTRAL"
    else:
        bridge_adjustment = -2.0
        bridge_signal = "IP_QUALITY_WEAK"

    top_ipc_subclass = (
        df["ipc_subclass_refined"]
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .head(15)
        .to_dict()
    )

    top_ipc_main = (
        df["ipc_main_refined"]
        .replace("", pd.NA)
        .dropna()
        .value_counts()
        .head(15)
        .to_dict()
    )

    top_applicants = {}
    if "applicant_name" in df.columns:
        top_applicants = (
            df["applicant_name"]
            .replace("", pd.NA)
            .dropna()
            .value_counts()
            .head(10)
            .to_dict()
        )

    return {
        "company_slug": company_slug,
        "company_name": company_name,
        "field": field,
        "source_csv": str(source_csv),
        "enriched_csv": str(enriched_csv),
        "generated_at": datetime.now().isoformat(timespec="seconds"),

        "core_counts": {
            "total_patents": total,
            "registered_patents_estimated": registered_count,
            "alive_patents_estimated": alive_count,
            "negative_disposal_patents_estimated": negative_disposal_count,
            "recent_5y_application_patents": recent_5y_count,
            "h01l_core_patents": h01l_count,
            "semiconductor_related_ipc_patents": semiconductor_related_count,
            "ipc_subclass_count": ipc_subclass_count,
            "ipc_main_group_count": ipc_main_count,
            "tech_keyword_match_total": keyword_total,
            "tech_keyword_match_avg": keyword_avg,
        },

        "core_rates": {
            "registration_rate_estimated": registration_rate,
            "alive_rate_total_estimated": alive_rate_total,
            "alive_rate_among_registered_estimated": alive_rate_registered,
            "negative_disposal_rate_estimated": negative_disposal_rate,
            "recent_5y_application_rate": recent_5y_rate,
            "h01l_core_rate": h01l_rate,
            "semiconductor_related_ipc_rate": semiconductor_related_rate,
        },

        "year_features": {
            "application_year_min": application_year_min,
            "application_year_max": application_year_max,
            "application_year_span": application_year_span,
            "recent_5y_threshold": recent_5y_threshold,
        },

        "scores": {
            "legal_stability_score_estimated": legal_stability_score,
            "portfolio_momentum_score": portfolio_momentum_score,
            "ip_technology_fit_score": ip_technology_fit_score,
            "kipris_tech_ml_score": kipris_tech_ml_score,
        },

        "tech_to_value_bridge_adjustment": {
            "bridge_adjustment_points": bridge_adjustment,
            "bridge_signal": bridge_signal,
            "usage_rule": "Add this as a conservative KIPRIS/IP feature adjustment to Tech-to-Value Bridge, but do not treat it as direct commercialization evidence.",
        },

        "top_ipc_subclass": top_ipc_subclass,
        "top_ipc_main_group": top_ipc_main,
        "top_applicants": top_applicants,

        "cautions": [
            "final_disposal is not present in the source CSV, so legal status is estimated from register_status/register_number/register_date.",
            "register_date appears unavailable or unparsable in the current source, so registration year range should not be overclaimed.",
            "KIPRIS/IP score supports technology defensibility, but customer adoption, mass production, sales conversion, and FCF conversion must be verified separately.",
        ],
    }


def write_markdown(features: dict[str, Any], md_path: Path) -> None:
    counts = features["core_counts"]
    rates = features["core_rates"]
    scores = features["scores"]
    bridge = features["tech_to_value_bridge_adjustment"]
    years = features["year_features"]

    lines: list[str] = []
    lines.append(f"# {features['company_name']} KIPRIS Tech ML Features")
    lines.append("")
    lines.append("## 1. Source")
    lines.append(f"- source_csv: `{features['source_csv']}`")
    lines.append(f"- enriched_csv: `{features['enriched_csv']}`")
    lines.append(f"- generated_at: {features['generated_at']}")
    lines.append("")
    lines.append("## 2. Core Counts")
    lines.append(f"- total_patents: {counts['total_patents']}")
    lines.append(f"- registered_patents_estimated: {counts['registered_patents_estimated']}")
    lines.append(f"- alive_patents_estimated: {counts['alive_patents_estimated']}")
    lines.append(f"- recent_5y_application_patents: {counts['recent_5y_application_patents']}")
    lines.append(f"- h01l_core_patents: {counts['h01l_core_patents']}")
    lines.append(f"- semiconductor_related_ipc_patents: {counts['semiconductor_related_ipc_patents']}")
    lines.append(f"- ipc_subclass_count: {counts['ipc_subclass_count']}")
    lines.append(f"- tech_keyword_match_total: {counts['tech_keyword_match_total']}")
    lines.append("")
    lines.append("## 3. Core Rates")
    lines.append(f"- registration_rate_estimated: {rates['registration_rate_estimated']}")
    lines.append(f"- alive_rate_among_registered_estimated: {rates['alive_rate_among_registered_estimated']}")
    lines.append(f"- recent_5y_application_rate: {rates['recent_5y_application_rate']}")
    lines.append(f"- h01l_core_rate: {rates['h01l_core_rate']}")
    lines.append(f"- semiconductor_related_ipc_rate: {rates['semiconductor_related_ipc_rate']}")
    lines.append("")
    lines.append("## 4. Year Features")
    lines.append(f"- application_year_range: {years['application_year_min']} ~ {years['application_year_max']}")
    lines.append(f"- application_year_span: {years['application_year_span']}")
    lines.append("")
    lines.append("## 5. Scores")
    lines.append(f"- legal_stability_score_estimated: {scores['legal_stability_score_estimated']}")
    lines.append(f"- portfolio_momentum_score: {scores['portfolio_momentum_score']}")
    lines.append(f"- ip_technology_fit_score: {scores['ip_technology_fit_score']}")
    lines.append(f"- kipris_tech_ml_score: {scores['kipris_tech_ml_score']}")
    lines.append("")
    lines.append("## 6. Tech-to-Value Bridge Adjustment")
    lines.append(f"- bridge_signal: {bridge['bridge_signal']}")
    lines.append(f"- bridge_adjustment_points: {bridge['bridge_adjustment_points']}")
    lines.append(f"- usage_rule: {bridge['usage_rule']}")
    lines.append("")
    lines.append("## 7. Top IPC Subclass")
    for key, value in features["top_ipc_subclass"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## 8. Cautions")
    for caution in features["cautions"]:
        lines.append(f"- {caution}")
    lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build KIPRIS Tech ML features")
    parser.add_argument("--field", default=DEFAULT_FIELD)
    parser.add_argument("--company-name", default=DEFAULT_COMPANY_NAME)
    parser.add_argument("--company-slug", default=DEFAULT_COMPANY_SLUG)
    args = parser.parse_args()
    field = normalize_field_name(args.field)

    tech_dir = Path("data") / field / args.company_name / "tech"
    source_csv = find_normalized_csv(tech_dir, args.company_slug)

    df = pd.read_csv(source_csv, encoding="utf-8-sig")
    enriched = enrich_dataframe(df)

    enriched_csv = tech_dir / f"{args.company_slug}_kipris_tech_ml_enriched.csv"
    feature_json = tech_dir / f"{args.company_slug}_kipris_tech_ml_features.json"
    feature_md = tech_dir / f"{args.company_slug}_kipris_tech_ml_features.md"

    enriched.to_csv(enriched_csv, index=False, encoding="utf-8-sig")

    features = build_features(
        df=enriched,
        source_csv=source_csv,
        enriched_csv=enriched_csv,
        field=field,
        company_name=args.company_name,
        company_slug=args.company_slug,
    )

    feature_json.write_text(
        json.dumps(features, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_markdown(features, feature_md)

    print("[DONE] KIPRIS Tech ML features created")
    print(f"- source csv: {source_csv}")
    print(f"- enriched csv: {enriched_csv}")
    print(f"- feature json: {feature_json}")
    print(f"- feature md: {feature_md}")
    print()
    print("[FEATURE SUMMARY]")
    print(json.dumps({
        "core_counts": features["core_counts"],
        "core_rates": features["core_rates"],
        "scores": features["scores"],
        "tech_to_value_bridge_adjustment": features["tech_to_value_bridge_adjustment"],
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
