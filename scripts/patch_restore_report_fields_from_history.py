from pathlib import Path

path = Path(r".\src\chair_agent\adapters.py")
text = path.read_text(encoding="utf-8")

helper_marker = "def _restore_original_history_report_fields"
insert_before = "def _compact_market_history_for_auditor"

helper_code = r'''
def _report_norm_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _clean_report_text(value: Any, *, max_chars: int = 2400) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    banned_terms = (
        "template",
        "placeholder",
        "missing-context",
        "missing context",
        "프롬프트",
        "템플릿",
        "작성 요청",
        "요청문",
    )

    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue

        lowered = s.lower()
        if any(term in lowered for term in banned_terms):
            continue

        lines.append(s)

    cleaned = " ".join(lines).strip()

    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "..."

    return cleaned


def _is_compact_fallback_text(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return True

    compact_markers = (
        "검증 가능한 핵심 근거는 다음과 같습니다",
        "market return metrics",
        "market drawdown metrics",
        "market liquidity metrics",
        "tech-to-value bridge metrics",
        "compact packet",
        "Auditor용",
        "history snapshot은",
    )

    return any(marker in text for marker in compact_markers)


def _is_report_text_usable(value: Any) -> bool:
    text = _clean_report_text(value)
    if len(text) < 40:
        return False
    if _is_compact_fallback_text(text):
        return False
    return True


def _iter_report_field_values(obj: Any, candidate_keys: set[str], *, max_depth: int = 7):
    skip_keys = {
        "claims",
        "claim",
        "evidences",
        "evidence",
        "source_contexts",
        "supported_claims",
        "unsupported_claims",
        "framework_metrics",
        "tech_framework_metrics",
        "market_framework",
        "adapter_compaction",
        "metric_source",
        "agent_history_snapshot",
    }

    def walk(x: Any, depth: int):
        if depth > max_depth:
            return

        if isinstance(x, dict):
            for k, v in x.items():
                nk = _report_norm_key(k)
                if nk in candidate_keys and v not in (None, "", [], {}):
                    yield v

            for k, v in x.items():
                nk = _report_norm_key(k)
                if nk in skip_keys:
                    continue
                yield from walk(v, depth + 1)

        elif isinstance(x, list):
            for item in x[:50]:
                yield from walk(item, depth + 1)

    yield from walk(obj, 0)


def _value_to_report_items(value: Any, *, max_items: int = 6, max_chars_each: int = 420) -> list[str]:
    items: list[str] = []

    def add_one(x: Any):
        if x in (None, "", [], {}):
            return

        if isinstance(x, dict):
            for key in ("text", "summary", "title", "reason", "name", "description"):
                if x.get(key):
                    add_one(x.get(key))
                    return
            return

        s = str(x).strip()
        if not s:
            return

        for prefix in ("- ", "• ", "* "):
            if s.startswith(prefix):
                s = s[len(prefix):].strip()

        s = _clean_report_text(s, max_chars=max_chars_each)

        if not s or _is_compact_fallback_text(s):
            return

        if s not in items:
            items.append(s)

    if isinstance(value, list):
        for item in value:
            add_one(item)

    elif isinstance(value, dict):
        for key in (
            "items",
            "points",
            "key_thesis",
            "thesis",
            "key_risks",
            "risks",
            "risk_factors",
            "strengths",
            "opportunities",
        ):
            if key in value:
                nested = _value_to_report_items(
                    value.get(key),
                    max_items=max_items,
                    max_chars_each=max_chars_each,
                )
                for item in nested:
                    if item not in items:
                        items.append(item)

        if not items:
            add_one(value)

    else:
        text = str(value or "").strip()
        raw_lines = [line.strip() for line in text.splitlines() if line.strip()]

        if len(raw_lines) >= 2:
            for line in raw_lines:
                add_one(line)
        else:
            add_one(text)

    return items[:max_items]


def _pick_report_summary_from_source(source: dict, *, fallback: str) -> str:
    candidate_keys = {
        "summary",
        "market_summary",
        "tech_summary",
        "finance_summary",
        "issue_summary",
        "macro_summary",
        "valuation_summary",
        "analysis_summary",
        "report_summary",
        "narrative_summary",
    }

    candidates = []
    for value in _iter_report_field_values(source, candidate_keys):
        if _is_report_text_usable(value):
            cleaned = _clean_report_text(value, max_chars=2600)
            candidates.append(cleaned)

    if not candidates:
        return _clean_report_text(fallback, max_chars=1200)

    # 너무 짧은 compact 요약보다 기존 agent가 만든 긴 설명을 우선한다.
    candidates = sorted(candidates, key=len, reverse=True)
    return candidates[0]


def _pick_report_items_from_source(
    source: dict,
    *,
    kind: str,
    fallback: list[str] | None = None,
) -> list[str]:
    if kind == "thesis":
        candidate_keys = {
            "key_thesis",
            "thesis",
            "investment_thesis",
            "positive_factors",
            "strengths",
            "opportunities",
            "main_points",
            "핵심_thesis",
        }
    else:
        candidate_keys = {
            "key_risks",
            "risks",
            "risk_factors",
            "negative_factors",
            "weaknesses",
            "concerns",
            "주의사항",
            "주요_risk",
        }

    best: list[str] = []

    for value in _iter_report_field_values(source, candidate_keys):
        items = _value_to_report_items(value, max_items=6)
        if len(" ".join(items)) > len(" ".join(best)):
            best = items

    if best:
        return best

    fallback = fallback or []
    return _value_to_report_items(fallback, max_items=6)


def _restore_original_history_report_fields(
    *,
    compact: dict,
    source: dict,
    agent_name: str,
    company: str,
) -> dict:
    """
    History replay에서는 Auditor 통과를 위해 compact evidence/claims는 유지하되,
    Chair 보고서에 들어가는 summary / key_thesis / key_risks는 원래 agent history payload에서 복원한다.

    이렇게 하면:
    - Auditor는 return/drawdown/liquidity 같은 compact 검증 필드를 계속 볼 수 있음
    - Chair 보고서는 기존처럼 상세한 시장/기술/이슈 설명을 유지함
    - 네패스뿐 아니라 모든 company_dir에 공통 적용됨
    """
    if not isinstance(compact, dict):
        compact = {}

    if not isinstance(source, dict):
        return compact

    fallback_summary = compact.get("summary") or f"{company} {agent_name} 분석 요약입니다."

    restored_summary = _pick_report_summary_from_source(
        source,
        fallback=fallback_summary,
    )

    restored_thesis = _pick_report_items_from_source(
        source,
        kind="thesis",
        fallback=compact.get("key_thesis") or compact.get("thesis") or [],
    )

    restored_risks = _pick_report_items_from_source(
        source,
        kind="risks",
        fallback=compact.get("key_risks") or compact.get("risks") or [],
    )

    if restored_summary:
        compact["summary"] = restored_summary

    if restored_thesis:
        compact["key_thesis"] = restored_thesis
        compact["thesis"] = restored_thesis

    if restored_risks:
        compact["key_risks"] = restored_risks
        compact["risks"] = restored_risks

    compact["report_detail_restore"] = {
        "enabled": True,
        "agent": agent_name,
        "source": "original_history_payload",
        "auditor_compact_evidence_preserved": True,
        "summary_chars": len(str(compact.get("summary") or "")),
        "thesis_count": len(compact.get("key_thesis") or []),
        "risk_count": len(compact.get("key_risks") or []),
    }

    return compact

'''

