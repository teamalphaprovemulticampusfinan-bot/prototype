from __future__ import annotations

import json
import pandas as pd
from pathlib import Path
from typing import Dict, Any


def save_json_report(result: Dict[str, Any], path: Path) -> None:
    """
    결과를 JSON 파일로 저장
    """

    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"  ✅ JSON 저장 완료: {path}")


def save_csv_report(result: Dict[str, Any], path: Path) -> None:
    """
    결과를 CSV로 저장 (한 행)
    """

    flat = flatten_dict(result)

    df = pd.DataFrame([flat])
    df.to_csv(path, index=False, encoding="utf-8-sig")

    print(f"  ✅ CSV 저장 완료: {path}")


def save_markdown_report(result: Dict[str, Any], path: Path) -> None:
    """
    결과를 Markdown 리포트로 저장.

    변경 사항:
    - 커버리지(coverage) 섹션 추가
    - score_breakdown 섹션 추가 (항목별 기여도)
    - LLM watch_points를 구조화 객체 테이블로 출력
    - sector_impact 섹션 추가
    - evidence_links 섹션 추가
    """
    details = result.get("details", {})
    llm_analysis = details.get("llm_analysis") or {}
    coverage_info = details.get("data_coverage") or {}

    # ── 헤더 및 범례 ──────────────────────────────────────────
    report = f"""# 📊 매크로 분석 리포트 (반도체 딥테크 섹터)

## 📘 지표 설명

### 🔢 점수 Score
- 매크로 환경을 종합한 점수입니다.
- 양수는 위험자산에 우호적, 음수는 위험자산에 비우호적입니다.

| 점수 구간 | 의미 |
|---|---|
| +4 이상 | 강한 매수 환경 |
| +2 ~ +3 | 매수 우위 |
| -1 ~ +1 | 중립 |
| -2 ~ -3 | 매도 우위 |
| -4 이하 | 강한 매도 환경 |

### ⚠️ 위험도 Risk Level

| 위험도 | 의미 |
|---|---|
| LOW | 매우 안정 |
| MEDIUM_LOW | 비교적 안정 |
| NEUTRAL | 중립 / 방향성 불확실 |
| MEDIUM_HIGH | 리스크 증가 |
| HIGH | 매우 위험 |

### 🎯 신뢰도 Confidence
- 0에 가까울수록 불확실, 1에 가까울수록 확신이 강합니다.
- 데이터 커버리지가 낮으면 penalty가 적용됩니다.

| 신뢰도 | 의미 |
|---|---|
| 0.7 이상 | 높은 신뢰 |
| 0.4 ~ 0.7 | 중간 신뢰 |
| 0.4 이하 | 낮은 신뢰 |

---

## 🧾 요약

- 생성 시각: {result.get("created_at")}
- 신호: **{result.get("signal")}**
- 점수: {result.get("score")}
- 위험도: {result.get("risk_level")}
- 신뢰도: {result.get("confidence")}
- 커버리지: {int(coverage_info.get("coverage_ratio", 1.0) * 100)}% (penalty: {coverage_info.get("coverage_penalty", 0.0)})

---

## 📌 한 줄 요약

{result.get("summary")}

---

## 📡 데이터 커버리지

"""
    # ── 커버리지 섹션 ──────────────────────────────────────────
    available = coverage_info.get("available") or []
    missing = coverage_info.get("missing") or []
    ratio = coverage_info.get("coverage_ratio", 1.0)
    penalty = coverage_info.get("coverage_penalty", 0.0)

    report += f"- 사용 가능: {', '.join(available) if available else '없음'}\n"
    report += f"- 누락: {', '.join(missing) if missing else '없음'}\n"
    report += f"- 커버리지 비율: {int(ratio * 100)}%"
    if penalty > 0:
        report += f" → confidence penalty -{penalty:.2f} 적용\n"
    else:
        report += "\n"

    # ── 판단 근거 ──────────────────────────────────────────────
    report += "\n---\n\n## 🔍 판단 근거\n\n"
    for r in result.get("reasons", []):
        report += f"- {r}\n"

    # ── score_breakdown ────────────────────────────────────────
    score_breakdown_sections = [
        k for k in ["ecos_일별", "ext_일별", "ecos_월별", "ecos_분기별", "ext_월별", "뉴스", "규제"]
        if k in details and isinstance(details[k], dict)
    ]
    if score_breakdown_sections:
        report += "\n---\n\n## 📊 항목별 핵심 수치 (Score Breakdown)\n\n"
        for section in score_breakdown_sections:
            d = details[section]
            report += f"### {section}\n"
            # _zone 키는 별도 표기, 수치 키만 먼저 출력
            num_rows = [(k, v) for k, v in d.items() if not str(k).endswith("_zone")]
            zone_rows = [(k, v) for k, v in d.items() if str(k).endswith("_zone")]
            for k, v in num_rows:
                report += f"- {k}: {v}\n"
            for k, v in zone_rows:
                report += f"- {k}: `{v}`\n"
            report += "\n"

    # ── LLM 보조 분석 ─────────────────────────────────────────
    if llm_analysis:
        report += "---\n\n## 🤖 LLM 보조 분석 (반도체 딥테크 섹터 관점)\n\n"

        # 요약
        if llm_analysis.get("llm_summary"):
            report += f"### 요약\n{llm_analysis['llm_summary']}\n\n"

        # 매크로 해석
        if llm_analysis.get("macro_interpretation"):
            report += f"### 매크로 해석\n{llm_analysis['macro_interpretation']}\n\n"

        # 반도체 섹터 영향
        if llm_analysis.get("sector_impact"):
            report += f"### 🔬 반도체 섹터 종합 영향\n{llm_analysis['sector_impact']}\n\n"

        # 주요 리스크
        key_risks = llm_analysis.get("key_risks") or []
        if key_risks:
            report += "### 주요 리스크\n"
            for risk in key_risks:
                report += f"- {risk}\n"
            report += "\n"

        # watch_points — 구조화 객체 테이블 출력
        watch_points = llm_analysis.get("watch_points") or []
        if watch_points:
            report += "### 📌 확인 포인트 (Watch Points)\n\n"
            # 구조화 객체인지 문자열인지 판별
            if watch_points and isinstance(watch_points[0], dict):
                report += "| 지표 | 현재 상태 | 주의 기준 | 반도체 관련성 |\n"
                report += "|---|---|---|---|\n"
                for wp in watch_points:
                    indicator = wp.get("indicator", "")
                    current = wp.get("current", "")
                    threshold = wp.get("threshold", "")
                    semi_rel = wp.get("semiconductor_relevance", "")
                    report += f"| {indicator} | {current} | {threshold} | {semi_rel} |\n"
                report += "\n"
            else:
                # 하위 호환: 문자열 리스트인 경우
                for point in watch_points:
                    report += f"- {point}\n"
                report += "\n"

        # evidence_links
        evidence_links = llm_analysis.get("evidence_links") or []
        if evidence_links:
            report += "### 🔗 근거 연결 (Evidence Links)\n\n"
            for ev in evidence_links:
                ev_id = ev.get("evidence_id", "")
                claim = ev.get("claim", "")
                source = ev.get("source_section", "")
                report += f"- **[{ev_id}]** {claim} _(출처: {source})_\n"
            report += "\n"

    # ── 상세 데이터 (score_breakdown 외 나머지) ────────────────
    skip_sections = set(score_breakdown_sections) | {"llm_analysis", "data_coverage"}
    remaining = {k: v for k, v in details.items() if k not in skip_sections and isinstance(v, dict)}
    if remaining:
        report += "---\n\n## 📂 상세 데이터\n\n"
        for section, values in remaining.items():
            report += f"### {section}\n"
            for k, v in values.items():
                report += f"- {k}: {v}\n"
            report += "\n"

    with open(path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"  ✅ 리포트 저장 완료: {path}")


def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
    """
    nested dict → 1차원 dict로 변환 (CSV용)
    """

    items = []

    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k

        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))

    return dict(items)