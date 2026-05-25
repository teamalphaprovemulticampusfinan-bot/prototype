# 엑셀 파일에서 여러 기업 정보를 읽어서 `workspace/companies/*/company.yaml`을 자동 생성하는 스크립트입니다.

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_COMPANIES = ROOT / "workspace" / "companies"


COLUMN_ALIASES = {
    "slug": ["slug", "folder", "folder_name", "code_name", "회사폴더", "폴더명"],
    "corp_name": ["corp_name", "company", "company_name", "회사명", "기업명"],
    "corp_name_en": ["corp_name_en", "company_en", "영문명", "영문회사명"],
    "stock_code": ["stock_code", "ticker", "종목코드", "코드"],
    "homepage_url": ["homepage_url", "homepage", "website", "홈페이지"],
    "ir_url": ["ir_url", "ir", "ir_page", "IR", "IR페이지"],
    "aliases": ["aliases", "alias", "별칭", "aliases_list"],
    "keywords": ["keywords", "keyword", "키워드"],
    "core_keywords": ["core_keywords", "핵심키워드", "핵심 기술 키워드"],
    "products": ["products", "product", "제품", "대표제품"],
    "tech_keywords": ["tech_keywords", "기술키워드", "기술 키워드"],
    "kipris": ["kipris", "patent_url", "특허", "특허링크"],
    "news": ["news", "기사", "뉴스"],
    "brochure": ["brochure", "브로셔", "catalog"],
    "notes": ["notes", "비고", "메모", "설명"],
}


def normalize_header(value: Any) -> str:
    if value is None:
        return ""
    s = str(value).strip().lower()
    s = s.replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", "", s)
    return s


def build_header_map(columns: list[str]) -> dict[str, str]:
    normalized_to_original = {normalize_header(c): c for c in columns}
    field_map: dict[str, str] = {}

    for target_field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = normalize_header(alias)
            if key in normalized_to_original:
                field_map[target_field] = normalized_to_original[key]
                break

    return field_map


def split_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, float) and pd.isna(value):
        return []

    s = str(value).strip()
    if not s:
        return []

    parts = re.split(r"[,\n;/|]+", s)
    cleaned = [p.strip() for p in parts if p and p.strip()]
    # 중복 제거
    return list(dict.fromkeys(cleaned))


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def make_slug(row: dict[str, Any]) -> str:
    for key in ["slug", "corp_name_en", "stock_code", "corp_name"]:
        value = clean_text(row.get(key))
        if not value:
            continue

        if key == "corp_name_en":
            s = value.lower()
            s = re.sub(r"[^a-z0-9]+", "_", s)
            s = s.strip("_")
            if s:
                return s

        if key == "stock_code":
            s = re.sub(r"[^0-9]", "", value)
            if s:
                return s

        if key == "corp_name":
            s = value.lower()
            s = re.sub(r"[^a-z0-9가-힣]+", "_", s)
            s = s.strip("_")
            if s:
                return s

        if key == "slug":
            s = value.lower()
            s = re.sub(r"[^a-z0-9_\\-]+", "_", s)
            s = s.strip("_")
            if s:
                return s

    raise ValueError("slug를 만들 수 없습니다. slug 또는 회사명을 확인하세요.")


def row_to_company_yaml(row: dict[str, Any]) -> dict[str, Any]:
    corp_name = clean_text(row.get("corp_name"))
    corp_name_en = clean_text(row.get("corp_name_en"))
    stock_code = clean_text(row.get("stock_code"))

    aliases = split_list(row.get("aliases"))
    keywords = split_list(row.get("keywords"))
    core_keywords = split_list(row.get("core_keywords"))
    products = split_list(row.get("products"))
    tech_keywords = split_list(row.get("tech_keywords"))

    if corp_name and corp_name not in keywords:
        keywords.insert(0, corp_name)

    data = {
        "corp_name": corp_name,
        "corp_name_en": corp_name_en,
        "stock_code": stock_code,
        "aliases": aliases,
        "homepage_url": clean_text(row.get("homepage_url")),
        "ir_url": clean_text(row.get("ir_url")),
        "keywords": keywords,
        "core_keywords": core_keywords,
        "products": products,
        "tech_keywords": tech_keywords,
        "extra_urls": {
            "kipris": split_list(row.get("kipris")),
            "news": split_list(row.get("news")),
            "brochure": split_list(row.get("brochure")),
        },
        "notes": clean_text(row.get("notes")),
    }

    return data


def save_company_yaml(slug: str, data: dict[str, Any]) -> Path:
    company_dir = WORKSPACE_COMPANIES / slug
    company_dir.mkdir(parents=True, exist_ok=True)

    yaml_path = company_dir / "company.yaml"
    with yaml_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
    return yaml_path


def main() -> None:
    parser = argparse.ArgumentParser(description="엑셀에서 company.yaml 파일 자동 생성")
    parser.add_argument("--xlsx", required=True, help="입력 엑셀 파일 경로")
    parser.add_argument("--sheet", default=0, help="시트명 또는 시트 인덱스")
    parser.add_argument("--only", default="", help="특정 회사명만 생성")
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx)
    if not xlsx_path.exists():
        raise FileNotFoundError(f"엑셀 파일을 찾을 수 없습니다: {xlsx_path}")

    df = pd.read_excel(xlsx_path, sheet_name=args.sheet, engine="openpyxl")
    df = df.fillna("")

    header_map = build_header_map(list(df.columns))
    required = ["corp_name", "stock_code"]
    missing_required = [k for k in required if k not in header_map]
    if missing_required:
        raise ValueError(
            f"필수 열을 찾지 못했습니다: {missing_required}\n"
            f"현재 컬럼: {list(df.columns)}"
        )

    WORKSPACE_COMPANIES.mkdir(parents=True, exist_ok=True)

    created = 0
    for _, raw_row in df.iterrows():
        mapped_row = {}
        for field, original_col in header_map.items():
            mapped_row[field] = raw_row.get(original_col, "")

        corp_name = clean_text(mapped_row.get("corp_name"))
        if not corp_name:
            continue

        if args.only and args.only.strip() not in corp_name:
            continue

        slug = make_slug(mapped_row)
        data = row_to_company_yaml(mapped_row)
        out_path = save_company_yaml(slug, data)
        print(f"[OK] {corp_name} -> {out_path}")
        created += 1

    print(f"\n총 생성 건수: {created}")


if __name__ == "__main__":
    main()