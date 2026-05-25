from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re

import pandas as pd


FIELD = "반도체"
COMPANY_NAME = "네패스"
COMPANY_SLUG = "nepes"

TECH_DIR = Path("data") / FIELD / COMPANY_NAME / "tech"

INPUT_CSV = TECH_DIR / f"{COMPANY_SLUG}_kipris_bibliographic_normalized.csv"

OUT_JSON_COMMON = TECH_DIR / "tech_ip_legal_features.json"
OUT_JSON_COMPANY = TECH_DIR / f"{COMPANY_SLUG}_tech_ip_legal_features.json"
OUT_MD_COMPANY = TECH_DIR / f"{COMPANY_SLUG}_tech_ip_legal_features.md"


NEGATIVE_KEYWORDS = [
    "REJECTED",
    "WITHDRAWN",
    "EXPIRED",
    "LAPSED",
    "거절",
    "취하",
    "소멸",
    "만료",
]

REGISTERED_KEYWORDS = [
    "REGISTERED",
    "등록",
]

ALIVE_NEGATIVE_KEYWORDS = [
    "EXPIRED",
    "LAPSED",
    "REJECTED",
    "WITHDRAWN",
    "소멸",
    "만료",
    "거절",
    "취하",
]

PENDING_KEYWORDS = [
    "PUBLISHED",
    "PENDING",
    "공개",
    "심사",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    text = str(value).strip()

    if text.lower() in {"nan", "none", "null"}:
        return ""

    return re.sub(r"\s+", " ", text)


def has_value(value: Any) -> bool:
    return bool(clean_text(value))


def contains_any(value: Any, keywords: list[str]) -> bool:
    text = clean_text(value).upper()
    return any(keyword.upper() in text for keyword in keywords)


def safe_rate(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def pct(value: float) -> float:
    return round(value * 100, 2)


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def classify_row(row: pd.Series) -> dict[str, bool]:
    register_status = clean_text(row.get("register_status"))
    final_disposal = clean_text(row.get("final_disposal"))
    register_number = clean_text(row.get("register_number"))
    register_date = clean_text(row.get("register_date"))

    status_joined = f"{register_status} {final_disposal}"

    is_negative = contains_any(status_joined, NEGATIVE_KEYWORDS)

    # 등록률은 현재 살아있는 등록뿐 아니라, 등록 후 소멸된 권리도 '등록 이력'으로 본다.
    is_registered = (
        contains_any(status_joined, REGISTERED_KEYWORDS)
        or has_value(register_number)
        or has_value(register_date)
        or "EXPIRED" in final_disposal.upper()
        or "LAPSED" in final_disposal.upper()
    )

    # 존속 추정은 등록 상태이면서 소멸/거절/취하가 아닌 경우로 보수적으로 계산한다.
    is_alive = is_registered and not contains_any(status_joined, ALIVE_NEGATIVE_KEYWORDS)

    is_pending = (
        not is_registered
        and not is_negative
        and contains_any(status_joined, PENDING_KEYWORDS)
    )

    return {
        "is_registered_estimated": bool(is_registered),
        "is_alive_estimated": bool(is_alive),
        "is_negative_disposal_estimated": bool(is_negative),
        "is_pending_or_published_estimated": bool(is_pending),
    }


def coverage(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns or len(df) == 0:
        return 0.0

    return safe_rate(
        df[column].apply(has_value).sum(),
        len(df),
    )


def count_recent_5y(df: pd.DataFrame, date_col: str = "application_date") -> int:
    if date_col not in df.columns or len(df) == 0:
        return 0

    years = []

    for value in df[date_col].tolist():
        text = clean_text(value)
        match = re.match(r"^(\d{4})", text)
        if match:
            years.append(int(match.group(1)))

    if not years:
        return 0

    max_year = max(years)
    min_recent_year = max_year - 4

    return sum(1 for year in years if year >= min_recent_year)


def top_counts(df: pd.DataFrame, column: str, top_n: int = 15) -> dict[str, int]:
    if column not in df.columns:
        return {}

    values: list[str] = []

    for value in df[column].tolist():
        text = clean_text(value)
        if not text:
            continue
        values.append(text)

    if not values:
        return {}

    return {
        str(k): int(v)
        for k, v in pd.Series(values).value_counts().head(top_n).items()
    }


def split_ipc_values(value: Any) -> list[str]:
    text = clean_text(value)
    if not text:
        return []

    parts = re.split(r"[|,;/]+", text)
    return [p.strip() for p in parts if p.strip()]


def ipc_stats(df: pd.DataFrame) -> dict[str, Any]:
    if "ipc_number" not in df.columns:
        return {
            "ipc_raw_count": 0,
            "ipc_unique_count": 0,
            "ipc_subclass_count": 0,
            "h01l_count": 0,
            "h10_related_count": 0,
            "semiconductor_related_count": 0,
            "top_ipc_prefix": {},
        }

    ipc_all: list[str] = []

    for value in df["ipc_number"].tolist():
        ipc_all.extend(split_ipc_values(value))

    unique_ipc = sorted(set(ipc_all))

    subclasses = set()
    h01l_count = 0
    h10_related_count = 0
    semiconductor_related_count = 0
    prefixes: list[str] = []

    for ipc in ipc_all:
        normalized = ipc.upper().strip()

        subclass_match = re.match(r"^([A-H]\d{2}[A-Z])", normalized)
        if subclass_match:
            subclasses.add(subclass_match.group(1))

        prefix_match = re.match(r"^([A-H]\d{2}[A-Z]\s*\d+)", normalized)
        if prefix_match:
            prefixes.append(prefix_match.group(1).replace("  ", " "))

        if normalized.startswith("H01L"):
            h01l_count += 1

        if normalized.startswith("H10"):
            h10_related_count += 1

        if (
            normalized.startswith("H01L")
            or normalized.startswith("H10")
            or normalized.startswith("G06F")
            or normalized.startswith("B23K")
            or "반도체" in normalized
        ):
            semiconductor_related_count += 1

    return {
        "ipc_raw_count": int(len(ipc_all)),
        "ipc_unique_count": int(len(unique_ipc)),
        "ipc_subclass_count": int(len(subclasses)),
        "h01l_count": int(h01l_count),
        "h10_related_count": int(h10_related_count),
        "semiconductor_related_count": int(semiconductor_related_count),
        "top_ipc_prefix": {
            str(k): int(v)
            for k, v in pd.Series(prefixes).value_counts().head(15).items()
        } if prefixes else {},
    }


def calculate_legal_stability_score(
    *,
    registration_rate: float,
    alive_rate_among_registered: float,
    negative_disposal_rate: float,
    right_holder_coverage: float,
    abstract_coverage: float,
    drawing_coverage: float,
    right_transfer_history_coverage: float,
    fee_payment_status_coverage: float,
) -> dict[str, Any]:
    # 100점 만점.
    # 현재 source에 right_transfer_history / fee_payment_status가 없으므로
    # 두 항목은 작은 가중치만 부여하고, 핵심은 등록률·존속률·부정처분 비중에 둔다.
    components = {
        "registration_rate_component": registration_rate * 30.0,
        "alive_rate_component": alive_rate_among_registered * 30.0,
        "negative_disposal_inverse_component": (1.0 - negative_disposal_rate) * 20.0,
        "right_holder_coverage_component": right_holder_coverage * 7.0,
        "abstract_coverage_component": abstract_coverage * 4.0,
        "drawing_coverage_component": drawing_coverage * 4.0,
        "right_transfer_history_coverage_component": right_transfer_history_coverage * 2.5,
        "fee_payment_status_coverage_component": fee_payment_status_coverage * 2.5,
    }

    score = round(clamp(sum(components.values())), 2)

    return {
        "legal_stability_score_estimated": score,
        "score_components": {
            key: round(value, 4)
            for key, value in components.items()
        },
        "score_note": (
            "right_transfer_history와 fee_payment_status는 현재 원천 CSV에 없어 0점 처리했습니다. "
            "따라서 이 점수는 KIPRIS 기본 서지정보 기반 보수 추정값입니다."
        ),
    }


def bridge_signal(
    *,
    legal_stability_score: float,
    registration_rate: float,
    alive_rate_among_registered: float,
    negative_disposal_rate: float,
) -> dict[str, Any]:
    if (
        legal_stability_score >= 80
        and registration_rate >= 0.65
        and alive_rate_among_registered >= 0.80
        and negative_disposal_rate <= 0.40
    ):
        return {
            "bridge_adjustment_points": 2.0,
            "bridge_signal": "IP_LEGAL_STABILITY_POSITIVE",
            "bridge_interpretation": (
                "등록률과 등록권리 내 존속률이 높고 부정처분 비중이 과도하지 않아 "
                "Tech-to-Value Bridge에서 기술 방어력 가산 근거로 사용할 수 있습니다."
            ),
        }

    if legal_stability_score >= 65 and alive_rate_among_registered >= 0.65:
        return {
            "bridge_adjustment_points": 1.0,
            "bridge_signal": "IP_LEGAL_STABILITY_NEUTRAL_POSITIVE",
            "bridge_interpretation": (
                "권리 안정성은 보통 이상이나 일부 부정처분 또는 데이터 공백이 있어 "
                "보수적 가산 근거로만 사용하는 것이 적절합니다."
            ),
        }

    if negative_disposal_rate >= 0.50 or legal_stability_score < 55:
        return {
            "bridge_adjustment_points": -2.0,
            "bridge_signal": "TECH_EVIDENCE_WEAK",
            "bridge_interpretation": (
                "소멸·거절·취하 등 부정처분 비중 또는 권리 안정성 점수가 낮아 "
                "특허 수량만으로 기술가치를 강하게 주장하기 어렵습니다."
            ),
        }

    return {
        "bridge_adjustment_points": 0.0,
        "bridge_signal": "IP_LEGAL_STABILITY_NEUTRAL",
        "bridge_interpretation": (
            "권리 안정성은 중립 수준으로 판단되며, Tech-to-Value Bridge에서는 "
            "별도 가산·감산 없이 보조 근거로 사용하는 것이 적절합니다."
        ),
    }


def build_markdown(feature: dict[str, Any]) -> str:
    c = feature["core_counts"]
    r = feature["core_rates"]
    cov = feature["data_coverage"]
    s = feature["scores"]
    b = feature["tech_to_value_bridge_adjustment"]

    lines = [
        f"# {feature['company_name']} Tech/IP Legal Features",
        "",
        "## 1. 핵심 권리 안정성 지표",
        "",
        f"- 전체 특허 수: {c['total_patents']}건",
        f"- 등록 이력 특허 수: {c['registered_patents_estimated']}건",
        f"- 존속 가능 등록특허 수: {c['alive_patents_estimated']}건",
        f"- 소멸·거절·취하 등 부정처분 추정 특허 수: {c['negative_disposal_patents_estimated']}건",
        f"- 최근 5년 출원 특허 수: {c['recent_5y_application_patents']}건",
        "",
        "## 2. 핵심 비율",
        "",
        f"- 등록률: {pct(r['registration_rate_estimated'])}%",
        f"- 전체 기준 존속률: {pct(r['alive_rate_total_estimated'])}%",
        f"- 등록특허 내 존속률: {pct(r['alive_rate_among_registered_estimated'])}%",
        f"- 소멸·거절·취하 비중: {pct(r['negative_disposal_rate_estimated'])}%",
        f"- 최근 5년 출원 비중: {pct(r['recent_5y_application_rate'])}%",
        "",
        "## 3. 데이터 반영률",
        "",
        f"- 권리자 정보 반영률: {pct(cov['right_holder_coverage'])}%",
        f"- 권리이전 이력 반영률: {pct(cov['right_transfer_history_coverage'])}%",
        f"- 연차료 납부상태 반영률: {pct(cov['fee_payment_status_coverage'])}%",
        f"- 초록 반영률: {pct(cov['abstract_coverage'])}%",
        f"- 도면 반영률: {pct(cov['drawing_coverage'])}%",
        "",
        "## 4. 권리 안정성 점수",
        "",
        f"- legal_stability_score_estimated: {s['legal_stability_score_estimated']}",
        "",
        "## 5. Tech-to-Value Bridge 반영 신호",
        "",
        f"- bridge_adjustment_points: {b['bridge_adjustment_points']}",
        f"- bridge_signal: {b['bridge_signal']}",
        f"- 해석: {b['bridge_interpretation']}",
        "",
        "## 6. 주의",
        "",
        "- 이 결과는 KIPRIS 기본 서지정보 기반의 보수 추정값입니다.",
        "- right_transfer_history와 fee_payment_status는 현재 원천 CSV에 없어 KIPRIS Plus 추가 수집 대상으로 남겨둡니다.",
        "- 이 지표는 직접적인 매출화 증거가 아니라 Tech-to-Value Bridge의 권리 안정성 보조 신호입니다.",
    ]

    return "\n".join(lines)


def main() -> int:
    if not INPUT_CSV.exists():
        print(f"[ERROR] normalized CSV가 없습니다: {INPUT_CSV}")
        print("먼저 scripts\\normalize_kipris_ip_legal_nepes.py 를 실행하세요.")
        return 1

    df = pd.read_csv(INPUT_CSV, dtype=str, keep_default_na=False, encoding="utf-8-sig")

    if len(df) == 0:
        print("[ERROR] normalized CSV가 비어 있습니다.")
        return 1

    class_rows = df.apply(classify_row, axis=1, result_type="expand")

    for col in class_rows.columns:
        df[col] = class_rows[col].astype(bool)

    total = int(len(df))
    registered_count = int(df["is_registered_estimated"].sum())
    alive_count = int(df["is_alive_estimated"].sum())
    negative_count = int(df["is_negative_disposal_estimated"].sum())
    pending_count = int(df["is_pending_or_published_estimated"].sum())
    recent_5y_count = int(count_recent_5y(df))

    registration_rate = safe_rate(registered_count, total)
    alive_rate_total = safe_rate(alive_count, total)
    alive_rate_registered = safe_rate(alive_count, registered_count)
    negative_rate = safe_rate(negative_count, total)
    pending_rate = safe_rate(pending_count, total)
    recent_5y_rate = safe_rate(recent_5y_count, total)

    data_coverage = {
        "application_date_coverage": coverage(df, "application_date"),
        "open_number_coverage": coverage(df, "open_number"),
        "open_date_coverage": coverage(df, "open_date"),
        "publication_number_coverage": coverage(df, "publication_number"),
        "publication_date_coverage": coverage(df, "publication_date"),
        "register_number_coverage": coverage(df, "register_number"),
        "register_date_coverage": coverage(df, "register_date"),
        "register_status_coverage": coverage(df, "register_status"),
        "final_disposal_coverage": coverage(df, "final_disposal"),
        "right_holder_coverage": coverage(df, "right_holder"),
        "right_transfer_history_coverage": coverage(df, "right_transfer_history"),
        "fee_payment_status_coverage": coverage(df, "fee_payment_status"),
        "abstract_coverage": coverage(df, "abstract"),
        "drawing_coverage": coverage(df, "drawing"),
        "big_drawing_coverage": coverage(df, "big_drawing"),
    }

    score_result = calculate_legal_stability_score(
        registration_rate=registration_rate,
        alive_rate_among_registered=alive_rate_registered,
        negative_disposal_rate=negative_rate,
        right_holder_coverage=data_coverage["right_holder_coverage"],
        abstract_coverage=data_coverage["abstract_coverage"],
        drawing_coverage=data_coverage["drawing_coverage"],
        right_transfer_history_coverage=data_coverage["right_transfer_history_coverage"],
        fee_payment_status_coverage=data_coverage["fee_payment_status_coverage"],
    )

    bridge = bridge_signal(
        legal_stability_score=score_result["legal_stability_score_estimated"],
        registration_rate=registration_rate,
        alive_rate_among_registered=alive_rate_registered,
        negative_disposal_rate=negative_rate,
    )

    ipc = ipc_stats(df)

    feature = {
        "company_slug": COMPANY_SLUG,
        "company_name": COMPANY_NAME,
        "field": FIELD,
        "source_csv": str(INPUT_CSV),
        "feature_files": {
            "common_json": str(OUT_JSON_COMMON),
            "company_json": str(OUT_JSON_COMPANY),
            "company_md": str(OUT_MD_COMPANY),
        },
        "feature_type": "kipris_ip_legal_stability_features",
        "core_counts": {
            "total_patents": total,
            "registered_patents_estimated": registered_count,
            "alive_patents_estimated": alive_count,
            "negative_disposal_patents_estimated": negative_count,
            "pending_or_published_patents_estimated": pending_count,
            "recent_5y_application_patents": recent_5y_count,
        },
        "core_rates": {
            "registration_rate_estimated": registration_rate,
            "alive_rate_total_estimated": alive_rate_total,
            "alive_rate_among_registered_estimated": alive_rate_registered,
            "negative_disposal_rate_estimated": negative_rate,
            "pending_or_published_rate_estimated": pending_rate,
            "recent_5y_application_rate": recent_5y_rate,
        },
        "data_coverage": data_coverage,
        "ipc_stats": ipc,
        "top_final_disposal": top_counts(df, "final_disposal", 15),
        "top_register_status": top_counts(df, "register_status", 15),
        "top_right_holders": top_counts(df, "right_holder", 15),
        "scores": score_result,
        "tech_to_value_bridge_adjustment": bridge,
        "interpretation": {
            "summary": (
                f"{COMPANY_NAME}의 KIPRIS 기본 서지정보 기준 등록률은 {pct(registration_rate)}%, "
                f"등록특허 내 존속률은 {pct(alive_rate_registered)}%, "
                f"소멸·거절·취하 등 부정처분 비중은 {pct(negative_rate)}%입니다. "
                f"권리 안정성 점수는 {score_result['legal_stability_score_estimated']}점으로 산출되었습니다."
            ),
            "caution": (
                "right_transfer_history와 fee_payment_status는 현재 원천 CSV에 없어 "
                "KIPRIS Plus 추가 수집 후 보완하는 것이 필요합니다."
            ),
            "bridge_usage_rule": (
                "Tech-to-Value Bridge에서는 특허 수량이 아니라 등록률, 존속률, 부정처분 비중, "
                "권리자 정보 반영률을 함께 반영해 기술 방어력 보조 가산/감산 신호로 사용합니다."
            ),
        },
        "notes": [
            "final_disposal은 normalized CSV에서 보수 추정된 값을 사용했습니다.",
            "소멸·거절·취하는 negative_disposal_patents_estimated에 포함했습니다.",
            "등록률은 현재 등록 상태뿐 아니라 등록번호/등록일이 있는 소멸 권리도 등록 이력으로 계산했습니다.",
            "존속률은 등록 이력이 있으면서 소멸·거절·취하가 아닌 권리만 보수적으로 계산했습니다.",
            "이 결과는 직접적인 사업화·매출화 증거가 아니라 IP 권리 안정성 보조 feature입니다.",
        ],
    }

    OUT_JSON_COMMON.write_text(json.dumps(feature, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_JSON_COMPANY.write_text(json.dumps(feature, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD_COMPANY.write_text(build_markdown(feature), encoding="utf-8")

    print("[DONE] Tech/IP legal stability features created")
    print(f"- input csv: {INPUT_CSV}")
    print(f"- common json: {OUT_JSON_COMMON}")
    print(f"- company json: {OUT_JSON_COMPANY}")
    print(f"- company md: {OUT_MD_COMPANY}")
    print()
    print("[FEATURE SUMMARY]")
    print(json.dumps({
        "core_counts": feature["core_counts"],
        "core_rates": feature["core_rates"],
        "data_coverage": {
            "right_holder_coverage": data_coverage["right_holder_coverage"],
            "right_transfer_history_coverage": data_coverage["right_transfer_history_coverage"],
            "fee_payment_status_coverage": data_coverage["fee_payment_status_coverage"],
            "abstract_coverage": data_coverage["abstract_coverage"],
            "drawing_coverage": data_coverage["drawing_coverage"],
        },
        "scores": {
            "legal_stability_score_estimated": score_result["legal_stability_score_estimated"],
        },
        "tech_to_value_bridge_adjustment": bridge,
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
