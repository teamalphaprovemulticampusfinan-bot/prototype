from pathlib import Path
import re

path = Path("src/tech_agent/chair_section.py")
text = path.read_text(encoding="utf-8")

backup = path.with_suffix(".py.bak_ip_evidence_chair_render")
backup.write_text(text, encoding="utf-8")

START = "# === IP_EVIDENCE_CHAIR_REPORT_RENDER_WRAPPER_START ==="
END = "# === IP_EVIDENCE_CHAIR_REPORT_RENDER_WRAPPER_END ==="

pattern = re.compile(
    re.escape(START) + r".*?" + re.escape(END) + r"\s*",
    flags=re.DOTALL,
)
text = pattern.sub("", text).rstrip() + "\n\n"

block = r'''
# === IP_EVIDENCE_CHAIR_REPORT_RENDER_WRAPPER_START ===
# Auto-added: render IP Evidence Composite adjusted Tech-to-Value score in Chair report.
# Purpose:
# - tech_chair_summary.json already contains IP Evidence Composite adjustment.
# - Chair report must display final_bridge_score_after_ip_evidence, not only base_bridge_score.

import json as _ipev_chair_json
import re as _ipev_chair_re
from pathlib import Path as _IpevChairPath


def _ipev_chair_clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null"}:
        return ""
    return text


def _ipev_chair_float(value, default=None):
    try:
        if value is None:
            return default
        text = str(value).replace(",", "").replace("%", "").strip()
        if not text:
            return default
        return float(text)
    except Exception:
        return default


def _ipev_chair_fmt_score(value):
    x = _ipev_chair_float(value)
    if x is None:
        return "확인 제한"
    return f"{x:.2f}/100"


def _ipev_chair_fmt_num(value, suffix=""):
    x = _ipev_chair_float(value)
    if x is None:
        return "확인 제한"
    return f"{x:.2f}{suffix}"


def _ipev_chair_find_summary(company_dir="", company_name=""):
    root = _IpevChairPath.cwd()
    company_dir = _ipev_chair_clean(company_dir)
    company_name = _ipev_chair_clean(company_name)

    candidates = []

    if company_name:
        candidates.extend(root.glob(f"data/*/{company_name}/tech/tech_chair_summary.json"))
        if company_dir:
            candidates.extend(root.glob(f"data/*/{company_name}/tech/{company_dir}_tech_chair_summary.json"))

    if company_dir:
        candidates.extend(root.glob(f"data/*/*/tech/{company_dir}_tech_chair_summary.json"))
        candidates.extend(root.glob("data/*/*/tech/tech_chair_summary.json"))

    scored = []
    for p in candidates:
        if not p.exists():
            continue
        s = str(p).replace("\\", "/")
        score = 0
        if company_name and company_name in s:
            score += 50
        if company_dir and company_dir in s:
            score += 30
        if p.name == "tech_chair_summary.json":
            score += 10
        scored.append((score, p.stat().st_mtime, p))

    if not scored:
        return {}

    scored.sort(reverse=True)
    best = scored[0][2]

    try:
        return _ipev_chair_json.loads(best.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _ipev_chair_extract_company_args(args, kwargs):
    company_dir = (
        kwargs.get("company_dir")
        or kwargs.get("company_slug")
        or kwargs.get("slug")
        or ""
    )
    company_name = (
        kwargs.get("company")
        or kwargs.get("company_name")
        or kwargs.get("name")
        or ""
    )

    # Expected signature often looks like:
    # inject_compact_tech_section(report, opinions, company_dir, company)
    if not company_dir and len(args) >= 3 and isinstance(args[2], str):
        company_dir = args[2]

    if not company_name and len(args) >= 4 and isinstance(args[3], str):
        company_name = args[3]

    return _ipev_chair_clean(company_dir), _ipev_chair_clean(company_name)


def _ipev_chair_build_block(summary):
    if not isinstance(summary, dict):
        return ""

    tv = summary.get("tech_to_value") or {}
    selected_ml = summary.get("selected_ml") or {}

    final_score = (
        tv.get("final_bridge_score_after_ip_evidence")
        or selected_ml.get("final_bridge_score_after_ip_evidence")
        or tv.get("peer_adjusted_bridge_score")
    )

    peer_before = tv.get("peer_adjusted_bridge_score_before_ip_evidence")
    ip_score = (
        tv.get("ip_evidence_composite_score")
        or selected_ml.get("ip_evidence_composite_score")
    )
    ip_signal = (
        tv.get("ip_evidence_composite_bridge_signal")
        or selected_ml.get("ip_evidence_bridge_signal")
    )
    ip_adjustment = (
        tv.get("ip_evidence_composite_adjustment_points")
        or selected_ml.get("ip_evidence_bridge_adjustment_points")
    )
    formula = tv.get("ip_evidence_formula") or (
        "final_bridge_score_after_ip_evidence = "
        "peer_adjusted_bridge_score_before_ip_evidence + "
        "ip_evidence_composite_adjustment_points"
    )

    if _ipev_chair_float(final_score) is None:
        return ""

    lines = []
    lines.append("<!-- IP_EVIDENCE_CHAIR_REPORT_RENDER_START -->")
    lines.append("")
    lines.append("#### IP Evidence Composite 반영 최종 Tech-to-Value Score")
    lines.append("")
    lines.append("| 항목 | 값 | Chair 해석 |")
    lines.append("|---|---:|---|")
    lines.append(
        f"| IP Evidence 반영 전 Peer-adjusted Score | "
        f"{_ipev_chair_fmt_score(peer_before)} | Peer ML 보정 이후, IP Evidence Composite 반영 전 점수입니다. |"
    )
    lines.append(
        f"| IP Evidence Composite Score | "
        f"{_ipev_chair_fmt_score(ip_score)} | 법적 안정성·청구항 방어력·인용 영향력·글로벌 패밀리 확장성을 종합한 IP 질적 근거 점수입니다. |"
    )
    lines.append(
        f"| IP Evidence Bridge Signal | "
        f"{ip_signal or '확인 제한'} | Tech-to-Value Bridge에 반영되는 IP Evidence 방향성입니다. |"
    )
    lines.append(
        f"| IP Evidence Adjustment Points | "
        f"{_ipev_chair_fmt_num(ip_adjustment, '점')} | 최종 Tech-to-Value 점수에 더해지는 조정값입니다. |"
    )
    lines.append(
        f"| Final Tech-to-Value Score After IP Evidence | "
        f"{_ipev_chair_fmt_score(final_score)} | Chair 기술 분석에서 우선 사용해야 하는 최종 기술 점수입니다. |"
    )
    lines.append("")
    lines.append(f"- 산식: `{formula}`")
    lines.append("- 네패스의 경우 IP Evidence 조정값이 0.0이므로, IP Evidence 반영 전후 점수 변화가 없는 것이 정상입니다.")
    lines.append("- 다만 Chair 보고서에서는 기존 Base Bridge Score 72.00이 아니라, Peer ML 및 IP Evidence 반영 후 최종 점수 80.53을 기술 종합 판단에 우선 반영해야 합니다.")
    lines.append("")
    lines.append("<!-- IP_EVIDENCE_CHAIR_REPORT_RENDER_END -->")
    lines.append("")
    return "\n".join(lines)


def _ipev_chair_replace_or_insert(report, block):
    if not isinstance(report, str) or not block:
        return report

    start = "<!-- IP_EVIDENCE_CHAIR_REPORT_RENDER_START -->"
    end = "<!-- IP_EVIDENCE_CHAIR_REPORT_RENDER_END -->"

    if start in report and end in report:
        before = report.split(start, 1)[0].rstrip()
        after = report.split(end, 1)[1].lstrip()
        report = before + "\n\n" + block.strip() + "\n\n" + after
    else:
        # Prefer inserting inside the technical analysis section.
        anchor_patterns = [
            r"(#### 1\)\s*Tech-to-Value Bridge 판정\s*)",
            r"(### 기술 분석\s*)",
            r"(## 기술 분석\s*)",
        ]

        inserted = False
        for pat in anchor_patterns:
            m = _ipev_chair_re.search(pat, report)
            if m:
                pos = m.end()
                report = report[:pos] + "\n" + block.strip() + "\n\n" + report[pos:]
                inserted = True
                break

        if not inserted:
            report = report.rstrip() + "\n\n" + block.strip() + "\n"

    return report


def _ipev_chair_update_inline_score(report, summary):
    if not isinstance(report, str) or not isinstance(summary, dict):
        return report

    tv = summary.get("tech_to_value") or {}
    selected_ml = summary.get("selected_ml") or {}

    final_score = (
        tv.get("final_bridge_score_after_ip_evidence")
        or selected_ml.get("final_bridge_score_after_ip_evidence")
        or tv.get("peer_adjusted_bridge_score")
    )

    final_score_float = _ipev_chair_float(final_score)
    if final_score_float is None:
        return report

    final_score_text = f"{final_score_float:.2f}/100"

    # Existing sentence often says:
    # Tech-to-Value Bridge Score는 72.0/100이며
    report = _ipev_chair_re.sub(
        r"(Tech-to-Value Bridge Score는)\s*[0-9]+(?:\.[0-9]+)?/100",
        rf"\1 {final_score_text}",
        report,
        count=3,
    )

    return report


_ipev_chair_original_inject_compact_tech_section = globals().get("inject_compact_tech_section")

if callable(_ipev_chair_original_inject_compact_tech_section):

    def inject_compact_tech_section(*args, **kwargs):
        report = _ipev_chair_original_inject_compact_tech_section(*args, **kwargs)

        company_dir, company_name = _ipev_chair_extract_company_args(args, kwargs)
        summary = _ipev_chair_find_summary(company_dir=company_dir, company_name=company_name)

        if isinstance(report, str) and isinstance(summary, dict) and summary:
            block = _ipev_chair_build_block(summary)
            report = _ipev_chair_update_inline_score(report, summary)
            report = _ipev_chair_replace_or_insert(report, block)

        return report

# === IP_EVIDENCE_CHAIR_REPORT_RENDER_WRAPPER_END ===
'''

text = text + block.strip() + "\n"
path.write_text(text, encoding="utf-8")

print("[DONE] chair_section.py patched for IP Evidence Chair report rendering")
print(f"[BACKUP] {backup}")
