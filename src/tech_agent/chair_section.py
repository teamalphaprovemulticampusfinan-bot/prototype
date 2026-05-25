from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from common.output_paths import agent_output_dir, output_candidates, read_json_first

ROOT = Path(__file__).resolve().parents[2]


GRADE_LABELS = {
    "VALUE_CONVERSION_CONFIRMED": "가치 전환 확인형",
    "COMMERCIALIZATION_WATCH": "사업화 추적형",
    "TECH_FINANCE_GAP": "기술-재무 괴리형",
    "TECH_EVIDENCE_WEAK": "근거 보강 필요형",
    "DISTINCTIVE_TECH_LEADER": "차별화 선도형",
    "DIFFERENTIATED_TECH_POSITION": "차별화 확인형",
    "MODERATE_DIFFERENTIATION": "보통 차별화형",
    "LIMITED_DIFFERENTIATION": "차별화 제한형",
    "TECH_TO_VALUE_READY": "사업화 연결 준비형",
    "INVESTOR_TECH_CONVICTION": "기술-사업화 확신형",
}


FINAL_GRADE_BY_SCORE = [
    (80.0, "VALUE_CONVERSION_CONFIRMED"),
    (60.0, "COMMERCIALIZATION_WATCH"),
    (50.0, "TECH_FINANCE_GAP"),
    (0.0, "TECH_EVIDENCE_WEAK"),
]


def _rel_project_path(value: Any) -> str:
    """Return a project-relative path string for repo portability."""
    if value is None:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""
    raw = raw.replace("\\", "/")
    try:
        p = Path(raw)
        if p.is_absolute():
            return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        pass
    for prefix in ("data", "workspace", "src", "scripts"):
        m = re.search(rf"(?:^|.*?)({prefix}[\/].*)$", raw)
        if m:
            return m.group(1).replace("\\", "/")
    return raw.replace("\\", "/")


