from __future__ import annotations

from pathlib import Path
import re
import pandas as pd


SOURCE_DIR = Path("data") / "반도체" / "네패스" / "tech" / "source"

TARGET_COLUMNS = {
    "application_date": ["application_date", "appl_date", "출원일자", "출원일", "출원 날짜"],
    "open_number": ["open_number", "publication_number", "pub_no", "공개번호", "공개 번호"],
    "open_date": ["open_date", "publication_date", "pub_date", "공개일자", "공개일"],
    "register_date": ["register_date", "registration_date", "reg_date", "등록일자", "등록일"],
    "final_disposal": ["final_disposal", "final_status", "최종처분", "최종 처분", "최종처분내용", "처분상태", "심사상태"],
    "register_status": ["register_status", "registration_status", "등록상태", "등록 상태", "등록여부", "상태", "status"],
    "abstract": ["abstract", "summary", "요약", "초록", "요약문"],
    "drawing": ["drawing", "drawings", "representative_drawing", "대표도면", "도면", "도면URL"],
}


def norm(text: object) -> str:
    text = str(text or "").strip().lower()
    return re.sub(r"[\s_\-./()\[\]{}:]+", "", text)


def read_table(path: Path) -> dict[str, pd.DataFrame]:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        sheets = pd.read_excel(path, sheet_name=None, nrows=5)
        return {str(k): v for k, v in sheets.items()}

    last_error = None
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            df = pd.read_csv(path, encoding=enc, nrows=5)
            return {"csv": df}
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"CSV 읽기 실패: {last_error}")


def check_columns(columns: list[str]) -> tuple[dict[str, str], list[str]]:
    normalized_map = {norm(col): col for col in columns}

    found: dict[str, str] = {}
    missing: list[str] = []

    for canonical, aliases in TARGET_COLUMNS.items():
        matched_col = None
        for alias in aliases:
            key = norm(alias)
            if key in normalized_map:
                matched_col = normalized_map[key]
                break

        if matched_col:
            found[canonical] = matched_col
        else:
            missing.append(canonical)

    return found, missing


def main() -> int:
    if not SOURCE_DIR.exists():
        print(f"[ERROR] source 폴더가 없습니다: {SOURCE_DIR}")
        return 1

    files = []
    for pattern in ["*kipris*.csv", "*KIPRIS*.csv", "*특허*.csv", "*patent*.csv",
                    "*kipris*.xlsx", "*KIPRIS*.xlsx", "*특허*.xlsx", "*patent*.xlsx"]:
        files.extend(SOURCE_DIR.glob(pattern))

    files = sorted(set(files))

    if not files:
        print(f"[ERROR] KIPRIS/특허 원천 파일을 찾지 못했습니다: {SOURCE_DIR}")
        print("확인할 파일명 예: *kipris*.csv, *특허*.csv, *patent*.xlsx")
        return 1

    print("=" * 80)
    print("[KIPRIS 원천 파일 컬럼 확인]")
    print(f"source dir: {SOURCE_DIR}")
    print("=" * 80)

    overall_found = set()
    overall_missing = set(TARGET_COLUMNS.keys())

    for path in files:
        print()
        print(f"## FILE: {path}")
        print(f"- size: {path.stat().st_size:,} bytes")

        try:
            tables = read_table(path)
        except Exception as exc:
            print(f"[READ ERROR] {exc}")
            continue

        for sheet_name, df in tables.items():
            columns = [str(c).strip() for c in df.columns]
            found, missing = check_columns(columns)

            overall_found.update(found.keys())
            overall_missing = overall_missing - set(found.keys())

            print()
            print(f"### SHEET: {sheet_name}")
            print(f"- detected columns count: {len(columns)}")
            print("- detected columns:")
            for col in columns:
                print(f"  - {col}")

            print()
            print("- target column match:")
            for canonical in TARGET_COLUMNS:
                if canonical in found:
                    print(f"  [OK]      {canonical}  <=  {found[canonical]}")
                else:
                    print(f"  [MISSING] {canonical}")

    print()
    print("=" * 80)
    print("[전체 요약]")
    print("FOUND:")
    for col in sorted(overall_found):
        print(f"  [OK] {col}")

    print("MISSING:")
    if overall_missing:
        for col in sorted(overall_missing):
            print(f"  [MISSING] {col}")
    else:
        print("  없음. 필요한 기본 서지/상태 컬럼이 모두 확인됨.")

    print("=" * 80)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
