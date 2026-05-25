from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests

try:
    from dotenv import find_dotenv, load_dotenv

    _DOTENV_PATH = find_dotenv(usecwd=True)
    if _DOTENV_PATH:
        load_dotenv(_DOTENV_PATH, override=False)
except Exception:
    # dotenv is optional at runtime; agents can still receive env vars directly.
    pass


DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


def normalize_gemini_base_url(base_url: str | None) -> str:
    """Return a safe Gemini REST base URL.

    Some local .env files keep GEMINI_BASE_URL for OpenAI-compatible routes.
    The Gemini generateContent API must use the Google Generative Language
    endpoint, so non-Google URLs are ignored instead of causing 404 errors.
    """

    raw = (base_url or DEFAULT_GEMINI_BASE_URL).strip().rstrip("/")
    if not raw:
        return DEFAULT_GEMINI_BASE_URL
    if "generativelanguage.googleapis.com" not in raw:
        return DEFAULT_GEMINI_BASE_URL
    raw = raw.split("/models", 1)[0].rstrip("/")
    host_prefix, path_suffix = raw.split("generativelanguage.googleapis.com", 1)
    host = host_prefix + "generativelanguage.googleapis.com"
    path = path_suffix.rstrip("/")
    if path in {"", "/"}:
        return host + "/v1beta"
    if path == "/v1beta" or path.startswith("/v1beta/"):
        return host + "/v1beta"
    if path == "/v1" or path.startswith("/v1/"):
        return host + "/v1"
    return DEFAULT_GEMINI_BASE_URL


@dataclass
class SimpleLLMResult:
    """Minimal response object compatible with LangChain-style `.content` access."""

    content: str


