from __future__ import annotations

import argparse
import csv
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

ROOT = Path(__file__).resolve().parents[2]

DEFAULT_COMPANY_NAMES: dict[str, str] = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "엘티씨",
}
COMPANY_NAME_TO_SLUG: dict[str, str] = {v: k for k, v in DEFAULT_COMPANY_NAMES.items()}
COMPANY_ALIASES: dict[str, set[str]] = {
    "nepes": {"nepes", "네패스", "NEPES", "033640", "033640.KQ"},
    "hanmi": {"hanmi", "한미반도체", "Hanmi Semiconductor", "042700", "042700.KS", "042700.KQ"},
    "hansol": {"hansol", "한솔케미칼", "Hansol Chemical", "014680", "014680.KS"},
    "duksan": {"duksan", "덕산테코피아", "Duksan Techopia", "317330", "317330.KQ"},
    "ltc": {"ltc", "엘티씨", "LTC", "170920", "170920.KQ"},
}

try:  # Keep the full appendix aligned with src/tech_agent/prompts.py.
    from .prompts import (
        CAPITAL_AND_DILUTION_POLICY,
        DATA_QUALITY_POLICY,
        EVIDENCE_SOURCE_PRIORITY,
        FINAL_TECH_SCORE_POLICY,
        INVESTOR_OUTPUT_POLICY,
        LITERATURE_APPLICATION_POLICY,
        TECH_TO_VALUE_BRIDGE_PROMPT,
    )
except Exception:  # pragma: no cover - script fallback
    try:
        from tech_agent.prompts import (
            CAPITAL_AND_DILUTION_POLICY,
            DATA_QUALITY_POLICY,
            EVIDENCE_SOURCE_PRIORITY,
            FINAL_TECH_SCORE_POLICY,
            INVESTOR_OUTPUT_POLICY,
            LITERATURE_APPLICATION_POLICY,
            TECH_TO_VALUE_BRIDGE_PROMPT,
        )
    except Exception:
        CAPITAL_AND_DILUTION_POLICY = ""
        DATA_QUALITY_POLICY = ""
        EVIDENCE_SOURCE_PRIORITY = []
        FINAL_TECH_SCORE_POLICY = {"weights": {}, "grade_thresholds": {}}
        INVESTOR_OUTPUT_POLICY = ""
        LITERATURE_APPLICATION_POLICY = ""
        TECH_TO_VALUE_BRIDGE_PROMPT = ""


MEANINGLESS_TERMS = {
    # 특허 청구항/명세서에 반복되는 기능어·형식어
    "상기", "이를", "관한", "발명은", "것이다", "있는", "있다", "위한", "이용한", "이용", "포함하는",
    "포함", "한다", "하게", "되는", "또는", "그리고", "및", "으로", "에서", "에게", "따른", "있으며",
    "기술적", "사상은", "발명의", "형태", "실시", "예에", "실시예", "실시 예에", "제1", "제2", "제3",
    "단계", "제공한다", "제공", "방법", "장치", "구성", "형성", "형성하는", "이의", "된다", "가능한",
    "상에", "하에", "어느", "하나", "복수", "각각", "일측", "타측", "전술한", "후술하는", "이하", "이상",
    "하기", "화학식", "하기 화학식", "도면", "설명", "바람직한", "특징으로", "구비하는", "배치되는",
    # 자주 튀는 비기술 phrase
    "필름 이를", "이를 포함하는", "관한 것이다", "상기 제1", "발명의 실시", "단계 상기",
    "상기 반도체", "제1 반도체", "형성하는 단계", "기술적 사상", "발명의 기술적",
}

BAD_TERM_PATTERNS = [
    r"^상기\s+", r"\s+상기$", r"^제[0-9]+\s+", r"^어느$", r"하기\s*화학식",
    r"형성하는\s*단계", r"제공하는\s*단계", r"발명의\s*기술적", r"기술적\s*사상",
    r"필름\s*이를", r"이를\s*포함", r"관한\s*것", r"^.{0,2}상에$",
]

GRADE_KR = {
    "DISTINCTIVE_TECH_LEADER": "차별화 리더형",
    "DIFFERENTIATED_TECH_POSITION": "차별화 확인형",
    "MODERATE_DIFFERENTIATION": "보통 차별화형",
    "LOW_DIFFERENTIATION": "차별화 제한형",
    "COMMERCIALIZATION_WATCH": "사업화 추적형",
    "TECH_FINANCE_GAP": "기술-재무 괴리형",
}


def _infer_bridge_grade_from_score(score: Any) -> str | None:
    x = _to_float(score)
    if x is None:
        return None
    if x >= 82:
        return "VALUE_BRIDGE_READY(점수 기반 보조 판정)"
    if x >= 60:
        return "COMMERCIALIZATION_WATCH(점수 기반 보조 판정)"
    return "TECH_FINANCE_GAP(점수 기반 보조 판정)"


def _infer_diff_grade_from_score(score: Any) -> str | None:
    x = _to_float(score)
    if x is None:
        return None
    if x >= 75:
        return "DISTINCTIVE_TECH_LEADER"
    if x >= 60:
        return "DIFFERENTIATED_TECH_POSITION"
    if x >= 45:
        return "MODERATE_DIFFERENTIATION"
    return "LOW_DIFFERENTIATION"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _slug(value: str | None) -> str:
    if not value:
        return "unknown"
    s = str(value).strip()
    if s in COMPANY_NAME_TO_SLUG:
        return COMPANY_NAME_TO_SLUG[s]
    return Path(s).stem.strip().lower()


def _display_company(company_dir: str, company: str | None = None, company_name: str | None = None) -> str:
    if company_name:
        return company_name
    if company:
        return company
    return DEFAULT_COMPANY_NAMES.get(company_dir, company_dir)


def _aliases(company_dir: str, company: str | None = None) -> set[str]:
    values = {company_dir, company_dir.lower(), DEFAULT_COMPANY_NAMES.get(company_dir, company_dir)}
    values |= COMPANY_ALIASES.get(company_dir, set())
    if company:
        values.add(company)
    return {str(v).strip() for v in values if str(v).strip()}


def _norm_key(value: Any) -> str:
    return re.sub(r"[\s_\-\.()\[\]/]+", "", str(value or "")).lower()


def _is_missing(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return True
    if isinstance(v, str):
        return not v.strip() or v.strip().lower() in {"nan", "none", "null", "원문 확인 필요", "n/a"}
    if isinstance(v, (list, dict, tuple, set)):
        return len(v) == 0
    return False


def _coalesce(*values: Any, default: Any = None) -> Any:
    for v in values:
        if not _is_missing(v):
            return v
    return default


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if math.isnan(float(v)) or math.isinf(float(v)):
            return None
        return float(v)
    s = str(v).strip().replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0))
    except Exception:
        return None


def _num_from_text(text: Any, *patterns: str) -> float | None:
    s = str(text or "")
    for pat in patterns:
        m = re.search(pat, s, flags=re.I)
        if m:
            return _to_float(m.group(1))
    return None


def _fmt(v: Any, suffix: str = "", none: str = "원문 확인 필요", decimals: int = 2) -> str:
    if _is_missing(v):
        return none
    if isinstance(v, bool):
        return "예" if v else "아니오"
    x = _to_float(v)
    if x is not None and (isinstance(v, (int, float)) or re.fullmatch(r"\s*-?[\d,.]+(?:\.\d+)?\s*", str(v))):
        if abs(x - int(x)) < 1e-9:
            return f"{int(x):,}{suffix}"
        return f"{x:,.{decimals}f}{suffix}"
    return str(v).strip()


def _score(v: Any, none: str = "원문 확인 필요") -> str:
    x = _to_float(v)
    if x is None:
        return none
    return f"{x:.2f}/100"


def _score_scaled(v: Any, max_score: Any = None, none: str = "원문 확인 필요") -> str:
    x = _to_float(v)
    if x is None:
        return none
    m = _to_float(max_score)
    # Tech 원점수가 7개 축×5점=35점 체계로 저장된 경우 100점처럼 보이지 않도록 표기한다.
    if m is not None and m > 0 and m != 100:
        return f"{x:.2f}/{m:g} ({x / m * 100:.2f}/100 환산)"
    if 0 <= x <= 35 and (m is None):
        return f"{x:.2f}/35 (추정 {x / 35 * 100:.2f}/100 환산)"
    return f"{x:.2f}/100"


def _pct(v: Any, none: str = "원문 확인 필요") -> str:
    x = _to_float(v)
    if x is None:
        return none
    return f"{x:.2f}%"


def _clean(value: Any, limit: int = 160, none: str = "원문 확인 필요") -> str:
    if _is_missing(value):
        return none
    text = re.sub(r"\s+", " ", str(value)).strip()
    text = text.replace("\ufeff", "")
    if not text:
        return none
    return text[:limit] + ("..." if len(text) > limit else "")



