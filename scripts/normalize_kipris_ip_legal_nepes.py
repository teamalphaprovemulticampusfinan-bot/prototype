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
SOURCE_CSV = TECH_DIR / "source" / "kipris_nepes_patents.csv"

OUT_CSV = TECH_DIR / f"{COMPANY_SLUG}_kipris_bibliographic_normalized.csv"
OUT_JSON = TECH_DIR / f"{COMPANY_SLUG}_kipris_bibliographic_normalized_summary.json"
OUT_MD = TECH_DIR / f"{COMPANY_SLUG}_kipris_bibliographic_normalized_summary.md"


ALIASES = {
    "query_applicant": ["query_applicant", "검색출원인", "조회출원인"],
    "index_no": ["index_no", "번호", "순번"],
    "register_status": ["register_status", "registration_status", "등록상태", "상태"],
    "invention_title": ["invention_title", "발명의명칭", "발명명칭", "특허명", "제목"],
    "ipc_number": ["ipc_number", "ipc", "IPC", "ipc분류", "IPC분류"],
    "register_number": ["register_number", "registration_number", "등록번호"],
    "register_date": ["register_date", "registration_date", "등록일자", "등록일"],
    "application_number": ["application_number", "출원번호"],
    "application_date": ["application_date", "출원일자", "출원일"],
    "open_number": ["open_number", "publication_number", "pub_no", "공개번호"],
    "open_date": ["open_date", "publication_date", "pub_date", "공개일자", "공개일"],
    "publication_number": ["publication_number", "공고번호"],
    "publication_date": ["publication_date", "공고일자", "공고일"],
    "abstract": ["abstract", "summary", "초록", "요약", "요약문"],
    "drawing": ["drawing", "대표도면", "도면"],
    "big_drawing": ["big_drawing", "큰도면", "대형도면"],
    "applicant_name": ["applicant_name", "출원인", "출원인명", "권리자", "right_holder"],
    "final_disposal": ["final_disposal", "final_status", "최종처분", "최종처분내용"],
    "right_holder": ["right_holder", "권리자", "권리자명"],
    "right_transfer_history": ["right_transfer_history", "권리이전", "권리이전이력", "양도이력"],
    "fee_payment_status": ["fee_payment_status", "연차료", "연차료납부", "수수료납부상태"],
}


OUTPUT_COLUMNS = [
    "company_slug",
    "company_name",
    "source_file",
    "source_row_number",
    "query_applicant",
    "index_no",
    "application_number",
    "application_date",
    "open_number",
    "open_date",
    "publication_number",
    "publication_date",
    "register_number",
    "register_date",
    "register_status",
    "final_disposal",
    "final_disposal_source",
    "right_holder",
    "right_holder_source",
    "right_transfer_history",
    "right_transfer_history_source",
    "fee_payment_status",
    "fee_payment_status_source",
    "invention_title",
    "ipc_number",
    "abstract",
    "drawing",
    "big_drawing",
    "applicant_name",
]


DATE_COLUMNS = {
    "application_date",
    "open_date",
    "publication_date",
    "register_date",
}

ID_COLUMNS = {
    "application_number",
    "open_number",
    "publication_number",
    "register_number",
    "index_no",
}


def norm_col(value: Any) -> str:
    text = str(value or "").strip().lower()
    return re.sub(r"[\s_\-./()\[\]{}:]+", "", text)


def read_csv(path: Path) -> pd.DataFrame:
    last_error = None

    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            return pd.read_csv(
                path,
                encoding=enc,
                dtype=str,
                keep_default_na=False,
            )
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"CSV 읽기 실패: {path} / {last_error}")


def find_col(df: pd.DataFrame, canonical: str) -> str | None:
    col_map = {norm_col(c): c for c in df.columns}

    for alias in ALIASES.get(canonical, [canonical]):
        key = norm_col(alias)
        if key in col_map:
            return col_map[key]

    return None


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

    text = re.sub(r"\s+", " ", text)

    # pandas float artifact 제거: 20190227.0 -> 20190227
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".")[0]

    return text


