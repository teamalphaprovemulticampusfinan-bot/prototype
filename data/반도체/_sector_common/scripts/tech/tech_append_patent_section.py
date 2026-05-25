from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys
ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_FOR_IMPORT / "src"))
from common.data_paths import company_agent_dir, company_common_dir, company_config_path, field_agent_dir, field_common_dir, ml_universe_dir, tech_source_dir
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = field_agent_dir("tech")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def metric_map(data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for metric in data.get("metrics") or []:
        name = clean_text(metric.get("metric_name"))
        out[name] = metric.get("value")

    return out


def metric_value(data: dict[str, Any], name: str, default: Any = 0) -> Any:
    return metric_map(data).get(name, default)


def metric_line(metric: dict[str, Any]) -> str:
    name = clean_text(metric.get("metric_name"))
    value = clean_text(metric.get("value"))
    unit = clean_text(metric.get("unit"))
    detail = metric.get("detail")

    suffix = ""
    if isinstance(detail, dict) and detail:
        suffix = " — " + ", ".join(f"{k} {v}회" for k, v in list(detail.items())[:8])
    elif isinstance(detail, list) and detail:
        suffix = " — " + ", ".join(clean_text(x) for x in detail[:12])

    return f"- {name}: {value}{unit}{suffix}"


def patent_text(record: dict[str, Any]) -> str:
    title = clean_text(record.get("title")) or "특허명 미확인"
    applicant = clean_text(record.get("applicant")) or "출원인 미확인"
    status = clean_text(record.get("status")) or "상태 미확인"
    app_no = clean_text(record.get("application_no"))
    reg_no = clean_text(record.get("registration_no"))
    year = clean_text(record.get("application_year") or record.get("registration_year") or "연도 미확인")

    ipc = record.get("ipc_codes") or []
    if isinstance(ipc, list):
        ipc_text = ", ".join(clean_text(x) for x in ipc[:6])
    else:
        ipc_text = clean_text(ipc)

    keywords = record.get("tech_keyword_hits") or []
    if isinstance(keywords, list):
        keyword_text = ", ".join(clean_text(x) for x in keywords[:8])
    else:
        keyword_text = clean_text(keywords)

    nums = []
    if app_no:
        nums.append(f"출원번호 {app_no}")
    if reg_no:
        nums.append(f"등록번호 {reg_no}")

    return f"{title} | {applicant} | {status} | {year} | {'; '.join(nums)} | IPC/CPC: {ipc_text or '미확인'} | 기술매칭: {keyword_text or '미확인'}"


def patent_replacement_phrase(data: dict[str, Any]) -> str:
    matched = metric_value(data, "출원인/권리자 회사 매칭 특허 수", data.get("company_matched_record_count", 0))
    registered = metric_value(data, "등록 특허 수", 0)
    active = metric_value(data, "존속 가능 특허 수", 0)
    recent = metric_value(data, "최근 5년 특허 수", 0)
    ipc_count = metric_value(data, "IPC/CPC 기술분류 수", 0)
    semi_ipc = metric_value(data, "반도체 핵심 IPC 특허 수", 0)

    return (
        f"KIPRIS 회사매칭 특허 {matched}건, "
        f"등록 {registered}건, 존속가능 {active}건, "
        f"최근 5년 {recent}건, IPC/CPC {ipc_count}개, "
        f"반도체 핵심 IPC {semi_ipc}건"
    )


def patch_existing_report_body(report: str, data: dict[str, Any]) -> str:
    """
    기존 본문 표에 남아 있는
    '특허/산업재산권 근거 문서 수 0건'
    표현을 실제 KIPRIS 정량 지표로 교체한다.
    """
    phrase = patent_replacement_phrase(data)

    patterns = [
        r"특허/산업재산권 근거 문서 수\s*\d+\s*건",
        r"특허/산업재산권 근거 문서 수\s*\d+\s*개",
        r"특허/산업재산권 근거\s*\d+\s*건",
        r"특허 근거 문서 수\s*\d+\s*건",
    ]

    patched = report
    for pattern in patterns:
        patched = re.sub(pattern, phrase, patched)

    # 경쟁우위 섹션 결과문 보강
    anchor = "### 3-4. 경쟁 우위/대체가능성"
    if anchor in patched and "KIPRIS 특허 정량 반영:" not in patched:
        patched = patched.replace(
            anchor,
            anchor + f"\n- KIPRIS 특허 정량 반영: {phrase}",
            1,
        )

    return patched


def build_section(company: str, data: dict[str, Any]) -> str:
    company_name = data.get("company_name") or company

    lines = [
        "",
        "---",
        "",
        "## KIPRIS/특허 정량화 요약",
        "",
        f"- 분석 기업: {company_name}",
        f"- 특허 원천 파일 수: {len(data.get('source_files') or [])}개",
        f"- 정규화 특허 레코드 수: {data.get('normalized_record_count', 0)}건",
        f"- 출원인/권리자 회사 매칭 특허 수: {data.get('company_matched_record_count', 0)}건",
        "",
        "### 특허 정량 지표",
    ]

    for metric in data.get("metrics") or []:
        lines.append(metric_line(metric))

    lines += ["", "### 대표 특허"]

    representatives = data.get("representative_patents") or []
    if representatives:
        for idx, record in enumerate(representatives[:10], 1):
            lines.append(f"{idx}. {patent_text(record)}")
    else:
        lines.append("- 대표 특허 없음")

    lines += [
        "",
        "### Tech-to-Value 해석",
        "- 특허 수 자체는 기술 우위의 보조지표이며, 가치평가 가산 요인으로 쓰려면 고객사 채택, 양산, 매출 전환, FCF 개선 근거와 함께 확인해야 합니다.",
        "- IPC/CPC 다양성, 최근 5년 특허, 등록/존속 특허 수는 기술 지속성과 진입장벽을 판단하는 정량 보조지표로 사용합니다.",
        "- 기존 Tech 본문 내 특허/산업재산권 0건 표기는 KIPRIS 정량 지표로 보정되었습니다.",
    ]

    flags = data.get("quality_flags") or []
    if flags:
        lines += ["", "### 특허 데이터 품질 플래그"]
        for flag in flags:
            lines.append(f"- {flag}")

    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Append and inject KIPRIS patent section into Tech high-quality report.")
    parser.add_argument("--company", required=True)
    args = parser.parse_args()

    company = args.company.strip()

    report_path = OUTPUT_DIR / f"{company}_tech_high_quality_report.md"
    patent_json_path = OUTPUT_DIR / f"{company}_tech_patent_evidence.json"

    if not patent_json_path.exists():
        print(f"[실패] 특허 JSON 없음: {patent_json_path}")
        print(f"먼저 실행: python .\\scripts\\kipris_build_patent_outputs.py --company {company}")
        return 2

    if not report_path.exists():
        print(f"[실패] Tech 보고서 없음: {report_path}")
        print(f"먼저 실행: python main.py tech --company workspace\\companies\\{company}\\company.yaml")
        return 2

    data = json.loads(patent_json_path.read_text(encoding="utf-8"))
    report = report_path.read_text(encoding="utf-8", errors="ignore")

    marker = "## KIPRIS/특허 정량화 요약"
    if marker in report:
        report = report.split(marker)[0].rstrip()

    report = patch_existing_report_body(report, data)
    section = build_section(company, data)

    report_path.write_text(report.rstrip() + "\n\n" + section, encoding="utf-8")

    print(f"[완료] Tech 보고서 본문 0건 표기 보정 + KIPRIS/특허 섹션 반영: {report_path}")
    print(f"[반영 문구] {patent_replacement_phrase(data)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())