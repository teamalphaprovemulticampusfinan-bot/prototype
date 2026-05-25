from __future__ import annotations

import argparse
import json
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


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null", "nat"}:
        return ""
    if text.endswith(".0") and re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text.strip()


def _norm_key(value: Any) -> str:
    text = _clean_text(value).lower()
    return re.sub(r"[\s_\-./()\[\]{}:]+", "", text)


def _read_csv(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(path, encoding=enc, dtype=str).fillna("")
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"CSV 읽기 실패: {path} / {last_error}")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _find_col(df: pd.DataFrame, aliases: list[str]) -> str:
    norm_map = {_norm_key(c): c for c in df.columns}

    for alias in aliases:
        key = _norm_key(alias)
        if key in norm_map:
            return norm_map[key]

    for alias in aliases:
        key = _norm_key(alias)
        for nk, col in norm_map.items():
            if key and (key in nk or nk in key):
                return col

    return ""


def _coverage(df: pd.DataFrame, col: str) -> float:
    if not col or col not in df.columns or len(df) == 0:
        return 0.0
    s = df[col].map(_clean_text)
    return round(float((s != "").mean()), 4)


def _contains_any(text: str, words: list[str]) -> bool:
    t = _clean_text(text).upper()
    return any(w.upper() in t for w in words)


def _is_registered(row: dict[str, Any], cols: dict[str, str]) -> bool:
    register_status = _clean_text(row.get(cols.get("register_status", ""), ""))
    final_disposal = _clean_text(row.get(cols.get("final_disposal", ""), ""))
    register_number = _clean_text(row.get(cols.get("register_number", ""), ""))
    register_date = _clean_text(row.get(cols.get("register_date", ""), ""))

    if _contains_any(register_status, ["등록", "REGISTER"]):
        return True
    if _contains_any(final_disposal, ["등록", "REGISTER"]):
        return True
    if register_number or register_date:
        return True
    return False


def _is_negative_disposal(row: dict[str, Any], cols: dict[str, str]) -> bool:
    text = " ".join(
        _clean_text(row.get(cols.get(k, ""), ""))
        for k in ["register_status", "final_disposal", "legal_status"]
    )

    negative_words = [
        "거절", "취하", "포기", "소멸", "무효", "취소", "각하", "불수리",
        "REJECT", "WITHDRAW", "ABANDON", "EXPIRE", "INVALID", "CANCEL", "DEAD",
    ]

    return _contains_any(text, negative_words)


def _is_alive_estimated(row: dict[str, Any], cols: dict[str, str]) -> bool:
    if not _is_registered(row, cols):
        return False

    text = " ".join(
        _clean_text(row.get(cols.get(k, ""), ""))
        for k in ["register_status", "final_disposal", "legal_status", "fee_payment_status"]
    )

    dead_words = [
        "소멸", "만료", "포기", "무효", "취소", "EXPIRE", "EXPIRED", "LAPSE", "LAPSED",
        "ABANDON", "INVALID", "CANCEL", "DEAD",
    ]

    return not _contains_any(text, dead_words)


def _score_legal_stability(
    registration_rate: float,
    alive_rate_among_registered: float,
    negative_disposal_rate: float,
    right_holder_coverage: float,
    fee_payment_status_coverage: float,
) -> float:
    score = (
        registration_rate * 35
        + alive_rate_among_registered * 35
        + (1 - negative_disposal_rate) * 20
        + right_holder_coverage * 5
        + fee_payment_status_coverage * 5
    )
    return round(max(0.0, min(100.0, score)), 2)


def _bridge_signal(score: float, registration_rate: float, alive_rate: float, negative_rate: float) -> tuple[float, str]:
    if score >= 80 and registration_rate >= 0.65 and alive_rate >= 0.70 and negative_rate <= 0.30:
        return 2.0, "IP_LEGAL_STABILITY_STRONG_POSITIVE"
    if score >= 65 and registration_rate >= 0.45 and alive_rate >= 0.55:
        return 1.0, "IP_LEGAL_STABILITY_NEUTRAL_POSITIVE"
    if score >= 45:
        return 0.0, "IP_LEGAL_STABILITY_NEUTRAL"
    return -1.0, "IP_LEGAL_STABILITY_WEAK"


