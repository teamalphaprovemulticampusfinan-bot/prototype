from __future__ import annotations


def to_markdown(analysis: dict) -> str:
    score   = analysis.get("total_score", "?")
    summary = analysis.get("market_summary", {})

    lines: list[str] = []
    lines.append(f"# [{analysis.get('company', '')}] 마켓 분석 보고서\n")
    lines.append(f"**마켓 점수: {score}/100**\n")
    lines.append(f"> {analysis.get('summary', '')}\n")

    lines.append("## 마켓 점수")
    lines.append("| 항목 | 점수 | 근거 |")
    lines.append("|------|------|------|")
    for key, value in analysis.get("scoring", {}).items():
        lines.append(f"| {key} | {value['score']}/{value['max']} | {value['reason']} |")
    lines.append(f"| **합계** | **{score}/100** | |")

    lines.append("\n## 시장 환경 해석")
    lines.append(f"- **OECD 경기선행지수**: {summary.get('oecd_interpretation', '')}")
    lines.append(f"- **산업 성장 단계**: {summary.get('industry_stage', '')}")
    lines.append(f"- **밸류체인 포지션**: {summary.get('value_chain_position', '')}")
    lines.append(f"- **경쟁 구도**: {summary.get('competitive_position', '')}")

    lines.append("\n## 리스크")
    # 교체
    for risk in analysis.get("risks", []):
        if isinstance(risk, dict):
            sev = {"상": "🔴", "중": "🟡", "하": "🟢"}.get(risk.get("severity", ""), "⚪")
            lines.append(f"- {sev} [{risk.get('severity', '')}] {risk.get('risk', '')}")
        else:
            lines.append(f"- ⚪ {risk}")

    lines.append("\n## 기회요인")
    for opp in analysis.get("opportunities", []):
        lines.append(f"- {opp.get('opportunity', '')} — {opp.get('basis', '')}")

    return "\n".join(lines)
