from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from common.data_paths import field_agent_dir, first_auditor_dir
from typing import Any

from common.output_paths import agent_output_dir, agent_output_path, output_candidates, read_json_first, read_text_first


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = field_agent_dir("tech")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def metric_map(patent_data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}

    for metric in patent_data.get("metrics") or []:
        name = clean_text(metric.get("metric_name"))
        out[name] = metric.get("value")

    return out


def num(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default

    if isinstance(value, (int, float)):
        return float(value)

    text = clean_text(value)
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return default

    try:
        return float(match.group(0))
    except Exception:
        return default


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def count_terms(text: str, terms: list[str]) -> int:
    low = text.lower()
    return sum(low.count(term.lower()) for term in terms)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def score_patent_layer(patent_data: dict[str, Any]) -> tuple[float, list[str], dict[str, Any]]:
    metrics = metric_map(patent_data)

    matched = num(metrics.get("출원인/권리자 회사 매칭 특허 수"), patent_data.get("company_matched_record_count", 0))
    registered = num(metrics.get("등록 특허 수"))
    active = num(metrics.get("존속 가능 특허 수"))
    recent = num(metrics.get("최근 5년 특허 수"))
    ipc_count = num(metrics.get("IPC/CPC 기술분류 수"))
    h01l = num(metrics.get("H01L 반도체 IPC 특허 수"))
    semi_ipc = num(metrics.get("반도체 핵심 IPC 특허 수"))
    keyword_hits = num(metrics.get("특허-기술 키워드 매칭 수"))

    score = 0.0
    score += clamp(matched / 300 * 5, 0, 5)
    score += clamp(registered / 200 * 6, 0, 6)
    score += clamp(active / 150 * 5, 0, 5)
    score += clamp(recent / 50 * 6, 0, 6)
    score += clamp(ipc_count / 20 * 4, 0, 4)
    score += clamp(semi_ipc / 50 * 4, 0, 4)
    score += clamp(keyword_hits / 300 * 5, 0, 5)

    reasons = [
        f"KIPRIS 회사매칭 특허 {int(matched)}건",
        f"등록 특허 {int(registered)}건, 존속 가능 {int(active)}건",
        f"최근 5년 특허 {int(recent)}건",
        f"IPC/CPC 기술분류 {int(ipc_count)}개",
        f"H01L {int(h01l)}건, 반도체 핵심 IPC {int(semi_ipc)}건",
        f"특허-기술 키워드 매칭 {int(keyword_hits)}회",
    ]

    detail = {
        "matched_patents": matched,
        "registered_patents": registered,
        "active_patents": active,
        "recent_5y_patents": recent,
        "ipc_cpc_diversity": ipc_count,
        "h01l_patents": h01l,
        "semiconductor_ipc_patents": semi_ipc,
        "patent_keyword_hits": keyword_hits,
        "max_score": 35,
    }

    return round(score, 2), reasons, detail


def score_commercialization_layer(tech_report_text: str) -> tuple[float, list[str], dict[str, Any]]:
    groups = {
        "customer_adoption": ["고객", "고객사", "채택", "레퍼런스", "공급", "수주", "승인"],
        "mass_production": ["양산", "생산", "공정", "라인", "수율", "품질", "검증"],
        "revenue_conversion": ["매출", "매출 비중", "성장률", "수익성", "영업이익", "FCF", "현금흐름"],
        "application_market": ["스마트폰", "서버", "고성능컴퓨터", "웨어러블", "자동차", "AI", "전장", "Application"],
        "performance_value": ["고성능", "소형화", "방열", "고집적", "재배선", "차폐", "성능", "효율"],
    }

    max_by_group = {
        "customer_adoption": 7,
        "mass_production": 7,
        "revenue_conversion": 6,
        "application_market": 5,
        "performance_value": 5,
    }

    score = 0.0
    detail: dict[str, Any] = {}
    reasons: list[str] = []

    for group, terms in groups.items():
        hits = count_terms(tech_report_text, terms)
        group_score = clamp(hits / 10 * max_by_group[group], 0, max_by_group[group])
        score += group_score
        detail[group] = {"hits": hits, "score": round(group_score, 2), "max_score": max_by_group[group]}

        if hits > 0:
            reasons.append(f"{group}: 관련 문맥 {hits}회")

    if not reasons:
        reasons.append("고객 채택·양산·매출 전환 문맥이 약함")

    return round(score, 2), reasons, detail


def score_finance_bridge_layer(company: str, overlay: dict[str, Any], tech_report_text: str) -> tuple[float, list[str], dict[str, Any]]:
    """
    기술이 가치평가로 연결되려면 재무/가치/신용 overlay와 충돌하지 않아야 한다.
    다만 이 모듈은 최종 투자판단을 바꾸지 않고, Tech-to-Value 연결 가능성만 점수화한다.
    """
    text = json.dumps(overlay, ensure_ascii=False) + "\n" + tech_report_text

    valuation_positive = any(k in text for k in ["ATTRACTIVE", "valuation_attractive", "상대가치 매력"])
    credit_medium = any(k in text for k in ["MEDIUM_RISK", "medium_risk"])
    credit_high = any(k in text for k in ["HIGH_RISK", "high_risk", "watch_grade=D"])
    finance_risk = any(k in text for k in ["부채비율", "유동비율", "영업이익률 -", "현금흐름", "재무안정성 리스크", "적자"])

    score = 10.0
    reasons: list[str] = []

    if valuation_positive:
        score += 5
        reasons.append("ML 가치평가 overlay가 ATTRACTIVE 또는 상대가치 매력 신호를 제시")

    if credit_medium:
        score -= 2
        reasons.append("신용위험 overlay가 MEDIUM_RISK로 분류되어 가치가산에 보수적 접근 필요")

    if credit_high:
        score -= 5
        reasons.append("신용위험 또는 watch grade가 높아 기술 프리미엄 반영에 강한 할인 필요")

    if finance_risk:
        score -= 3
        reasons.append("수익성·현금흐름·재무안정성 리스크 문맥이 확인됨")

    if count_terms(tech_report_text, ["매출", "수익성", "현금흐름", "FCF", "성장률"]) >= 5:
        score += 4
        reasons.append("기술 근거가 매출·수익성·현금흐름 문맥과 일부 연결됨")
    else:
        reasons.append("기술 우위가 매출·FCF 개선으로 직접 연결되는 근거는 아직 제한적")

    score = clamp(score, 0, 20)

    detail = {
        "valuation_positive": valuation_positive,
        "credit_medium": credit_medium,
        "credit_high": credit_high,
        "finance_risk": finance_risk,
        "max_score": 20,
    }

    return round(score, 2), reasons, detail


def score_evidence_quality_layer(patent_data: dict[str, Any], tech_report_text: str) -> tuple[float, list[str], dict[str, Any]]:
    source_files = patent_data.get("source_files") or []
    representative = patent_data.get("representative_patents") or []

    has_dart = "dart_latest_business_report.txt" in tech_report_text or "사업보고서" in tech_report_text
    has_official = "nepes.co.kr" in tech_report_text or "공식" in tech_report_text
    has_kipris = bool(source_files) and bool(representative)
    has_quant = "정량" in tech_report_text or "KIPRIS/특허 정량화" in tech_report_text

    score = 0.0
    reasons: list[str] = []

    if has_dart:
        score += 5
        reasons.append("DART/사업보고서 기반 근거 확인")
    if has_official:
        score += 4
        reasons.append("공식 홈페이지/IR 기반 근거 확인")
    if has_kipris:
        score += 7
        reasons.append("KIPRIS 특허 원천 및 대표 특허 확인")
    if has_quant:
        score += 4
        reasons.append("정량화 지표가 보고서에 반영됨")

    if not reasons:
        reasons.append("공식·DART·KIPRIS 근거 연결이 약함")

    detail = {
        "has_dart": has_dart,
        "has_official": has_official,
        "has_kipris": has_kipris,
        "has_quant": has_quant,
        "max_score": 20,
    }

    return round(score, 2), reasons, detail


def grade_bridge(score: float, finance_detail: dict[str, Any]) -> str:
    if finance_detail.get("credit_high") and score < 75:
        return "TECH_FINANCE_GAP"

    if score >= 80:
        return "VALUE_BRIDGE_READY"
    if score >= 65:
        return "COMMERCIALIZATION_WATCH"
    if score >= 45:
        return "TECH_FINANCE_GAP"
    return "EVIDENCE_GAP"


def build_tech_to_value_bridge(company: str) -> dict[str, Any]:
    audit_overlay_path = first_auditor_dir(company) / "valuation_credit_overlay.json"

    patent_data = read_json_first(output_candidates(company, "tech", f"{company}_tech_patent_evidence.json", root=ROOT)) or {}
    tech_report_text = read_text_first(output_candidates(company, "tech", f"{company}_tech_high_quality_report.md", root=ROOT))
    overlay = load_json(audit_overlay_path)

    patent_score, patent_reasons, patent_detail = score_patent_layer(patent_data)
    commercialization_score, commercialization_reasons, commercialization_detail = score_commercialization_layer(tech_report_text)
    finance_score, finance_reasons, finance_detail = score_finance_bridge_layer(company, overlay, tech_report_text)
    evidence_score, evidence_reasons, evidence_detail = score_evidence_quality_layer(patent_data, tech_report_text)

    total_score = round(patent_score + commercialization_score + finance_score + evidence_score, 2)
    grade = grade_bridge(total_score, finance_detail)

    interpretation = (
        "기술 우위가 특허·사업보고서·공식 근거로 확인되며, 고객 채택·양산·매출 전환 근거가 함께 확인될수록 가치평가 가산 요인으로 활용 가능하다."
    )

    if grade == "TECH_FINANCE_GAP":
        interpretation = (
            "특허와 기술 근거는 강하지만, 수익성·현금흐름·재무안정성 리스크가 남아 있어 기술 프리미엄을 가치평가에 전면 반영하기보다 보수적으로 할인해야 한다."
        )
    elif grade == "COMMERCIALIZATION_WATCH":
        interpretation = (
            "특허·기술 포트폴리오는 의미 있으나, 고객 채택·양산·매출 전환 근거를 추가 확인해야 가치평가 가산 요인으로 안정적으로 반영할 수 있다."
        )
    elif grade == "VALUE_BRIDGE_READY":
        interpretation = (
            "특허·기술·상업화·정량 근거가 비교적 잘 연결되어 기술 우위를 가치평가 보조 신호로 활용할 수 있다."
        )
    elif grade == "EVIDENCE_GAP":
        interpretation = (
            "기술 또는 특허 근거가 가치평가로 연결되기에는 근거 품질과 정량 연결성이 부족하다."
        )

    result = {
        "version": "v14_t2v_with_kipris_patent_metrics",
        "company": company,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "tech_to_value_bridge_score": total_score,
        "max_score": 100,
        "grade": grade,
        "layer_scores": {
            "patent_layer": {
                "score": patent_score,
                "max_score": 35,
                "reasons": patent_reasons,
                "detail": patent_detail,
            },
            "commercialization_layer": {
                "score": commercialization_score,
                "max_score": 25,
                "reasons": commercialization_reasons,
                "detail": commercialization_detail,
            },
            "finance_bridge_layer": {
                "score": finance_score,
                "max_score": 20,
                "reasons": finance_reasons,
                "detail": finance_detail,
            },
            "evidence_quality_layer": {
                "score": evidence_score,
                "max_score": 20,
                "reasons": evidence_reasons,
                "detail": evidence_detail,
            },
        },
        "interpretation": interpretation,
        "auditor_principle": (
            "기술 우위는 고객사 채택, 양산, 매출 전환, FCF 개선 근거와 연결될 때만 가치평가 가산 요인으로 반영한다."
        ),
        "chair_insert_summary": [
            f"Tech-to-Value Bridge Score: {total_score} / 100",
            f"판정: {grade}",
            interpretation,
            "KIPRIS 특허 지표는 기술 지속성·진입장벽의 정량 보조지표이며, 최종 투자판단은 재무·시장·이슈·거시 신호와 함께 보수적으로 해석한다.",
        ],
    }

    return result


def write_tech_to_value_bridge(company: str, result: dict[str, Any]) -> dict[str, str]:
    audit_out_dir = ensure_dir(first_auditor_dir(company))
    output_out_dir = agent_output_dir(company, "tech", root=ROOT)
    auditor_out_dir = agent_output_dir(company, "auditor", root=ROOT)

    audit_json = audit_out_dir / "tech_to_value_bridge.json"
    output_json = output_out_dir / f"{company}_tech_to_value_bridge.json"
    auditor_json = auditor_out_dir / f"{company}_tech_to_value_bridge.json"
    audit_md = audit_out_dir / "tech_to_value_bridge.md"
    output_md = output_out_dir / f"{company}_tech_to_value_bridge.md"
    auditor_md = auditor_out_dir / f"{company}_tech_to_value_bridge.md"

    write_json(audit_json, result)
    write_json(output_json, result)
    write_json(auditor_json, result)

    md = render_markdown(result)

    audit_md.write_text(md, encoding="utf-8")
    output_md.write_text(md, encoding="utf-8")
    auditor_md.write_text(md, encoding="utf-8")

    return {
        "audit_json": str(audit_json),
        "output_json": str(output_json),
        "auditor_json": str(auditor_json),
        "audit_md": str(audit_md),
        "output_md": str(output_md),
        "auditor_md": str(auditor_md),
    }


def render_markdown(result: dict[str, Any]) -> str:
    lines = [
        f"# {result.get('company')} Tech-to-Value Bridge Score",
        "",
        f"- Tech-to-Value Bridge Score: {result.get('tech_to_value_bridge_score')} / 100",
        f"- 판정: {result.get('grade')}",
        f"- 해석: {result.get('interpretation')}",
        f"- 원칙: {result.get('auditor_principle')}",
        "",
        "## 1. 계층별 점수",
    ]

    layer_titles = {
        "patent_layer": "KIPRIS 특허·IPC 정량 계층",
        "commercialization_layer": "고객 채택·양산·매출 전환 계층",
        "finance_bridge_layer": "재무·가치·신용 연결 계층",
        "evidence_quality_layer": "근거 품질 계층",
    }

    for key, layer in (result.get("layer_scores") or {}).items():
        lines += [
            "",
            f"### {layer_titles.get(key, key)}",
            f"- 점수: {layer.get('score')} / {layer.get('max_score')}",
            "- 근거:",
        ]

        for reason in layer.get("reasons") or []:
            lines.append(f"  - {reason}")

    lines += [
        "",
        "## 2. Chair/Auditor 전달용 핵심 문장",
    ]

    for item in result.get("chair_insert_summary") or []:
        lines.append(f"- {item}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Tech-to-Value Bridge Score using Tech report and KIPRIS patent metrics.")
    parser.add_argument("--company", required=True)
    args = parser.parse_args()

    company = args.company.strip()

    result = build_tech_to_value_bridge(company)
    files = write_tech_to_value_bridge(company, result)

    print("[완료] Tech-to-Value Bridge Score 생성")
    print(json.dumps(files, ensure_ascii=False, indent=2))
    print(f"[점수] {result['tech_to_value_bridge_score']} / 100")
    print(f"[판정] {result['grade']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())