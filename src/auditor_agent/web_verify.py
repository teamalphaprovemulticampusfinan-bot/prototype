from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

import requests


UNVERIFIED_SOURCE_TYPES = {
    "agent_output_unverified",
    "llm_only",
    "self_generated",
    "generated",
    "unknown",
}

SERPER_URL = "https://google.serper.dev/search"
NAVER_NEWS_URL = "https://openapi.naver.com/v1/search/news.json"


@dataclass
class WebVerifyLLM:
    api_key: str
    base_url: str
    model: str
    provider: str = "openai_compatible"
    timeout: int = 60
    max_tokens: int = 2048


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value and str(value).strip():
            return str(value).strip()
    return default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or str(value).strip() == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(*names: str, default: int = 2048) -> int:
    value = _env_first(*names, default=str(default))
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _normalize_provider(value: str | None) -> str:
    provider = str(value or "").strip().lower().replace("-", "_")
    if provider in {"gemini", "google", "google_gemini"}:
        return "gemini"
    if provider in {"anthropic", "claude"}:
        return "anthropic"
    if provider in {"nvidia", "openai", "openai_compatible", "openai_compat", "web_verify", ""}:
        return "openai_compatible"
    return provider


def _auditor_provider() -> str:
    return _normalize_provider(
        _env_first(
            "AUDITOR_LLM_PROVIDER",
            "AUDITOR_PROVIDER",
            "WEB_VERIFY_PROVIDER",
            default="anthropic",
        )
    )


def _provider_candidates(preferred: str) -> list[str]:
    order = [preferred, "anthropic", "gemini", "openai_compatible"]
    out: list[str] = []
    for provider in order:
        normalized = _normalize_provider(provider)
        if normalized and normalized not in out:
            out.append(normalized)
    return out


def _build_llm_for_provider(provider: str) -> WebVerifyLLM | None:
    provider = _normalize_provider(provider)
    timeout = _env_int("AUDITOR_LLM_TIMEOUT", "WEB_VERIFY_TIMEOUT", "REQUEST_TIMEOUT", default=60)

    if provider == "gemini":
        api_key = _env_first(
            "AUDITOR_GEMINI_API_KEY",
            "GEMINI_AUDITOR_API_KEY",
            "GEMINI_PARALLEL_API_KEY",
            "GEMINI_API_KEY",
        )
        if not api_key:
            return None
        return WebVerifyLLM(
            api_key=api_key,
            base_url=_env_first(
                "AUDITOR_GEMINI_BASE_URL",
                "GEMINI_AUDITOR_BASE_URL",
                "GEMINI_BASE_URL",
                default="https://generativelanguage.googleapis.com/v1beta",
            ).rstrip("/"),
            model=_env_first(
                "AUDITOR_GEMINI_MODEL",
                "GEMINI_AUDITOR_MODEL",
                "AUDITOR_MODEL",
                "WEB_VERIFY_MODEL",
                "GEMINI_PARALLEL_MODEL",
                "GEMINI_MODEL",
                default="gemini-2.5-flash-lite",
            ),
            provider="gemini",
            timeout=timeout,
            max_tokens=_env_int(
                "AUDITOR_GEMINI_MAX_TOKENS",
                "GEMINI_AUDITOR_MAX_TOKENS",
                "AUDITOR_MAX_TOKENS",
                "WEB_VERIFY_MAX_TOKENS",
                "GEMINI_MAX_OUTPUT_TOKENS",
                default=2048,
            ),
        )

    if provider == "anthropic":
        api_key = _env_first(
            "ANTHROPIC_AUDITOR_API_KEY",
            "AUDITOR_ANTHROPIC_API_KEY",
            "ANTHROPIC_API_KEY",
        )
        if not api_key:
            return None
        return WebVerifyLLM(
            api_key=api_key,
            base_url=_env_first(
                "ANTHROPIC_AUDITOR_BASE_URL",
                "AUDITOR_ANTHROPIC_BASE_URL",
                "ANTHROPIC_BASE_URL",
                default="https://api.anthropic.com",
            ).rstrip("/"),
            model=_env_first(
                "ANTHROPIC_AUDITOR_MODEL",
                "AUDITOR_ANTHROPIC_MODEL",
                "AUDITOR_MODEL",
                "WEB_VERIFY_MODEL",
                default="claude-sonnet-4-6",
            ),
            provider="anthropic",
            timeout=timeout,
            max_tokens=_env_int(
                "ANTHROPIC_AUDITOR_MAX_TOKENS",
                "AUDITOR_ANTHROPIC_MAX_TOKENS",
                "AUDITOR_MAX_TOKENS",
                "WEB_VERIFY_MAX_TOKENS",
                default=2048,
            ),
        )

    if provider == "openai_compatible":
        api_key = _env_first(
            "NVIDIA_WEB_VERIFY_KEY",
            "WEB_VERIFY_API_KEY",
            "NVIDIA_AUDITOR_API_KEY",
            "AUDITOR_API_KEY",
            "NVIDIA_API_KEY",
            "OPENAI_API_KEY",
        )
        if not api_key:
            return None
        return WebVerifyLLM(
            api_key=api_key,
            base_url=_env_first(
                "NVIDIA_WEB_VERIFY_BASE_URL",
                "WEB_VERIFY_BASE_URL",
                "NVIDIA_AUDITOR_BASE_URL",
                "AUDITOR_BASE_URL",
                "NVIDIA_BASE_URL",
                "OPENAI_BASE_URL",
                default="https://integrate.api.nvidia.com/v1",
            ).rstrip("/"),
            model=_env_first(
                "NVIDIA_WEB_VERIFY_MODEL",
                "WEB_VERIFY_MODEL",
                "NVIDIA_AUDITOR_MODEL",
                "AUDITOR_MODEL",
                "OPENAI_MODEL",
                default="deepseek-ai/deepseek-v4-pro",
            ),
            provider="openai_compatible",
            timeout=timeout,
            max_tokens=_env_int("AUDITOR_MAX_TOKENS", "WEB_VERIFY_MAX_TOKENS", default=2048),
        )

    return None


