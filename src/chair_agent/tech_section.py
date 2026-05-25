from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

GRADE_GUIDE: dict[str, tuple[str, str, str]] = {
    "VALUE_CONVERSION_CONFIRMED": (
        "가치 전환 확인형",
        "기술 근거가 고객 채택·양산·매출 전환·현금흐름 개선 근거와 비교적 잘 연결된 상태입니다.",
        "기술 요인을 가치평가 가산 요인으로 일부 반영할 수 있습니다.",
    ),
    "TECH_VALUE_CONNECTED": (
        "가치 전환 확인형",
        "기술 근거가 고객 채택·양산·매출 전환·현금흐름 개선 근거와 비교적 잘 연결된 상태입니다.",
        "기술 요인을 가치평가 가산 요인으로 일부 반영할 수 있습니다.",
    ),
    "COMMERCIALIZATION_WATCH": (
        "사업화 추적형",
        "기술성은 확인되지만 고객 채택·양산·매출 전환·FCF 개선까지 이어지는 연결 고리를 계속 확인해야 하는 상태입니다.",
        "기술 우위는 긍정 보조 근거로 쓰되, 단독 매수 근거로 과대 반영하지 않습니다.",
    ),
    "TECH_FINANCE_GAP": (
        "기술-재무 괴리형",
        "기술 포트폴리오는 있으나 수익성·현금흐름·재무안정성으로의 전환 근거가 약한 상태입니다.",
        "기술 점수는 보수적으로 반영하고, 재무 개선 확인 전까지 가치평가 가산을 제한합니다.",
    ),
    "TECH_EVIDENCE_WEAK": (
        "근거 보강 필요형",
        "기술·특허·양산·고객 채택 근거가 충분히 구조화되지 않아 판단 신뢰도가 낮은 상태입니다.",
        "기술 분석은 참고 정보로만 쓰고, 최종 판단 기여도를 낮춥니다.",
    ),
}

SECTION_ORDER = [
    "대표 기술",
    "핵심 제품/서비스",
    "고객 구매 이유",
    "경쟁 우위/대체가능성",
    "활용 및 확장 산업",
    "진입 부담/장벽",
    "R&D 강도",
]

TECH_STOPWORDS = {
    "상기", "관한", "관련", "포함", "포함하는", "구비", "구비하는", "이용", "이용한", "이를", "통해",
    "발명", "본 발명", "발명은", "것이다", "제공", "제공하는", "형성", "형성하는", "방법", "장치", "시스템",
    "주식회사", "반도체", "소자", "기판", "모듈", "부재", "구성", "처리", "제어", "사용", "가능", "기술",
    "method", "device", "system", "apparatus", "using", "including", "include", "provided", "thereof", "comprising",
}

COMMERCIALIZATION_TERMS = ["고객", "고객사", "채택", "수주", "납품", "공급", "레퍼런스", "승인", "계약", "양산 적용"]
PRODUCTION_TERMS = ["양산", "생산", "공정", "수율", "라인", "설비", "검증", "품질", "qualification", "mass production"]
REVENUE_TERMS = ["매출", "수익", "영업이익", "마진", "원가", "비중", "성장", "asp", "revenue"]
FCF_TERMS = ["fcf", "현금흐름", "영업현금", "capex", "투자", "차입", "상환", "free cash flow"]

FOCAL_DIR_TO_NAME = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "LTC",
}


def inject_high_quality_tech_section(
    report: str,
    *,
    opinions: list[dict[str, Any]] | None = None,
    company_dir: str = "",
    company: str = "",
) -> str:
    """
    Chair 최종 보고서 저장 직전에 기존 `### 기술 분석` 섹션을 고도화된 기술/ML 섹션으로 교체한다.

    포함 블록:
    1) Tech-to-Value Bridge 판정과 점수 충돌 정리
    2) 기술 포지션 요약
    3) KIPRIS/IP 정량 신호
    4) 특허 KMeans
    5) 5개 focal 기업 cosine similarity
    6) 30개 reference universe KMeans peer group
    7) UMAP/PCA 2D peer map
    8) 사업화 연결 체크
    9) Chair 반영 원칙
    10) 엑셀 틀 기반 직접 추출 결과
    """
    opinions = opinions or []
    tech_op = next((x for x in opinions if _agent_name(x) == "tech"), {})

    section = build_high_quality_tech_section(
        tech_op,
        opinions=opinions,
        company_dir=company_dir,
        company=company,
    )

    report = _sanitize_links(report or "")
    report = report.replace(
        "**재무 분석:** Tech-to-Value Bridge",
        "**기술-가치 연결 검증:** Tech-to-Value Bridge",
    )
    report = report.replace(
        "**재무 분석:** Tech-to-Value",
        "**기술-가치 연결 검증:** Tech-to-Value",
    )
    report = _clarify_bridge_score_in_core(report)

    pattern = r"### 기술 분석\s*.*?(?=\n### 이슈 분석|\n### 거시경제|\n## 5\.|\Z)"
    if re.search(pattern, report, flags=re.DOTALL):
        return re.sub(pattern, lambda _: section, report, count=1, flags=re.DOTALL)
    return report.rstrip() + "\n\n" + section + "\n"


