from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from common.data_paths import chair_quality_dir

from common.output_paths import agent_output_path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


RECOMMENDATIONS = ("매수", "보유", "매도")
AGENT_SECTIONS = {
    "finance": "재무 분석",
    "market": "시장 분석",
    "tech": "기술 분석",
    "issue": "이슈 분석",
    "macro": "거시경제",
}
DEFAULT_REQUIRED_SECTIONS = [
    "## 1. 최종 추천",
    "## 2. 최종 추천 산정 근거",
    "## 3. 핵심 근거",
    "## 4. 하위 에이전트 의견 요약",
    "## 5. 충돌 지점 및 해석",
    "## 6. 주의점 및 리스크",
    "## 7. 종합 의견",
]


@dataclass
class QualityIssue:
    severity: str
    category: str
    message: str
    evidence: str = ""
    recommendation: str = ""


@dataclass
class QualityMetric:
    name: str
    score: float
    max_score: float
    status: str
    details: List[str] = field(default_factory=list)


@dataclass
class QualityResult:
    company_dir: str
    company_name: str
    report_path: str
    evaluated_at: str
    total_score: float
    status: str
    metrics: List[QualityMetric]
    issues: List[QualityIssue]
    parsed: Dict[str, Any]


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Chair report not found: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def _section(text: str, heading: str) -> str:
    pattern = re.escape(heading)
    m = re.search(pattern, text)
    if not m:
        return ""
    start = m.start()
    level = len(heading) - len(heading.lstrip("#"))
    next_pat = r"\n#{1,%d}\s+" % level
    n = re.search(next_pat, text[m.end():])
    if n:
        return text[start : m.end() + n.start()]
    return text[start:]


def _first_match(patterns: Sequence[str], text: str, flags: int = re.IGNORECASE | re.MULTILINE) -> Optional[str]:
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            return m.group(1).strip()
    return None


def parse_final_recommendation(text: str) -> Optional[str]:
    sec = _section(text, "## 1. 최종 추천") or text[:1500]
    rec = _first_match(
        [
            r"\*\*(매수|보유|매도)\*\*",
            r"최종\s*추천[^\n]*(매수|보유|매도)",
            r"\b(매수|보유|매도)\b",
        ],
        sec,
    )
    return rec if rec in RECOMMENDATIONS else None


def parse_weighted_sum(text: str) -> Optional[float]:
    patterns = [
        r"가중\s*판단[^\n=]*=[^\-\+0-9]*([\-+]?\d+(?:\.\d+)?)",
        r"가중\s*합계[^\n=]*=[^\-\+0-9]*([\-+]?\d+(?:\.\d+)?)",
        r"가중합[^\-\+0-9]{0,30}([\-+]?\d+(?:\.\d+)?)",
        r"기본\s*가중치[^\-\+0-9]{0,30}([\-+]?\d+(?:\.\d+)?)",
    ]
    raw = _first_match(patterns, text, flags=re.IGNORECASE | re.MULTILINE)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def expected_recommendation_from_weighted_sum(weighted_sum: Optional[float]) -> Optional[str]:
    """Diagnostic direction from weighted signal without a fixed no-trade band.

    The final report should use the Auditor/Chair probability recommendation.
    This helper is retained only for quality diagnostics; it no longer recreates
    Buy/Hold/Sell from arbitrary ±0.25 thresholds.
    """
    if weighted_sum is None or not math.isfinite(weighted_sum):
        return None
    if weighted_sum > 0:
        return "매수"
    if weighted_sum < 0:
        return "매도"
    return "보유"


def parse_agent_opinions(text: str) -> Dict[str, Optional[str]]:
    result: Dict[str, Optional[str]] = {}
    for agent, label in AGENT_SECTIONS.items():
        sec = _section(text, f"### {label}")
        opinion = _first_match(
            [
                r"-\s*\*\*의견:\*\*\s*(매수|보유|매도)",
                r"의견[^\n]*(매수|보유|매도)",
            ],
            sec,
        )
        result[agent] = opinion if opinion in RECOMMENDATIONS else None
    return result