def build_web_verify_llm() -> WebVerifyLLM | None:
    """
    웹 검증용 LLM 생성 정보입니다.

    주의:
    - 이 LLM이 직접 웹을 검색하는 것이 아닙니다.
    - 네이버 뉴스 API 또는 Serper로 검색 결과를 수집한 뒤,
      이 LLM은 해당 검색 결과와 agent JSON의 claim을 대조합니다.
    """
    preferred = _auditor_provider()
    for provider in _provider_candidates(preferred):
        llm = _build_llm_for_provider(provider)
        if llm is not None:
            return llm
    return None


def get_web_verify_receipt_info() -> dict:
    preferred = _auditor_provider()
    llm = build_web_verify_llm()
    return {
        "web_verify_provider_requested": preferred,
        "web_verify_provider": llm.provider if llm else None,
        "web_verify_model": llm.model if llm else None,
        "web_verify_base_url": llm.base_url if llm else None,
        "naver_enabled": bool(_env_first("NAVER_CLIENT_ID") and _env_first("NAVER_CLIENT_SECRET")) and _env_bool("AUDITOR_WEB_ENABLE_NAVER", True),
        "serper_enabled": bool(_env_first("SERPER_API_KEY", "GOOGLE_SERPER_API_KEY")),
        "web_verify_llm_enabled": llm is not None,
    }


