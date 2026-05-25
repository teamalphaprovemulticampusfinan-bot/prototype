from __future__ import annotations

import json
import os
import re
import time
import warnings
from typing import Any

from common.llm_clients import build_gemini_chat_client, is_gemini_provider

from .config import NVIDIA_PARALLEL_API_KEY, NVIDIA_PARALLEL_BASE_URL, NVIDIA_PARALLEL_MODEL
from .prompts import MARKET_PROMPT
from .schemas import MarketState


warnings.filterwarnings(
    "ignore",
    message=r"Found .* in available_models, but type is unknown.*",
    category=UserWarning,
)


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return default


def _safe_int(value: str | None, default: int) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(str(value).strip())
    except Exception:
        return default


def _normalize_base_url(base_url: str) -> str:
    return (base_url or "https://integrate.api.nvidia.com/v1").strip().rstrip("/")


def _build_chat_openai(*, api_key, model, base_url="", temperature=0) -> Any:
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "api_key": api_key,
        "base_url": _normalize_base_url(base_url),
        "timeout": _safe_int(os.getenv("REQUEST_TIMEOUT"), 80),
        "max_tokens": _safe_int(os.getenv("MARKET_MAX_TOKENS"), 4096),
    }

    try:
        return ChatOpenAI(**kwargs)
    except TypeError:
        kwargs.pop("timeout", None)
        try:
            return ChatOpenAI(**kwargs)
        except TypeError:
            kwargs.pop("max_tokens", None)
            return ChatOpenAI(**kwargs)


def _build_chat_nvidia_fallback(*, api_key, model, base_url="", temperature=0) -> Any:
    from langchain_nvidia_ai_endpoints import ChatNVIDIA

    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "api_key": api_key,
    }

    if base_url:
        kwargs["base_url"] = _normalize_base_url(base_url)

    try:
        return ChatNVIDIA(**kwargs)
    except TypeError:
        kwargs.pop("base_url", None)
        return ChatNVIDIA(**kwargs)


def build_llm() -> Any:
    prefer = _env_first(
        "MARKET_LLM_PROVIDER",
        "PARALLEL_LLM_PROVIDER",
        default="openai_compatible",
    ).lower()

    if is_gemini_provider(prefer):
        llm = build_gemini_chat_client(
            agent_name="market",
            model_env_names=("MARKET_GEMINI_MODEL",),
            max_tokens_env_names=("MARKET_MAX_TOKENS",),
            temperature=0,
        )
        print(f"[market] LLM provider=gemini model={llm.model}")
        return llm

    api_key = _env_first(
        "MARKET_NVIDIA_API_KEY",
        "NVIDIA_PARALLEL_API_KEY",
        "OPENAI_API_KEY",
        default=NVIDIA_PARALLEL_API_KEY,
    )

    if not api_key:
        raise ValueError("Market LLM API 키가 없습니다.")

    model = _env_first(
        "MARKET_NVIDIA_MODEL",
        "NVIDIA_PARALLEL_MODEL",
        "OPENAI_MODEL",
        default=NVIDIA_PARALLEL_MODEL,
    )

    base_url = _env_first(
        "MARKET_NVIDIA_BASE_URL",
        "NVIDIA_PARALLEL_BASE_URL",
        "OPENAI_BASE_URL",
        default=NVIDIA_PARALLEL_BASE_URL,
    )

    if prefer not in {"nvidia", "chatnvidia"}:
        try:
            llm = _build_chat_openai(
                api_key=api_key,
                model=model,
                base_url=base_url,
                temperature=0,
            )
            print(f"[market] LLM provider=openai_compatible model={model}")
            return llm
        except Exception as exc:
            print(f"[market] ChatOpenAI 생성 실패 → ChatNVIDIA fallback: {exc}")

    llm = _build_chat_nvidia_fallback(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=0,
    )
    print(f"[market] LLM provider=chatnvidia_fallback model={model}")
    return llm