def build_high_quality_tech_section(
    tech_op: dict[str, Any] | None,
    *,
    opinions: list[dict[str, Any]] | None = None,
    company_dir: str,
    company: str,
) -> str:
    opinions = opinions or []
    tech_op = tech_op or {}
    company = company or _get_company(tech_op) or FOCAL_DIR_TO_NAME.get(company_dir, company_dir) or "해당 기업"

    files = _load_outputs(company_dir)
    text = _useful_text(tech_op, files)

    bridge = _extract_bridge(files, text, opinions)
    raw_score = bridge.get("tech_agent_raw_score")
    auditor_score = bridge.get("auditor_adjusted_score")
    finance_overlay_score = bridge.get("finance_overlay_score")
    final_score = bridge.get("final_chair_tech_score")
    raw_grade = _grade(str(bridge.get("raw_grade") or "")) or "COMMERCIALIZATION_WATCH"
    final_grade = _grade(str(bridge.get("final_grade") or "")) or raw_grade
    final_label, final_meaning, final_policy = GRADE_GUIDE.get(final_grade, GRADE_GUIDE["COMMERCIALIZATION_WATCH"])

    opinion = str(tech_op.get("opinion") or tech_op.get("recommendation") or "보유").strip()
    if opinion not in {"매수", "보유", "매도"}:
        opinion = "보유"

    core = _terms(
        text,
        [
            "WLP", "FOWLP", "FO-WLP", "FOPLP", "FO-PLP", "PLP", "Bumping", "Flip Chip", "SiP",
            "TC bonder", "TC 본더", "비전플레이스먼트", "전구체", "과산화수소", "식각", "세정", "박리",
            "첨단 패키징", "후공정", "반도체 패키징", "반도체 장비", "반도체 소재", "재배선", "테스트", "전자재료", "고순도", "정밀합성",
        ],
        7,
    )
    products = _terms(
        text,
        [
            "WLP", "FOWLP", "FO-WLP", "FOPLP", "FO-PLP", "Bumping", "SiP", "TC 본더", "비전플레이스먼트",
            "PMIC", "DDI", "SoC", "AP", "RF", "CIS", "과산화수소", "전구체", "식각액", "세정액", "박리액", "전자재료",
        ],
        8,
    )
    apps = _terms(
        text,
        ["AI", "HPC", "HBM", "서버", "스마트폰", "웨어러블", "자동차", "5G", "모바일", "CIS", "디스플레이", "반도체", "배터리"],
        7,
    )

    patents = _patent_metrics(files, text)
    representatives = _representative_patents(files, text)

    return f"""### 기술 분석
- **의견:** {opinion}

#### 1) Tech-to-Value Bridge 판정
- **Tech Agent 원점수:** {_score_text(raw_score)} / 원판정 **{raw_grade}({GRADE_GUIDE.get(raw_grade, GRADE_GUIDE['COMMERCIALIZATION_WATCH'])[0]})**
- **Auditor 보수 반영 점수:** {_score_text(auditor_score)}
- **Finance/credit overlay 보수 점수:** {_score_text(finance_overlay_score)}
- **Chair 최종 기술 반영 점수:** **{_score_text(final_score)}**
- **최종 Bridge 판정:** **{final_grade}({final_label})**
- **점수 충돌 정리:** Tech Agent의 기술 원점수는 기술성·IP 포트폴리오 중심 점수이고, Finance/credit overlay 점수는 수익성·현금흐름·재무안정성까지 반영한 보수 점수입니다. 따라서 최종 Chair 반영에는 더 보수적인 점수와 판정을 우선 사용합니다.
- **COMMERCIALIZATION_WATCH = 사업화 추적형:** 기술성은 확인되지만 고객 채택·양산·매출 전환·FCF 개선까지 이어지는 연결 고리를 계속 추적해야 하는 상태입니다.
- **TECH_FINANCE_GAP = 기술-재무 괴리형:** 기술 포트폴리오는 있으나 수익성·현금흐름·재무안정성으로의 전환 근거가 약해 기술 점수를 보수적으로 반영해야 하는 상태입니다.

#### 2) 기술 포지션 요약
{company}는 원천 자료 기준 **{', '.join(core) if core else '핵심 기술 키워드 확인 제한'}**을 핵심 기술 축으로 보유한 기업으로 정리됩니다. 이 기술 축은 **{', '.join(products) if products else '제품·공정 축 추가 확인 필요'}**와 연결되며, 적용 시장은 **{', '.join(apps) if apps else '적용 산업 추가 확인 필요'}**로 해석됩니다. 다만 기술 포지션은 단독 투자 근거가 아니라 **고객 채택 → 양산 → 매출 전환 → FCF/현금흐름 개선**까지 확인될 때 가치평가 가산 요인으로 반영합니다.

#### 3) KIPRIS/특허 기반 IP 정량 신호
{_patent_signal_lines(patents, representatives)}

{_format_tech_ml_signal_block(company_dir)}

{_format_tech_peer_similarity_block(company_dir)}

{_format_reference_peer_cluster_block(company_dir)}

{_format_peer_map_block(company_dir)}

#### 8) 사업화 연결 체크
| 체크 항목 | 현재 판정 | 근거 요약 | 비고 |
|---|---|---|---|
{_commercialization_table(_commercialization_rows(text, files))}

#### 9) Chair 반영 원칙
- 기술 우위는 **긍정 보조 근거**로 반영하되, 고객 채택·양산·매출 전환·FCF 개선 근거가 부족하면 단독 매수 근거로 과대평가하지 않습니다.
- 특허 수, 기술 키워드 빈도, 문서 수는 기술 지속성·진입장벽의 보조 지표이며, 실제 가치평가 반영은 수익성·현금흐름·재무 안정성과 연결될 때만 강화합니다.
- 특허 KMeans는 기업 내부 특허 포트폴리오 구조를 보여주고, Cosine Similarity는 5개 focal 기업 간 기술 유사도를 보여줍니다.
- Reference Universe KMeans와 UMAP 2D Peer Map은 30개 비교군 안에서 현재 기업의 기술 peer 위치를 보여주는 ML 근거입니다.
- **적용 정책:** {final_policy}

#### 10) 엑셀 틀 기반 기술평가 직접 추출 결과
{_excel_frame_tables(files)}""".strip()


def _load_outputs(company_dir: str) -> dict[str, Any]:
    root = Path.cwd()
    out = root / "workspace" / "outputs"
    packet_dir = root / "workspace" / "packets" / company_dir
    ml_universe = root / "workspace" / "ml_universe"
    paths = {
        "hq_md": out / f"{company_dir}_tech_high_quality_report.md",
        "patent_json": out / f"{company_dir}_tech_patent_evidence.json",
        "patent_md": out / f"{company_dir}_tech_patent_evidence.md",
        "tech_ml_json": out / f"{company_dir}_tech_ml_signal.json",
        "bridge_json": out / f"{company_dir}_tech_to_value_inputs.json",
        "bridge_json_legacy": out / f"{company_dir}_tech_to_value_bridge.json",
        "bridge_md": out / f"{company_dir}_tech_to_value_bridge.md",
        "packet_json": out / f"{company_dir}_tech_agent_packet.json",
        "chair_packet_json": packet_dir / "tech.json",
        "peer_cluster_packet": packet_dir / "tech_peer_cluster.json",
        "peer_map_packet": packet_dir / "tech_peer_map.json",
        "peer_similarity_json": out / "tech_peer_similarity.json",
        "reference_cluster_json": ml_universe / "tech_peer_clusters.json",
        "peer_map_json": ml_universe / "tech_peer_map.json",
    }
    result: dict[str, Any] = {}
    for key, path in paths.items():
        if not path.exists():
            continue
        result[key] = _read_any(path)
    return result


def _read_any(path: Path) -> Any:
    raw = ""
    for enc in ["utf-8-sig", "utf-8", "cp949", "euc-kr"]:
        try:
            raw = path.read_text(encoding=enc, errors="replace")
            break
        except Exception:
            continue
    if path.suffix.lower() == ".json":
        try:
            return json.loads(raw)
        except Exception:
            return {}
    return raw