def _safe_json_loads(text: str) -> dict:
    if not text:
        return {}

    text = str(text).strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return {}

    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _call_web_verify_llm(llm: WebVerifyLLM, system_prompt: str, user_prompt: str) -> dict:
    try:
        if llm.provider == "gemini":
            url = f"{llm.base_url}/models/{llm.model}:generateContent"
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}],
                    }
                ],
                "generationConfig": {
                    "temperature": 0,
                    "maxOutputTokens": llm.max_tokens,
                    "responseMimeType": "application/json",
                },
            }
            response = requests.post(url, params={"key": llm.api_key}, json=payload, timeout=llm.timeout)
            response.raise_for_status()
            body = response.json()
            parts = ((body.get("candidates") or [{}])[0].get("content", {}).get("parts") or [])
            content = "".join(str(part.get("text", "")) for part in parts if isinstance(part, dict))
            return _safe_json_loads(content)

        if llm.provider == "anthropic":
            url = f"{llm.base_url}/v1/messages"
            payload = {
                "model": llm.model,
                "max_tokens": llm.max_tokens,
                "temperature": 0,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            }
            headers = {
                "x-api-key": llm.api_key,
                "anthropic-version": _env_first("ANTHROPIC_VERSION", default="2023-06-01"),
                "Content-Type": "application/json",
            }
            response = requests.post(url, headers=headers, json=payload, timeout=llm.timeout)
            response.raise_for_status()
            body = response.json()
            content = "".join(
                str(part.get("text", ""))
                for part in (body.get("content") or [])
                if isinstance(part, dict) and part.get("type") == "text"
            )
            return _safe_json_loads(content)

        url = f"{llm.base_url}/chat/completions"
        payload = {
            "model": llm.model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {llm.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json=payload, timeout=llm.timeout)
        response.raise_for_status()
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        return _safe_json_loads(content)
    except Exception as exc:
        return {
            "verdict": "not_checked",
            "score": 0.0,
            "reason": f"web verify LLM 호출 실패(provider={llm.provider}): {type(exc).__name__}: {exc}",
            "cited_sources": [],
        }


def _normalize_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _collect_evidences(packet: dict) -> list[dict]:
    evidences = []
    for key in ("evidences", "evidence"):
        value = packet.get(key)
        if isinstance(value, list):
            evidences.extend([x for x in value if isinstance(x, dict)])

    seen = set()
    result = []
    for idx, ev in enumerate(evidences, start=1):
        ev = dict(ev)
        evidence_id = ev.get("evidence_id") or ev.get("id")
        if not evidence_id:
            evidence_id = f"{packet.get('agent', 'agent')}.ev.auto.{idx:03d}"
            ev["evidence_id"] = evidence_id

        if evidence_id in seen:
            continue

        seen.add(evidence_id)
        result.append(ev)

    return result


def _collect_claims(packet: dict) -> list[dict]:
    agent = packet.get("agent", "agent")
    claims = []

    raw_claims = packet.get("claims")
    if isinstance(raw_claims, list):
        for idx, claim in enumerate(raw_claims, start=1):
            if isinstance(claim, dict):
                text = str(claim.get("text") or claim.get("claim") or "").strip()
                if not text:
                    continue
                claims.append(
                    {
                        "agent": agent,
                        "claim_id": claim.get("claim_id") or f"{agent}.cl.{idx:03d}",
                        "text": text,
                        "evidence_ids": _normalize_list(claim.get("evidence_ids")),
                    }
                )
            elif isinstance(claim, str) and claim.strip():
                claims.append(
                    {
                        "agent": agent,
                        "claim_id": f"{agent}.cl.{idx:03d}",
                        "text": claim.strip(),
                        "evidence_ids": [],
                    }
                )

    if claims:
        return claims

    fallback_fields = (
        "summary",
        "key_thesis",
        "key_points",
        "risks",
        "key_risks",
        "opportunities",
    )

    idx = 1
    for field in fallback_fields:
        value = packet.get(field)
        items = value if isinstance(value, list) else [value]
        for item in items:
            if isinstance(item, dict):
                text = str(
                    item.get("text")
                    or item.get("risk")
                    or item.get("opportunity")
                    or item.get("thesis")
                    or ""
                ).strip()
            else:
                text = str(item or "").strip()

            if not text:
                continue

            claims.append(
                {
                    "agent": agent,
                    "claim_id": f"{agent}.cl.fallback.{idx:03d}",
                    "text": text,
                    "evidence_ids": [],
                }
            )
            idx += 1

    return claims


def _usable_evidence(ev: dict) -> bool:
    source_type = str(ev.get("source_type") or "").lower().strip()
    snippet = str(ev.get("snippet") or "").strip()

    if source_type in UNVERIFIED_SOURCE_TYPES:
        return False

    if "확인 불가" in snippet:
        return False

    if ev.get("value") is None and not snippet:
        return False

    return True


def _evidence_text(ev: dict) -> str:
    parts = []
    for key in ("source_type", "source", "metric", "value", "unit", "period", "snippet"):
        value = ev.get(key)
        if value is not None and str(value).strip():
            parts.append(f"{key}={value}")
    return " | ".join(parts)


def _search_query(company: str, claim_text: str) -> str:
    text = re.sub(r"\s+", " ", claim_text).strip()
    text = re.sub(r"[{}\[\]\"']", " ", text)
    text = text[:160]
    return f"{company} {text}"


def _strip_search_html(text: Any) -> str:
    if text is None:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", str(text))
    cleaned = (
        cleaned.replace("&quot;", '"')
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    return re.sub(r"\s+", " ", cleaned).strip()


def _naver_search(query: str, *, num: int = 5) -> list[dict]:
    """Auditor 웹 교차검증용 네이버 뉴스 검색입니다."""
    if not _env_bool("AUDITOR_WEB_ENABLE_NAVER", True):
        return []

    client_id = _env_first("NAVER_CLIENT_ID")
    client_secret = _env_first("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        return []

    try:
        response = requests.get(
            NAVER_NEWS_URL,
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret,
            },
            params={
                "query": query,
                "display": max(1, min(int(num), 100)),
                "start": 1,
                "sort": "date",
            },
            timeout=int(_env_first("REQUEST_TIMEOUT", default="25")),
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return []

    rows: list[dict] = []
    for item in payload.get("items", [])[:num]:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "title": _strip_search_html(item.get("title", "")),
                "link": item.get("originallink") or item.get("link") or "",
                "snippet": _strip_search_html(item.get("description", "")),
                "source": "naver_news",
            }
        )
    return rows[:num]


def _serper_search(query: str, *, num: int = 5) -> list[dict]:
    # Serper는 네이버 뉴스가 실패했을 때만 쓰는 fallback입니다.
    api_key = _env_first("SERPER_API_KEY", "GOOGLE_SERPER_API_KEY")
    if not api_key:
        return []

    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "q": query,
        "num": num,
        "gl": "kr",
        "hl": "ko",
    }

    try:
        response = requests.post(
            SERPER_URL,
            headers=headers,
            json=payload,
            timeout=int(_env_first("REQUEST_TIMEOUT", default="25")),
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    results = []

    for item in data.get("organic", []) or []:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("source", "serper"),
            }
        )

    for item in data.get("news", []) or []:
        if not isinstance(item, dict):
            continue
        results.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("source", "serper_news"),
            }
        )

    return results[:num]