def _read_json(path: Path) -> Optional[Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return None
    except Exception:
        return None
    return None



def _glob_summary_by_company_dir(company_dir: str) -> Dict[str, Any]:
    """Fallback summary lookup that also works with literal #Uxxxx zip paths."""
    slug = str(company_dir or "").strip()
    if not slug:
        return {}

    roots = [ROOT / "data", ROOT / "workspace" / "outputs", ROOT / "workspace" / "packets"]
    patterns = [
        "*/*/tech/tech_chair_summary.json",
        "*/*/tech/*_tech_chair_summary.json",
        "*/tech/tech_chair_summary.json",
        "*/tech/*_tech_chair_summary.json",
        f"**/{slug}_tech_chair_summary.json",
        "**/tech_chair_summary.json",
    ]
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        for pattern in patterns:
            for path in root.glob(pattern):
                key = str(path.resolve())
                if key in seen:
                    continue
                seen.add(key)
                data = _read_json(path)
                if not isinstance(data, dict):
                    continue
                data_slug = str(data.get("company_dir") or data.get("company_slug") or "").strip()
                if data_slug == slug or path.name.startswith(f"{slug}_"):
                    return data
    return {}


def _clean(text: Any, limit: int = 180) -> str:
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    if not s:
        return "확인 제한"
    s = s.replace('"', "").replace("`", "")
    s = re.sub(r"0\s*(회|개|건)", "확인 제한", s)
    s = re.sub(r"agent_output_unverified|self_generated|unverified", "확인 제한", s, flags=re.IGNORECASE)
    return s[:limit] + ("..." if len(s) > limit else "")


def _num(value: Any) -> Optional[float]:
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except Exception:
        return None


def _fmt_score(value: Any, suffix: str = "/100") -> str:
    x = _num(value)
    return "확인 제한" if x is None else f"{x:.2f}{suffix}"


def _fmt_pct(value: Any) -> str:
    x = _num(value)
    return "확인 제한" if x is None else f"{x:.2f}%"


def _fmt_count(value: Any, suffix: str = "건") -> str:
    x = _num(value)
    return "확인 제한" if x is None else f"{x:,.0f}{suffix}"


def _grade(raw: Any) -> str:
    if isinstance(raw, dict):
        code = str(raw.get("code") or "").strip()
        label = str(raw.get("label") or "").strip()
        if code and label:
            return f"{label}({code})"
        if label:
            return label
        raw = code

    g = str(raw or "").strip()
    if not g:
        return "확인 제한"
    return f"{GRADE_LABELS.get(g, g)}({g})" if g in GRADE_LABELS else g


def _grade_code_from_score(score: Any) -> str:
    x = _num(score)
    if x is None:
        return ""
    for threshold, code in FINAL_GRADE_BY_SCORE:
        if x >= threshold:
            return code
    return "TECH_EVIDENCE_WEAK"


def _first_present(mapping: Dict[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def _final_bridge_score(tv: Dict[str, Any], selected_ml: Dict[str, Any] | None = None) -> Any:
    selected_ml = selected_ml or {}
    return _first_present(
        tv,
        (
            "final_bridge_score_after_ip_evidence",
            "ip_evidence_adjusted_score",
            "peer_adjusted_bridge_score",
            "peer_adjusted_bridge_score_before_ip_evidence",
            "base_bridge_score",
        ),
    ) or _first_present(selected_ml, ("final_bridge_score_after_ip_evidence", "ip_evidence_adjusted_score"))


def _final_bridge_grade(tv: Dict[str, Any], selected_ml: Dict[str, Any] | None = None) -> Any:
    selected_ml = selected_ml or {}
    explicit = _first_present(
        tv,
        (
            "final_bridge_grade_after_ip_evidence",
            "ip_evidence_adjusted_grade",
            "final_tech_to_value_grade",
            "peer_adjusted_grade",
            "base_bridge_grade",
        ),
    ) or _first_present(selected_ml, ("final_bridge_grade_after_ip_evidence", "ip_evidence_adjusted_grade"))
    if explicit:
        return explicit
    return _grade_code_from_score(_final_bridge_score(tv, selected_ml))


def _find_tech_opinion(opinions: Sequence[Dict[str, Any]] | None) -> Dict[str, Any]:
    for op in opinions or []:
        if str(op.get("agent") or "").lower() == "tech":
            return op
    return {}


def _load_summary(company_dir: str, opinions: Sequence[Dict[str, Any]] | None) -> Dict[str, Any]:
    tech_op = _find_tech_opinion(opinions)
    embedded = tech_op.get("tech_chair_summary")
    if isinstance(embedded, dict) and embedded:
        return embedded

    candidates = [agent_output_dir(company_dir, "tech", root=ROOT, create=False) / "tech_chair_summary.json"]
    candidates.extend(output_candidates(company_dir, "tech", f"{company_dir}_tech_chair_summary.json", root=ROOT))
    candidates.extend(output_candidates(company_dir, "tech", "tech_chair_summary.json", root=ROOT))
    data = read_json_first(candidates)
    if isinstance(data, dict) and data:
        return data

    data = _glob_summary_by_company_dir(company_dir)
    if isinstance(data, dict) and data:
        return data

    # Fallback for older runs: build minimal summary from tech packet.
    tech_packet = _read_json(agent_output_dir(company_dir, "tech", root=ROOT, create=False) / "tech.json") or {}
    if not isinstance(tech_packet, dict):
        tech_packet = {}
    return {
        "company": tech_packet.get("company") or tech_packet.get("company_name") or company_dir,
        "company_dir": company_dir,
        "opinion": tech_packet.get("opinion") or tech_op.get("opinion") or "보유",
        "tech_to_value": tech_packet.get("tech_to_value") or tech_packet.get("tech_to_value_inputs") or {},
        "excel_frame_summary": tech_packet.get("categories") or [],
        "ip_quant_signals": {},
        "selected_ml": {},
        "businessization_gate": [],
        "chair_policy": [
            "Tech compact summary가 아직 생성되지 않았습니다. `python main.py tech --company-dir <company_dir> --company-name <회사명>` 실행 후 Chair를 다시 실행하세요.",
        ],
    }


def _extract_rows(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for r in summary.get("excel_frame_summary") or []:
        if not isinstance(r, dict):
            continue
        rows.append(
            {
                "category": _clean(r.get("category") or r.get("title") or r.get("name") or "기술 항목", 40),
                "item": _clean(r.get("item") or r.get("metric_name") or r.get("category") or "핵심 항목", 50),
                "quantification": _clean(r.get("quantification") or r.get("metric_value") or "정량화 가능 자료 확인 필요", 70),
                "evidence": _clean(r.get("evidence") or r.get("basis") or r.get("summary") or "원천 근거 확인 필요", 85),
                "grade": _clean(r.get("grade") or r.get("score") or "정성 확인", 30),
                "note": _clean(r.get("note") or r.get("limitation") or "필요 시 원천 근거 확인", 60),
            }
        )
    return rows[:7]


def _render_ip_evidence_block(tv: Dict[str, Any], selected_ml: Dict[str, Any]) -> str:
    final_score = _final_bridge_score(tv, selected_ml)
    if _num(final_score) is None:
        return ""

    peer_before = _first_present(tv, ("peer_adjusted_bridge_score_before_ip_evidence", "peer_adjusted_bridge_score"))
    ip_score = _first_present(tv, ("ip_evidence_composite_score", "ip_evidence_score")) or _first_present(selected_ml, ("ip_evidence_composite_score",))
    ip_signal = _first_present(tv, ("ip_evidence_composite_bridge_signal", "ip_evidence_bridge_signal")) or _first_present(selected_ml, ("ip_evidence_bridge_signal",))
    ip_adjustment = _first_present(tv, ("ip_evidence_composite_adjustment_points", "ip_evidence_bridge_adjustment_points")) or _first_present(selected_ml, ("ip_evidence_bridge_adjustment_points",))
    formula = tv.get("ip_evidence_formula") or (
        "final_bridge_score_after_ip_evidence = peer_adjusted_bridge_score_before_ip_evidence + ip_evidence_composite_adjustment_points"
    )
    final_grade = _final_bridge_grade(tv, selected_ml)

    lines = [
        "##### 1-1. IP Evidence Composite 반영 최종 Tech-to-Value Score",
        "",
        "| 항목 | 값 | Chair 해석 |",
        "|---|---:|---|",
        f"| IP Evidence 반영 전 Peer-adjusted Score | {_fmt_score(peer_before)} | Peer ML 보정 이후, IP Evidence Composite 반영 전 점수입니다. |",
        f"| IP Evidence Composite Score | {_fmt_score(ip_score)} | 법적 안정성·청구항 방어력·인용 영향력·글로벌 패밀리 확장성을 종합한 IP 질적 근거 점수입니다. |",
        f"| IP Evidence Bridge Signal | {_clean(ip_signal, 60)} | Tech-to-Value Bridge에 반영되는 IP Evidence 방향성입니다. |",
        f"| IP Evidence Adjustment Points | {_fmt_score(ip_adjustment, '점')} | 최종 Tech-to-Value 점수에 더해지는 조정값입니다. |",
        f"| Final Tech-to-Value Score After IP Evidence | {_fmt_score(final_score)} | Chair 기술 분석에서 우선 사용해야 하는 최종 기술 점수입니다. |",
        f"| Final IP-adjusted Grade | {_grade(final_grade)} | Base/Peer 판정보다 우선 적용하는 최종 기술 판정입니다. |",
        "",
        f"- 산식: `{formula}`",
        "- Chair 보고서에서는 Base Bridge Score와 Peer-adjusted Score를 참고값으로만 두고, **IP Evidence 반영 후 최종 점수와 최종 판정**을 기술 종합 판단에 우선 반영합니다.",
    ]
    return "\n".join(lines).strip()


def _render_investor_scorecard(summary: Dict[str, Any], tv: Dict[str, Any]) -> str:
    view = summary.get("tech_investor_view")
    if not isinstance(view, dict) or not view:
        score = _first_present(tv, ("investor_final_tech_score", "final_investor_tech_score"))
        grade = _first_present(tv, ("investor_final_tech_grade", "final_investor_tech_grade"))
        if _num(score) is None and not grade:
            return ""
        view = {
            "final_tech_investor_score": score,
            "final_tech_investor_grade": grade,
            "score_component_rows": [],
            "investor_evidence": [],
        }

    score = view.get("final_tech_investor_score") or view.get("investor_final_tech_score") or _first_present(tv, ("investor_final_tech_score", "final_investor_tech_score"))
    grade = view.get("final_tech_investor_grade") or view.get("investor_final_tech_grade") or _first_present(tv, ("investor_final_tech_grade", "final_investor_tech_grade"))

    lines = [
        "#### 개인투자자용 Tech 최종 점수판",
        "",
        f"- **최종 Tech 점수:** {_fmt_score(score)}",
        f"- **최종 판정:** {_grade(grade)}",
        "- **해석:** 기술/IP/Excel 정량 근거를 하나의 점수로 합성해 Chair 판단에 반영했습니다.",
    ]

    rows = [row for row in (view.get("score_component_rows") or []) if isinstance(row, dict)]
    if rows:
        lines.extend(["", "| 구성요소 | 점수 | 가중치 | 의미 |", "|---|---:|---:|---|"])
        for row in rows[:8]:
            lines.append(
                f"| {_clean(row.get('label'), 40)} | {_fmt_score(row.get('score'))} | {_clean(row.get('weight'), 20)} | {_clean(row.get('meaning'), 90)} |"
            )

    evidences = [ev for ev in (view.get("investor_evidence") or []) if isinstance(ev, dict)]
    if evidences:
        lines.extend(["", "- **핵심 근거:**"])
        for ev in evidences[:5]:
            lines.append(f"  - {_clean(ev.get('title'), 60)}: {_clean(ev.get('detail'), 160)}")
    return "\n".join(lines).strip()




def _status_badge(status: Any) -> str:
    s = _clean(status, 40)
    mapping = {
        "DIRECT_EVIDENCE": "직접 근거 확인",
        "INDIRECT_EVIDENCE": "간접 근거 확인",
        "PARTIAL_EVIDENCE": "부분 근거 확인",
        "CROSS_CHECK_REQUIRED": "교차 검증 필요",
        "NOT_FOUND": "확인 제한",
    }
    return mapping.get(s, s or "확인 제한")


def _render_value_evidence_bridge(summary: Dict[str, Any]) -> str:
    """Render Tech Intake Value Evidence Bridge for the Chair tech section."""
    bridge = summary.get("value_evidence_bridge")
    if not isinstance(bridge, dict) or not bridge:
        # Backward compatibility: some runs may expose only refined checkpoints.
        cps = summary.get("next_checkpoints_refined") or []
        if not cps:
            return ""
        lines = [
            "#### 7) Value Evidence Bridge 기반 다음 확인 포인트",
            "",
            "Tech Intake Value Evidence Bridge 파일은 아직 병합되지 않았지만, 정제된 확인 포인트가 존재합니다.",
        ]
        lines.extend([f"- {_clean(cp, 220)}" for cp in cps[:7]])
        return "\n".join(lines).strip()

    dims = bridge.get("dimensions") if isinstance(bridge.get("dimensions"), dict) else {}
    lines: List[str] = [
        "#### 7) Tech Intake Value Evidence Bridge",
        "",
        "- **목적:** 기술 우위가 실제 고객 채택, 양산, 매출 전환, IP 품질, 마진·현금흐름 개선으로 연결되는지 원천 산출물 기준으로 분리 점검합니다.",
        f"- **종합 점수:** {_fmt_score(bridge.get('value_evidence_score'))}",
        f"- **종합 라벨:** {_clean(bridge.get('value_evidence_label'), 80)}",
        f"- **스캔한 원천 문서:** {_fmt_count(bridge.get('source_document_count'))}",
        "",
        "| 연결 항목 | 상태 | 점수 | 직접/간접/부분 | 핵심 해석 |",
        "|---|---|---:|---|---|",
    ]
    for key in ["customer_adoption", "mass_production", "revenue_conversion", "ip_quality", "margin_cashflow_linkage"]:
        d = dims.get(key) if isinstance(dims.get(key), dict) else {}
        if not d:
            continue
        counts = (
            f"직접 {_fmt_count(d.get('direct_evidence_count'))} / "
            f"간접 {_fmt_count(d.get('indirect_evidence_count'))} / "
            f"부분 {_fmt_count(d.get('partial_or_cross_check_count'))}"
        )
        lines.append(
            f"| {_clean(d.get('label') or key, 50)} | {_status_badge(d.get('status'))} | {_fmt_score(d.get('score'))} | {counts} | {_clean(d.get('summary'), 130)} |"
        )

    # 대표 근거는 길게 붙이지 않고, 항목별 1개씩만 보여준다. 상세는 tech_intake_value_evidence.md에 보관한다.
    evidence_lines: List[str] = []
    for key in ["customer_adoption", "mass_production", "revenue_conversion", "ip_quality", "margin_cashflow_linkage"]:
        d = dims.get(key) if isinstance(dims.get(key), dict) else {}
        evs = [ev for ev in (d.get("evidence") or []) if isinstance(ev, dict)]
        if not evs:
            continue
        ev = evs[0]
        url = ""
        urls = ev.get("urls") or ev.get("fallback_urls") or []
        if urls:
            url = f" / URL: {_clean(urls[0], 120)}"
        evidence_lines.append(
            f"- **{_clean(d.get('label') or key, 40)}:** {_clean(ev.get('snippet'), 180)} "
            f"(source={_clean(ev.get('source_file'), 90)}{url})"
        )
    if evidence_lines:
        lines.extend(["", "- **대표 근거:**"])
        lines.extend(evidence_lines[:5])

    checkpoints = bridge.get("next_checkpoints_refined") or summary.get("next_checkpoints_refined") or []
    if checkpoints:
        lines.extend(["", "- **다음 확인 포인트:**"])
        for cp in checkpoints[:7]:
            lines.append(f"  - {_clean(cp, 220)}")

    files = bridge.get("output_files") if isinstance(bridge.get("output_files"), dict) else {}
    detail = files.get("md") or files.get("prefixed_md")
    if detail:
        lines.append(f"- **상세 근거 파일:** `{_rel_project_path(detail)}`")
    return "\n".join(lines).strip()


def _render_compact_tech_section(summary: Dict[str, Any], company: str) -> str:
    company = company or summary.get("company") or summary.get("company_dir") or "기업"
    opinion = summary.get("opinion") or "보유"
    tv = summary.get("tech_to_value") or {}
    ip = summary.get("ip_quant_signals") or {}
    ml = summary.get("selected_ml") or {}
    peer = ml.get("peer_ml") or {}
    diff = ml.get("technology_differentiation") or {}
    conf = ml.get("evidence_confidence") or {}
    pm = ml.get("patent_momentum") or {}
    ipml = ml.get("tech_ip_strength") or {}
    rows = _extract_rows(summary)
    files = summary.get("summary_files") or summary.get("detail_files") or {}

    final_score = _final_bridge_score(tv, ml)
    final_grade = _final_bridge_grade(tv, ml)
    ip_block = _render_ip_evidence_block(tv, ml)
    investor_block = _render_investor_scorecard(summary, tv)
    value_evidence_block = _render_value_evidence_bridge(summary)

    lines: List[str] = [
        "### 기술 분석",
        f"- **의견:** {opinion}",
        "- **요약 방식:** 상세 Excel-frame·KIPRIS/IP·Tech ML 표는 Tech Agent 산출물에 보관하고, Chair에는 검증 후 핵심 신호만 요약합니다.",
        "- **최종 반영 기준:** Base/Peer 점수가 아니라 **Final Tech-to-Value Score After IP Evidence**와 **Final IP-adjusted Grade**를 우선 적용합니다.",
        "",
        "#### 1) Tech-to-Value Bridge 판정",
    ]

    if ip_block:
        lines.extend([ip_block, ""])

    lines.extend(
        [
            "| 항목 | 값 | 해석 |",
            "|---|---:|---|",
            f"| Tech Agent 원점수 | {_fmt_score(tv.get('tech_agent_raw_score'))} | Tech Agent 내부 원점수입니다. |",
            f"| Auditor 보수 반영 점수 | {_fmt_score(tv.get('auditor_adjusted_score'))} | claim/evidence 검증 후 보수적으로 반영한 점수입니다. |",
            f"| Base Bridge Score | {_fmt_score(tv.get('base_bridge_score'))} | 기본 Tech-to-Value Bridge 판정입니다. |",
            f"| Peer-adjusted Bridge Score | {_fmt_score(tv.get('peer_adjusted_bridge_score'))} | Reference Universe, KMeans, Cosine Similarity, UMAP, Peer Percentile 기반 보정 신호입니다. |",
            f"| Final IP-adjusted Score | {_fmt_score(final_score)} | IP Evidence Composite 반영 후 Chair 기술 분석에 우선 적용할 점수입니다. |",
            f"| Final IP-adjusted Grade | {_grade(final_grade)} | Chair가 최종 기술 판단에 우선 적용할 판정입니다. |",
            "",
            "- **COMMERCIALIZATION_WATCH:** 사업화 추적형. 기술성은 확인되지만 고객 채택·양산·매출 전환·FCF 개선까지 이어지는 연결고리를 계속 추적해야 하는 상태입니다.",
            "- **TECH_FINANCE_GAP:** 기술-재무 괴리형. 기술/IP 포트폴리오는 존재하지만 수익성·현금흐름·재무안정성으로 전환되는 직접 근거가 약한 상태입니다.",
        ]
    )

    if investor_block:
        lines.extend(["", investor_block])

    lines.extend(
        [
            "",
            "#### 2) Excel-frame 기반 기술 포지션 요약",
            "| 대분류 | 항목 | 정량화 | 핵심 근거 | 등급 | 비고 |",
            "|---|---|---|---|---|---|",
        ]
    )
    if rows:
        for r in rows:
            lines.append(f"| {r['category']} | {r['item']} | {r['quantification']} | {r['evidence']} | {r['grade']} | {r['note']} |")
    else:
        lines.append("| 확인 제한 | 확인 제한 | 정량화 가능 자료 확인 필요 | Tech compact summary 생성 필요 | 확인 제한 | `python main.py tech` 실행 필요 |")

    lines += [
        "",
        "#### 3) KIPRIS/특허 기반 IP 정량 신호",
        "| 원천 신호 | 값 |",
        "|---|---:|",
        f"| 정규화 특허 텍스트 레코드 | {_fmt_count(ip.get('normalized_patent_text_records'))} |",
        f"| 회사 출원인/권리자 매칭 | {_fmt_count(ip.get('company_matched_patents'))} |",
        f"| 등록 특허 | {_fmt_count(ip.get('registered_patents'))} |",
        f"| 존속 가능 특허 | {_fmt_count(ip.get('alive_patents'))} |",
        f"| 최근 5년 특허 | {_fmt_count(ip.get('recent_5y_patents'))} |",
        f"| IPC/CPC 다양성 | {_fmt_count(ip.get('ipc_cpc_classes'), '개')} |",
        f"| H01L 등 핵심 IPC 특허 | {_fmt_count(ip.get('core_ipc_h01l_patents'))} |",
        "",
        "#### 4) 사업화 연결 체크",
        "| 연결 항목 | 상태 | 점수 | 직접/간접/확인 제한 |",
        "|---|---|---:|---|",
    ]
    gate = summary.get("businessization_gate") or []
    if gate:
        for g in gate:
            if not isinstance(g, dict):
                continue
            direct = _fmt_count(g.get("direct_evidence_count"))
            indirect = _fmt_count(g.get("indirect_evidence_count"))
            limited = _fmt_count(g.get("limited_evidence_count"))
            lines.append(f"| {_clean(g.get('dimension'), 40)} | {_clean(g.get('status'), 40)} | {_fmt_score(g.get('score'))} | 직접 {direct} / 간접 {indirect} / 확인 제한 {limited} |")
    else:
        lines.append("| 고객 채택·양산·매출 전환·FCF/현금흐름 | 확인 제한 | 확인 제한 | Tech-to-Value Evidence Confidence 산출 필요 |")

    if value_evidence_block:
        lines.extend(["", value_evidence_block])

    lines += [
        "",
        "#### 8) 선택 ML 신호 요약",
        "| ML 신호 | 값 | Chair 반영 의미 |",
        "|---|---:|---|",
        f"| Technology Differentiation Score | {_fmt_score(diff.get('score'))} / {_fmt_pct(diff.get('percentile'))} | peer 대비 특허/IP 포트폴리오의 구별성입니다. |",
        f"| Tech-to-Value Evidence Confidence | {_fmt_score(conf.get('score'))} | 고객 채택·양산·매출·FCF 근거의 직접성을 보수적으로 평가합니다. |",
        f"| Patent Momentum Score | {_fmt_score(pm.get('score'))} | 최근 특허 활동과 기술 지속성 신호입니다. |",
        f"| Tech/IP Strength Index + NMF Topic Modeling | {_fmt_score(ipml.get('score'))} / topic={_clean(ipml.get('dominant_topic'), 80)} | 특허/IP 포트폴리오 강도와 기술 주제 집중도를 설명합니다. |",
        "",
        "#### 9) Tech Peer ML 통합 보정",
        "- **Peer ML 구성:** Reference Universe 기반 KMeans peer group, 5개 focal 기업 Cosine Similarity, UMAP 2D Peer Map, Peer Percentile 기반 Tech-to-Value Bridge 보정.",
        f"- **Peer-adjusted Bridge:** {_fmt_score(peer.get('peer_adjusted_bridge_score') or tv.get('peer_adjusted_bridge_score'))}, percentile={_fmt_pct(peer.get('peer_composite_percentile'))}, cluster={_clean(peer.get('cluster_name'), 80)}.",
        "- **해석:** 이 ML 신호는 미래 수익률 예측이 아니라 기술/IP 포트폴리오의 상대 위치와 차별성을 설명하기 위한 return-free 보조 지표입니다.",
        "",
        "#### 10) Chair 반영 원칙",
    ]
    policies = summary.get("chair_policy") or []
    if policies:
        for policy in policies[:4]:
            lines.append(f"- {_clean(policy, 240)}")
    else:
        lines.append("- 기술 점수는 단독 투자 근거가 아니라 고객 채택·양산·매출 전환·FCF 개선 근거와 결합될 때만 가치평가 보조 신호로 반영합니다.")

    detail_md = files.get("tech_full_appendix_md") or files.get("tech_deep_dive_md") or files.get("chair_summary_md")
    if detail_md:
        lines.append(f"- **상세 부록:** `{_rel_project_path(detail_md)}`")
    return "\n".join(lines).strip() + "\n"


def _replace_tech_section(report: str, new_section: str) -> str:
    """Replace the existing tech section without interpreting backslashes in paths."""
    text = report or ""
    pat = re.compile(
        r"(?ms)^###\s*기술\s*분석\s*\n.*?(?=^###\s*(?:이슈\s*분석|거시경제|시장\s*분석|재무\s*분석)\s*$|^##\s+)",
    )
    if pat.search(text):
        return pat.sub(lambda _m: new_section.rstrip() + "\n\n", text, count=1)

    for marker in ["### 이슈 분석", "### 거시경제", "## 5. 충돌 지점 및 해석"]:
        idx = text.find(marker)
        if idx >= 0:
            return text[:idx].rstrip() + "\n\n" + new_section.rstrip() + "\n\n" + text[idx:]
    return text.rstrip() + "\n\n" + new_section.rstrip() + "\n"


def inject_compact_tech_section(
    report: str,
    opinions: Sequence[Dict[str, Any]] | None = None,
    company_dir: str = "",
    company: str = "",
    company_name: str | None = None,
    **_: Any,
) -> str:
    """Inject the Chair-facing compact tech section.

    Supported calls:
    - inject_compact_tech_section(report, opinions=opinions, company_dir=slug, company=name)
    - inject_compact_tech_section(report, opinions, slug, name)
    - inject_compact_tech_section(report, slug, name)  # legacy wrapper/test style

    The previous patch stack wrapped this function with a different positional
    signature and could raise `got multiple values for argument 'opinions'`; this
    implementation is the single canonical entry point.
    """
    if isinstance(opinions, str):
        # Legacy call style: (report, company_dir, company_name).
        legacy_company_dir = opinions
        legacy_company = company_dir if isinstance(company_dir, str) else ""
        opinions = None
        company_dir = legacy_company_dir
        if not company and legacy_company:
            company = legacy_company

    summary = _load_summary(company_dir, opinions)
    display_company = company or company_name or summary.get("company") or company_dir
    section = _render_compact_tech_section(summary, display_company)
    return _replace_tech_section(report, section)


# Backward-compatible function name. graph.py can import either name.
def inject_high_quality_tech_section(
    report: str,
    opinions: Sequence[Dict[str, Any]] | None = None,
    company_dir: str = "",
    company: str = "",
    company_name: str | None = None,
    **kwargs: Any,
) -> str:
    return inject_compact_tech_section(
        report,
        opinions=opinions,
        company_dir=company_dir,
        company=company,
        company_name=company_name,
        **kwargs,
    )