def parse_tech_scores(text: str) -> List[float]:
    scores: List[float] = []
    patterns = [
        r"Tech-to-Value[^0-9]{0,80}(\d+(?:\.\d+)?)\s*/\s*100",
        r"Bridge\s*Score[^0-9]{0,80}(\d+(?:\.\d+)?)\s*/\s*100",
        r"Peer-adjusted\s*Bridge\s*Score[^0-9]{0,80}(\d+(?:\.\d+)?)\s*/\s*100",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            try:
                val = float(m.group(1))
                if 0 <= val <= 100:
                    scores.append(round(val, 2))
            except ValueError:
                pass
    uniq: List[float] = []
    for value in scores:
        if value not in uniq:
            uniq.append(value)
    return uniq


def _contains_all(text: str, terms: Iterable[str]) -> Tuple[int, List[str]]:
    found = 0
    missing: List[str] = []
    lowered = text.lower()
    for term in terms:
        if term.lower() in lowered:
            found += 1
        else:
            missing.append(term)
    return found, missing


def _has_malformed_url(text: str) -> List[str]:
    bad: List[str] = []
    for m in re.finditer(r"https?://[^\s\)\]]+", text):
        url = m.group(0)
        if '"' in url or url.endswith(("'", '",')):
            bad.append(url[:160])
    for m in re.finditer(r"\[[^\]]*\"[^\]]*\]\([^\)]*\"[^\)]*\)", text):
        bad.append(m.group(0)[:160])
    return bad


def _count_occurrences(text: str, patterns: Sequence[str]) -> int:
    return sum(len(re.findall(p, text, re.IGNORECASE)) for p in patterns)


def _metric(name: str, score: float, max_score: float, details: List[str]) -> QualityMetric:
    score = max(0.0, min(score, max_score))
    ratio = score / max_score if max_score else 0.0
    if ratio >= 0.85:
        status = "PASS"
    elif ratio >= 0.65:
        status = "REVIEW"
    else:
        status = "FAIL"
    return QualityMetric(name=name, score=round(score, 2), max_score=max_score, status=status, details=details)


def evaluate_chair_report(
    report_path: Path,
    company_dir: str = "",
    company_name: str = "",
    output_root: Path = Path("data"),
    save: bool = True,
) -> QualityResult:
    text = _read_text(report_path)
    company_dir = company_dir or report_path.stem.replace("_chair_report", "")
    company_name = company_name or company_dir

    issues: List[QualityIssue] = []
    metrics: List[QualityMetric] = []

    present_sections = [s for s in DEFAULT_REQUIRED_SECTIONS if s in text]
    missing_sections = [s for s in DEFAULT_REQUIRED_SECTIONS if s not in text]
    structure_score = 15 * len(present_sections) / len(DEFAULT_REQUIRED_SECTIONS)
    structure_details = [f"필수 섹션 {len(present_sections)}/{len(DEFAULT_REQUIRED_SECTIONS)}개 확인"]
    if missing_sections:
        structure_details.append("누락: " + ", ".join(missing_sections))
        issues.append(QualityIssue(
            severity="high",
            category="structure",
            message="Chair 최종 보고서의 필수 섹션이 누락되었습니다.",
            evidence=", ".join(missing_sections),
            recommendation="최종 추천, 산정 근거, 핵심 근거, 하위 에이전트 요약, 리스크, 종합 의견을 모두 포함하세요.",
        ))
    metrics.append(_metric("보고서 기본 구조", structure_score, 15, structure_details))

    opinions = parse_agent_opinions(text)
    covered_agents = [a for a, op in opinions.items() if op in RECOMMENDATIONS]
    missing_agents = [AGENT_SECTIONS[a] for a, op in opinions.items() if op not in RECOMMENDATIONS]
    coverage_score = 15 * len(covered_agents) / len(AGENT_SECTIONS)
    coverage_details = [f"하위 에이전트 의견 {len(covered_agents)}/{len(AGENT_SECTIONS)}개 확인"]
    if missing_agents:
        coverage_details.append("의견 누락: " + ", ".join(missing_agents))
        issues.append(QualityIssue(
            severity="high",
            category="agent_coverage",
            message="하위 에이전트 의견 섹션 일부가 누락되거나 의견값이 파싱되지 않았습니다.",
            evidence=", ".join(missing_agents),
            recommendation="각 섹션에 '- **의견:** 매수/보유/매도' 형식으로 표시하세요.",
        ))
    metrics.append(_metric("하위 에이전트 커버리지", coverage_score, 15, coverage_details))

    final_rec = parse_final_recommendation(text)
    weighted_sum = parse_weighted_sum(text)
    expected_rec = expected_recommendation_from_weighted_sum(weighted_sum)
    consistency_score = 15
    consistency_details = [
        f"최종 추천={final_rec or '파싱 실패'}",
        f"가중합={weighted_sum if weighted_sum is not None else '파싱 실패'}",
        f"가중합 기준 추천={expected_rec or '산출 불가'}",
    ]
    if not final_rec:
        consistency_score -= 7
        issues.append(QualityIssue(
            severity="critical",
            category="recommendation",
            message="최종 추천이 명확히 표시되지 않았습니다.",
            evidence="## 1. 최종 추천 섹션에서 매수/보유/매도 파싱 실패",
            recommendation="최종 추천은 '**보유**'처럼 굵게 명시하세요.",
        ))
    if final_rec and expected_rec and final_rec != expected_rec:
        if "보수 조정" in text or "조정" in _section(text, "## 2. 최종 추천 산정 근거"):
            consistency_score -= 4
            severity = "medium"
        else:
            consistency_score -= 8
            severity = "high"
        issues.append(QualityIssue(
            severity=severity,
            category="recommendation",
            message="가중합 기준 추천과 최종 추천이 다릅니다.",
            evidence=f"final={final_rec}, weighted_expected={expected_rec}, weighted_sum={weighted_sum}",
            recommendation="다른 판단을 내렸다면 '보수 조정 여부'에서 조정 사유를 명확히 설명하세요.",
        ))
    metrics.append(_metric("최종 추천 논리 일관성", consistency_score, 15, consistency_details))

    evidence_score = 15
    evidence_details: List[str] = []
    bad_urls = _has_malformed_url(text)
    if bad_urls:
        evidence_score -= min(6, 2 * len(bad_urls))
        evidence_details.append(f"깨진 URL 후보 {len(bad_urls)}개")
        issues.append(QualityIssue(
            severity="medium",
            category="evidence",
            message="URL 또는 Markdown 링크에 따옴표 등 깨진 문자가 포함되어 있습니다.",
            evidence="; ".join(bad_urls[:3]),
            recommendation="URL 끝의 따옴표/불필요 문자를 제거하세요.",
        ))
    unverified_count = _count_occurrences(text, [r"agent_output_unverified", r"self_generated", r"unverified"])
    if unverified_count:
        evidence_score -= min(5, unverified_count * 2)
        evidence_details.append(f"unverified/self_generated 표현 {unverified_count}회")
        issues.append(QualityIssue(
            severity="high",
            category="evidence",
            message="검증되지 않은 근거 표현이 최종 보고서에 남아 있습니다.",
            evidence=f"count={unverified_count}",
            recommendation="최종 보고서에는 Auditor-safe evidence 또는 확인 제한 문장만 남기세요.",
        ))
    placeholder_count = _count_occurrences(text, [r"\bN/A\b", r"TODO", r"None", r"null"])
    if placeholder_count:
        evidence_score -= min(3, placeholder_count)
        evidence_details.append(f"placeholder 후보 {placeholder_count}회")
    if not evidence_details:
        evidence_details.append("깨진 URL/unverified/self_generated 주요 문제 미탐지")
    metrics.append(_metric("근거/링크 위생", evidence_score, 15, evidence_details))

    finance_sec = _section(text, "### 재무 분석")
    finance_terms = ["Sales Growth", "Operating Margin", "ROE", "FCF", "Debt Ratio", "Annual Return", "MDD"]
    finance_found, finance_missing = _contains_all(finance_sec, finance_terms)
    finance_score = 10 * finance_found / len(finance_terms)
    finance_details = [f"재무 필수 지표 {finance_found}/{len(finance_terms)}개 확인"]
    if finance_missing:
        finance_details.append("누락: " + ", ".join(finance_missing))
        issues.append(QualityIssue(
            severity="medium",
            category="finance",
            message="재무 분석 핵심 근거가 부족합니다.",
            evidence=", ".join(finance_missing),
            recommendation="prompts.py의 필수 지표를 핵심 근거에 포함하세요.",
        ))
    if "ML 기반 보조 판단" not in finance_sec:
        finance_score -= 1
        finance_details.append("ML 기반 보조 판단 문구 미확인")
    metrics.append(_metric("재무 분석 근거 충분성", finance_score, 10, finance_details))

    tech_sec = _section(text, "### 기술 분석")
    tech_required_terms = ["Tech-to-Value", "KIPRIS", "특허", "고객 채택", "양산", "매출 전환", "FCF"]
    peer_terms = ["Tech Peer ML 통합 보정", "Reference Universe", "KMeans", "Cosine Similarity", "UMAP", "Peer Percentile", "Peer-adjusted"]
    tech_found, tech_missing = _contains_all(tech_sec, tech_required_terms)
    peer_found, peer_missing = _contains_all(tech_sec, peer_terms)
    tech_score = 12 * tech_found / len(tech_required_terms) + 8 * peer_found / len(peer_terms)
    tech_details = [
        f"기술 필수 해석 키워드 {tech_found}/{len(tech_required_terms)}개 확인",
        f"Peer ML 블록 키워드 {peer_found}/{len(peer_terms)}개 확인",
    ]
    if tech_missing:
        tech_details.append("기술 해석 누락: " + ", ".join(tech_missing))
    if peer_missing:
        tech_details.append("Peer ML 누락: " + ", ".join(peer_missing))
        issues.append(QualityIssue(
            severity="high",
            category="tech_peer_ml",
            message="Chair 기술 분석 섹션에 7단계 Peer ML 결과가 충분히 삽입되지 않았습니다.",
            evidence=", ".join(peer_missing),
            recommendation="tech_section.py에서 tech_peer_section.py 호출 결과가 기술 분석 섹션에 삽입되는지 확인하세요.",
        ))

    tech_scores = parse_tech_scores(text)
    score_context_terms = ["원점수", "Auditor 보수", "보수 반영", "Peer-adjusted", "보정", "peer-adjusted"]
    if len(tech_scores) >= 2 and not any(t in text for t in score_context_terms):
        tech_score -= 4
        issues.append(QualityIssue(
            severity="high",
            category="tech_score_conflict",
            message="Tech-to-Value Bridge 점수가 여러 개 등장하지만 원점수/보수반영/peer보정 구분이 약합니다.",
            evidence=f"scores={tech_scores}",
            recommendation="Tech Agent 원점수, Auditor 보수 반영 점수, Peer-adjusted 점수를 표로 분리하세요.",
        ))
    elif len(tech_scores) >= 2:
        tech_details.append(f"Tech-to-Value 관련 점수 복수 확인: {tech_scores} / 구분 문구 존재")
    metrics.append(_metric("기술/Peer ML 분석 완성도", tech_score, 20, tech_details))

    needed_risk_terms = ["리스크", "한계", "확인", "과장하지", "고객사", "현금흐름"]
    risk_found, risk_missing = _contains_all(text, needed_risk_terms)
    risk_score = 10 * risk_found / len(needed_risk_terms)
    risk_details = [f"리스크/한계 관련 키워드 {risk_found}/{len(needed_risk_terms)}개 확인"]
    if risk_missing:
        risk_details.append("누락: " + ", ".join(risk_missing))
    metrics.append(_metric("리스크/한계 고지", risk_score, 10, risk_details))

    readability_score = 10
    read_details = []
    line_count = len(text.splitlines())
    char_count = len(text)
    read_details.append(f"문자 수={char_count:,}, 줄 수={line_count:,}")
    if char_count < 1800:
        readability_score -= 4
        issues.append(QualityIssue(
            severity="medium",
            category="readability",
            message="보고서가 지나치게 짧아 핵심 판단 근거가 부족해 보일 수 있습니다.",
            evidence=f"chars={char_count}",
            recommendation="핵심 근거, 하위 에이전트 요약, 리스크, 종합 의견을 보강하세요.",
        ))
    if char_count > 18000:
        readability_score -= 3
        issues.append(QualityIssue(
            severity="low",
            category="readability",
            message="보고서가 지나치게 길어 발표/사용자 관점에서 가독성이 떨어질 수 있습니다.",
            evidence=f"chars={char_count}",
            recommendation="상단에 1페이지 요약표를 추가하거나 상세 부록으로 분리하세요.",
        ))
    zero_noise = len(re.findall(r"0\s*(회|개|건)", text))
    if zero_noise:
        readability_score -= min(3, zero_noise)
        issues.append(QualityIssue(
            severity="medium",
            category="readability",
            message="'0회/0개/0건' 표현이 보고서에 남아 있습니다.",
            evidence=f"count={zero_noise}",
            recommendation="실제 의미가 있는 경우만 남기고, 산출 불가 항목은 '필요 자료' 또는 '확인 제한'으로 바꾸세요.",
        ))
    metrics.append(_metric("가독성/노이즈 관리", readability_score, 10, read_details))

    total = round(sum(m.score for m in metrics), 2)
    has_critical = any(i.severity == "critical" for i in issues)
    high_count = sum(1 for i in issues if i.severity == "high")
    if has_critical or total < 70:
        status = "FAIL"
    elif total < 85 or high_count >= 2:
        status = "REVIEW"
    else:
        status = "PASS"

    parsed = {
        "final_recommendation": final_rec,
        "weighted_sum": weighted_sum,
        "weighted_sum_expected_recommendation": expected_rec,
        "agent_opinions": opinions,
        "tech_scores": tech_scores,
        "report_chars": char_count,
        "report_lines": line_count,
    }
    result = QualityResult(
        company_dir=company_dir,
        company_name=company_name,
        report_path=str(report_path),
        evaluated_at=datetime.now().isoformat(timespec="seconds"),
        total_score=total,
        status=status,
        metrics=metrics,
        issues=issues,
        parsed=parsed,
    )

    if save:
        out_dir = chair_quality_dir(company_dir) if output_root.name == "data" else output_root / company_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "chair_report_quality.json").write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / "chair_report_quality.md").write_text(format_quality_markdown(result), encoding="utf-8")
    return result