class GeminiChatClient:
    """Small dependency-free Gemini REST client for AlphaProve agents.

    It exposes `.invoke(prompt)` so Finance/Market/Issue/Chair-style code can use it
    in the same way as LangChain chat models. The client intentionally does not
    enable Google Search grounding; search/news collection should stay inside the
    Data Intake layer where rate, cost, and evidence provenance are controlled.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-2.5-flash-lite",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        timeout: int = 60,
        max_retries: int | None = None,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.model = (model or "gemini-2.5-flash-lite").strip()
        self.base_url = normalize_gemini_base_url(base_url)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self.timeout = int(timeout)
        if max_retries is not None:
            self.max_retries = max(0, int(max_retries))
        else:
            try:
                self.max_retries = max(0, int(os.getenv("GEMINI_MAX_RETRIES", "2")))
            except Exception:
                self.max_retries = 2

        if not self.api_key:
            raise ValueError("GEMINI_PARALLEL_API_KEY/GEMINI_API_KEY가 없습니다.")

    def invoke(self, prompt: Any) -> SimpleLLMResult:
        text = self._prompt_to_text(prompt)
        response_text = self.generate(text)
        return SimpleLLMResult(content=response_text)

    def generate(self, prompt: str) -> str:
        """Call Gemini REST API with small retry for temporary capacity errors.

        A 503 from Gemini means the model endpoint is reachable but currently
        overloaded.  It is not an env/key routing error.  We retry briefly and
        then raise a sanitized error so the caller can decide whether to use
        local deterministic output.  This client never switches providers by
        itself.
        """

        url = f"{self.base_url}/models/{self.model}:generateContent"
        params = {"key": self.api_key}
        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }

        retry_statuses = {429, 500, 502, 503, 504}
        last_status: int | None = None
        last_preview = ""

        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.post(url, params=params, json=payload, timeout=self.timeout)
            except requests.RequestException as exc:
                if attempt < self.max_retries:
                    time.sleep(min(1.5 * (attempt + 1), 5.0))
                    continue
                raise RuntimeError(f"Gemini API request failed: {exc.__class__.__name__}") from exc

            last_status = resp.status_code
            last_preview = (resp.text or "")[:300].replace(self.api_key, "***KEY***").replace("\n", " ")

            if resp.status_code in retry_statuses and attempt < self.max_retries:
                wait_sec = min(1.5 * (attempt + 1), 5.0)
                print(
                    f"[Gemini] temporary status={resp.status_code}; "
                    f"retry {attempt + 1}/{self.max_retries} after {wait_sec:.1f}s"
                )
                time.sleep(wait_sec)
                continue

            if resp.status_code >= 400:
                raise RuntimeError(f"Gemini API error status={resp.status_code}: {last_preview}")

            data = resp.json()
            try:
                candidates = data.get("candidates") or []
                if not candidates:
                    raise ValueError("empty candidates")
                parts = candidates[0].get("content", {}).get("parts") or []
                texts = [str(part.get("text", "")) for part in parts if isinstance(part, dict) and part.get("text")]
                content = "".join(texts).strip()
                if not content:
                    finish_reason = candidates[0].get("finishReason")
                    raise ValueError(f"empty text; finishReason={finish_reason}")
                return content
            except Exception as exc:
                preview = str(data)[:500]
                raise RuntimeError(f"Gemini 응답 파싱 실패: {exc}; preview={preview}") from exc

        raise RuntimeError(f"Gemini API error status={last_status}: {last_preview}")

    @staticmethod
    def _prompt_to_text(prompt: Any) -> str:
        if isinstance(prompt, str):
            return prompt
        if hasattr(prompt, "to_string"):
            return str(prompt.to_string())
        if hasattr(prompt, "content"):
            return str(getattr(prompt, "content"))
        return str(prompt)


def env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value and str(value).strip():
            return str(value).strip()
    return default


def env_int(*names: str, default: int = 4096) -> int:
    value = env_first(*names, default=str(default))
    try:
        return int(str(value).strip())
    except Exception:
        return default


def env_float(*names: str, default: float = 0.0) -> float:
    value = env_first(*names, default=str(default))
    try:
        return float(str(value).strip())
    except Exception:
        return default


def is_gemini_provider(provider: str | None) -> bool:
    return str(provider or "").strip().lower() in {"gemini", "google", "google_gemini", "google-gemini"}


def build_gemini_chat_client(
    *,
    agent_name: str,
    api_key_env_names: tuple[str, ...] = (),
    model_env_names: tuple[str, ...] = (),
    max_tokens_env_names: tuple[str, ...] = (),
    max_retries_env_names: tuple[str, ...] = (),
    temperature: float | None = None,
) -> GeminiChatClient:
    """Build Gemini client using common and agent-specific env variables."""

    upper = agent_name.upper().replace("-", "_")
    api_key = env_first(
        *(api_key_env_names or (
            f"{upper}_GEMINI_API_KEY",
            "GEMINI_PARALLEL_API_KEY",
            "GEMINI_API_KEY",
        )),
    )
    model = env_first(
        *model_env_names,
        f"{upper}_GEMINI_MODEL",
        "GEMINI_PARALLEL_MODEL",
        "GEMINI_MODEL",
        default="gemini-2.5-flash-lite",
    )
    base_url = normalize_gemini_base_url(
        env_first(
            f"{upper}_GEMINI_BASE_URL",
            "GEMINI_PARALLEL_BASE_URL",
            "GEMINI_BASE_URL",
            default=DEFAULT_GEMINI_BASE_URL,
        )
    )
    max_tokens = env_int(
        *max_tokens_env_names,
        f"{upper}_GEMINI_MAX_TOKENS",
        "GEMINI_PARALLEL_MAX_TOKENS",
        "GEMINI_MAX_OUTPUT_TOKENS",
        default=4096,
    )
    timeout = env_int(
        f"{upper}_GEMINI_TIMEOUT",
        "GEMINI_TIMEOUT",
        "REQUEST_TIMEOUT",
        default=60,
    )
    max_retries = env_int(
        *max_retries_env_names,
        f"{upper}_GEMINI_MAX_RETRIES",
        "GEMINI_MAX_RETRIES",
        default=2,
    )
    temp = temperature if temperature is not None else env_float(
        f"{upper}_GEMINI_TEMPERATURE",
        "GEMINI_TEMPERATURE",
        default=0.0,
    )

    return GeminiChatClient(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=float(temp),
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
    )