def _policy_excerpt(text: Any, limit: int = 240) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return "원문 확인 필요"
    return cleaned[:limit] + ("..." if len(cleaned) > limit else "")


def render_prompt_policy_overview() -> str:
    """Render the shared prompt/rubric policy used by deterministic Tech outputs."""
    weights = FINAL_TECH_SCORE_POLICY.get("weights") if isinstance(FINAL_TECH_SCORE_POLICY, dict) else {}
    thresholds = FINAL_TECH_SCORE_POLICY.get("grade_thresholds") if isinstance(FINAL_TECH_SCORE_POLICY, dict) else {}
    lines = [
        "## Shared Tech Rubric Alignment",
        "",
        "- **원천 파일:** `src/tech_agent/prompts.py`",
        f"- **최종 점수 정책:** {_policy_excerpt(FINAL_TECH_SCORE_POLICY.get('description') if isinstance(FINAL_TECH_SCORE_POLICY, dict) else '')}",
        f"- **가중치:** {weights or '원문 확인 필요'}",
        f"- **판정 임계값:** {thresholds or '원문 확인 필요'}",
        f"- **Tech-to-Value 원칙:** {_policy_excerpt(TECH_TO_VALUE_BRIDGE_PROMPT)}",
        f"- **논문/IB/사업타당성 반영:** {_policy_excerpt(LITERATURE_APPLICATION_POLICY)}",
        f"- **데이터 품질 원칙:** {_policy_excerpt(DATA_QUALITY_POLICY)}",
        f"- **자금조달·희석 리스크 원칙:** {_policy_excerpt(CAPITAL_AND_DILUTION_POLICY)}",
        "",
        "| 근거 우선순위 | 설명 |",
        "|---:|---|",
    ]
    priorities = EVIDENCE_SOURCE_PRIORITY if isinstance(EVIDENCE_SOURCE_PRIORITY, list) else []
    if priorities:
        for idx, item in enumerate(priorities[:8], start=1):
            lines.append(f"| {idx} | {_clean(item, 120)} |")
    else:
        lines.append("| - | 원문 확인 필요 |")
    return "\n".join(lines) + "\n"



def _rel(path: Path | str | None) -> str:
    if not path:
        return "원문 확인 필요"
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except Exception:
        s = str(path).replace("\\", "/")
        for marker in ("data/", "src/", "scripts/"):
            idx = s.find(marker)
            if idx >= 0:
                return s[idx:]
        return p.name


def _read_text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return ""


def _read_json(path: Path | None) -> Any | None:
    text = _read_text(path)
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _deep_values(obj: Any, key: str) -> list[Any]:
    target = _norm_key(key)
    found: list[Any] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if _norm_key(k) == target:
                found.append(v)
            found.extend(_deep_values(v, key))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_deep_values(item, key))
    return found


def _first_key(obj: Any, keys: Iterable[str], default: Any = None) -> Any:
    for key in keys:
        for v in _deep_values(obj, key):
            if not _is_missing(v):
                return v
    return default