def _build_markdown(feature: dict[str, Any]) -> str:
    lines = []
    lines.append(f"# {feature.get('company_name')} KIPRIS IP Legal Stability Feature")
    lines.append("")
    lines.append("## 1. Summary")
    lines.append(f"- status: {feature.get('status')}")
    lines.append(f"- total_patents: {feature.get('total_patents')}")
    lines.append(f"- registered_patents_estimated: {feature.get('registered_patents_estimated')}")
    lines.append(f"- alive_patents_estimated: {feature.get('alive_patents_estimated')}")
    lines.append(f"- negative_disposal_patents_estimated: {feature.get('negative_disposal_patents_estimated')}")
    lines.append("")
    lines.append("## 2. Core Rates")
    lines.append(f"- registration_rate_estimated: {feature.get('registration_rate_estimated')}")
    lines.append(f"- alive_rate_among_registered_estimated: {feature.get('alive_rate_among_registered_estimated')}")
    lines.append(f"- negative_disposal_rate_estimated: {feature.get('negative_disposal_rate_estimated')}")
    lines.append("")
    lines.append("## 3. Coverage")
    lines.append(f"- right_holder_coverage: {feature.get('right_holder_coverage')}")
    lines.append(f"- right_transfer_history_coverage: {feature.get('right_transfer_history_coverage')}")
    lines.append(f"- fee_payment_status_coverage: {feature.get('fee_payment_status_coverage')}")
    lines.append(f"- abstract_coverage: {feature.get('abstract_coverage')}")
    lines.append(f"- drawing_coverage: {feature.get('drawing_coverage')}")
    lines.append("")
    lines.append("## 4. Tech-to-Value Bridge")
    lines.append(f"- legal_stability_score_estimated: {feature.get('legal_stability_score_estimated')}")
    lines.append(f"- bridge_adjustment_points: {feature.get('bridge_adjustment_points')}")
    lines.append(f"- bridge_signal: {feature.get('bridge_signal')}")
    lines.append(f"- usage_rule: {feature.get('usage_rule')}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build KIPRIS IP legal stability features from normalized patent CSV.")
    parser.add_argument("--field", required=True, help="예: 반도체")
    parser.add_argument("--company-name", required=True, help="예: 한미반도체")
    parser.add_argument("--company-slug", required=True, help="예: hanmi")
    parser.add_argument("--force", action="store_true", help="호환성 옵션: 기존 산출물을 덮어씁니다.")
    args = parser.parse_args()
    field = normalize_field_name(args.field)

    tech_dir = Path("data") / field / args.company_name / "tech"

    candidates = [
        tech_dir / f"{args.company_slug}_kipris_bibliographic_normalized.csv",
        tech_dir / f"{args.company_slug}_kipris_patents_normalized.csv",
        tech_dir / f"{args.company_slug}_tech_patent_normalized.csv",
    ]

    input_csv = next((p for p in candidates if p.exists()), None)
    if input_csv is None:
        raise FileNotFoundError(
            "KIPRIS normalized CSV를 찾지 못했습니다:\n"
            + "\n".join(str(p) for p in candidates)
        )

    df = _read_csv(input_csv)
    total = int(len(df))

    cols = {
        "application_number": _find_col(df, ["application_number", "applicationNumber", "출원번호"]),
        "application_date": _find_col(df, ["application_date", "applicationDate", "출원일자", "출원일"]),
        "open_number": _find_col(df, ["open_number", "openNumber", "공개번호"]),
        "open_date": _find_col(df, ["open_date", "openDate", "공개일자", "공개일"]),
        "publication_number": _find_col(df, ["publication_number", "publicationNumber", "공고번호", "공보번호"]),
        "publication_date": _find_col(df, ["publication_date", "publicationDate", "공고일자", "공보일자"]),
        "register_number": _find_col(df, ["register_number", "registerNumber", "registration_number", "등록번호"]),
        "register_date": _find_col(df, ["register_date", "registerDate", "registration_date", "등록일자", "등록일"]),
        "register_status": _find_col(df, ["register_status", "registerStatus", "registration_status", "등록상태", "상태"]),
        "final_disposal": _find_col(df, ["final_disposal", "finalDisposal", "final_status", "최종처분", "처분상태"]),
        "legal_status": _find_col(df, ["legal_status", "legalStatus", "법적상태"]),
        "right_holder": _find_col(df, ["right_holder", "rightHolder", "권리자", "출원인", "applicant"]),
        "right_transfer_history": _find_col(df, ["right_transfer_history", "rightTransferHistory", "권리이전", "권리변동"]),
        "fee_payment_status": _find_col(df, ["fee_payment_status", "feePaymentStatus", "연차료", "등록료", "료납부"]),
        "abstract": _find_col(df, ["abstract", "초록", "요약"]),
        "drawing": _find_col(df, ["drawing", "도면"]),
        "big_drawing": _find_col(df, ["big_drawing", "대표도면", "큰도면"]),
    }

    rows = df.to_dict(orient="records")

    registered = sum(1 for row in rows if _is_registered(row, cols))
    negative = sum(1 for row in rows if _is_negative_disposal(row, cols))
    alive = sum(1 for row in rows if _is_alive_estimated(row, cols))

    registration_rate = registered / total if total else 0.0
    alive_rate = alive / registered if registered else 0.0
    negative_rate = negative / total if total else 0.0

    right_holder_coverage = _coverage(df, cols["right_holder"])
    right_transfer_history_coverage = _coverage(df, cols["right_transfer_history"])
    fee_payment_status_coverage = _coverage(df, cols["fee_payment_status"])
    abstract_coverage = _coverage(df, cols["abstract"])
    drawing_coverage = max(_coverage(df, cols["drawing"]), _coverage(df, cols["big_drawing"]))

    legal_score = _score_legal_stability(
        registration_rate=registration_rate,
        alive_rate_among_registered=alive_rate,
        negative_disposal_rate=negative_rate,
        right_holder_coverage=right_holder_coverage,
        fee_payment_status_coverage=fee_payment_status_coverage,
    )

    bridge_points, bridge_signal = _bridge_signal(
        score=legal_score,
        registration_rate=registration_rate,
        alive_rate=alive_rate,
        negative_rate=negative_rate,
    )

    feature = {
        "company_slug": args.company_slug,
        "company_name": args.company_name,
        "status": "OK",
        "source_file": str(input_csv),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "total_patents": total,
        "registered_patents_estimated": int(registered),
        "alive_patents_estimated": int(alive),
        "negative_disposal_patents_estimated": int(negative),
        "registration_rate_estimated": round(registration_rate, 4),
        "alive_rate_among_registered_estimated": round(alive_rate, 4),
        "negative_disposal_rate_estimated": round(negative_rate, 4),
        "right_holder_coverage": right_holder_coverage,
        "right_transfer_history_coverage": right_transfer_history_coverage,
        "fee_payment_status_coverage": fee_payment_status_coverage,
        "abstract_coverage": abstract_coverage,
        "drawing_coverage": drawing_coverage,
        "legal_stability_score_estimated": legal_score,
        "kipris_tech_ml_score": legal_score,
        "bridge_adjustment_points": bridge_points,
        "bridge_signal": bridge_signal,
        "detected_columns": cols,
        "usage_rule": (
            "KIPRIS normalized bibliographic/legal fields 기반 권리 안정성 추정치입니다. "
            "등록률·존속률·부정 처분 비중·권리자/연차료 커버리지를 Tech-to-Value Bridge의 보조 조정 신호로만 사용합니다."
        ),
    }

    slug_json = tech_dir / f"{args.company_slug}_tech_ip_legal_features.json"
    common_json = tech_dir / "tech_ip_legal_features.json"
    md_path = tech_dir / f"{args.company_slug}_tech_ip_legal_features.md"

    _write_json(slug_json, feature)
    _write_json(common_json, feature)
    _write_text(md_path, _build_markdown(feature))

    print("[DONE] IP legal feature created")
    print(f"- input csv: {input_csv}")
    print(f"- feature json: {slug_json}")
    print(f"- common feature json: {common_json}")
    print(f"- feature md: {md_path}")
    print()
    print("[FEATURE SUMMARY]")
    print(json.dumps({
        "status": feature.get("status"),
        "total_patents": feature.get("total_patents"),
        "registered_patents_estimated": feature.get("registered_patents_estimated"),
        "alive_patents_estimated": feature.get("alive_patents_estimated"),
        "negative_disposal_patents_estimated": feature.get("negative_disposal_patents_estimated"),
        "registration_rate_estimated": feature.get("registration_rate_estimated"),
        "alive_rate_among_registered_estimated": feature.get("alive_rate_among_registered_estimated"),
        "negative_disposal_rate_estimated": feature.get("negative_disposal_rate_estimated"),
        "legal_stability_score_estimated": feature.get("legal_stability_score_estimated"),
        "bridge_adjustment_points": feature.get("bridge_adjustment_points"),
        "bridge_signal": feature.get("bridge_signal"),
    }, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
