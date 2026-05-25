from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tech_agent.config import DEFAULT_TEMPLATE_BASE_PATH, DEFAULT_TEMPLATE_PATH, OUTPUT_DIR
from tech_agent.evidence_harvester import harvest_all_tech_evidence, write_evidence_harvest
from tech_agent.formula_rules import write_formula_catalog
from tech_agent.runner import load_company, resolve_company_dir
from tech_agent.source_planner import write_template_framework_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Tech Agent v11 excel-frame actual-source concise quantification extraction utility")
    parser.add_argument("--company", "--company-dir", dest="company", required=True)
    args = parser.parse_args()

    company_dir = resolve_company_dir(args.company)
    company = load_company(company_dir)

    framework_files = write_template_framework_catalog(company_dir, DEFAULT_TEMPLATE_PATH, DEFAULT_TEMPLATE_BASE_PATH, OUTPUT_DIR)
    formula_files = write_formula_catalog(company_dir, DEFAULT_TEMPLATE_PATH, OUTPUT_DIR)
    harvest = harvest_all_tech_evidence(company, company_dir, template_path=DEFAULT_TEMPLATE_PATH)
    harvest_files = write_evidence_harvest(company_dir, harvest, OUTPUT_DIR)

    print("[완료] 엑셀 베이스/수식 시트 기반 추출 설계 코드화")
    print(json.dumps(framework_files, ensure_ascii=False, indent=2))
    print("[완료] 수식 정리 코드화")
    print(json.dumps(formula_files, ensure_ascii=False, indent=2))
    print("[완료] 실제 원천 기반 모든 근거 추출")
    print(json.dumps(harvest_files, ensure_ascii=False, indent=2))
    print(
        f"문서 {harvest.get('document_count')}건, 통과 URL {harvest.get('accepted_url_count')}건, "
        f"제외 URL {harvest.get('rejected_url_count')}건, 정량 신호 {len(harvest.get('quantitative_signals') or [])}건"
    )
    if harvest.get("quality_flags"):
        print("[품질 플래그]")
        for flag in harvest.get("quality_flags") or []:
            print("-", flag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