def _web_search(query: str, *, num: int = 5) -> list[dict]:
    # 1순위: 네이버 뉴스 API
    results = _naver_search(query, num=num)
    if results:
        return results[:num]

    # 2순위: Serper fallback
    results = _serper_search(query, num=num)
    if results:
        return results[:num]

    # NewsAPI는 현재 429 이슈 때문에 Auditor 웹 검증에서는 기본 사용하지 않습니다.
    # 나중에 별도로 켜고 싶으면 AUDITOR_WEB_ENABLE_NEWS_API 같은 플래그를 만들어 이곳에 추가하세요.
    return []


def _extract_numbers(text: str) -> list[float]:
    if not text:
        return []

    nums = []
    for raw in re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", str(text)):
        try:
            nums.append(float(raw.replace(",", "")))
        except ValueError:
            continue
    return nums


def _claim_uses_korean_eok(text: str) -> bool:
    return "억" in str(text)


def _detect_unit_mismatch(claim_text: str, evidences: list[dict]) -> str | None:
    """
    대표적인 오류:
    - 원천 value가 원 단위인데 Chair 또는 agent가 그대로 억 원이라고 표현하는 경우.
    """
    claim_nums = _extract_numbers(claim_text)
    if not claim_nums:
        return None

    if not _claim_uses_korean_eok(claim_text):
        return None

    for ev in evidences:
        value = ev.get("value")
        unit = str(ev.get("unit") or "").strip()

        if value is None:
            continue

        try:
            ev_value = float(value)
        except Exception:
            continue

        if unit == "원":
            ev_eok = ev_value / 100_000_000
            for claim_num in claim_nums:
                if abs(claim_num) < 1e-9:
                    continue

                # claim 숫자가 원천값 그대로인데 '억'을 붙인 경우를 강하게 차단
                if abs(abs(claim_num) - abs(ev_value)) / max(abs(ev_value), 1.0) < 0.01:
                    return (
                        "단위 불일치: 원 단위 원천값을 억 원으로 잘못 표현했을 가능성이 큽니다. "
                        f"원천값={ev_value}원, 억원 환산={ev_eok:.2f}억 원, claim={claim_text}"
                    )

                # 억원 환산값과 너무 크게 다르면 차단
                if abs(abs(claim_num) - abs(ev_eok)) / max(abs(ev_eok), 1.0) > 0.35:
                    if abs(claim_num) > abs(ev_eok) * 10:
                        return (
                            "단위 불일치: claim의 억 원 수치가 원천값의 억원 환산값과 크게 다릅니다. "
                            f"원천값={ev_value}원, 억원 환산={ev_eok:.2f}억 원, claim={claim_text}"
                        )

    return None


