from __future__ import annotations

import os
import warnings
from typing import Any

from common.llm_clients import build_gemini_chat_client, is_gemini_provider

from .config import SETTINGS


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


def _build_chat_openai(
    *,
    api_key: str,
    model: str,
    base_url: str = "",
    temperature: float = 0,
) -> Any:
    """NVIDIA NIM OpenAI-compatible endpoint용 LLM 생성.

    DeepSeek 계열 모델은 ChatNVIDIA에서 모델 타입 경고가 날 수 있어
    기본적으로 ChatOpenAI 호환 호출을 우선 사용합니다.
    """
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "api_key": api_key,
        "base_url": _normalize_base_url(base_url),
        "timeout": _safe_int(os.getenv("REQUEST_TIMEOUT"), 80),
        "max_tokens": _safe_int(os.getenv("ISSUE_MAX_TOKENS"), 4096),
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


def _build_chat_nvidia_fallback(
    *,
    api_key: str,
    model: str,
    base_url: str = "",
    temperature: float = 0,
) -> Any:
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


def build_issue_llm() -> Any:
    """Issue Agent LLM 생성.

    기본은 NVIDIA/OpenAI-compatible endpoint다.
    ISSUE_LLM_PROVIDER 또는 PARALLEL_LLM_PROVIDER=gemini이면 Gemini 백업을 사용한다.
    """
    prefer = _env_first("ISSUE_LLM_PROVIDER", "PARALLEL_LLM_PROVIDER", default="openai_compatible").lower()

    if is_gemini_provider(prefer):
        llm = build_gemini_chat_client(
            agent_name="issue",
            model_env_names=("ISSUE_GEMINI_MODEL",),
            max_tokens_env_names=("ISSUE_MAX_TOKENS",),
            temperature=0,
        )
        print(f"[issue] LLM provider=gemini model={llm.model} timeout={llm.timeout}")
        return llm

    api_key = _env_first(
        "ISSUE_NVIDIA_API_KEY",
        "NVIDIA_PARALLEL_API_KEY",
        "OPENAI_API_KEY",
        default=SETTINGS.nvidia_api_key,
    )

    if not api_key:
        raise ValueError(
            "Issue LLM API 키가 없습니다. "
            "ISSUE_NVIDIA_API_KEY 또는 NVIDIA_PARALLEL_API_KEY를 확인하세요. "
            "Gemini를 쓰려면 PARALLEL_LLM_PROVIDER=gemini 와 GEMINI_API_KEY를 설정하세요."
        )

    model = _env_first(
        "ISSUE_NVIDIA_MODEL",
        "NVIDIA_PARALLEL_MODEL",
        "OPENAI_MODEL",
        default=SETTINGS.nvidia_model,
    )

    base_url = _env_first(
        "ISSUE_NVIDIA_BASE_URL",
        "NVIDIA_PARALLEL_BASE_URL",
        "OPENAI_BASE_URL",
        default=SETTINGS.nvidia_base_url,
    )

    if prefer not in {"nvidia", "chatnvidia"}:
        try:
            llm = _build_chat_openai(
                api_key=api_key,
                model=model,
                base_url=base_url,
                temperature=0,
            )
            print(f"[issue] LLM provider=openai_compatible base_url={_normalize_base_url(base_url)} model={model}")
            return llm
        except Exception as exc:
            print(f"[issue] ChatOpenAI 생성 실패 → ChatNVIDIA fallback 사용: {exc}")

    llm = _build_chat_nvidia_fallback(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=0,
    )
    print(f"[issue] LLM provider=chatnvidia_fallback model={model}")
    return llm


def call_issue_llm(prompt: str) -> str:
    """
    issue_agent 전용 LLM 호출 함수.

    - 기본은 NVIDIA_PARALLEL_* 또는 ISSUE_NVIDIA_* 환경변수를 사용합니다.
    - ISSUE_LLM_PROVIDER 또는 PARALLEL_LLM_PROVIDER=gemini이면 Gemini 백업을 사용합니다.
    - DeepSeek V4 Pro 등 OpenAI-compatible 모델은 ChatOpenAI로 우선 호출합니다.
    - LLM 장애가 나면 runner에서 fallback JSON을 만들 수 있도록 예외를 그대로 전달합니다.
    """
    llm = build_issue_llm()
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else ""
    if not str(content).strip():
        additional = getattr(response, "additional_kwargs", {}) or {}
        content = additional.get("reasoning_content", "")
    return content if content else str(response)
