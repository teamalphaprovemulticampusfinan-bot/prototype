from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import yaml
except Exception:
    yaml = None

from common.data_paths import field_common_dir, field_dir, company_slug

COLUMNS = [
    "slug",
    "company",
    "stock_code",
    "export_ratio_pct",
    "raw_material_ratio_pct",
    "china_revenue_ratio_pct",
    "foreign_currency_debt_ratio_pct",
    "interest_bearing_debt_ratio_pct",
    "source",
    "note",
]


def read_yaml(path: Path) -> dict:
    if yaml is None:
        return {}
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return yaml.safe_load(path.read_text(encoding=enc)) or {}
        except Exception:
            continue
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="macro 기업별 민감도 외부 보강 CSV 템플릿 생성")
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    out_dir = field_common_dir("macro_company_sensitivity", field=args.field, create=True)
    out_path = out_dir / "company_sensitivity_external.csv"
    if out_path.exists() and not args.force:
        print(f"[SKIP] already exists: {out_path}")
        print("       overwrite하려면 --force 사용")
        return 0

    rows = []
    base = field_dir(args.field, create=False)
    for yaml_path in sorted(base.glob("*/_company_common/company.yaml")):
        meta = read_yaml(yaml_path)
        company = str(meta.get("corp_name") or yaml_path.parent.parent.name)
        slug = str(meta.get("slug") or company_slug(company))
        rows.append({
            "slug": slug,
            "company": company,
            "stock_code": str(meta.get("stock_code") or ""),
            "export_ratio_pct": "",
            "raw_material_ratio_pct": "",
            "china_revenue_ratio_pct": "",
            "foreign_currency_debt_ratio_pct": "",
            "interest_bearing_debt_ratio_pct": "",
            "source": "DART 사업보고서/IR 원문 확인 후 입력",
            "note": "값을 모르면 비워두세요. 임의값은 넣지 않습니다.",
        })

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] template saved: {out_path}")
    print(f"[rows] {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