def _local_support_score(claim: dict, evidences_by_id: dict[str, dict]) -> tuple[float, list[dict], str | None]:
    evidence_ids = _normalize_list(claim.get("evidence_ids"))
    matched = []

    for evidence_id in evidence_ids:
        ev = evidences_by_id.get(str(evidence_id))
        if ev and _usable_evidence(ev):
            matched.append(ev)

    if not evidence_ids:
        return 0.25, [], "claim에 evidence_ids가 없습니다."

    if not matched:
        return 0.20, [], "claim의 evidence_ids가 사용 가능한 evidences와 연결되지 않았습니다."

    mismatch = _detect_unit_mismatch(claim.get("text", ""), matched)
    if mismatch:
        return 0.10, matched, mismatch

    claim_text = str(claim.get("text") or "")
    claim_nums = _extract_numbers(claim_text)

    if claim_nums:
        ev_text = " ".join(_evidence_text(ev) for ev in matched)
        ev_nums = _extract_numbers(ev_text)

        if not ev_nums:
            return 0.55, matched, "claim에는 수치가 있으나 evidence에는 비교 가능한 수치가 부족합니다."

        return 0.85, matched, None

    return 0.80, matched, None


def _llm_verify_claim(
    *,
    llm: WebVerifyLLM,
    company: str,
    claim: dict,
    matched_evidences: list[dict],
    search_results: list[dict],
) -> dict:
    system_prompt = """
You are a web-verification auditor for investment-analysis outputs.
Your role is factual verification, not investment recommendation.

Rules:
1. Judge only from the provided local_evidence and web_search_results.
2. Do not use your prior knowledge to fill gaps.
3. Treat customers, orders, contracts, world-first claims, and outlook statements as unsupported when they are absent from the search results.
4. If numbers, periods, or units differ, classify the claim as contradicted or unsupported.
5. Return JSON only.
""".strip()

    user_payload = {
        "company": company,
        "claim": claim,
        "local_evidence": [_evidence_text(ev) for ev in matched_evidences],
        "web_search_results": search_results,
        "return_schema": {
            "verdict": "supported | partial | unsupported | contradicted | not_enough",
            "score": "0.0~1.0",
            "reason": "judgment reason",
            "cited_sources": ["search-result title or link"],
        },
    }

    user_prompt = json.dumps(user_payload, ensure_ascii=False, indent=2)
    result = _call_web_verify_llm(llm, system_prompt, user_prompt)

    verdict = str(result.get("verdict") or "not_enough").lower()
    if verdict not in {"supported", "partial", "unsupported", "contradicted", "not_enough", "not_checked"}:
        verdict = "not_enough"

    try:
        score = float(result.get("score", 0.0))
    except Exception:
        score = 0.0

    result["verdict"] = verdict
    result["score"] = max(0.0, min(1.0, score))
    result["reason"] = str(result.get("reason") or "")
    result["cited_sources"] = _normalize_list(result.get("cited_sources"))

    return result