def _all_dicts(obj: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        out.append(obj)
        for v in obj.values():
            out.extend(_all_dicts(v))
    elif isinstance(obj, list):
        for item in obj:
            out.extend(_all_dicts(item))
    return out


def _first_existing(paths: Iterable[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def _json_from_paths(paths: Iterable[Path]) -> tuple[Any | None, Path | None]:
    for p in paths:
        data = _read_json(p)
        if data is not None:
            return data, p
    return None, None


def _text_from_paths(paths: Iterable[Path]) -> tuple[str, Path | None]:
    for p in paths:
        text = _read_text(p)
        if text:
            return text, p
    return "", None


def _company_tech_dir(company_dir: str, company: str | None = None) -> Path:
    display = _display_company(company_dir, company=company)
    return ROOT / "data" / "반도체" / display / "tech"


def _candidate_paths(company_dir: str, filename: str, company: str | None = None) -> list[Path]:
    display = _display_company(company_dir, company=company)
    return [
        ROOT / "data" / "반도체" / display / "tech" / filename,
        ROOT / "data" / "반도체" / company_dir / "tech" / filename,
        ROOT / "data" / "반도체" / "_sector_common" / "ml_universe" / filename,
        ROOT / "data" / "반도체" / "common" / "ml_universe" / filename,
        ROOT / "src" / "auditor_agent" / "resources" / filename,
    ]


def _find_png(company_dir: str, company: str | None, *filenames: str) -> Path | None:
    candidates: list[Path] = []
    for filename in filenames:
        candidates.extend(_candidate_paths(company_dir, filename, company=company))
    # 새 team-a 구조에서는 이름이 조금 달라질 수 있어 data 기반 tech 폴더를 glob으로도 확인한다.
    for base in [
        _company_tech_dir(company_dir, company),
        ROOT / "data" / "반도체" / company_dir / "tech",
        ROOT / "data" / "반도체" / "_sector_common" / "ml_universe",
    ]:
        if base.exists():
            candidates.extend(sorted(base.glob("*peer*map*.png")))
            candidates.extend(sorted(base.glob("*umap*.png")))
    return _first_existing(candidates)


def _artifact_status(path: Path | None) -> str:
    return f"확인됨: `{_rel(path)}`" if path else "원문 확인 필요: 산출물 파일을 찾지 못했습니다."


def _extract_company_record(data: Any, company_dir: str, company: str | None = None) -> Any | None:
    if not data:
        return None
    aliases = {_norm_key(x) for x in _aliases(company_dir, company)}

    def is_target(d: dict[str, Any]) -> bool:
        for key in ("company_dir", "slug", "ticker", "stock_code", "company", "company_name", "name", "corp_name"):
            val = d.get(key)
            if val is not None and _norm_key(val) in aliases:
                return True
        return False

    if isinstance(data, dict):
        if is_target(data):
            return data
        for container_key in ("companies", "packets", "items", "results", "assignments", "records", "data"):
            container = data.get(container_key)
            if isinstance(container, dict):
                for k, v in container.items():
                    if _norm_key(k) in aliases:
                        return v
                    if isinstance(v, dict) and is_target(v):
                        return v
            if isinstance(container, list):
                for item in container:
                    if isinstance(item, dict) and is_target(item):
                        return item
        # similarity matrix는 회사 레코드로 자르면 안 되므로 전체 반환
        if any(k in data for k in ("similarity_matrix", "matrix", "pairwise", "pairs", "similarities")):
            return data
        # nested company record fallback
        for d in _all_dicts(data):
            if d is not data and is_target(d):
                return d
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and is_target(item):
                return item
    return None


def load_artifacts(company_dir: str, company: str | None = None) -> dict[str, Any]:
    names: dict[str, list[str]] = {
        "chair_summary": ["tech_chair_summary.json", f"{company_dir}_tech_chair_summary.json"],
        "tech_packet": ["tech.json", "tech_packet.json", f"{company_dir}_tech_agent_packet.json"],
        "high_quality_json": [f"{company_dir}_tech_high_quality_report.json", "tech_high_quality_report.json"],
        "high_quality_md": [f"{company_dir}_tech_high_quality_report.md", "tech_high_quality_report.md"],
        "tech_to_value": ["tech_to_value_bridge.json", f"{company_dir}_tech_to_value_bridge.json", f"{company_dir}_tech_to_value_inputs.json"],
        "patent_json": [f"{company_dir}_tech_patent_evidence.json", "tech_patent_evidence.json", "tech_ip_ml.json"],
        "ml_signal": ["tech_ml_signal.json", f"{company_dir}_tech_ml_signal.json"],
        "peer_similarity": ["tech_peer_similarity.json"],
        "peer_cluster": ["tech_peer_cluster.json", "tech_peer_clusters.json", "tech_peer_cluster_all.json"],
        "peer_map": ["tech_peer_map.json"],
        "peer_percentile": ["tech_peer_percentile_bridge.json", f"{company_dir}_tech_peer_percentile_bridge.json", "tech_peer_percentile_bridge_all.json"],
        "tech_ip_ml": ["tech_ip_ml.json", f"{company_dir}_tech_ip_ml.json", "tech_ip_strength_all.json"],
        "tech_differentiation": ["tech_differentiation.json", f"{company_dir}_tech_differentiation.json", "tech_differentiation_all.json"],
        "tech_momentum_confidence": ["tech_momentum_confidence.json", f"{company_dir}_tech_momentum_confidence.json", "tech_momentum_confidence_all.json"],
    }
    artifacts: dict[str, Any] = {}
    for key, filenames in names.items():
        paths: list[Path] = []
        for filename in filenames:
            paths.extend(_candidate_paths(company_dir, filename, company=company))
        if key.endswith("_md"):
            text, path = _text_from_paths(paths)
            artifacts[key] = text
            artifacts[f"{key}_path"] = path
        else:
            data, path = _json_from_paths(paths)
            if data is not None and key not in {"peer_similarity"}:
                extracted = _extract_company_record(data, company_dir, company=company)
                if extracted is not None:
                    data = extracted
            artifacts[key] = data or {}
            artifacts[f"{key}_path"] = path
    return artifacts


# -----------------------------------------------------------------------------
# Markdown parsing and keyword cleanup
# -----------------------------------------------------------------------------

def _parse_md_tables(md: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    lines = md.splitlines()
    i = 0
    while i < len(lines):
        if "|" in lines[i] and i + 1 < len(lines) and re.search(r"\|?\s*:?-{2,}:?\s*\|", lines[i + 1]):
            rows: list[list[str]] = []
            while i < len(lines) and "|" in lines[i]:
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            if len(rows) >= 3:
                tables.append(rows)
        i += 1
    return tables


def _score_grade(value: Any) -> str:
    """Convert a 0~100 style score into a compact Korean grade."""
    raw = str(value or "")
    frac = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", raw)
    if frac:
        denom = float(frac.group(2)) or 1.0
        num = float(frac.group(1)) / denom * 100.0
    else:
        num = _to_float(value)
    if num is None:
        return "원문 참조"
    if num >= 80:
        return "강"
    if num >= 60:
        return "중"
    return "보강 필요"


def _sanitize_evidence_text(text: Any, limit: int = 120) -> str:
    """Remove noisy zero-count wording while preserving useful evidence counts."""
    s = _clean(text, limit * 2)
    if not s or s == "원문 확인 필요":
        return "원천 산출물 기준 확인"
    replacements = [
        (r"직접\s*근거\s*0개\s*/\s*보조\s*근거\s*(\d+)개", r"직접 근거 제한적 / 보조 근거 \1개"),
        (r"직접\s*근거\s*0건\s*/\s*보조\s*근거\s*(\d+)건", r"직접 근거 제한적 / 보조 근거 \1건"),
        (r"정량\s*신호\s*0개", "정량 신호 제한적"),
        (r"정량\s*신호\s*0건", "정량 신호 제한적"),
        (r"문서\s*0건", "문서 근거 제한적"),
        (r"0회", "제한적"),
    ]
    for pat, repl in replacements:
        s = re.sub(pat, repl, s)
    return _clean(s, limit)


def _split_hq_sections(md: str) -> list[tuple[str, str]]:
    """Parse one-line high_quality_report.md sections such as '### 3-1. 대표 기술 ...'."""
    if not md:
        return []
    heading_pat = re.compile(r"###\s*3-\d+\.\s*")
    matches = list(heading_pat.finditer(md))
    sections: list[tuple[str, str]] = []
    for idx, m in enumerate(matches):
        start = m.end()
        stop = matches[idx + 1].start() if idx + 1 < len(matches) else len(md)
        chunk = md[start:stop]
        # Title continues until the generated score marker. This also works for
        # one-line reports where a lazy regex previously captured only the first
        # Korean syllable of the title.
        title_part = re.split(r"\s+-\s*점수\s*:", chunk, maxsplit=1)[0]
        title = _clean(title_part, 60)
        if not title:
            title = f"3-{idx + 1} 기술 항목"
        sections.append((title, chunk))
    return sections


def _extract_pipe_rows_from_oneline_table(body: str) -> list[list[str]]:
    """Extract pipe-table-like cells even when Markdown newlines are missing."""
    rows: list[list[str]] = []
    # Match 3-column and 5-column rows. The high-quality report uses both.
    for m in re.finditer(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|(?:\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|)?", body):
        cells = [_clean(c, 160) for c in m.groups() if c is not None]
        if not cells:
            continue
        joined = " ".join(cells)
        if re.search(r"^-+$|^---", joined):
            continue
        if any(c in {"항목", "값", "근거/해석", "산출값", "직접 근거", "대표 출처", "해석"} for c in cells):
            continue
        rows.append(cells)
    return rows


def _extract_excel_frame_rows(md: str, json_obj: Any) -> list[dict[str, Any]]:
    """Return filled Excel-frame rows from JSON, normal tables, or one-line MD.

    Earlier versions tried to read only clean Markdown tables, but the current Tech
    report often stores the high-quality report as a single long line. That made
    Step 1 fall back to '원문 확인 필요'. This parser keeps the latest team-a folder
    structure while restoring the concrete Step 1 output.
    """
    rows = _coalesce(
        _first_key(json_obj, ["excel_frame_rows", "excel_frame", "table_rows", "high_quality_rows"], None),
        default=None,
    )
    if isinstance(rows, list) and rows:
        out = [r for r in rows if isinstance(r, dict)]
        if out:
            return out

    for table in _parse_md_tables(md):
        header = [_norm_key(x) for x in table[0]]
        if any(x in header for x in ["대분류", "항목"]) and any(x in header for x in ["정량화", "점수", "등급", "산출값"]):
            out = []
            for raw in table[2:]:
                if len(raw) < len(table[0]):
                    raw = raw + [""] * (len(table[0]) - len(raw))
                d = {table[0][idx].strip(): raw[idx].strip() for idx in range(len(table[0]))}
                if any(d.values()):
                    out.append(d)
            if out:
                return out

    # Fallback for one-line high_quality_report.md.
    out: list[dict[str, Any]] = []
    for title, body in _split_hq_sections(md):
        pipe_rows = _extract_pipe_rows_from_oneline_table(body)
        score_match = re.search(r"점수\s*:\s*([^\-\|]+)", body)
        basis_match = re.search(r"점수\s*근거\s*:\s*([^\-\|]+)", body)
        score_value = _clean(score_match.group(1), 40) if score_match else "원문 산출물 참조"
        score_basis = _sanitize_evidence_text(basis_match.group(1), 140) if basis_match else "원천 산출물 기준 확인"
        detail_item = title
        detail_value = "정량 산출물 참조"
        detail_basis = "원천 산출물 기준 확인"
        detail_source = "Tech evidence harvest / high_quality_report"
        detail_note = "Excel-frame 항목 기준"

        for cells in pipe_rows:
            head = _norm_key(cells[0])
            if head == "점수" and len(cells) >= 3:
                score_value = cells[1]
                score_basis = _sanitize_evidence_text(cells[2], 140)
                continue
            if head in {"결과", "주의", "기준", "항목", "항목명", "대분류"}:
                continue
            if len(cells) >= 5:
                # Detailed high-quality report row: 항목 / 산출값 / 직접근거 / 대표출처 / 해석
                detail_item = cells[0]
                detail_value = cells[1]
                detail_basis = _sanitize_evidence_text(cells[2], 130)
                detail_source = _sanitize_evidence_text(cells[3], 80)
                detail_note = _sanitize_evidence_text(cells[4], 90)
                break

        combined_basis = detail_basis
        if score_basis and score_basis not in combined_basis:
            combined_basis = _clean(f"{combined_basis}; {score_basis}", 150)
        quant = score_value if score_value != "원문 산출물 참조" else detail_value
        out.append({
            "대분류": title,
            "항목": detail_item or title,
            "정량화": quant,
            "핵심 근거": combined_basis,
            "등급": _score_grade(quant),
            "비고": detail_source if detail_source else detail_note,
        })
    return out


def _filter_terms(terms: Any, limit: int = 12) -> list[str]:
    if terms is None:
        return []
    if isinstance(terms, str):
        raw = re.split(r"[,/;|]\s*|\n+", terms)
    elif isinstance(terms, list):
        raw = []
        for t in terms:
            if isinstance(t, dict):
                raw.append(str(_coalesce(t.get("term"), t.get("keyword"), t.get("word"), t.get("text"), default="")))
            else:
                raw.append(str(t))
    else:
        raw = [str(terms)]
    cleaned: list[str] = []
    seen: set[str] = set()
    for term in raw:
        s = re.sub(r"\s+", " ", term).strip(" ,;|/\t\n\r")
        if not s:
            continue
        # 특허 문장 파편 정리: "상기 반도체", "제1 반도체", "형성하는 단계" 같은 표현은
        # 기술어라기보다 청구항 문법에 가까워 보고서에서 제거한다.
        s = re.sub(r"\b제\s*([0-9]+)\b", r"제\1", s)
        ns = _norm_key(s)
        if len(ns) <= 1:
            continue
        if s in MEANINGLESS_TERMS or ns in {_norm_key(x) for x in MEANINGLESS_TERMS}:
            continue
        if any(re.search(pat, s, flags=re.I) for pat in BAD_TERM_PATTERNS):
            continue
        if re.fullmatch(r"[a-z]\d+[a-z]?|\d+", s.lower()):
            continue
        # 조사/형식어로 끝나는 애매한 2~3어절 phrase 제거
        if re.search(r"(이를|이의|상에|하기|어느|단계)$", s):
            continue
        if ns in seen:
            continue
        seen.add(ns)
        cleaned.append(s)
        if len(cleaned) >= limit:
            break
    return cleaned


def _cluster_id(row: dict[str, Any]) -> Any:
    return _coalesce(row.get("cluster_id"), row.get("cluster"), row.get("label"), row.get("kmeans_cluster"))


# -----------------------------------------------------------------------------
# Step renderers
# -----------------------------------------------------------------------------

def render_step1(company: str, a: dict[str, Any]) -> str:
    hq_json = a.get("high_quality_json") or {}
    hq_md = a.get("high_quality_md") or ""
    rows = _extract_excel_frame_rows(hq_md, hq_json)
    default_labels = [
        "대표 기술", "핵심 제품/서비스", "고객 구매 이유", "경쟁 우위/대체가능성",
        "활용 및 확장 산업", "진입 부담/장벽", "R&D 강도",
    ]
    lines = [
        "## Step 1. Excel-frame based technology position",
        f"- **산출물 상태:** {_artifact_status(a.get('high_quality_md_path') or a.get('high_quality_json_path'))}",
        "- **의미:** 기존 Excel 틀(high_quality_report.py)의 대분류를 Tech Agent 소유 풀버전 부록으로 옮긴 영역입니다.",
        "",
        "| 대분류 | 항목 | 정량화 | 핵심 근거 | 등급 | 비고 |",
        "|---|---|---:|---|---|---|",
    ]
    if rows:
        for r in rows[:12]:
            major = _coalesce(r.get("대분류"), r.get("category"), r.get("major_category"), r.get("구분"), default="원문 산출물 참조")
            item = _coalesce(r.get("항목"), r.get("metric"), r.get("name"), r.get("세부항목"), default=major)
            quant = _coalesce(r.get("정량화"), r.get("점수"), r.get("score"), r.get("value"), default="산출물 원문 참조")
            basis = _coalesce(r.get("핵심 근거"), r.get("근거"), r.get("basis"), r.get("evidence"), default="원문 Markdown 확인 필요")
            grade = _coalesce(r.get("등급"), r.get("grade"), r.get("평가"), default="원문 참조")
            note = _coalesce(r.get("비고"), r.get("note"), r.get("comment"), default="정량 산출 근거 확인")
            lines.append(f"| {_clean(major, 30)} | {_clean(item, 40)} | {_fmt(quant)} | {_clean(basis, 90)} | {_clean(grade, 20)} | {_clean(note, 60)} |")
    else:
        for label in default_labels:
            lines.append(f"| {label} | {label} | 산출물 원문 참조 | high_quality_report 또는 evidence_harvest 원문 확인 | 보강 필요 | 템플릿 컬럼명 확인 |")
    return "\n".join(lines) + "\n"


def render_step2(company: str, a: dict[str, Any]) -> str:
    data = a.get("tech_to_value") or {}
    pp = a.get("peer_percentile") or {}
    peer_adjusted = _coalesce(_first_key(pp, ["peer_adjusted_bridge_score", "adjusted_score"]), _first_key(data, ["peer_adjusted_bridge_score"]))
    base_score = _first_key(data, ["base_bridge_score", "tech_to_value_bridge_score", "bridge_score"], None)
    bridge_grade = _coalesce(
        _first_key(data, ["bridge_grade", "final_bridge_grade", "judgement", "judgment", "grade"]),
        _first_key(pp, ["final_bridge_grade", "bridge_grade", "grade"]),
        _infer_bridge_grade_from_score(peer_adjusted),
        _infer_bridge_grade_from_score(base_score),
        default="별도 판정 미생성",
    )
    raw_score = _first_key(data, ["tech_agent_raw_score", "raw_score", "tech_score", "score"], None)
    raw_max = _first_key(data, ["raw_max_score", "max_score", "tech_score_max", "score_denominator"], None)
    lines = [
        "## Step 2. Tech-to-Value Bridge",
        f"- **산출물 상태:** {_artifact_status(a.get('tech_to_value_path'))}",
        "| 항목 | 값 | 해석 |",
        "|---|---:|---|",
        f"| Tech Agent 원점수 | {_score_scaled(raw_score, raw_max)} | Tech Agent 내부 원점수 또는 기술 평가 총점입니다. |",
        f"| Auditor 보수 반영 점수 | {_score(_first_key(data, ['auditor_adjusted_score', 'auditor_score', 'conservative_score']), none='별도 Auditor 보수 점수 미생성')} | claim/evidence 검증 후 Chair 반영에 사용하는 보수 점수입니다. |",
        f"| Base Bridge Score | {_score(base_score)} | 사업화 연결 전 기본 Tech-to-Value 점수입니다. |",
        f"| Peer-adjusted Bridge Score | {_score(peer_adjusted)} | Step 8의 peer percentile 보정 후 점수입니다. |",
        f"| Bridge Grade | {_clean(bridge_grade, 70)} | {GRADE_KR.get(str(bridge_grade), '최종 기술-가치 연결 판정입니다.')} |",
        f"| Shared Rubric | prompts.py | {_policy_excerpt(TECH_TO_VALUE_BRIDGE_PROMPT, 140)} |",
        "",
        "- **COMMERCIALIZATION_WATCH:** 기술성은 확인되지만 고객 채택·양산·매출 전환·FCF 개선까지 추적해야 하는 사업화 추적형입니다.",
        "- **TECH_FINANCE_GAP:** 기술/IP 포트폴리오는 있으나 수익성·현금흐름·재무안정성 전환 근거가 약한 기술-재무 괴리형입니다.",
    ]
    return "\n".join(lines) + "\n"


def _raw_metrics(*objs: Any) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for obj in objs:
        if not obj:
            continue
        raw = _coalesce(_first_key(obj, ["raw_metrics", "metrics", "patent_metrics", "ip_metrics"], None), default=None)
        if isinstance(raw, dict):
            merged.update(raw)
        if isinstance(obj, dict):
            alias_map = {
                "normalized_patent_records": ["normalized_patent_records", "normalized_records", "text_records", "patent_text_records"],
                "analysis_patent_text_records": ["analysis_patent_text_records", "analysis_records", "total_text_records", "total_patent_text_records"],
                "company_matched_patents": ["company_matched_patents", "matched_patents", "company_patents", "applicant_owner_matched_patents"],
                "applicant_matched_patents": ["applicant_matched_patents", "applicant_owner_matches", "applicant_matches", "owner_matches", "matched_records"],
                "registered_patents": ["registered_patents", "registered_patent_count", "registration_count", "registered_count"],
                "active_patents": ["active_patents", "valid_patents", "surviving_patents", "maintained_patents", "alive_patents", "patents_in_force", "valid_registered_patents", "active_patent_count", "valid_patent_count"],
                "valid_patents": ["valid_patents", "active_patents", "surviving_patents", "maintained_patents", "alive_patents", "patents_in_force", "valid_registered_patents", "valid_patent_count", "active_patent_count"],
                "recent_5y_patents": ["recent_5y_patents", "recent_patents_5y", "recent_five_year_patents", "recent_patent_count", "recent_patents"],
                "ipc_cpc_classes": ["ipc_cpc_classes", "ipc_cpc_diversity", "ipc_classes", "cpc_classes", "ipc_diversity_count", "ipc_cpc_class_count"],
                "core_ipc_h01l_patents": ["core_ipc_h01l_patents", "h01l_patents", "core_ipc_patents", "h01l_count", "core_ipc_count"],
                "patent_keyword_matches": ["patent_keyword_matches", "keyword_matches", "tech_keyword_matches", "keyword_match_count"],
                "keyword_density": ["keyword_density", "keyword_density_score", "tech_keyword_density", "keyword_density_pct"],
                "keyword_density_score": ["keyword_density_score", "keyword_density", "tech_keyword_density_score"],
            }
            for canonical, aliases in alias_map.items():
                v = _first_key(obj, aliases, None)
                if not _is_missing(v):
                    merged[canonical] = v
    return merged


def render_step3(company: str, a: dict[str, Any]) -> str:
    data = a.get("tech_ip_ml") or {}
    patent = a.get("patent_json") or {}
    raw = _raw_metrics(data, patent)
    examples = _coalesce(_first_key(patent, ["representative_patents", "sample_patents", "patent_examples"], None), _first_key(data, ["representative_patents", "sample_patents"], None), default=[])
    lines = [
        "## Step 3. KIPRIS/IP quantitative signals",
        f"- **산출물 상태:** {_artifact_status(a.get('patent_json_path') or a.get('tech_ip_ml_path'))}",
        "| 원천 신호 | 값 |",
        "|---|---:|",
        f"| 정규화 특허 텍스트 레코드 | {_fmt(_coalesce(raw.get('normalized_patent_records'), raw.get('analysis_patent_text_records')), '건')} |",
        f"| 회사 출원인/권리자 매칭 | {_fmt(_coalesce(raw.get('company_matched_patents'), raw.get('applicant_matched_patents'), raw.get('matched_records')), '건')} |",
        f"| 등록 특허 | {_fmt(raw.get('registered_patents'), '건')} |",
        f"| 존속 가능 특허 | {_fmt(_coalesce(raw.get('active_patents'), raw.get('valid_patents')), '건')} |",
        f"| 최근 5년 특허 | {_fmt(raw.get('recent_5y_patents'), '건')} |",
        f"| IPC/CPC 다양성 | {_fmt(raw.get('ipc_cpc_classes'), '개')} |",
        f"| H01L 등 핵심 IPC 특허 | {_fmt(raw.get('core_ipc_h01l_patents'), '건')} |",
        f"| 핵심기술 키워드 매칭 | {_fmt(raw.get('patent_keyword_matches'), '회')} |",
        "",
        "| 대표 특허 예시 | 상태/연도 |",
        "|---|---|",
    ]
    if isinstance(examples, list) and examples:
        for p in examples[:5]:
            if isinstance(p, dict):
                title = _coalesce(p.get("title"), p.get("invention_title"), p.get("name"), default="원문 산출물 참조")
                status = _coalesce(p.get("status"), p.get("legal_status"), p.get("register_status"), p.get("year"), default="원문 산출물 참조")
            else:
                title, status = p, "원문 참조"
            lines.append(f"| {_clean(title, 80)} | {_clean(status, 40)} |")
    else:
        lines.append("| 대표 특허 예시 | patent evidence JSON의 title/status 필드 확인 필요 |")
    return "\n".join(lines) + "\n"


def render_step4(company: str, a: dict[str, Any]) -> str:
    data = a.get("ml_signal") or {}
    clusters = _coalesce(_first_key(data, ["clusters", "cluster_summary", "kmeans_clusters"], None), default=[])
    model = _coalesce(_first_key(data, ["method", "model", "algorithm"], None), default="TF-IDF + KMeans")
    n_records = _first_key(data, ["normalized_patent_records", "analysis_patent_text_records", "n_records", "document_count"], None)
    n_clusters = _coalesce(_first_key(data, ["n_clusters", "cluster_count", "k"], None), len(clusters) if isinstance(clusters, list) and clusters else None)
    lines = [
        "## Step 4. Patent KMeans clustering",
        f"- **산출물 상태:** {_artifact_status(a.get('ml_signal_path'))}",
        "| 항목 | 값 |",
        "|---|---:|",
        f"| 모델 | {_clean(model, 80)} |",
        f"| 정규화 특허 텍스트 레코드 | {_fmt(n_records, '건')} |",
        f"| 특허 클러스터 수 | {_fmt(n_clusters, '개')} |",
        "",
        "| Cluster | 특허 수 | 대표 키워드 | 해석 |",
        "|---:|---:|---|---|",
    ]
    if isinstance(clusters, list) and clusters:
        for row in clusters[:10]:
            if not isinstance(row, dict):
                continue
            cid = _cluster_id(row)
            count = _coalesce(row.get("patent_count"), row.get("count"), row.get("n"), row.get("size"))
            terms = _coalesce(row.get("top_terms"), row.get("keywords"), row.get("representative_keywords"), row.get("terms"), default=[])
            interpretation = _coalesce(row.get("interpretation"), row.get("description"), row.get("label"), default="기술 텍스트 유사도 기반 클러스터")
            filtered = _filter_terms(terms, limit=8)
            if not filtered:
                filtered = _filter_terms(interpretation, limit=5)
            term_text = ", ".join(filtered) if filtered else "산출물 원문 확인 필요"
            lines.append(f"| {_fmt(cid, none='0')} | {_fmt(count, '건')} | {term_text} | {_clean(interpretation, 80)} |")
    else:
        lines.append("| - | 원문 확인 필요 | `tech_ml_signal.json`의 clusters/cluster_summary 구조 확인 필요 | 산출물 원문 확인 |")
    return "\n".join(lines) + "\n"


def _extract_similarity_rows(data: Any, company_dir: str, company: str | None = None) -> list[tuple[str, Any]]:
    """Extract company-level cosine similarity rows from multiple artifact schemas."""
    rows: list[tuple[str, Any]] = []
    aliases = {_norm_key(x) for x in _aliases(company_dir, company)}

    def add_pair(name: Any, sim: Any) -> None:
        if _is_missing(name) or _is_missing(sim):
            return
        if _norm_key(name) in aliases:
            return
        rows.append((str(name), sim))

    # New team-a schema: {company:{nearest_peer, similarity}, similarity_matrix:[{company_dir,...}]}
    company_block = data.get("company") if isinstance(data, dict) else None
    if isinstance(company_block, dict):
        add_pair(
            _coalesce(company_block.get("nearest_peer"), company_block.get("nearest_peer_dir"), company_block.get("peer")),
            _coalesce(company_block.get("similarity"), company_block.get("cosine_similarity"), company_block.get("score")),
        )

    matrix_list = _first_key(data, ["similarity_matrix"], None) if isinstance(data, dict) else None
    if isinstance(matrix_list, list):
        label_map: dict[str, str] = {}
        for item in matrix_list:
            if isinstance(item, dict):
                cd = item.get("company_dir")
                cn = item.get("company")
                if cd and cn:
                    label_map[str(cd)] = str(cn)
        for item in matrix_list:
            if not isinstance(item, dict):
                continue
            row_name = _coalesce(item.get("company_dir"), item.get("company"))
            if _norm_key(row_name) not in aliases:
                continue
            for k, v in item.items():
                if k in {"company_dir", "company"} or _norm_key(k) in aliases:
                    continue
                if _to_float(v) is not None:
                    add_pair(label_map.get(str(k), k), v)

    # Legacy pair/list schemas.
    for key in ("pairs", "pairwise", "similarities", "company_pairs", "edges", "rows", "results", "pairwise_similarity", "nearest_peers"):
        container = _first_key(data, [key], None)
        if isinstance(container, list):
            for item in container:
                if not isinstance(item, dict):
                    continue
                a_name = _coalesce(item.get("company_a"), item.get("source"), item.get("left"), item.get("company1"), item.get("from"))
                b_name = _coalesce(item.get("company_b"), item.get("target"), item.get("right"), item.get("company2"), item.get("to"))
                sim = _coalesce(item.get("cosine_similarity"), item.get("similarity"), item.get("score"), item.get("value"))
                if _norm_key(a_name) in aliases:
                    add_pair(b_name, sim)
                elif _norm_key(b_name) in aliases:
                    add_pair(a_name, sim)
                elif _norm_key(_coalesce(item.get("company_dir"), item.get("slug"))) in aliases:
                    peer = _coalesce(item.get("peer"), item.get("peer_name"), item.get("other_company"), item.get("company_name"))
                    add_pair(peer, sim)

    # Matrix dictionary schemas.
    matrix = _coalesce(_first_key(data, ["matrix"], None), default=None)
    labels = _coalesce(_first_key(data, ["labels", "companies", "company_names", "company_dirs"], None), default=None)
    if isinstance(matrix, dict):
        for k, row in matrix.items():
            if _norm_key(k) in aliases and isinstance(row, dict):
                for name, sim in row.items():
                    add_pair(name, sim)
            elif isinstance(row, dict):
                for name, sim in row.items():
                    if _norm_key(name) in aliases:
                        add_pair(k, sim)
    if isinstance(matrix, list) and isinstance(labels, list):
        norm_labels = [_norm_key(x) for x in labels]
        for idx, label in enumerate(labels):
            if norm_labels[idx] in aliases and idx < len(matrix):
                row = matrix[idx]
                if isinstance(row, list):
                    for j, sim in enumerate(row):
                        if j < len(labels):
                            add_pair(labels[j], sim)

    # De-duplicate by peer and sort descending.
    best: dict[str, Any] = {}
    for name, sim in rows:
        val = _to_float(sim)
        if val is None:
            continue
        if val > 1:
            val = val / 100.0
        if name not in best or val > (_to_float(best[name]) or -1):
            best[name] = val
    return sorted(best.items(), key=lambda x: _to_float(x[1]) or -1, reverse=True)


def render_step5(company: str, company_dir: str, a: dict[str, Any]) -> str:
    data = a.get("peer_similarity") or {}
    method = _coalesce(_first_key(data, ["method", "algorithm"], None), default="TF-IDF + Cosine Similarity")
    rows = _extract_similarity_rows(data, company_dir, company)
    lines = [
        "## Step 5. Focal-company cosine similarity",
        f"- **산출물 상태:** {_artifact_status(a.get('peer_similarity_path'))}",
        f"- **분석 방법:** {_clean(method, 80)}",
        "",
        "| 비교 기업 | Cosine Similarity | 해석 |",
        "|---|---:|---|",
    ]
    if rows:
        for name, sim in rows:
            lines.append(f"| {_clean(name, 50)} | {_fmt(sim, decimals=4)} | 특허 텍스트 포트폴리오의 기술 유사도입니다. |")
    else:
        lines.append("| 비교군 | 산출물 원문 참조 | pairwise/matrix/company_pairs 중 회사명 매칭 구조 확인 필요 |")
    lines.append("\n- Cosine Similarity는 기술 텍스트 유사도 신호이며, 재무 건전성이나 주가 방향을 직접 의미하지 않습니다.")
    return "\n".join(lines) + "\n"


def render_step6(company: str, company_dir: str, a: dict[str, Any]) -> str:
    data = a.get("peer_cluster") or {}
    cluster = _coalesce(_first_key(data, ["cluster_id", "cluster", "assigned_cluster", "kmeans_cluster"], None), default=None)
    label = _coalesce(_first_key(data, ["peer_group_label", "cluster_label", "peer_group", "label", "cluster_name"], None), default="후공정/패키징/테스트")
    peers = _coalesce(_first_key(data, ["peer_candidates", "peers", "same_cluster_peers", "neighbors", "cluster_members"], None), default=[])
    lines = [
        "## Step 6. Reference-universe company-level KMeans peer group",
        f"- **산출물 상태:** {_artifact_status(a.get('peer_cluster_path'))}",
        "| 항목 | 값 |",
        "|---|---|",
        f"| 현재 기업 cluster | {_fmt(cluster)} |",
        f"| Peer group | {_clean(label, 80)} |",
        "| Reference universe | valuation/credit ML overlay 기반 딥테크 후보군 |",
    ]
    if isinstance(peers, list) and peers:
        lines.extend(["", "| Peer 후보 | 근거 |", "|---|---|"])
        for p in peers[:10]:
            if isinstance(p, dict):
                name = _coalesce(p.get("company_name"), p.get("name"), p.get("company"), p.get("company_dir"), default="원문 산출물 참조")
                basis = _coalesce(p.get("basis"), p.get("reason"), p.get("cluster_label"), default="동일/인접 기술 cluster")
            else:
                name, basis = p, "동일/인접 기술 cluster"
            if _norm_key(name) not in {_norm_key(x) for x in _aliases(company_dir, company)}:
                lines.append(f"| {_clean(name, 50)} | {_clean(basis, 90)} |")
    lines.append("\n- Company-level KMeans는 기업 단위 특허/IP 특징량을 기준으로 기술 peer group을 배정합니다.")
    return "\n".join(lines) + "\n"


def render_step7(company: str, company_dir: str, a: dict[str, Any]) -> str:
    data = a.get("peer_map") or {}
    x = _first_key(data, ["umap_x", "x", "x_coord", "coord_x"], None)
    y = _first_key(data, ["umap_y", "y", "y_coord", "coord_y"], None)
    cluster = _first_key(data, ["cluster_id", "cluster", "assigned_cluster"], None)
    png = _first_key(data, ["map_png", "png_path", "figure_path", "image_path"], None)
    if _is_missing(png):
        png_path = _find_png(company_dir, company, "tech_peer_map.png", f"{company_dir}_tech_peer_map.png", "deeptech_peer_map.png", "umap_peer_map.png")
        png = png_path if png_path else None
    lines = [
        "## Step 7. UMAP 2D tech peer map",
        f"- **산출물 상태:** {_artifact_status(a.get('peer_map_path'))}",
        "| 항목 | 값 |",
        "|---|---:|",
        f"| UMAP x | {_fmt(x)} |",
        f"| UMAP y | {_fmt(y)} |",
        f"| Cluster | {_fmt(cluster)} |",
        f"| Map PNG | `{_rel(png) if png else '원문 확인 필요'}` |",
        "",
        "- UMAP 2D Peer Map은 고차원 특허/IP 특징량을 2차원으로 압축해 peer 위치를 설명하는 시각화 보조지표입니다.",
        "- 한글 폰트는 시스템에 설치된 Malgun Gothic/Noto Sans CJK/AppleGothic을 우선 사용하도록 처리합니다.",
    ]
    return "\n".join(lines) + "\n"


def render_step8(company: str, a: dict[str, Any]) -> str:
    data = a.get("peer_percentile") or {}
    adjusted = _first_key(data, ["peer_adjusted_bridge_score", "adjusted_bridge_score", "adjusted_score"], None)
    base = _first_key(data, ["base_bridge_score", "base_score", "tech_to_value_bridge_score"], None)
    final_grade = _coalesce(_first_key(data, ["final_bridge_grade", "bridge_grade", "grade"], None), _infer_bridge_grade_from_score(adjusted), _infer_bridge_grade_from_score(base), default="별도 판정 미생성")
    lines = [
        "## Step 8. Peer-percentile adjusted Tech-to-Value Bridge",
        f"- **산출물 상태:** {_artifact_status(a.get('peer_percentile_path'))}",
        "| 항목 | 값 | 해석 |",
        "|---|---:|---|",
        f"| Base Bridge Score | {_score(base)} | Tech-to-Value 기본 점수입니다. |",
        f"| Peer-adjusted Bridge Score | {_score(adjusted)} | reference universe 내 상대 위치를 반영한 보정 점수입니다. |",
        f"| Peer Percentile | {_pct(_first_key(data, ['peer_percentile', 'percentile', 'reference_percentile']))} | 같은 기술군 내 상대 순위입니다. |",
        f"| Final Bridge Grade | {_clean(final_grade, 70)} | Chair 반영 시 보수 판단 기준입니다. |",
        "",
        "- 이 보정은 기술/IP 상대 위치를 설명하기 위한 return-free 보조 지표이며, 미래 수익률 예측이 아닙니다.",
    ]
    return "\n".join(lines) + "\n"


def _topic_rows(data: Any) -> list[tuple[str, Any, str]]:
    topics = _coalesce(_first_key(data, ["dominant_topics", "topics", "nmf_topics"], None), default=[])
    out: list[tuple[str, Any, str]] = []
    if isinstance(topics, list):
        for t in topics[:5]:
            if isinstance(t, dict):
                label = _coalesce(t.get("topic_label"), t.get("label"), t.get("name"), default=f"Topic {t.get('topic_id', '')}".strip())
                weight = _coalesce(t.get("topic_weight"), t.get("weight"), t.get("score"), t.get("ratio"))
                terms = _coalesce(t.get("terms"), t.get("keywords"), t.get("top_terms"), default=label)
            else:
                label, weight, terms = str(t), None, str(t)
            out.append((_clean(label, 90), weight, " / ".join(_filter_terms(terms, 6)) or _clean(terms, 80)))
    return out


def render_step9(company: str, a: dict[str, Any]) -> str:
    data = a.get("tech_ip_ml") or {}
    raw = _raw_metrics(data)
    lines = [
        "## Step 9. Tech/IP Strength Index + NMF Topic Modeling",
        f"- **산출물 상태:** {_artifact_status(a.get('tech_ip_ml_path'))}",
        "### 9-1. Tech/IP Strength Index",
        "| 항목 | 값 | 해석 |",
        "|---|---:|---|",
        f"| Tech/IP Strength Index | {_score(_first_key(data, ['tech_ip_strength_index', 'tech_ip_strength_score', 'score']))} | 특허 등록률·존속성·최근성·IPC/CPC 다양성·핵심기술 키워드 밀도 점수를 통합한 IP 강도 지표입니다. |",
        f"| Reference Universe Percentile | {_pct(_first_key(data, ['tech_ip_strength_percentile', 'reference_percentile', 'percentile']))} | reference universe 안에서의 상대적 기술/IP 위치입니다. |",
        f"| Patent Momentum Score | {_score(_first_key(data, ['patent_momentum_score', 'momentum_score']))} | 최근 특허 활동과 기술 포트폴리오 지속성을 반영합니다. |",
        "",
        "### 9-2. 특허/IP 원천 신호",
        "| 원천 신호 | 값 |",
        "|---|---:|",
        f"| 정규화 특허 텍스트 레코드 | {_fmt(_coalesce(raw.get('normalized_patent_records'), raw.get('analysis_patent_text_records')), '건')} |",
        f"| 회사 출원인/권리자 매칭 | {_fmt(_coalesce(raw.get('company_matched_patents'), raw.get('applicant_matched_patents'), raw.get('matched_records')), '건')} |",
        f"| 등록 특허 | {_fmt(raw.get('registered_patents'), '건')} |",
        f"| 존속 가능 특허 | {_fmt(_coalesce(raw.get('active_patents'), raw.get('valid_patents')), '건')} |",
        f"| 최근 5년 특허 | {_fmt(raw.get('recent_5y_patents'), '건')} |",
        f"| IPC/CPC 다양성 | {_fmt(raw.get('ipc_cpc_classes'), '개')} |",
        f"| H01L 등 핵심 IPC 특허 | {_fmt(raw.get('core_ipc_h01l_patents'), '건')} |",
        f"| 핵심기술 키워드 매칭 | {_fmt(raw.get('patent_keyword_matches'), '회')} |",
        f"| 핵심기술 키워드 밀도 점수 | {_score(_coalesce(raw.get('keyword_density_score'), raw.get('keyword_density')))} |",
        "",
        "### 9-3. NMF Topic Modeling",
        "| Topic | 비중/점수 | 대표 키워드 |",
        "|---|---:|---|",
    ]
    topics = _topic_rows(data)
    if topics:
        for label, weight, terms in topics[:5]:
            lines.append(f"| {label} | {_fmt(weight, decimals=3)} | {terms} |")
    else:
        lines.append("| Topic | 산출물 원문 참조 | `dominant_topics`/`topics` 구조 확인 필요 |")
    interpretation = _first_key(data, ["interpretation", "chair_interpretation", "summary"], None)
    lines.extend(["", "### 9-4. 해석", f"- {_clean(interpretation or f'{company}의 Tech/IP Strength Index는 특허/IP 포트폴리오 상대 강도 신호입니다.', 340)}"])
    return "\n".join(lines) + "\n"


def render_step10(company: str, a: dict[str, Any]) -> str:
    data = a.get("tech_differentiation") or {}
    interp = _first_key(data, ["interpretation", "chair_interpretation", "summary"], None)
    score = _first_key(data, ["technology_differentiation_score", "differentiation_score", "score"], None)
    percentile = _coalesce(
        _first_key(data, ["reference_percentile", "percentile", "differentiation_percentile"], None),
        _num_from_text(interp, r"percentile\s*([0-9]+(?:\.[0-9]+)?)", r"percentile[은는\s]*([0-9]+(?:\.[0-9]+)?)"),
    )
    raw_grade = _coalesce(_first_key(data, ["raw_grade", "grade", "grade_code"], None), _infer_diff_grade_from_score(score), default=None)
    grade = _coalesce(_first_key(data, ["grade_kr", "grade_label_kr", "grade_label"], None), GRADE_KR.get(str(raw_grade)), default=None)
    if _is_missing(grade) and interp:
        for cand in ["차별화 리더형", "차별화 확인형", "보통 차별화형", "차별화 제한형"]:
            if cand in str(interp):
                grade = cand
                break
    nearest = _first_key(data, ["nearest_peer", "nearest_tech_peer"], None)
    if isinstance(nearest, dict):
        nearest_name = _coalesce(nearest.get("company_name"), nearest.get("name"), nearest.get("company"), nearest.get("company_dir"))
        nearest_sim = _coalesce(nearest.get("cosine_similarity"), nearest.get("similarity"), nearest.get("score"))
        nearest_dist = _coalesce(nearest.get("technology_distance"), nearest.get("distance"))
    else:
        nearest_name = nearest
        nearest_sim = _first_key(data, ["nearest_peer_similarity", "cosine_similarity"], None)
        nearest_dist = _first_key(data, ["technology_distance", "nearest_peer_distance"], None)
    dom_topic = _first_key(data, ["dominant_nmf_topic", "dominant_topic"], None)
    if isinstance(dom_topic, dict):
        topic_label = _coalesce(dom_topic.get("topic_label"), dom_topic.get("label"), dom_topic.get("name"))
        topic_weight = _coalesce(dom_topic.get("topic_weight"), dom_topic.get("weight"), dom_topic.get("score"))
        topic_rarity = _coalesce(dom_topic.get("topic_rarity"), dom_topic.get("rarity"))
    else:
        topic_label = dom_topic
        topic_weight = _first_key(data, ["topic_weight"], None)
        topic_rarity = _first_key(data, ["topic_rarity"], None)
    comps = _first_key(data, ["component_scores", "components"], {}) or {}
    raw = _raw_metrics(data, a.get("tech_ip_ml") or {})
    keywords = _coalesce(_first_key(data, ["unique_keywords", "differentiation_keywords", "top_unique_terms", "unique_terms"], None), default=[])
    filtered_keywords = _filter_terms(keywords, limit=12)
    if not filtered_keywords and interp:
        # 마지막 fallback은 해석문에서 기술어만 일부 추출한다.
        filtered_keywords = _filter_terms(re.findall(r"[가-힣A-Za-z0-9+/]{2,}(?:\s+[가-힣A-Za-z0-9+/]{2,})?", str(interp)), limit=8)

    lines = [
        "## Step 10. Technology Differentiation Score",
        f"- **산출물 상태:** {_artifact_status(a.get('tech_differentiation_path'))}",
        "### 10-1. Technology Differentiation Score 요약",
        "| 항목 | 값 | 해석 |",
        "|---|---:|---|",
        f"| Technology Differentiation Score | {_score(score)} | peer 대비 특허/IP 포트폴리오가 얼마나 구별되는지 보는 비지도 ML 기반 차별화 점수입니다. |",
        f"| Reference Percentile | {_pct(percentile)} | 분석 universe 안에서의 상대적 차별화 위치입니다. |",
        f"| Grade | {_clean(grade, 50)} | 원문 grade: `{_clean(raw_grade, 50)}` |",
        f"| Nearest Tech Peer | {_clean(nearest_name, 40)} | cosine similarity={_fmt(nearest_sim, decimals=4)}, technology distance={_fmt(nearest_dist, decimals=4)} |",
        f"| Dominant NMF Topic | {_clean(topic_label, 90)} | topic weight={_fmt(topic_weight, decimals=4)}, topic rarity={_fmt(topic_rarity)} |",
        "",
        "### 10-2. 구성 점수",
        "| 구성 요소 | 값 | 의미 |",
        "|---|---:|---|",
        f"| Peer uniqueness | {_score(_first_key(comps, ['peer_uniqueness', 'peer_uniqueness_score']))} | 가장 가까운 peer와의 기술 텍스트 거리입니다. |",
        f"| Topic distinctiveness | {_score(_first_key(comps, ['topic_distinctiveness', 'topic_distinctiveness_score']))} | NMF dominant topic 집중도와 희소성을 반영합니다. |",
        f"| IPC specialization | {_score(_first_key(comps, ['ipc_specialization', 'ipc_specialization_score']))} | IPC/CPC 다양성과 핵심 IPC 집중도를 반영합니다. |",
        f"| Keyword uniqueness | {_score(_first_key(comps, ['keyword_uniqueness', 'keyword_uniqueness_score']))} | TF-IDF 상위 용어 중 고유 기술어 비중입니다. |",
        "",
        "### 10-3. 차별화 근거 신호",
        "| 원천 신호 | 값 |",
        "|---|---:|",
        f"| 차별화 분석용 특허 텍스트 레코드 | {_fmt(_coalesce(raw.get('analysis_patent_text_records'), raw.get('normalized_patent_records')), '건')} |",
        f"| 회사 출원인/권리자 매칭 | {_fmt(_coalesce(raw.get('company_matched_patents'), raw.get('applicant_matched_patents'), raw.get('matched_records')), '건')} |",
        f"| 등록 특허 | {_fmt(raw.get('registered_patents'), '건')} |",
        f"| 존속 가능 특허 | {_fmt(_coalesce(raw.get('active_patents'), raw.get('valid_patents')), '건')} |",
        f"| 최근 5년 특허 | {_fmt(raw.get('recent_5y_patents'), '건')} |",
        f"| IPC/CPC 다양성 | {_fmt(raw.get('ipc_cpc_classes'), '개')} |",
        f"| H01L 등 핵심 IPC 특허 | {_fmt(raw.get('core_ipc_h01l_patents'), '건')} |",
        "",
        "### 10-4. 고유 기술어 / 차별화 키워드",
        f"- {', '.join(filtered_keywords) if filtered_keywords else '산출물 원문 확인 필요'}",
        "",
        "### 10-5. 해석",
        f"- {_clean(interp or f'{company}의 Technology Differentiation Score는 peer 대비 기술/IP 포트폴리오 차별성 신호입니다.', 360)}",
        "- 현재는 5개 focal 기업 중심 검증 단계이며, 30개 reference universe 전체에 동일한 산출 방식을 확장 적용하면 percentile 해석의 안정성과 비교 설명력이 강화됩니다.",
    ]
    return "\n".join(lines) + "\n"


def render_step11(company: str, a: dict[str, Any]) -> str:
    data = a.get("tech_momentum_confidence") or {}
    pm = _first_key(data, ["patent_momentum", "momentum"], {}) or {}
    ev = _first_key(data, ["tech_to_value_evidence_confidence", "evidence_confidence"], {}) or {}
    dims = _first_key(ev, ["dimensions", "businessization_dimensions"], {}) or {}

    def dim(key: str, label: str) -> str:
        d = dims.get(key, {}) if isinstance(dims, dict) else {}
        return (
            f"| {label} | {_clean(_coalesce(d.get('status_kr'), d.get('status')), 40)} | "
            f"{_fmt(d.get('direct_evidence_count'), none='0')} | {_fmt(d.get('indirect_evidence_count'), none='0')} | {_fmt(d.get('limited_evidence_count'), none='0')} |"
        )

    lines = [
        "## Step 11. Patent Momentum Score + Tech-to-Value Evidence Confidence",
        f"- **산출물 상태:** {_artifact_status(a.get('tech_momentum_confidence_path'))}",
        "### 11-1. Patent Momentum Score",
        "| 항목 | 값 | 해석 |",
        "|---|---:|---|",
        f"| Patent Momentum Score | {_score(_first_key(pm, ['patent_momentum_score', 'score']))} | 최근 특허 활동과 기술 포트폴리오 지속성 신호입니다. |",
        f"| Momentum Grade | {_clean(_first_key(pm, ['grade_kr', 'grade'], None), 80)} | 최근성·지속성 기준 보조 등급입니다. |",
        "",
        "### 11-2. Tech-to-Value Evidence Confidence",
        "| 항목 | 값 | 해석 |",
        "|---|---:|---|",
        f"| Evidence Confidence | {_score(_first_key(ev, ['tech_to_value_evidence_confidence_score', 'evidence_confidence_score', 'score']))} | 고객 채택·양산·매출·FCF 근거의 직접성을 보수적으로 평가합니다. |",
        f"| Confidence Grade | {_clean(_first_key(ev, ['grade_kr', 'grade'], None), 90)} | 2차 산출물보다 직접 원천 근거를 우선하는 보수 기준입니다. |",
        f"| Direct Dimension Count | {_fmt(_first_key(ev, ['direct_dimension_count'], None))}/4 | 직접 근거가 확인된 사업화 연결 항목 수입니다. |",
        "",
        "### 11-3. 고객 채택·양산·매출·FCF별 직접성",
        "| 항목 | 상태 | 직접 근거 | 간접 근거 | 원문 확인 필요 |",
        "|---|---|---:|---:|---:|",
        dim("customer_adoption", "고객 채택"),
        dim("mass_production", "양산"),
        dim("revenue_conversion", "매출 전환"),
        dim("fcf_cashflow", "FCF/현금흐름"),
        "",
        "- Evidence Confidence는 `agent_output`, `generated_report` 등 2차 산출물보다 DART/IR/공시/CSV 직접 수치 근거를 더 강하게 인정합니다.",
        "- 대표 스니펫이 문서 첫머리·목차·생성 보고서 헤더에 가까우면 강한 근거로 사용하지 않습니다.",
    ]
    return "\n".join(lines) + "\n"


def render_inventory(a: dict[str, Any]) -> str:
    labels = [
        ("chair_summary", "chair_summary_path"), ("tech_packet", "tech_packet_path"), ("high_quality_md", "high_quality_md_path"),
        ("tech_to_value", "tech_to_value_path"), ("patent_json", "patent_json_path"), ("ml_signal", "ml_signal_path"),
        ("peer_similarity", "peer_similarity_path"), ("peer_cluster", "peer_cluster_path"), ("peer_map", "peer_map_path"),
        ("peer_percentile", "peer_percentile_path"), ("tech_ip_ml", "tech_ip_ml_path"),
        ("tech_differentiation", "tech_differentiation_path"), ("tech_momentum_confidence", "tech_momentum_confidence_path"),
    ]
    lines = ["## Artifact inventory", "| 구분 | 경로 | 상태 |", "|---|---|---|"]
    for label, key in labels:
        path = a.get(key)
        lines.append(f"| {label} | `{_rel(path)}` | {'확인됨' if path else '미확인'} |")
    return "\n".join(lines) + "\n"


def render_investor_scorecard(company_dir: str) -> str:
    """Render the deterministic investor-facing final Tech score if available."""
    try:
        from .investor_tech_view import render_investor_tech_view_markdown
    except Exception:
        try:
            from tech_agent.investor_tech_view import render_investor_tech_view_markdown
        except Exception:
            return "## Final Investor Tech Scorecard\n\n- scorecard module: 확인 제한\n"

    candidates = [
        _company_tech_dir(company_dir, DEFAULT_COMPANY_NAMES.get(company_dir, company_dir)) / "tech_investor_scorecard.json",
        _company_tech_dir(company_dir, DEFAULT_COMPANY_NAMES.get(company_dir, company_dir)) / "tech_chair_summary.json",
    ]
    view = {}
    for path in candidates:
        data = _read_json(path)
        if not isinstance(data, dict) or not data:
            continue
        if "final_tech_investor_score" in data or "final_investor_tech_score" in data:
            view = data
            break
        if isinstance(data.get("investor_tech_view"), dict):
            view = data.get("investor_tech_view") or {}
            break
    if not view:
        return "## Final Investor Tech Scorecard\n\n- 아직 `tech_investor_scorecard.json`이 생성되지 않았습니다. `python main.py tech ...` 또는 tech_intake를 먼저 실행하세요.\n"
    md = render_investor_tech_view_markdown(view)
    md = md.replace("## 개인투자자용 최종 Tech Scorecard", "## Final Investor Tech Scorecard")
    return md


def build_tech_full_report(
    company_dir: str,
    company: str | None = None,
    company_name: str | None = None,
    save: bool = True,
    opinion: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    company_dir = _slug(company_dir)
    company_display = _display_company(company_dir, company=company, company_name=company_name)
    artifacts = load_artifacts(company_dir, company_display)
    sections = [
        f"# {company_display} Tech Agent Full Appendix",
        "",
        f"- **생성 시각:** {_now()}",
        "- **목적:** Chair 보고서에는 compact summary만 전달하고, Excel-frame·KIPRIS/IP·Tech ML 상세 산출물은 Tech Agent가 소유하는 풀버전 부록입니다.",
        "- **검증 원칙:** 이 부록은 미래수익률 예측이 아니라 특허/IP·사업화 근거·peer 상대위치 기반 return-free 기술 설명 지표를 정리합니다.",
        "",
        render_prompt_policy_overview(),
        render_investor_scorecard(company_dir),
        render_step1(company_display, artifacts),
        render_step2(company_display, artifacts),
        render_step3(company_display, artifacts),
        render_step4(company_display, artifacts),
        render_step5(company_display, company_dir, artifacts),
        render_step6(company_display, company_dir, artifacts),
        render_step7(company_display, company_dir, artifacts),
        render_step8(company_display, artifacts),
        render_step9(company_display, artifacts),
        render_step10(company_display, artifacts),
        render_step11(company_display, artifacts),
        render_inventory(artifacts),
    ]
    md = "\n".join(part.rstrip() for part in sections if part is not None).rstrip() + "\n"
    output_dir = _company_tech_dir(company_dir, company_display)
    md_path = output_dir / f"{company_dir}_tech_full_appendix.md"
    json_path = output_dir / "tech_full_appendix.json"
    result = {
        "company": company_display,
        "company_dir": company_dir,
        "created_at": _now(),
        "purpose": "Tech-owned long appendix; Chair uses compact summary only.",
        "opinion": opinion,
        "path": _rel(md_path),
        "included_sections": [
            "Shared Tech Rubric Alignment",
            "Step 1 Excel-frame based technology position",
            "Step 2 Tech-to-Value Bridge",
            "Step 3 KIPRIS/IP quantitative signals",
            "Step 4 Patent KMeans clustering",
            "Step 5 Focal-company cosine similarity",
            "Step 6 Reference-universe company-level KMeans peer group",
            "Step 7 UMAP 2D tech peer map",
            "Step 8 Peer-percentile adjusted Tech-to-Value Bridge",
            "Step 9 Tech/IP Strength Index + NMF Topic Modeling",
            "Step 10 Technology Differentiation Score",
            "Step 11 Patent Momentum Score + Tech-to-Value Evidence Confidence",
        ],
        "markdown": md,
    }
    if save:
        _write_text(md_path, md)
        compact_result = {k: v for k, v in result.items() if k != "markdown"}
        _write_json(json_path, compact_result)
        # workspace legacy mirror removed: canonical outputs are saved only under data/반도체/<회사명>/tech.
    return result


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build Tech Agent full appendix with Step 1~11.")
    parser.add_argument("--company-dir", required=True, help="Company slug, e.g. nepes")
    parser.add_argument("--company", default=None, help="Display company name, e.g. 네패스")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args(argv)
    res = build_tech_full_report(args.company_dir, company=args.company, save=not args.no_save)
    print(f"[Tech Full Appendix] generated: {res['path']}")
    if not args.no_save:
        print("[Tech Full Appendix] saved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