def normalize_identifier(value: Any) -> str:
    text = clean_text(value)

    if not text:
        return ""

    # 1020190019874.0 같은 식별번호 artifact 제거
    if re.fullmatch(r"\d+\.0+", text):
        return text.split(".")[0]

    return text


def normalize_date(value: Any) -> str:
    text = clean_text(value)

    if not text:
        return ""

    # 이미 YYYY-MM-DD면 그대로 사용
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text

    # 20190227.0 -> 20190227
    if re.fullmatch(r"\d+\.0+", text):
        text = text.split(".")[0]

    digits = re.sub(r"\D", "", text)

    if len(digits) == 8:
        yyyy = digits[:4]
        mm = digits[4:6]
        dd = digits[6:8]
        return f"{yyyy}-{mm}-{dd}"

    if len(digits) == 6:
        yyyy = digits[:4]
        mm = digits[4:6]
        return f"{yyyy}-{mm}"

    if len(digits) == 4:
        return digits

    return text


def has_value(value: Any) -> bool:
    return bool(clean_text(value))


def derive_final_disposal(row: dict[str, Any]) -> tuple[str, str]:
    raw = clean_text(row.get("final_disposal"))
    if raw:
        return raw, "source.final_disposal"

    status = clean_text(row.get("register_status"))
    reg_no = clean_text(row.get("register_number"))
    reg_date = clean_text(row.get("register_date"))

    status_l = status.lower()

    if "거절" in status or "rejected" in status_l:
        return "REJECTED_ESTIMATED", "derived_from_register_status"

    if "취하" in status or "withdraw" in status_l:
        return "WITHDRAWN_ESTIMATED", "derived_from_register_status"

    if (
        "소멸" in status
        or "만료" in status
        or "expired" in status_l
        or "lapse" in status_l
    ):
        return "EXPIRED_OR_LAPSED_ESTIMATED", "derived_from_register_status"

    if "등록" in status or "registered" in status_l or reg_no or reg_date:
        return "REGISTERED_ESTIMATED", "derived_from_register_status_or_registration_fields"

    if "공개" in status:
        return "PUBLISHED_PENDING_ESTIMATED", "derived_from_register_status"

    if status:
        return status, "derived_from_register_status"

    return "UNKNOWN", "not_available_in_source"


def coverage_ratio(df: pd.DataFrame, col: str) -> float:
    if len(df) == 0 or col not in df.columns:
        return 0.0

    return round(
        df[col].astype(str).str.strip().replace("nan", "").ne("").sum() / len(df),
        4,
    )