def _useful_text(tech_op: dict[str, Any], files: dict[str, Any]) -> str:
    chunks: list[str] = []

    def walk(x: Any, key: str = "") -> None:
        low_key = key.lower()
        if any(bad in low_key for bad in ["mandatory", "overlay", "valuation_credit", "ml_crosscheck"]):
            return
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, str(k))
        elif isinstance(x, list):
            for v in x[:300]:
                walk(v, key)
        elif isinstance(x, (str, int, float)):
            s = str(x)
            if s and not _mojibake(s):
                chunks.append(s)

    walk(tech_op)
    for key in ["hq_md", "patent_md", "bridge_md", "patent_json", "tech_ml_json", "packet_json", "chair_packet_json"]:
        value = files.get(key)
        if isinstance(value, str):
            chunks.append(value)
        elif isinstance(value, (dict, list)):
            walk(value, key)
    return "\n".join(chunks)[:250000]


def _extract_bridge(files: dict[str, Any], text: str, opinions: list[dict[str, Any]]) -> dict[str, Any]:
    bridge_json = files.get("bridge_json") if isinstance(files.get("bridge_json"), dict) else {}
    legacy = files.get("bridge_json_legacy") if isinstance(files.get("bridge_json_legacy"), dict) else {}
    packet = files.get("packet_json") if isinstance(files.get("packet_json"), dict) else files.get("chair_packet_json") if isinstance(files.get("chair_packet_json"), dict) else {}
    merged = {**legacy, **bridge_json}

    raw_score = _first_number(
        merged,
        ["tech_agent_raw_score", "raw_score", "tech_score", "bridge_score", "score", "tech_to_value_score"],
    )
    auditor_score = _first_number(
        merged,
        ["auditor_adjusted_score", "adjusted_score", "conservative_score", "auditor_score", "final_score"],
    )
    raw_grade = _grade(str(_first_value(merged, ["grade", "bridge_grade", "label", "tech_ml_label"]) or ""))

    packet_text = json.dumps(packet, ensure_ascii=False) if packet else ""
    all_text = "\n".join([text, packet_text, str(files.get("bridge_md") or "")])
    parsed_score = _parse_bridge_score(all_text)
    parsed_grade = _parse_bridge_grade(all_text)

    if raw_score is None:
        raw_score = parsed_score
    if auditor_score is None:
        auditor_score = parsed_score or raw_score
    if not raw_grade:
        raw_grade = parsed_grade or "COMMERCIALIZATION_WATCH"

    finance_score, finance_grade = _finance_overlay_bridge(opinions)
    scores = [x for x in [raw_score, auditor_score, finance_score] if _float(x) is not None]
    final_score = min(scores) if scores else raw_score or auditor_score
    final_grade = raw_grade
    if finance_score is not None and final_score == finance_score:
        final_grade = finance_grade or "TECH_FINANCE_GAP"
    elif auditor_score is not None and raw_score is not None and _float(auditor_score) < _float(raw_score):
        final_grade = parsed_grade or raw_grade

    if final_grade == "COMMERCIALIZATION_WATCH" and _float(final_score) is not None and _float(final_score) < 70:
        final_grade = "TECH_FINANCE_GAP"

    return {
        "tech_agent_raw_score": raw_score,
        "auditor_adjusted_score": auditor_score,
        "finance_overlay_score": finance_score,
        "raw_grade": raw_grade,
        "finance_overlay_grade": finance_grade,
        "final_chair_tech_score": final_score,
        "final_grade": final_grade,
    }