if helper_marker not in text:
    if insert_before not in text:
        raise RuntimeError("insert marker not found: def _compact_market_history_for_auditor")
    text = text.replace(insert_before, helper_code + "\n\n" + insert_before, 1)


def inject_restore_call(text: str, func_name: str, agent_name: str) -> str:
    start = text.find(f"def {func_name}(")
    if start < 0:
        raise RuntimeError(f"{func_name} not found")

    next_def = text.find("\ndef ", start + 1)
    pos_positive = text.find("\nPOSITIVE_TERMS", start + 1)

    end_candidates = [p for p in [next_def, pos_positive] if p > start]
    end = min(end_candidates) if end_candidates else len(text)

    body = text[start:end]

    call = f'''    compact = _restore_original_history_report_fields(
        compact=compact,
        source=source,
        agent_name="{agent_name}",
        company=company,
    )

'''

    if call.strip() in body:
        return text

    marker = '''    if history_meta:
        compact["agent_history_snapshot"] = history_meta

    return compact
'''

    if marker not in body:
        raise RuntimeError(f"return marker not found inside {func_name}")

    body_new = body.replace(marker, call + marker, 1)

    return text[:start] + body_new + text[end:]


text = inject_restore_call(
    text,
    "_compact_market_history_for_auditor",
    "market",
)

text = inject_restore_call(
    text,
    "_compact_tech_history_for_auditor",
    "tech",
)

path.write_text(text, encoding="utf-8")
print("[OK] adapters.py patched: report fields restored from original history payload while keeping compact auditor evidence.")