def run_web_crosscheck(
    *,
    company: str,
    opinions: list[dict],
    source_contexts: dict[str, str] | None = None,
    llm: WebVerifyLLM | None = None,
) -> dict:
    """
    5개 agent JSON의 claim을 실제 검색 결과와 대조합니다.

    핵심:
    - Auditor LLM은 직접 웹 검색하지 않습니다.
    - 네이버 뉴스 API 또는 Serper로 검색 결과를 가져오고,
      AUDITOR_LLM_PROVIDER/AUDITOR_PROVIDER로 선택한 모델이 그 검색 결과를 검증합니다.
    """
    started_at = time.time()

    source_contexts = source_contexts or {}
    llm = llm or build_web_verify_llm()

    naver_enabled = bool(_env_first("NAVER_CLIENT_ID") and _env_first("NAVER_CLIENT_SECRET")) and _env_bool("AUDITOR_WEB_ENABLE_NAVER", True)
    serper_enabled = bool(_env_first("SERPER_API_KEY", "GOOGLE_SERPER_API_KEY"))
    web_search_enabled = naver_enabled or serper_enabled
    llm_enabled = llm is not None

    max_claims_per_agent = int(_env_first("WEB_VERIFY_MAX_CLAIMS_PER_AGENT", default="12"))
    search_num = int(_env_first("WEB_VERIFY_SEARCH_RESULTS", default="5"))

    if not isinstance(opinions, list):
        opinions = []

    agent_results: dict[str, dict] = {}
    all_claim_results = []
    hard_fail_claims = []
    supported_claims = []
    unsupported_claims = []

    for packet in opinions:
        if not isinstance(packet, dict):
            continue

        agent = str(packet.get("agent") or "unknown")
        evidences = _collect_evidences(packet)
        evidences_by_id = {
            str(ev.get("evidence_id")): ev
            for ev in evidences
            if ev.get("evidence_id")
        }

        claims = _collect_claims(packet)[:max_claims_per_agent]
        claim_results = []

        for claim in claims:
            local_score, matched_evidences, local_issue = _local_support_score(claim, evidences_by_id)

            query = _search_query(company, claim.get("text", ""))
            search_results = _web_search(query, num=search_num) if web_search_enabled else []

            if llm_enabled and search_results:
                llm_result = _llm_verify_claim(
                    llm=llm,
                    company=company,
                    claim=claim,
                    matched_evidences=matched_evidences,
                    search_results=search_results,
                )
                web_score = float(llm_result.get("score", 0.0))
                verdict = str(llm_result.get("verdict") or "not_enough").lower()
                reason = str(llm_result.get("reason") or "")
                cited_sources = _normalize_list(llm_result.get("cited_sources"))
            else:
                web_score = 0.0
                verdict = "not_checked" if not search_results else "not_enough"
                reason = (
                    "NAVER_CLIENT_ID/NAVER_CLIENT_SECRET 또는 SERPER_API_KEY가 없어 실제 웹 검색을 수행하지 못했습니다."
                    if not web_search_enabled
                    else "웹 검증 LLM이 없어 검색 결과를 판단하지 못했습니다."
                )
                cited_sources = []

            if local_issue and "단위 불일치" in local_issue:
                final_score = 0.10
                final_verdict = "contradicted"
                final_reason = local_issue
            elif verdict in {"supported", "partial"}:
                final_score = max(local_score, web_score)
                final_verdict = verdict
                final_reason = reason or "웹 검색 결과와 local evidence가 대체로 일치합니다."
            elif verdict in {"unsupported", "contradicted"}:
                final_score = min(local_score, web_score)
                final_verdict = verdict
                final_reason = reason or "웹 검색 결과로 claim을 뒷받침하지 못했습니다."
            elif local_score >= 0.80:
                final_score = local_score
                final_verdict = "local_supported"
                final_reason = local_issue or "웹 검증은 제한적이나, local evidence_id와 원천값 연결은 확인되었습니다."
            else:
                final_score = min(local_score, 0.45)
                final_verdict = "not_enough"
                final_reason = local_issue or reason or "근거가 부족합니다."

            claim_result = {
                "agent": agent,
                "claim_id": claim.get("claim_id"),
                "text": claim.get("text"),
                "evidence_ids": _normalize_list(claim.get("evidence_ids")),
                "verdict": final_verdict,
                "score": round(float(final_score), 4),
                "reason": final_reason,
                "web_query": query,
                "web_search_used": bool(search_results),
                "search_results": search_results,
                "matched_evidence_ids": [ev.get("evidence_id") for ev in matched_evidences],
                "cited_sources": cited_sources,
            }

            claim_results.append(claim_result)
            all_claim_results.append(claim_result)

            if final_verdict in {"supported", "partial", "local_supported"} and final_score >= 0.75:
                supported_claims.append(claim_result)
            else:
                unsupported_claims.append(claim_result)

            if final_verdict in {"unsupported", "contradicted"} or final_score < 0.50:
                hard_fail_claims.append(claim_result)

        if claim_results:
            agent_score = sum(x["score"] for x in claim_results) / len(claim_results)
        else:
            agent_score = 0.0

        agent_results[agent] = {
            "agent": agent,
            "score": round(agent_score, 4),
            "claim_count": len(claim_results),
            "supported_claims": [
                x for x in claim_results
                if x["verdict"] in {"supported", "partial", "local_supported"} and x["score"] >= 0.75
            ],
            "unsupported_claims": [
                x for x in claim_results
                if not (x["verdict"] in {"supported", "partial", "local_supported"} and x["score"] >= 0.75)
            ],
            "claim_results": claim_results,
        }

    if all_claim_results:
        total_score = sum(x["score"] for x in all_claim_results) / len(all_claim_results)
    else:
        total_score = 0.0

    checked = web_search_enabled or any(
        x.get("verdict") == "local_supported"
        for x in all_claim_results
    )

    passed = bool(
        checked
        and total_score >= 0.75
        and not any(x.get("verdict") == "contradicted" for x in hard_fail_claims)
    )

    return {
        "packet_version": "web_verify_v4_naver_serper_deepseek_claim_level",
        "checked": checked,
        "pass": passed,
        "score": round(total_score, 4),
        "naver_enabled": naver_enabled,
        "serper_enabled": serper_enabled,
        "web_search_enabled": web_search_enabled,
        "web_verify_llm_enabled": llm_enabled,
        "web_verify_provider_requested": _auditor_provider(),
        "web_verify_provider": llm.provider if llm else None,
        "web_verify_model": llm.model if llm else None,
        "web_verify_base_url": llm.base_url if llm else None,
        "agent_results": agent_results,
        "claim_results": all_claim_results,
        "supported_claims": supported_claims,
        "unsupported_claims": unsupported_claims,
        "hard_fail_claims": hard_fail_claims,
        "reason": (
            "네이버 뉴스/Serper 검색 결과와 local evidence를 함께 사용해 claim 단위 검증을 수행했습니다."
            if web_search_enabled
            else "NAVER_CLIENT_ID/NAVER_CLIENT_SECRET 또는 SERPER_API_KEY가 없어 실제 웹 검색은 수행하지 못했습니다. local evidence 중심으로만 검증했습니다."
        ),
        "elapsed_sec": round(time.time() - started_at, 3),
    }