def format_quality_markdown(result: QualityResult) -> str:
    lines: List[str] = []
    lines.append(f"# Chair 최종 보고서 품질평가 결과 - {result.company_name}")
    lines.append("")
    lines.append(f"- **company_dir:** {result.company_dir}")
    lines.append(f"- **report_path:** `{result.report_path}`")
    lines.append(f"- **evaluated_at:** {result.evaluated_at}")
    lines.append(f"- **total_score:** **{result.total_score:.2f}/100**")
    lines.append(f"- **status:** **{result.status}**")
    lines.append("")

    lines.append("## 1. 파싱 요약")
    lines.append("")
    lines.append("| 항목 | 값 |")
    lines.append("|---|---|")
    lines.append(f"| 최종 추천 | {result.parsed.get('final_recommendation') or '파싱 실패'} |")
    lines.append(f"| 가중합 | {result.parsed.get('weighted_sum')} |")
    lines.append(f"| 가중합 기준 추천 | {result.parsed.get('weighted_sum_expected_recommendation') or '산출 불가'} |")
    lines.append(f"| Tech-to-Value 관련 점수 | {result.parsed.get('tech_scores')} |")
    lines.append(f"| 보고서 길이 | {result.parsed.get('report_chars'):,}자 / {result.parsed.get('report_lines'):,}줄 |")
    lines.append("")

    opinions = result.parsed.get("agent_opinions") or {}
    lines.append("## 2. 하위 에이전트 의견 파싱")
    lines.append("")
    lines.append("| Agent | Opinion |")
    lines.append("|---|---|")
    for agent in ["finance", "market", "tech", "issue", "macro"]:
        lines.append(f"| {agent} | {opinions.get(agent) or '파싱 실패'} |")
    lines.append("")

    lines.append("## 3. 세부 점수")
    lines.append("")
    lines.append("| 평가영역 | 점수 | 상태 | 세부내용 |")
    lines.append("|---|---:|---|---|")
    for m in result.metrics:
        details = "<br>".join(m.details) if m.details else ""
        lines.append(f"| {m.name} | {m.score:.2f}/{m.max_score:.0f} | {m.status} | {details} |")
    lines.append("")

    lines.append("## 4. 발견 이슈")
    lines.append("")
    if not result.issues:
        lines.append("- 발견된 주요 이슈가 없습니다.")
    else:
        lines.append("| 심각도 | 범주 | 내용 | 근거 | 수정 권고 |")
        lines.append("|---|---|---|---|---|")
        for issue in result.issues:
            evidence = (issue.evidence or "").replace("|", "/")
            rec = (issue.recommendation or "").replace("|", "/")
            msg = (issue.message or "").replace("|", "/")
            lines.append(f"| {issue.severity} | {issue.category} | {msg} | {evidence} | {rec} |")
    lines.append("")

    lines.append("## 5. 판정 기준")
    lines.append("")
    lines.append("- **PASS:** 85점 이상이며 critical 이슈가 없고 high 이슈가 과도하지 않은 상태")
    lines.append("- **REVIEW:** 70점 이상이지만 보강이 필요한 상태")
    lines.append("- **FAIL:** 70점 미만 또는 critical 이슈가 있는 상태")
    lines.append("")
    lines.append("## 6. 활용 방법")
    lines.append("")
    lines.append("- 이 평가는 수익률이나 미래 성과를 사용하지 않는 return-free 품질평가입니다.")
    lines.append("- 최종 추천의 논리 일관성, 하위 에이전트 근거 충분성, Tech Peer ML 반영 여부, URL·근거 위생, 리스크 고지를 자동 채점합니다.")
    lines.append("- First Auditor 통과 여부와 별개로, 발표/사용자 관점에서 보고서 품질을 사후 검수하는 용도로 사용합니다.")
    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate Chair final report quality.")
    parser.add_argument("--company-dir", default="nepes", help="Company slug directory, e.g. nepes")
    parser.add_argument("--company", default="", help="Display company name, e.g. 네패스")
    parser.add_argument("--report", default="", help="Optional report path. Default: data/<field>/<company>/chair/<company-dir>_chair_report.md")
    parser.add_argument("--output-root", default="data", help="Output root directory")
    args = parser.parse_args(argv)

    report_path = Path(args.report) if args.report else agent_output_path(args.company_dir, "chair", f"{args.company_dir}_chair_report.md")
    result = evaluate_chair_report(
        report_path=report_path,
        company_dir=args.company_dir,
        company_name=args.company or args.company_dir,
        output_root=Path(args.output_root),
        save=True,
    )
    out_dir = chair_quality_dir(args.company_dir) if Path(args.output_root).name == "data" else Path(args.output_root) / args.company_dir
    print(f"[Chair Quality] status={result.status} score={result.total_score:.2f}/100")
    print(f"[Chair Quality] JSON: {out_dir / 'chair_report_quality.json'}")
    print(f"[Chair Quality] MD:   {out_dir / 'chair_report_quality.md'}")
    if result.issues:
        print(f"[Chair Quality] issues={len(result.issues)}")
        for issue in result.issues[:5]:
            print(f"  - {issue.severity.upper()} / {issue.category}: {issue.message}")
    return 0 if result.status in {"PASS", "REVIEW"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
