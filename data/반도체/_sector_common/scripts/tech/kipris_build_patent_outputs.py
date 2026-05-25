from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import sys
ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_FOR_IMPORT / "src"))
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tech_agent.patent_harvester import harvest_patent_evidence, write_patent_outputs

DEFAULT_COMPANIES = ["nepes", "hanmi", "hansol", "duksan", "ltc"]


def load_company(company_dir: str) -> dict:
    company_yaml = company_config_path(company_dir)

    if not company_yaml.exists():
        return {
            "corp_name": company_dir,
            "slug": company_dir,
            "aliases": [company_dir],
            "keywords": [],
            "core_keywords": [],
            "tech_keywords": [],
            "products": [],
        }

    try:
        import yaml
    except Exception:
        yaml = None

    if yaml is not None:
        with company_yaml.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        data.setdefault("slug", company_dir)
        return data

    # PyYAML이 없는 경우 최소 파싱
    data = {"slug": company_dir, "aliases": [], "keywords": [], "core_keywords": [], "tech_keywords": [], "products": []}
    current_key = None

    for line in company_yaml.read_text(encoding="utf-8", errors="ignore").splitlines():
        raw = line.rstrip()
        stripped = raw.strip()

        if not stripped or stripped.startswith("#"):
            continue

        if ":" in stripped and not stripped.startswith("-"):
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            current_key = key

            if value:
                data[key] = value
            elif key not in data:
                data[key] = []

        elif stripped.startswith("-") and current_key:
            value = stripped[1:].strip().strip('"').strip("'")
            if isinstance(data.get(current_key), list):
                data[current_key].append(value)
            else:
                data[current_key] = [value]

    return data


def resolve_targets(args: argparse.Namespace) -> list[str]:
    if args.all:
        return DEFAULT_COMPANIES
    if args.company:
        return [args.company.strip()]
    if args.companies:
        return [x.strip() for x in args.companies.split(",") if x.strip()]
    raise SystemExit("--company, --companies, --all 중 하나를 지정하세요.")


def build_one(company_dir: str) -> dict:
    company = load_company(company_dir)
    output_dir = field_agent_dir("tech")

    harvest = harvest_patent_evidence(company, company_dir)
    files = write_patent_outputs(company_dir, harvest, output_dir)

    summary = {
        "company_dir": company_dir,
        "company_name": harvest.get("company_name") or company.get("corp_name") or company_dir,
        "files": files,
        "source_files": len(harvest.get("source_files") or []),
        "raw": harvest.get("raw_record_count", 0),
        "normalized": harvest.get("normalized_record_count", 0),
        "company_matched": harvest.get("company_matched_record_count", 0),
        "effective": harvest.get("effective_record_count", 0),
        "representative": len(harvest.get("representative_patents") or []),
        "quality_flags": harvest.get("quality_flags") or [],
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build KIPRIS patent normalized outputs for one or five Tech Agent companies.")
    parser.add_argument("--company", "--company-dir", dest="company", required=False)
    parser.add_argument("--companies", required=False, help="쉼표로 구분한 company_dir 목록. 예: nepes,hanmi,hansol,duksan,ltc")
    parser.add_argument("--all", action="store_true", help="기본 5개 기업(nepes, hanmi, hansol, duksan, ltc)을 모두 처리")
    args = parser.parse_args()

    targets = resolve_targets(args)
    results = []
    exit_code = 0

    for company_dir in targets:
        print(f"\n[KIPRIS 정량화] {company_dir} 처리 시작")
        try:
            summary = build_one(company_dir)
            results.append(summary)
            print(
                "[요약] "
                f"source_files={summary['source_files']}, "
                f"raw={summary['raw']}, "
                f"normalized={summary['normalized']}, "
                f"company_matched={summary['company_matched']}, "
                f"effective={summary['effective']}, "
                f"representative={summary['representative']}"
            )
            if summary["quality_flags"]:
                print("[품질 플래그]")
                for flag in summary["quality_flags"]:
                    print("-", flag)
            if not summary["normalized"]:
                exit_code = 2
        except Exception as exc:
            exit_code = 1
            err = {"company_dir": company_dir, "error": str(exc)}
            results.append(err)
            print(f"[오류] {company_dir}: {exc}")

    result_path = field_agent_dir("tech") / "kipris_build_summary.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n[완료] KIPRIS/특허 정규화 및 정량화 산출물 생성")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"[저장] {result_path}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