def main() -> int:
    if not SOURCE_CSV.exists():
        print(f"[ERROR] 원천 CSV가 없습니다: {SOURCE_CSV}")
        return 1

    TECH_DIR.mkdir(parents=True, exist_ok=True)

    raw = read_csv(SOURCE_CSV)
    col_lookup = {key: find_col(raw, key) for key in ALIASES}

    rows: list[dict[str, Any]] = []

    for i, (_, src_row) in enumerate(raw.iterrows(), start=1):
        item: dict[str, Any] = {
            "company_slug": COMPANY_SLUG,
            "company_name": COMPANY_NAME,
            "source_file": str(SOURCE_CSV),
            "source_row_number": i,
        }

        for canonical in ALIASES:
            source_col = col_lookup.get(canonical)

            if source_col:
                value = src_row.get(source_col)
            else:
                value = ""

            if canonical in DATE_COLUMNS:
                item[canonical] = normalize_date(value)
            elif canonical in ID_COLUMNS:
                item[canonical] = normalize_identifier(value)
            else:
                item[canonical] = clean_text(value)

        # right_holder 원천 컬럼이 없으면 applicant_name을 대체값으로 사용
        if has_value(item.get("right_holder")):
            item["right_holder_source"] = "source.right_holder"
        elif has_value(item.get("applicant_name")):
            item["right_holder"] = item.get("applicant_name")
            item["right_holder_source"] = "derived_from_applicant_name"
        else:
            item["right_holder"] = ""
            item["right_holder_source"] = "not_available_in_source"

        if has_value(item.get("right_transfer_history")):
            item["right_transfer_history_source"] = "source.right_transfer_history"
        else:
            item["right_transfer_history"] = ""
            item["right_transfer_history_source"] = "not_available_in_source"

        if has_value(item.get("fee_payment_status")):
            item["fee_payment_status_source"] = "source.fee_payment_status"
        else:
            item["fee_payment_status"] = ""
            item["fee_payment_status_source"] = "not_available_in_source"

        item["final_disposal"], item["final_disposal_source"] = derive_final_disposal(item)

        rows.append({col: item.get(col, "") for col in OUTPUT_COLUMNS})

    normalized = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    normalized.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    summary = {
        "company_slug": COMPANY_SLUG,
        "company_name": COMPANY_NAME,
        "source_file": str(SOURCE_CSV),
        "normalized_csv": str(OUT_CSV),
        "total_patents": int(len(normalized)),
        "columns": list(normalized.columns),
        "coverage": {
            "application_date": coverage_ratio(normalized, "application_date"),
            "open_number": coverage_ratio(normalized, "open_number"),
            "open_date": coverage_ratio(normalized, "open_date"),
            "publication_number": coverage_ratio(normalized, "publication_number"),
            "publication_date": coverage_ratio(normalized, "publication_date"),
            "register_number": coverage_ratio(normalized, "register_number"),
            "register_date": coverage_ratio(normalized, "register_date"),
            "register_status": coverage_ratio(normalized, "register_status"),
            "final_disposal": coverage_ratio(normalized, "final_disposal"),
            "right_holder": coverage_ratio(normalized, "right_holder"),
            "right_transfer_history": coverage_ratio(normalized, "right_transfer_history"),
            "fee_payment_status": coverage_ratio(normalized, "fee_payment_status"),
            "abstract": coverage_ratio(normalized, "abstract"),
            "drawing": coverage_ratio(normalized, "drawing"),
            "big_drawing": coverage_ratio(normalized, "big_drawing"),
        },
        "source_mapping": {
            key: str(value) if value is not None else None
            for key, value in col_lookup.items()
        },
        "notes": [
            "final_disposal 원천 컬럼이 없으면 register_status/register_number/register_date 기준으로 보수 추정했습니다.",
            "right_holder 원천 컬럼이 없으면 applicant_name을 대체값으로 사용했습니다.",
            "right_transfer_history와 fee_payment_status는 원천 CSV에 없으면 빈 값으로 유지하고 KIPRIS Plus 추가 수집 대상으로 남겼습니다.",
            "날짜 컬럼은 YYYY-MM-DD 형식으로 정규화했습니다.",
            "번호 컬럼은 pandas 숫자형 artifact인 .0을 제거했습니다.",
        ],
    }

    OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        f"# {COMPANY_NAME} KIPRIS Bibliographic Normalized Summary",
        "",
        f"- source: `{SOURCE_CSV}`",
        f"- normalized csv: `{OUT_CSV}`",
        f"- total_patents: {len(normalized)}",
        "",
        "## Coverage",
    ]

    for key, value in summary["coverage"].items():
        md_lines.append(f"- {key}: {value}")

    md_lines.extend(["", "## Notes"])

    for note in summary["notes"]:
        md_lines.append(f"- {note}")

    OUT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print("[DONE] KIPRIS bibliographic normalized CSV created")
    print(f"- source rows: {len(raw)}")
    print(f"- normalized rows: {len(normalized)}")
    print(f"- normalized csv: {OUT_CSV}")
    print(f"- summary json: {OUT_JSON}")
    print(f"- summary md: {OUT_MD}")
    print()
    print("[COVERAGE]")
    print(json.dumps(summary["coverage"], ensure_ascii=False, indent=2))

    print()
    print("[FIRST 5 CHECK]")
    check_cols = [
        "application_number",
        "application_date",
        "open_number",
        "open_date",
        "register_number",
        "register_date",
        "register_status",
        "final_disposal",
        "right_holder",
    ]
    print(normalized[check_cols].head(5).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