def _first_number(d: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        if key in d:
            value = _float(d.get(key))
            if value is not None:
                return value
    for v in d.values():
        if isinstance(v, dict):
            found = _first_number(v, keys)
            if found is not None:
                return found
    return None


def _first_value(d: dict[str, Any], keys: list[str]) -> Any:
    for key in keys:
        if key in d and d.get(key) not in (None, ""):
            return d.get(key)
    for v in d.values():
        if isinstance(v, dict):
            found = _first_value(v, keys)
            if found not in (None, ""):
                return found
    return None


def _finance_overlay_bridge(opinions: list[dict[str, Any]]) -> tuple[float | None, str]:
    score: float | None = None
    grade = ""
    for op in opinions or []:
        if _agent_name(op) == "tech":
            continue
        blob = json.dumps(op, ensure_ascii=False)
        if "Tech-to-Value" not in blob and "Bridge" not in blob:
            continue
        s = _parse_bridge_score(blob)
        g = _parse_bridge_grade(blob)
        if s is not None:
            if score is None or s < score:
                score = s
                grade = g
    return score, grade


def _parse_bridge_score(text: str) -> float | None:
    patterns = [
        r"Tech[- ]to[- ]Value\s*Bridge\s*Score[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)\s*/\s*100",
        r"Bridge\s*Score[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)\s*/\s*100",
        r"Tech[- ]to[- ]Value[^0-9]{0,40}([0-9]+(?:\.[0-9]+)?)\s*/\s*100",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            return _float(m.group(1))
    return None


def _parse_bridge_grade(text: str) -> str:
    for grade in GRADE_GUIDE:
        if grade in text:
            return grade
    m = re.search(r"판정\s*[=:]\s*([A-Z_]+)", text)
    return _grade(m.group(1)) if m else ""


def _grade(x: str) -> str:
    x = str(x or "").upper().strip()
    for key in GRADE_GUIDE:
        if key in x:
            return key
    return ""


def _patent_metrics(files: dict[str, Any], text: str) -> dict[str, Any]:
    data = files.get("patent_json") if isinstance(files.get("patent_json"), dict) else {}
    ml = files.get("tech_ml_json") if isinstance(files.get("tech_ml_json"), dict) else {}
    merged = {**data, **ml}

    keys = {
        "normalized_records": ["normalized_patent_records", "normalized_records", "total_records", "record_count"],
        "company_matched": ["company_matched_patents", "company_match_count", "applicant_matched_count", "matched_patents"],
        "registered": ["registered_patents", "registered_count", "registration_count"],
        "alive": ["alive_patents", "valid_patents", "active_patents", "alive_count"],
        "recent_5y": ["recent_5y_patents", "recent_5_year_patents", "recent_patents", "recent_5y_count"],
        "ipc_cpc": ["ipc_cpc_count", "ipc_cpc_unique_count", "ipc_count", "technology_class_count"],
        "h01l": ["h01l_patents", "h01l_count", "semiconductor_ipc_patents"],
        "keyword_matches": ["keyword_match_count", "patent_keyword_matches", "tech_keyword_matches"],
    }
    out: dict[str, Any] = {}
    for out_key, candidates in keys.items():
        out[out_key] = _first_number(merged, candidates)

    fallback_patterns = {
        "normalized_records": r"정규화[^0-9]{0,20}([0-9,]+)\s*건",
        "company_matched": r"회사[^0-9]{0,20}매칭[^0-9]{0,20}([0-9,]+)\s*건",
        "registered": r"등록\s*특허[^0-9]{0,20}([0-9,]+)\s*건",
        "alive": r"존속\s*가능\s*특허[^0-9]{0,20}([0-9,]+)\s*건",
        "recent_5y": r"최근\s*5년\s*특허[^0-9]{0,20}([0-9,]+)\s*건",
        "ipc_cpc": r"IPC/CPC[^0-9]{0,20}([0-9,]+)\s*개",
        "h01l": r"H01L[^0-9]{0,20}([0-9,]+)\s*건",
        "keyword_matches": r"특허-기술\s*키워드\s*매칭[^0-9]{0,20}([0-9,]+)\s*회",
    }
    for key, pat in fallback_patterns.items():
        if out.get(key) is None:
            m = re.search(pat, text)
            if m:
                out[key] = _float(m.group(1).replace(",", ""))

    out["year_range"] = _first_value(merged, ["year_range", "patent_year_range", "application_year_range"]) or _parse_year_range(text)
    return out


def _parse_year_range(text: str) -> str:
    m = re.search(r"(19\d{2}|20\d{2})\s*[~\-–]\s*(20\d{2})", text)
    return f"{m.group(1)}~{m.group(2)}년" if m else "확인 제한"


def _representative_patents(files: dict[str, Any], text: str) -> list[str]:
    reps: list[str] = []
    for source in [files.get("patent_json"), files.get("tech_ml_json")]:
        if not isinstance(source, dict):
            continue
        for key in ["representative_patents", "sample_patents", "top_patents"]:
            vals = source.get(key)
            if isinstance(vals, list):
                for item in vals:
                    if isinstance(item, dict):
                        title = item.get("title") or item.get("invention_title") or item.get("name")
                    else:
                        title = str(item)
                    title = _clean(title, 80)
                    if title and title not in reps and not _is_noise_term(title):
                        reps.append(title)
    if not reps:
        for m in re.finditer(r"[가-힣A-Za-z0-9\s·/\-]{6,80}(?:제조방법|패키지|장치|방법|시스템)", text):
            title = _clean(m.group(0), 80)
            if title and title not in reps:
                reps.append(title)
            if len(reps) >= 5:
                break
    return reps[:5]


def _patent_signal_lines(p: dict[str, Any], reps: list[str]) -> str:
    lines = [
        f"- **정규화 특허 레코드:** {_num_or_limit(p.get('normalized_records'), '건')}",
        f"- **회사 출원인/권리자 매칭:** {_num_or_limit(p.get('company_matched'), '건')}",
        f"- **등록 특허:** {_num_or_limit(p.get('registered'), '건')}",
        f"- **존속 가능 특허:** {_num_or_limit(p.get('alive'), '건')}",
        f"- **최근 5년 특허:** {_num_or_limit(p.get('recent_5y'), '건')}",
        f"- **IPC/CPC 기술분류:** {_num_or_limit(p.get('ipc_cpc'), '개')}",
        f"- **H01L 반도체 핵심 IPC 특허:** {_num_or_limit(p.get('h01l'), '건')}",
        f"- **특허-기술 키워드 매칭:** {_num_or_limit(p.get('keyword_matches'), '회')}",
        f"- **특허 포트폴리오 범위:** {p.get('year_range') or '확인 제한'}",
        f"- **대표 특허 예시:** {', '.join(reps) if reps else '대표 특허명 추가 확인 필요'}",
        "- **해석:** 특허 포트폴리오는 기술 지속성·진입장벽의 보조 근거입니다. 다만 특허 수 자체가 매출 성장이나 주가 상승을 직접 의미하지 않으므로 사업화 연결 지표와 함께 봅니다.",
    ]
    return "\n".join(lines)


def _format_tech_ml_signal_block(company_dir: str) -> str:
    path = Path.cwd() / "workspace" / "outputs" / f"{company_dir}_tech_ml_signal.json"
    signal = _read_any(path) if path.exists() else {}
    if not isinstance(signal, dict) or not signal:
        return f"#### 4) Tech ML 기반 특허 KMeans 클러스터링 결과\n- **상태:** Tech ML 산출물을 확인하지 못했습니다.\n- **필요 실행:** `python .\\scripts\\run_tech_ml_signal.py --all` 실행 후 Chair를 다시 실행하세요.\n"

    clustering = signal.get("clustering") if isinstance(signal.get("clustering"), dict) else {}
    clusters = clustering.get("clusters") if isinstance(clustering.get("clusters"), list) else []
    total = _safe_int(signal.get("normalized_patent_records")) or sum(_safe_int(c.get("size")) for c in clusters if isinstance(c, dict))
    method = _clean(clustering.get("method") or signal.get("model_info", {}).get("algorithm") or "KMeans", 80)
    feature_count = _safe_int(clustering.get("feature_count"))
    hhi = clustering.get("technology_concentration_index", "확인 제한")

    lines = [
        "#### 4) Tech ML 기반 특허 KMeans 클러스터링 결과",
        f"- **ML 방식:** {method}",
        f"- **Tech ML 판정:** **{_clean(signal.get('tech_ml_label') or '미확인', 80)}**",
        f"- **Patent ML Score:** **{signal.get('patent_ml_score', '확인 제한')} / 100**",
        f"- **Commercialization Score:** **{signal.get('commercialization_score', '확인 제한')} / 100**",
        f"- **분석 특허 수:** **{total if total else '확인 제한'}건**",
        f"- **KMeans 클러스터 수:** **{clustering.get('cluster_count') or len(clusters) or '확인 제한'}개**",
        f"- **TF-IDF 피처 수:** **{feature_count if feature_count else '확인 제한'}개**",
        f"- **기술 집중도 HHI:** **{hhi}**",
        "",
        "| 클러스터 | 특허 수 | 비중 | 핵심 용어 | 대표 특허 예시 | 기술적 해석 | 비고 |",
        "|---:|---:|---:|---|---|---|---|",
    ]
    if not clusters:
        lines.append("| - | - | - | 확인 제한 | 확인 제한 | KMeans 결과 없음 | tech_ml_signal.json 확인 필요 |")
    else:
        for rank, cluster in enumerate(clusters[:10], 1):
            if not isinstance(cluster, dict):
                continue
            size = _safe_int(cluster.get("size"))
            terms = _filter_terms(cluster.get("top_terms") or cluster.get("terms") or [])
            samples = _filter_samples(cluster.get("sample_titles") or cluster.get("representative_titles") or cluster.get("samples") or [])
            meaning = _infer_cluster_meaning(terms, samples)
            note = _cluster_note(rank, size, total, meaning)
            lines.append(f"| {cluster.get('cluster_id', rank - 1)} | {size} | {_percent(size, total)} | {_cell(', '.join(terms[:8]), 90)} | {_cell('<br>'.join(samples[:3]), 140)} | {_cell(meaning, 90)} | {_cell(note, 90)} |")
    lines += [
        "",
        "##### 4-1. KMeans 결과의 Chair 반영 방식",
        "- 특허 클러스터의 규모와 핵심 용어는 기술 포트폴리오의 중심축을 설명하는 근거로 반영합니다.",
        "- `상기`, `관한`, `포함하는` 등 특허 관용어는 stopword로 제거해 기술적으로 의미 있는 용어만 표에 남깁니다.",
        "- 클러스터 수나 특허 수는 곧바로 매출·주가 상승을 의미하지 않으므로 고객 채택·양산·매출 전환·FCF 개선 근거가 없으면 보수적으로 반영합니다.",
    ]
    return "\n".join(lines).strip()


def _format_tech_peer_similarity_block(company_dir: str) -> str:
    path = Path.cwd() / "workspace" / "outputs" / "tech_peer_similarity.json"
    data = _read_any(path) if path.exists() else {}
    if not isinstance(data, dict) or not data:
        return "#### 5) 5개 기업 간 Cosine Similarity 기술 유사도\n- **상태:** `tech_peer_similarity.json`을 확인하지 못했습니다. `python .\\scripts\\run_tech_peer_similarity.py` 실행이 필요합니다.\n"

    companies = data.get("companies") if isinstance(data.get("companies"), list) else []
    matrix = data.get("similarity_matrix") if isinstance(data.get("similarity_matrix"), list) else []
    nearest = data.get("nearest_peers") if isinstance(data.get("nearest_peers"), list) else []
    current = next((x for x in nearest if x.get("company_dir") == company_dir), {})

    lines = [
        "#### 5) 5개 기업 간 Cosine Similarity 기술 유사도",
        f"- **분석 방법:** {_clean(data.get('method') or 'TF-IDF + Cosine Similarity', 100)}",
        f"- **분석 기업 수:** **{len(companies) or '확인 제한'}개**",
    ]
    if current:
        lines += [
            "",
            "##### 5-1. 현재 기업의 가장 가까운 기술 peer",
            f"- **현재 기업:** {FOCAL_DIR_TO_NAME.get(company_dir, company_dir)}",
            f"- **가장 가까운 peer:** {_clean(current.get('nearest_peer_company') or current.get('nearest_peer') or '확인 제한', 80)}",
            f"- **기술 유사도:** **{_similarity_percent(current)}**",
            f"- **자동 기술군 해석:** {_clean(current.get('domain') or current.get('technology_domain') or '기술군 자동판정 제한', 100)}",
        ]

    if matrix:
        company_labels = [_clean(c.get("company") or c.get("company_name") or c.get("company_dir"), 30) for c in companies]
        if not company_labels and matrix and isinstance(matrix[0], dict):
            company_labels = [_clean(r.get("company"), 30) for r in matrix]
        lines += ["", "##### 5-2. 5개 기업 기술 유사도 Matrix"]
        if matrix and isinstance(matrix[0], dict):
            keys = [k for k in matrix[0].keys() if k not in {"company", "company_dir"}]
            lines.append("| 기업 | " + " | ".join(keys) + " |")
            lines.append("|---" + "|---:" * len(keys) + "|")
            for row in matrix[:8]:
                lines.append("| " + _cell(row.get("company") or row.get("company_dir"), 40) + " | " + " | ".join(_fmt4(row.get(k)) for k in keys) + " |")
        elif isinstance(matrix, list) and matrix and isinstance(matrix[0], list):
            labels = company_labels or [str(i) for i in range(len(matrix))]
            lines.append("| 기업 | " + " | ".join(labels) + " |")
            lines.append("|---" + "|---:" * len(labels) + "|")
            for label, row in zip(labels, matrix):
                lines.append("| " + label + " | " + " | ".join(_fmt4(x) for x in row) + " |")

    if nearest:
        lines += ["", "##### 5-3. 기업별 nearest peer 요약", "| 기업 | 가장 가까운 peer | 유사도 | 기술군 해석 |", "|---|---|---:|---|"]
        for row in nearest[:10]:
            lines.append(f"| {_cell(row.get('company') or row.get('company_name') or row.get('company_dir'), 40)} | {_cell(row.get('nearest_peer_company') or row.get('nearest_peer'), 40)} | {_similarity_percent(row)} | {_cell(row.get('domain') or row.get('technology_domain') or '-', 80)} |")

    lines.append("\n- **해석:** Cosine Similarity는 특허·기술 텍스트 포트폴리오의 유사도를 보여주는 지표이며, 주가 방향이나 재무 건전성을 직접 의미하지 않습니다.")
    return "\n".join(lines).strip()


def _format_reference_peer_cluster_block(company_dir: str) -> str:
    packet_path = Path.cwd() / "workspace" / "packets" / company_dir / "tech_peer_cluster.json"
    packet = _read_any(packet_path) if packet_path.exists() else {}
    if not isinstance(packet, dict) or not packet:
        return "#### 6) Reference Universe 기반 Company-level KMeans Peer Group\n- **상태:** `tech_peer_cluster.json`을 확인하지 못했습니다. `python .\\scripts\\run_tech_peer_clustering.py` 실행 후 Chair를 다시 실행하세요.\n"

    assign = packet.get("company_assignment") if isinstance(packet.get("company_assignment"), dict) else {}
    summary = packet.get("cluster_summary") if isinstance(packet.get("cluster_summary"), dict) else {}
    peers = packet.get("nearest_peers_same_cluster") if isinstance(packet.get("nearest_peers_same_cluster"), list) else []
    lines = [
        "#### 6) Reference Universe 기반 Company-level KMeans Peer Group",
        "| 항목 | 내용 |",
        "|---|---|",
        "| Reference universe | valuation/credit ML overlay 기반 30개 반도체 딥테크 후보군 |",
        f"| 현재 기업 cluster | Cluster {assign.get('cluster_id', '확인 제한')} |",
        f"| Cluster 이름 | {_cell(summary.get('cluster_name') or assign.get('cluster_name') or '기술 포트폴리오 혼합 cluster', 100)} |",
        f"| Cluster 기업 수 | {summary.get('member_count', '확인 제한')}개 / focal {summary.get('focal_count', '확인 제한')}개 / reference {summary.get('reference_count', '확인 제한')}개 |",
        f"| Silhouette Score | {packet.get('silhouette_score', '확인 제한')} |",
        f"| 주요 기술 용어 | {_cell(', '.join(_filter_terms(summary.get('top_terms') or [])[:10]), 160)} |",
        f"| 주요 분야 | {_cell(', '.join(summary.get('top_sector_labels') or []), 160)} |",
        "| 해석 | 30개 reference universe 안에서 현재 기업이 어느 기술 peer group에 속하는지 보여주는 company-level KMeans 결과입니다. |",
        "",
        "##### 6-1. 같은 cluster 내 nearest peer",
        "| Peer 기업 | 유사도 | 역할 | 해석 |",
        "|---|---:|---|---|",
    ]
    if peers:
        for peer in peers[:8]:
            lines.append(f"| {_cell(peer.get('company_name'), 50)} | {_fmt_percent(peer.get('similarity'))} | {'focal' if int(peer.get('is_focal', 0) or 0) == 1 else 'reference'} | {_cell(peer.get('sector_label') or '동일 기술 cluster 내 비교군', 90)} |")
    else:
        lines.append("| - | - | - | 같은 cluster 내 peer 확인 제한 |")
    return "\n".join(lines).strip()


def _format_peer_map_block(company_dir: str) -> str:
    packet_path = Path.cwd() / "workspace" / "packets" / company_dir / "tech_peer_map.json"
    packet = _read_any(packet_path) if packet_path.exists() else {}
    if not isinstance(packet, dict) or not packet:
        return "#### 7) UMAP 2D Tech Peer Map\n- **상태:** `tech_peer_map.json`을 확인하지 못했습니다. `python .\\scripts\\run_tech_peer_map.py` 실행 후 Chair를 다시 실행하세요.\n"

    point = packet.get("company_point") if isinstance(packet.get("company_point"), dict) else {}
    summary = packet.get("cluster_map_summary") if isinstance(packet.get("cluster_map_summary"), dict) else {}
    png_path = packet.get("png_path") or "workspace/ml_universe/tech_peer_map.png"
    method = packet.get("method") or ("UMAP" if packet.get("umap_used") else "PCA fallback")
    lines = [
        "#### 7) UMAP 2D Tech Peer Map",
        "| 항목 | 내용 |",
        "|---|---|",
        f"| 차원축소 방식 | {method} |",
        f"| UMAP 사용 여부 | {packet.get('umap_used', '확인 제한')} |",
        f"| 현재 기업 좌표 | x={point.get('umap_x', '확인 제한')}, y={point.get('umap_y', '확인 제한')} |",
        f"| 현재 기업 cluster | Cluster {point.get('cluster_id', '확인 제한')} |",
        f"| 해당 cluster 중심 | x={summary.get('centroid_x', '확인 제한')}, y={summary.get('centroid_y', '확인 제한')} |",
        f"| 2D map 파일 | `{png_path}` |",
        "| 해석 | 가까운 점은 특허·기술 텍스트 포트폴리오가 유사하다는 의미이며, 재무 안정성이나 주가 방향을 직접 의미하지 않습니다. |",
    ]
    return "\n".join(lines).strip()


def _commercialization_rows(text: str, files: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    checks = [
        ("고객 채택", COMMERCIALIZATION_TERMS),
        ("양산", PRODUCTION_TERMS),
        ("매출 전환", REVENUE_TERMS),
        ("FCF/현금흐름", FCF_TERMS),
    ]
    for item, terms in checks:
        hits = [t for t in terms if t.lower() in text.lower()]
        evidence = _extract_sentence(text, hits[:3]) if hits else "직접 근거 확인 제한"
        if len(hits) >= 3:
            status = "부분 확인"
            note = "고객명·기간·제품별 수치 확인 필요"
        elif hits:
            status = "약한 신호"
            note = "키워드는 있으나 정량 근거 보강 필요"
        else:
            status = "확인 제한"
            note = "DART/IR/수주공시/제품별 매출/현금흐름 자료 필요"
        rows.append({"item": item, "status": status, "evidence": evidence, "note": note})
    return rows


def _commercialization_table(rows: list[dict[str, str]]) -> str:
    return "\n".join(f"| {r['item']} | {r['status']} | {_cell(r['evidence'], 120)} | {_cell(r['note'], 90)} |" for r in rows)


def _excel_frame_tables(files: dict[str, Any]) -> str:
    packet = files.get("packet_json") if isinstance(files.get("packet_json"), dict) else files.get("chair_packet_json")
    categories = packet.get("categories") if isinstance(packet, dict) else []
    if not isinstance(categories, list) or not categories:
        hq_md = str(files.get("hq_md") or "").strip()
        if hq_md:
            extracted = _extract_hq_markdown_frame(hq_md)
            if extracted:
                return _repair_zero_markdown(extracted)
        return "- high_quality_report.py 산출물이 없어 엑셀 틀 기반 세부 항목은 확인 제한입니다."

    by_cat = {_clean(sec.get("category"), 80): sec for sec in categories if isinstance(sec, dict)}
    ordered = [by_cat[c] for c in SECTION_ORDER if c in by_cat]
    ordered += [sec for sec in categories if isinstance(sec, dict) and _clean(sec.get("category"), 80) not in SECTION_ORDER]

    blocks: list[str] = []
    for idx, sec in enumerate(ordered, 1):
        category = _clean(sec.get("category"), 80) or f"기술평가 축 {idx}"
        raw_score = _float(sec.get("score"))
        items = sec.get("items") if isinstance(sec.get("items"), list) else []
        adjusted_score, score_reason = _calibrated_axis_score(category, raw_score, items)
        result = _clean(sec.get("result_sentence") or sec.get("result") or sec.get("summary"), 500)
        if _needs_zero_repair(result, items):
            result = _make_category_result_sentence(category, items)
        if not result:
            result = _make_category_result_sentence(category, items)

        blocks.append(f"##### 10-{idx}. {category}")
        blocks.append(f"- **원점수:** {_axis_score_text(raw_score)}")
        blocks.append(f"- **Chair 보수 보정 점수:** **{adjusted_score:.1f}/5** ({score_reason})")
        blocks.append(f"- **요약 문장:** {result}")
        blocks.append("| 항목명 | 정량화 결과 | 핵심 근거 문장 | 출처 | 비고 |")
        blocks.append("|---|---|---|---|---|")
        if not items:
            blocks.append("| 항목 확인 제한 | 정량 수치 직접 미확인 | 원천 근거 추가 필요 | - | DART/IR/KIPRIS 원천 필요 |")
        for item in items[:8]:
            if isinstance(item, dict):
                blocks.append(_excel_item_row(item))
        blocks.append("")
    return "\n".join(blocks).strip()


def _excel_item_row(item: dict[str, Any]) -> str:
    name = _clean(item.get("item_name") or item.get("name") or "항목명 확인 제한", 80)
    metrics = item.get("quant_metrics") if isinstance(item.get("quant_metrics"), list) else []
    metric_text = "; ".join(_format_metric(m) for m in metrics[:4] if isinstance(m, dict) and _format_metric(m))
    evs = item.get("evidence") if isinstance(item.get("evidence"), list) else []
    ev = next((e for e in evs if isinstance(e, dict) and not _mojibake(str(e.get("snippet") or ""))), {})
    snippet = _clean(ev.get("snippet") if ev else "", 180) or "핵심 원천 근거 추가 필요"
    source = _clean((ev.get("source_url") or ev.get("url") or ev.get("source_path") or ev.get("path") or ev.get("source_title")) if ev else "", 120) or "-"
    if metric_text:
        note = "정량화 가능"
    else:
        metric_text = "정량 수치 직접 미확인"
        note = "비고: 수치·단위·기간이 있는 DART/IR/KIPRIS 원천 필요"
    if not ev:
        note += "; 근거 보완 필요"
    return f"| {_cell(name, 50)} | {_cell(metric_text, 100)} | {_cell(snippet, 140)} | {_cell(source, 100)} | {_cell(note, 100)} |"


def _format_metric(m: dict[str, Any]) -> str:
    name = _clean(m.get("metric_name") or m.get("name"), 50)
    value = _clean(m.get("value"), 60)
    unit = _clean(m.get("unit"), 20)
    detail = m.get("detail")
    suffix = ""
    if isinstance(detail, dict) and detail:
        suffix = "(" + ", ".join(f"{_clean(k, 20)} {v}" for k, v in list(detail.items())[:4]) + ")"
    elif isinstance(detail, list) and detail:
        suffix = "(" + ", ".join(_clean(x, 20) for x in detail[:4]) + ")"
    if not name and not value:
        return ""
    return f"{name} {value}{unit}{suffix}".strip()


def _calibrated_axis_score(category: str, raw_score: float | None, items: list[Any]) -> tuple[float, str]:
    base = raw_score if raw_score is not None else 3.0
    has_metrics = _positive_metric_count(items) > 0
    cat = category.lower()
    cap = 4.2
    reason = "원점수 만점 남발 방지를 위해 Chair 단계에서 근거 강도별 보수 상한 적용"
    if "대표" in category:
        cap = 4.3 if has_metrics else 3.8
    elif "제품" in category:
        cap = 4.1 if has_metrics else 3.6
    elif "고객" in category:
        cap = 3.4 if has_metrics else 3.0
        reason = "고객명·수주·납품·승인 등 사업화 직접 근거가 제한되어 보수 반영"
    elif "경쟁" in category:
        cap = 3.8 if has_metrics else 3.3
    elif "활용" in category:
        cap = 3.7 if has_metrics else 3.2
    elif "장벽" in category or "진입" in category:
        cap = 3.8 if has_metrics else 3.3
    elif "r&d" in cat or "강도" in category:
        cap = 3.5 if has_metrics else 3.1
        reason = "R&D 투자액·인력·기간 등 수치 근거 확인 전까지 보수 반영"
    adjusted = min(max(base, 0.0), cap)
    if raw_score is not None and raw_score < adjusted:
        adjusted = raw_score
        reason = "원점수가 보수 상한보다 낮아 원점수 유지"
    return adjusted, reason


def _positive_metric_count(items: list[Any]) -> int:
    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        metrics = item.get("quant_metrics") if isinstance(item.get("quant_metrics"), list) else []
        for m in metrics:
            if not isinstance(m, dict):
                continue
            val = _float(m.get("value"))
            if val is not None and val > 0:
                count += 1
            elif _clean(m.get("value")) and _clean(m.get("value")) not in {"0", "0.0"}:
                count += 1
    return count


def _needs_zero_repair(result: str, items: list[Any]) -> bool:
    if not result:
        return True
    if not re.search(r"0\s*(회|개|건)", result):
        return False
    return _positive_metric_count(items) > 0


def _make_category_result_sentence(category: str, items: list[Any]) -> str:
    names: list[str] = []
    metric_count = 0
    metric_examples: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = _clean(item.get("item_name") or item.get("name"), 30)
        if name:
            names.append(name)
        metrics = item.get("quant_metrics") if isinstance(item.get("quant_metrics"), list) else []
        for m in metrics:
            formatted = _format_metric(m) if isinstance(m, dict) else ""
            if formatted:
                metric_count += 1
                metric_examples.append(formatted)
    if metric_count > 0:
        return f"{category} 축에서는 {', '.join(names[:4]) if names else '주요 항목'}을 중심으로 정량 지표 {metric_count}개가 확인됩니다. 대표 지표는 {', '.join(metric_examples[:3])}이며, Chair 단계에서는 원천 근거의 단위·기간·출처를 함께 확인해 보수 반영합니다."
    return f"{category} 축은 정성 근거 중심으로 확인되며, 정량화를 위해서는 항목별 수치·단위·기간이 포함된 DART/IR/KIPRIS 원천 자료 보강이 필요합니다."


def _extract_hq_markdown_frame(hq_md: str) -> str:
    for marker in ["## 3. 엑셀 틀 기반", "## 엑셀 틀", "### 엑셀 틀"]:
        idx = hq_md.find(marker)
        if idx >= 0:
            return hq_md[idx:].strip()
    return ""


def _repair_zero_markdown(md: str) -> str:
    # Markdown 원문만 있을 때는 표를 재구성하기 어렵기 때문에, 명백한 0회/0개 단정 문장만 완화한다.
    md = re.sub(r"관련 기술은 실제 원천에서\s*0회\s*확인됩니다[.]?", "관련 기술의 원천 확인 횟수는 항목별 표의 정량 지표를 기준으로 해석합니다.", md)
    md = re.sub(r"0개 제품·공정 영역", "확인된 제품·공정 영역", md)
    return md


def _clarify_bridge_score_in_core(report: str) -> str:
    return re.sub(
        r"(\*\*기술-가치 연결 검증:\*\*\s*Tech[- ]to[- ]Value\s*Bridge\s*Score:\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*100,\s*판정=([A-Z_]+))",
        r"**기술-가치 연결 검증:** Auditor/Finance overlay 보수 반영 Tech-to-Value Bridge Score: \2/100, 판정=\3",
        report,
        flags=re.I,
    )


def _filter_terms(values: Any) -> list[str]:
    if isinstance(values, str):
        values = re.split(r"[,;/|]", values)
    if not isinstance(values, list):
        values = []
    out: list[str] = []
    for x in values:
        if isinstance(x, dict):
            x = x.get("term") or x.get("word") or x.get("keyword") or ""
        term = _clean(x, 35)
        if not term or _is_noise_term(term):
            continue
        if term not in out:
            out.append(term)
    return out


def _filter_samples(values: Any) -> list[str]:
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for x in values:
        if isinstance(x, dict):
            x = x.get("title") or x.get("invention_title") or x.get("name") or ""
        title = _clean(x, 70)
        if not title or _mojibake(title):
            continue
        out.append(title)
    return out


def _is_noise_term(term: str) -> bool:
    term = _clean(term, 80).lower()
    if not term:
        return True
    if term in {x.lower() for x in TECH_STOPWORDS}:
        return True
    if len(term) <= 1:
        return True
    if re.fullmatch(r"[0-9\.\-_/]+", term):
        return True
    return any(sw.lower() == term for sw in TECH_STOPWORDS)


def _infer_cluster_meaning(terms: list[str] | str, samples: list[str] | str = "") -> str:
    if isinstance(terms, list):
        term_text = " ".join(terms)
    else:
        term_text = terms
    if isinstance(samples, list):
        sample_text = " ".join(samples)
    else:
        sample_text = samples
    text = f"{term_text} {sample_text}".lower()
    rules = [
        (["wlp", "fowlp", "fo-wlp", "plp", "bump", "bumping", "package", "패키", "재배선"], "후공정/첨단 패키징 기술군"),
        (["tc", "bonder", "bonding", "본더", "접합", "hbm", "검사", "테스트"], "반도체 장비·본딩·검사 기술군"),
        (["전구체", "precursor", "과산화수소", "h2o2", "식각", "etch", "세정", "clean", "박리", "strip"], "반도체·디스플레이 전자재료 기술군"),
        (["oled", "유기", "발광", "디스플레이", "emitting"], "OLED/디스플레이 소재 기술군"),
        (["battery", "배터리", "이차전지", "전해", "양극", "음극", "첨가제"], "이차전지 소재 기술군"),
        (["monitor", "sensor", "측정", "센서"], "공정 모니터링·센싱 기술군"),
    ]
    for keys, label in rules:
        if any(k in text for k in keys):
            return label
    return "기타 기술군 / 해석 보강 필요"


def _cluster_note(rank: int, size: int, total: int, meaning: str) -> str:
    if total <= 0 or size <= 0:
        return "비중 확인 제한"
    ratio = size / total
    if rank == 1 and ratio >= 0.30:
        return "최대 클러스터 / 핵심 기술축 후보"
    if ratio >= 0.20:
        return "주요 기술축"
    if ratio >= 0.10:
        return "보조 기술축"
    if "기타" in meaning:
        return "용어 해석 보강 필요"
    return "롱테일 기술축"


def _terms(text: str, candidates: list[str], limit: int) -> list[str]:
    found = []
    low = text.lower()
    for cand in candidates:
        if cand.lower() in low and cand not in found:
            found.append(cand)
        if len(found) >= limit:
            break
    return found


def _extract_sentence(text: str, keys: list[str]) -> str:
    if not keys:
        return ""
    # Python re는 가변 길이 lookbehind를 허용하지 않는다.
    # 기존 패턴 `(?<=[.!?。]|다\.)`는 Windows/Python 3.13에서 런타임 오류를 낼 수 있어
    # 고정 길이 lookbehind 2개와 줄바꿈 기준으로 분리한다.
    sentences = re.split(r"\n+|(?<=[.!?。])\s+|(?<=다\.)\s+", text)
    for s in sentences:
        if any(k.lower() in s.lower() for k in keys):
            return _clean(s, 160)
    return ""


def _agent_name(x: dict[str, Any]) -> str:
    return str(x.get("agent") or x.get("name") or x.get("agent_name") or "").lower().strip()


def _get_company(x: dict[str, Any]) -> str:
    return str(x.get("company") or x.get("company_name") or x.get("corp_name") or "").strip()


def _float(x: Any) -> float | None:
    try:
        if x in (None, ""):
            return None
        return float(str(x).replace(",", "").replace("%", "").strip())
    except Exception:
        return None


def _safe_int(x: Any) -> int:
    val = _float(x)
    return int(val) if val is not None else 0


def _score_text(x: Any) -> str:
    v = _float(x)
    return "확인 제한" if v is None else f"{v:.1f}/100"


def _axis_score_text(x: Any) -> str:
    v = _float(x)
    return "확인 제한" if v is None else f"{v:.1f}/5"


def _num_or_limit(x: Any, unit: str) -> str:
    v = _float(x)
    return "확인 제한" if v is None else f"{int(v):,}{unit}"


def _percent(n: int, total: int) -> str:
    if total <= 0:
        return "확인 제한"
    return f"{n / total * 100:.1f}%"


def _similarity_percent(row: dict[str, Any]) -> str:
    for key in ["similarity_percent", "nearest_peer_similarity_percent"]:
        if key in row:
            v = _float(row.get(key))
            if v is not None:
                return f"{v:.2f}%"
    for key in ["similarity", "nearest_peer_similarity"]:
        v = _float(row.get(key))
        if v is not None:
            return f"{v * 100:.2f}%" if v <= 1 else f"{v:.2f}%"
    return "확인 제한"


def _fmt_percent(x: Any) -> str:
    v = _float(x)
    if v is None:
        return "확인 제한"
    return f"{v * 100:.2f}%" if v <= 1 else f"{v:.2f}%"


def _fmt4(x: Any) -> str:
    v = _float(x)
    return "-" if v is None else f"{v:.4f}"


def _clean(x: Any, max_len: int = 240) -> str:
    text = re.sub(r"\s+", " ", str(x or "")).strip().strip('"').strip("'")
    text = text.replace("|", "/")
    if _mojibake(text):
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _cell(x: Any, max_len: int = 120) -> str:
    return _clean(x, max_len) or "-"


def _mojibake(text: str) -> bool:
    text = str(text or "")
    bad = sum(text.count(ch) for ch in ["�", "媛", "諛", "湲", "怨", "吏", "쒕", "ㅽ", "鍮", "寃", "猷"])
    korean = len(re.findall(r"[가-힣]", text))
    return bad >= 3 and bad > korean


def _sanitize_links(text: str) -> str:
    text = re.sub(r"\((https?://[^\s\)]*?)\"\)", r"(\1)", text)
    text = re.sub(r"\[([^\]]*?https?://[^\]]*?)\"\]", lambda m: "[" + m.group(1).rstrip('"') + "]", text)
    text = re.sub(r"(https?://[^\s\]\)\"'<>]+)[\"']", r"\1", text)
    return text
