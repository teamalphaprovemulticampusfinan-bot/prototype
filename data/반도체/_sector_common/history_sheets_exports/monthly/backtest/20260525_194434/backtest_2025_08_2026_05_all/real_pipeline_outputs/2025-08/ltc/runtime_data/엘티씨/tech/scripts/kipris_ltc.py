from __future__ import annotations

import csv
import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
import sys
ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_FOR_IMPORT / "src"))
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
from typing import Any

import requests


BASE_URL = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch"

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = tech_source_dir("ltc")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SERVICE_KEY = os.getenv("KIPRIS_PLUS_API_KEY", "").strip()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_text(item: ET.Element, tag: str) -> str:
    node = item.find(tag)
    if node is None or node.text is None:
        return ""
    return clean_text(node.text)


def parse_items(xml_bytes: bytes) -> tuple[list[dict[str, str]], int]:
    root = ET.fromstring(xml_bytes)

    result_code = root.findtext(".//resultCode")
    result_msg = root.findtext(".//resultMsg")
    if result_code and result_code != "00":
        print(f"[KIPRIS 응답] resultCode={result_code}, resultMsg={result_msg}")

    total_count_text = root.findtext(".//totalCount") or "0"
    try:
        total_count = int(total_count_text)
    except ValueError:
        total_count = 0

    rows: list[dict[str, str]] = []

    for item in root.findall(".//item"):
        rows.append(
            {
                "index_no": get_text(item, "indexNo"),
                "register_status": get_text(item, "registerStatus"),
                "invention_title": get_text(item, "inventionTitle"),
                "ipc_number": get_text(item, "ipcNumber"),
                "register_number": get_text(item, "registerNumber"),
                "register_date": get_text(item, "registerDate"),
                "application_number": get_text(item, "applicationNumber"),
                "application_date": get_text(item, "applicationDate"),
                "open_number": get_text(item, "openNumber"),
                "open_date": get_text(item, "openDate"),
                "publication_number": get_text(item, "publicationNumber"),
                "publication_date": get_text(item, "publicationDate"),
                "abstract": get_text(item, "astrtCont"),
                "drawing": get_text(item, "drawing"),
                "big_drawing": get_text(item, "bigDrawing"),
                "applicant_name": get_text(item, "applicantName"),
            }
        )

    return rows, total_count


def search_applicant(applicant: str, page_no: int = 1, num_rows: int = 100) -> tuple[list[dict[str, str]], int]:
    if not SERVICE_KEY:
        raise RuntimeError(
            "KIPRIS_PLUS_API_KEY 환경변수가 없습니다. "
            "PowerShell에서 $env:KIPRIS_PLUS_API_KEY='발급키' 설정 후 다시 실행하세요."
        )

    params = {
        "applicant": applicant,
        "patent": "true",
        "utility": "false",
        "numOfRows": str(num_rows),
        "pageNo": str(page_no),
        "descSort": "true",
        "ServiceKey": SERVICE_KEY,
    }

    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    return parse_items(response.content)


def save_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    fieldnames = [
        "query_applicant",
        "index_no",
        "register_status",
        "invention_title",
        "ipc_number",
        "register_number",
        "register_date",
        "application_number",
        "application_date",
        "open_number",
        "open_date",
        "publication_number",
        "publication_date",
        "abstract",
        "drawing",
        "big_drawing",
        "applicant_name",
    ]

    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> int:
    applicant_queries = [
        "엘티씨",
        "주식회사 엘티씨",
        "(주)엘티씨",
        "LTC",
        "LTC Co., Ltd.",
    ]

    all_rows: list[dict[str, str]] = []

    for applicant in applicant_queries:
        print(f"[검색] applicant={applicant}")

        page_no = 1
        num_rows = 100
        rows, total_count = search_applicant(applicant, page_no=page_no, num_rows=num_rows)

        print(f"  - page 1: {len(rows)}건 / totalCount={total_count}")

        for row in rows:
            row["query_applicant"] = applicant
        all_rows.extend(rows)

        # 100건 초과 기업 대비 페이지 추가 수집
        max_pages = min((total_count // num_rows) + 1, 5)
        for page_no in range(2, max_pages + 1):
            time.sleep(0.2)
            rows, _ = search_applicant(applicant, page_no=page_no, num_rows=num_rows)
            print(f"  - page {page_no}: {len(rows)}건")

            for row in rows:
                row["query_applicant"] = applicant
            all_rows.extend(rows)

    # 중복 제거
    deduped: list[dict[str, str]] = []
    seen = set()

    for row in all_rows:
        key = (
            row.get("application_number", ""),
            row.get("register_number", ""),
            row.get("invention_title", ""),
            row.get("applicant_name", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    output_path = OUT_DIR / "kipris_ltc_patents.csv"
    save_csv(deduped, output_path)

    print(f"[완료] 저장: {output_path}")
    print(f"[완료] 중복 제거 후 {len(deduped)}건")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())