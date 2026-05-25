from __future__ import annotations

import argparse
import json
from pathlib import Path

from tech_agent.config import DEFAULT_TEMPLATE_PATH, OUTPUT_DIR
from tech_agent.template_bridge import build_formula_catalog


def write_markdown(catalog: dict, path: Path) -> None:
    lines = ["# Tech Agent Formula Rules", ""]
    lines.append(f"- template_path: {catalog.get('template_path', '')}")
    lines.append(f"- category_count: {catalog.get('category_count', 0)}")
    lines.append(f"- formula_rule_count: {catalog.get('formula_rule_count', 0)}")
    lines.append("")
    for category, rows in (catalog.get("formula_map") or {}).items():
        lines.append(f"## {category}")
        for row in rows:
            lines.append(f"- {row.get('metric_name', '')}: {row.get('formula', '')}")
            if row.get("description"):
                lines.append(f"  - 의미: {row.get('description')}")
            if row.get("source_hint"):
                lines.append(f"  - 출처 힌트: {row.get('source_hint')}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="tech_template.xlsx의 수식 정리 시트를 JSON/Markdown으로 내보냅니다.")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE_PATH), help="tech_template.xlsx 경로")
    parser.add_argument("--out-dir", default=str(OUTPUT_DIR), help="저장 폴더")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    catalog = build_formula_catalog(args.template)
    json_path = out_dir / "tech_formula_rules_catalog.json"
    md_path = out_dir / "tech_formula_rules_catalog.md"
    json_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(catalog, md_path)
    print(f"[OK] {json_path}")
    print(f"[OK] {md_path}")


if __name__ == "__main__":
    main()