def _extract_json_object(text: str) -> str:
    """Return the largest likely JSON object from an LLM response."""
    cleaned = str(text or "")
    cleaned = cleaned.replace("```json", "").replace("```JSON", "").replace("```", "").strip()

    start = cleaned.find("{")
    if start < 0:
        return cleaned

    depth = 0
    in_string = False
    escaped = False
    end = -1

    for idx in range(start, len(cleaned)):
        ch = cleaned[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = idx
                break

    if end >= start:
        return cleaned[start : end + 1]

    # Fallback to the old broad slicing behavior when braces are unbalanced.
    last = cleaned.rfind("}")
    if last > start:
        return cleaned[start : last + 1]
    return cleaned[start:]


def _repair_json_text(text: str) -> str:
    """Apply conservative local repairs to common LLM JSON formatting errors."""
    out = str(text or "")
    out = out.replace("\ufeff", "")
    out = out.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    out = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", out)
    # Remove trailing commas before object/array endings.
    out = re.sub(r",\s*([}\]])", r"\1", out)
    # Convert Python-style literals that occasionally appear in model output.
    out = re.sub(r"\bNone\b", "null", out)
    out = re.sub(r"\bTrue\b", "true", out)
    out = re.sub(r"\bFalse\b", "false", out)
    return out.strip()


def clean_json(text: str) -> dict:
    """Parse LLM JSON output with local repair before giving up.

    The market LLM occasionally returns nearly-valid JSON that fails with errors
    like `Expecting ',' delimiter`.  We keep the original contract of returning a
    dict, but try conservative repairs before raising the original parse error.
    """
    candidate = _extract_json_object(text)
    candidate = _repair_json_text(candidate)

    try:
        parsed = json.loads(candidate)
        if not isinstance(parsed, dict):
            raise ValueError("LLM JSON root is not an object")
        return parsed
    except Exception as first_error:
        # Last local fallback: YAML can read some JSON-like outputs.  This does
        # not add another LLM call and is skipped when PyYAML is unavailable.
        try:
            import yaml  # type: ignore

            parsed = yaml.safe_load(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
        raise first_error


def _normalize_content(content) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if hasattr(item, "text"):
                parts.append(item.text)
            else:
                parts.append(str(item))
        return "".join(parts).strip()

    return str(content).strip()


def _num(value: Any) -> float | int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if float(value).is_integer() else float(value)
    text = str(value).replace(",", "").replace("%", "").strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        num = float(text)
    except Exception:
        return None
    return int(num) if num.is_integer() else num


def _fallback_analysis(company: str, error_message: str, state: MarketState | None = None) -> dict:
    static = (state or {}).get("static_data", {}) if isinstance(state, dict) else {}
    base = static.get("base", {}) if isinstance(static, dict) and isinstance(static.get("base"), dict) else {}
    chain = static.get("chain", {}) if isinstance(static, dict) and isinstance(static.get("chain"), dict) else {}

    opinion = str(base.get("투자의견") or "보유").strip()
    if opinion not in {"매수", "보유", "매도"}:
        opinion = "보유"

    scoring: dict[str, dict[str, Any]] = {}
    score_map = {
        "거시환경": "market_final_cached",
        "산업매력도": "market_final_cached",
        "경쟁위치": "market_final_cached",
        "정책수혜": "market_final_cached",
        "시장모멘텀": "market_final_cached",
    }
    for label, source in score_map.items():
        score = _num(base.get(label))
        if score is not None:
            scoring[label] = {
                "score": score,
                "reason": f"기존 market_final 산출물({source})에서 복원한 점수입니다.",
            }

    total_score = _num(base.get("총점"))
    if total_score is None and scoring:
        total_score = sum(float(v.get("score") or 0) for v in scoring.values())

    summary = str(base.get("요약") or "").strip()
    if not summary:
        summary = f"{company} 분석 중 LLM 호출 오류가 발생해 기존 market 산출물과 수치 근거를 우선 사용합니다."

    risks = []
    if error_message:
        risks.append(f"LLM 호출 실패로 최신 정성 해석은 제한됩니다: {error_message}")
    if chain.get("position"):
        risks.append(f"밸류체인 위치 확인: {chain.get('position')}")

    return {
        "company": company,
        "opinion": opinion,
        "confidence": 0.8,
        "summary": summary,
        "total_score": total_score,
        "scoring": scoring,
        "market_environment": {
            "oecd_cli": "",
            "industry_stage": str((static.get("growth") or "") if isinstance(static, dict) else ""),
            "value_chain_position": str(chain.get("position") or ""),
            "competition": "",
        },
        "risks": risks[:5],
        "opportunities": [],
        "error": error_message,
        "fallback_source": "market_final_static_data" if base else "minimal_fallback",
    }


def analyze_node(state: MarketState, llm: Any) -> dict:
    company = state["company"]

    payload = {
        "company": company,
        "stock": json.dumps(state.get("stock_data", {}), ensure_ascii=False),
        "oecd": json.dumps(state.get("oecd_data", {}), ensure_ascii=False),
        "static": json.dumps(state.get("static_data", {}), ensure_ascii=False),
        "news": json.dumps(state.get("news_data", {}), ensure_ascii=False),
        "dart": json.dumps(state.get("dart_data", {}), ensure_ascii=False),
    }

    prompt_value = MARKET_PROMPT.invoke(payload)
    prompt_text = prompt_value.to_string() if hasattr(prompt_value, "to_string") else str(prompt_value)

    last_error = None
    content = ""
    # Market qualitative parsing can fail when the model returns malformed JSON.
    # Keep this path bounded but allow exactly up to 3 LLM calls before fallback.
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            retry_note = ""
            if attempt > 1:
                retry_note = (
                    "\n\n[중요]\n"
                    "직전 응답은 JSON 파싱에 실패했습니다. "
                    "반드시 마크다운 없이 순수 JSON 객체만 출력하세요. "
                    "큰따옴표를 사용하고, 각 key-value 사이에는 쉼표를 빠짐없이 넣으세요. "
                    "문자열은 한 줄로 짧게 작성하고, trailing comma를 쓰지 마세요."
                )

            result = llm.invoke(prompt_text + retry_note)
            content = _normalize_content(result.content if hasattr(result, "content") else result)

            if not content.strip():
                raise ValueError("LLM 응답이 비어 있습니다.")

            analysis = clean_json(content)

            if "opinion" not in analysis or analysis.get("opinion") not in {"매수", "보유", "매도"}:
                analysis["opinion"] = "보유"

            if "confidence" not in analysis or analysis.get("confidence") in (None, ""):
                analysis["confidence"] = 0.8

            if "scoring" in analysis and isinstance(analysis["scoring"], dict):
                analysis["total_score"] = sum(
                    v.get("score", 0)
                    for v in analysis["scoring"].values()
                    if isinstance(v, dict)
                )

            print(f"  [{company}] 마켓 점수: {analysis.get('total_score', '?')}/100")
            return {"analysis": analysis}

        except Exception as e:
            last_error = str(e)
            print(f"  [{company}] LLM 호출/파싱 오류 (시도 {attempt}/{max_attempts}): {e}")

            if attempt < max_attempts:
                time.sleep(2)

    analysis = _fallback_analysis(company, last_error or "알 수 없는 오류", state)
    print(f"  [{company}] fallback 분석 반환")
    return {"analysis": analysis}
