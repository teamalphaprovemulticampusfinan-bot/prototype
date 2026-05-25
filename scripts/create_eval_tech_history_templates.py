from __future__ import annotations

r"""Create src_eval Tech history input templates.

Run from project root:
    python .\scripts\create_eval_tech_history_templates.py --field "반도체"
"""

import argparse
from pathlib import Path
import pandas as pd

BASE_COLUMNS = [
    "date", "as_of_date", "field", "company", "ticker", "stock_code", "company_dir",
    "source_url", "source_file", "evidence_type", "evidence_text", "score", "signal", "confidence",
]

TEMPLATES: dict[str, list[str]] = {
    "tech_patent_quality_monthly.csv": BASE_COLUMNS + ["application_date", "publication_date", "grant_date", "patent_title", "applicant", "right_holder", "patent_count", "registered_patents", "active_patents", "claims", "forward_citations", "backward_citations", "family_size", "renewal_status", "ipc_cpc", "technology_keyword"],
    "tech_lifecycle_monthly.csv": BASE_COLUMNS + ["technology_keyword", "trl", "readiness_stage", "patent_applications_yoy", "paper_report_growth_yoy", "industry_adoption_stage", "customer_adoption_speed", "roadmap_alignment_score"],
    "tech_certification_qualification_monthly.csv": BASE_COLUMNS + ["certification_type", "certification_status", "qualification_stage", "customer_name_masked", "sample_test_status", "pilot_status", "mass_production_approval", "first_delivery", "supply_contract"],
    "tech_commercialization_gate_monthly.csv": BASE_COLUMNS + ["commercialization_stage", "customer_adoption_signal", "production_signal", "tech_revenue_signal", "yield_improvement", "cost_reduction", "fcf_link_signal", "gate_label"],
    "tech_supply_chain_position_monthly.csv": BASE_COLUMNS + ["vc_role", "process_step", "front_customer_industry", "input_dependency", "alternative_supplier_count", "switching_cost", "localization_importance", "single_customer_dependency", "bottleneck_signal"],
    "tech_cost_yield_benchmark_monthly.csv": BASE_COLUMNS + ["product", "benchmark_metric", "company_value", "peer_value", "yield", "defect_rate", "unit_cost", "cost_reduction_rate", "performance_advantage", "throughput", "power_efficiency"],
    "tech_workforce_hiring_monthly.csv": BASE_COLUMNS + ["rnd_headcount", "masters_phd_ratio", "key_researcher_count", "inventor_repeat_count", "hiring_count", "hiring_keyword", "new_business_hiring", "team_expansion_signal"],
    "tech_government_rd_monthly.csv": BASE_COLUMNS + ["project_name", "government_funding", "total_budget", "project_start", "project_end", "target_trl", "patent_output", "paper_output", "commercialization_revenue", "follow_on_project", "technology_transfer"],
    "tech_licensing_transfer_monthly.csv": BASE_COLUMNS + ["contract_type", "counterparty_masked", "royalty_revenue", "license_revenue", "joint_development", "external_validation_signal"],
    "tech_risk_events_monthly.csv": BASE_COLUMNS + ["risk_type", "litigation", "invalidity_trial", "infringement_dispute", "quality_claim", "recall", "approval_delay", "yield_issue", "contract_termination", "impairment_loss", "risk_severity"],
    "tech_intangible_accounting_monthly.csv": BASE_COLUMNS + ["capitalized_development_cost", "expensed_rd", "intangible_assets", "impairment_loss", "amortization", "patent_book_value", "software_book_value", "accounting_quality_signal"],
}

README_TEXT = """# Tech history input templates

이 폴더는 `src_eval` 전용 Tech history 평가 입력값입니다. 기존 `src` 운영 레포트 산출 흐름은 건드리지 않습니다.

월별 평가는 `monthly`, 일별 평가는 `daily` 폴더를 읽습니다. 날짜 컬럼이 있는 행은 반드시 `as_of_date` 이전 행만 사용됩니다.
날짜 컬럼이 없는 공통 정보는 보조 근거로만 사용되며, `signal` 또는 `score` 컬럼이 있으면 연속 신호로 반영됩니다.

주요 근거: Hall-Jaffe-Trajtenberg 특허 인용/기업가치, Lanjouw-Schankerman/OECD 특허품질 복합지표, TRL/TRA 성숙도 프레임워크, IFC/Bpifrance Deep-Tech 상업화 단계.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--root", default=".")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    root = Path(args.root)
    base = root / "data" / args.field / "_sector_common" / "tech"
    base.mkdir(parents=True, exist_ok=True)

    for name, cols in TEMPLATES.items():
        for sub in ["monthly", "daily"]:
            fname = name.replace("_monthly", f"_{sub}")
            path = base / sub / fname
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists() and not args.overwrite:
                print(f"[SKIP] {path}")
                continue
            pd.DataFrame(columns=cols).to_csv(path, index=False, encoding="utf-8-sig")
            print(f"[OK] {path}")

    readme = base / "README_tech_history_inputs.md"
    if args.overwrite or not readme.exists():
        readme.write_text(README_TEXT, encoding="utf-8")
        print(f"[OK] {readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
