from __future__ import annotations

import ast
import json
import os
import re
import warnings
from typing import Any

from common.llm_clients import build_gemini_chat_client

from .config import FINANCE_LLM_PROVIDER, GEMINI_MODEL_NAME, MODEL_NAME, NVIDIA_API_KEY
from .schemas import Report

warnings.filterwarnings(
    "ignore",
    message=r"Found .* in available_models, but type is unknown.*",
    category=UserWarning,
)

DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"


def _env_first(*names: str, default: str = "") -> str:
    """환경변수를 우선순위대로 읽는다."""
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return default


def _env_first_name(*names: str) -> str:
    """Return the env var name that will be used, without exposing its value."""
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return name
    return "<missing>"


def _safe_int(value: str | None, default: int) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(str(value).strip())
    except Exception:
        return default


def _normalize_nvidia_base_url(base_url: str) -> str:
    """NVIDIA endpoint URL을 정리한다."""
    base_url = (base_url or DEFAULT_NVIDIA_BASE_URL).strip()
    return base_url.rstrip("/")



def _safe_error_message(exc: Exception, *, limit: int = 180) -> str:
    """Return a short, key-safe error message for logs."""

    raw = str(exc or "").strip()
    raw = re.sub(r"AIza[0-9A-Za-z_\-]+", "***KEY***", raw)
    raw = re.sub(r"Bearer\s+[0-9A-Za-z._\-]+", "Bearer ***", raw, flags=re.IGNORECASE)
    raw = re.sub(r"api[_-]?key[=:]\s*[0-9A-Za-z._\-]+", "api_key=***", raw, flags=re.IGNORECASE)
    raw = raw.replace("\r", " ").replace("\n", " ")
    if len(raw) > limit:
        raw = raw[:limit].rstrip() + "..."
    return raw or exc.__class__.__name__


class _SimpleLLMResult:
    def __init__(self, content: str) -> None:
        self.content = content


class _OpenAICompatibleChatClient:
    """Minimal OpenAI-compatible chat client with explicit timeout control.

    This is used for the NVIDIA fallback route to avoid long LangChain/ChatNVIDIA
    retries hanging the Chair pipeline when Gemini fails.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        timeout: int = 60,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.model = (model or MODEL_NAME).strip()
        self.base_url = _normalize_nvidia_base_url(base_url or DEFAULT_NVIDIA_BASE_URL)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self.timeout = int(timeout)
        if not self.api_key:
            raise ValueError("NVIDIA-compatible fallback API key is missing.")

    def _endpoint(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"

    @staticmethod
    def _prompt_to_text(prompt: Any) -> str:
        if isinstance(prompt, str):
            return prompt
        if hasattr(prompt, "to_string"):
            return str(prompt.to_string())
        if hasattr(prompt, "content"):
            return str(getattr(prompt, "content"))
        return str(prompt)

    def invoke(self, prompt: Any) -> _SimpleLLMResult:
        import requests

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": self._prompt_to_text(prompt)}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(self._endpoint(), headers=headers, json=payload, timeout=self.timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f"NVIDIA-compatible API status={resp.status_code} reason={resp.reason}")
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("NVIDIA-compatible API returned no choices.")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            content = "".join(
                str(part.get("text", "")) if isinstance(part, dict) else str(part)
                for part in content
            )
        content = str(content or "").strip()
        if not content:
            raise RuntimeError("NVIDIA-compatible API returned empty content.")
        return _SimpleLLMResult(content=content)


def _build_gemini_primary() -> Any:
    """Build Finance Gemini client from PARALLEL/GEMINI env variables.

    Default route:
      PARALLEL_LLM_PROVIDER=gemini
      GEMINI_PARALLEL_API_KEY or GEMINI_API_KEY
      GEMINI_PARALLEL_MODEL
      GEMINI_PARALLEL_MAX_TOKENS
      GEMINI_TEMPERATURE
      GEMINI_TIMEOUT
    """

    llm = build_gemini_chat_client(
        agent_name="finance",
        api_key_env_names=("GEMINI_PARALLEL_API_KEY", "FINANCE_GEMINI_API_KEY", "GEMINI_API_KEY"),
        model_env_names=("FINANCE_GEMINI_MODEL", "GEMINI_PARALLEL_MODEL"),
        max_tokens_env_names=("FINANCE_GEMINI_MAX_TOKENS", "GEMINI_PARALLEL_MAX_TOKENS", "FINANCE_MAX_TOKENS"),
        temperature=float(_env_first("FINANCE_GEMINI_TEMPERATURE", "GEMINI_TEMPERATURE", default="0") or 0),
    )
    source = _env_first_name("GEMINI_PARALLEL_API_KEY", "FINANCE_GEMINI_API_KEY", "GEMINI_API_KEY")
    print(f"[finance] LLM provider=gemini source={source} model={llm.model} base_url={llm.base_url} timeout={llm.timeout}")
    return llm


def _build_nvidia_fallback() -> Any:
    """Build NVIDIA-compatible fallback.

    The fallback is used when Gemini fails.  It reads explicit finance/NVIDIA
    variables first, then CHAIR_LLM_* and DART_LLM_* because many local .env files
    keep the NVIDIA-compatible route under those shared names.
    """

    api_key = _env_first(
        "FINANCE_NVIDIA_API_KEY",
        "NVIDIA_PARALLEL_API_KEY",
        "NVIDIA_API_KEY",
        "CHAIR_LLM_API_KEY",
        "DART_LLM_API_KEY",
        default=NVIDIA_API_KEY,
    )
    if not api_key:
        raise ValueError(
            "NVIDIA-compatible fallback key is missing. "
            "Set FINANCE_NVIDIA_API_KEY/NVIDIA_PARALLEL_API_KEY/NVIDIA_API_KEY, "
            "or provide CHAIR_LLM_API_KEY/DART_LLM_API_KEY."
        )

    model = _env_first(
        "FINANCE_NVIDIA_MODEL",
        "NVIDIA_PARALLEL_MODEL",
        "NVIDIA_MODEL",
        "CHAIR_LLM_MODEL",
        "DART_LLM_MODEL",
        default=MODEL_NAME,
    ) or MODEL_NAME

    base_url = _env_first(
        "FINANCE_NVIDIA_BASE_URL",
        "NVIDIA_PARALLEL_BASE_URL",
        "NVIDIA_BASE_URL",
        "CHAIR_LLM_BASE_URL",
        "DART_LLM_BASE_URL",
        default=DEFAULT_NVIDIA_BASE_URL,
    )

    timeout = _safe_int(
        _env_first("FINANCE_NVIDIA_TIMEOUT", "NVIDIA_TIMEOUT", "REQUEST_TIMEOUT", default="60"),
        60,
    )
    max_tokens = _safe_int(
        _env_first("FINANCE_NVIDIA_MAX_TOKENS", "NVIDIA_PARALLEL_MAX_TOKENS", "FINANCE_MAX_TOKENS", default="4096"),
        4096,
    )

    print(f"[finance] LLM fallback provider=nvidia-compatible model={model} timeout={timeout}")
    return _OpenAICompatibleChatClient(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=0,
        max_tokens=max_tokens,
        timeout=timeout,
    )


class _GeminiOnlyFinanceLLM:
    """Finance LLM wrapper that uses Gemini only.

    Previous code automatically switched to NVIDIA-compatible models when Gemini
    returned a temporary error.  That made logs and results confusing because a
    Gemini-capacity issue suddenly produced Qwen/DeepSeek output.  The default
    route is now Gemini-only.  NVIDIA is used only when the user explicitly sets
    FINANCE_LLM_PROVIDER=nvidia or PARALLEL_LLM_PROVIDER=nvidia.
    """

    def __init__(self) -> None:
        self._primary: Any | None = None

    def _primary_llm(self) -> Any:
        if self._primary is None:
            self._primary = _build_gemini_primary()
        return self._primary

    def invoke(self, prompt: Any) -> Any:
        try:
            return self._primary_llm().invoke(prompt)
        except Exception as exc:
            raise RuntimeError(
                "Finance Gemini LLM failed. "
                "Automatic NVIDIA fallback is disabled; "
                "set FINANCE_LLM_PROVIDER=nvidia or PARALLEL_LLM_PROVIDER=nvidia only when you intentionally want NVIDIA. "
                f"reason={_safe_error_message(exc)}"
            ) from exc


def _provider_is_nvidia(provider: str | None) -> bool:
    value = str(provider or "").strip().lower()
    return value in {
        "nvidia",
        "nvidia-compatible",
        "nvidia_compatible",
        "openai-compatible",
        "openai_compatible",
        "qwen",
        "deepseek",
    }


def build_llm() -> Any:
    """Finance Agent LLM 생성.

    Default:
        PARALLEL_LLM_PROVIDER=gemini
        GEMINI_PARALLEL_API_KEY / GEMINI_API_KEY
        GEMINI_PARALLEL_MODEL

    Manual fallback/switch:
        FINANCE_LLM_PROVIDER=nvidia 또는 PARALLEL_LLM_PROVIDER=nvidia 를 명시했을 때만
        NVIDIA-compatible route를 사용한다. Gemini 오류만으로 자동 fallback하지 않는다.
    """

    provider = _env_first("FINANCE_LLM_PROVIDER", "PARALLEL_LLM_PROVIDER", default=FINANCE_LLM_PROVIDER or "gemini")
    if _provider_is_nvidia(provider):
        print("[finance] LLM provider=nvidia-compatible selected by env; Gemini route is not used.")
        return _build_nvidia_fallback()

    if str(provider or "").strip().lower() not in {"", "gemini", "google", "google_gemini", "google-gemini"}:
        print(f"[finance] unknown LLM provider={provider!r}; using Gemini route by default.")

    return _GeminiOnlyFinanceLLM()



def _strip_think_blocks(text: str) -> str:
    """Qwen 3.5 등 thinking 모델의 <think>...</think> 블록을 제거합니다."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _extract_json(text: str) -> dict[str, Any]:
    """LLM 응답에서 JSON 객체 1개를 안전하게 추출한다."""
    cleaned = _strip_think_blocks(text)
    cleaned = cleaned.strip()

    # 1) ```json ... ``` 코드 펜스 안 JSON 우선 추출
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 2) 가장 바깥 중괄호 JSON 객체 추출
    start = cleaned.find("{")
    if start == -1:
        raise ValueError("응답에서 JSON 객체를 찾지 못했습니다.")

    depth = 0
    in_string = False
    escape_next = False
    end = start

    for i in range(start, len(cleaned)):
        ch = cleaned[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\":
            escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if depth != 0:
        raise ValueError("응답에서 완전한 JSON 객체를 찾지 못했습니다 (중괄호 불균형).")

    return json.loads(cleaned[start : end + 1])


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    return [value]


def _clean_short_text(value: Any, limit: int = 500) -> str:
    text = str(value or "").replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def _coerce_mapping(value: Any) -> dict[str, Any]:
    """dict 또는 dict처럼 보이는 문자열을 안전하게 dict로 변환한다.

    Gemini/일부 LLM이 다음처럼 summary 필드 안에 다시 dict를 넣는 경우가 있다.
    {
      "summary": {"summary": "...", "key_risks": [...]}
    }

    이 상태를 그대로 str() 처리하면 terminal/Chair View에서
    "{'summary': ... '영…"처럼 잘린 dict 문자열이 summary에 들어간다.
    """
    if isinstance(value, dict):
        return dict(value)
    if not isinstance(value, str):
        return {}

    text = value.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return {}

    # 1) 정상 JSON 우선
    try:
        obj = json.loads(text)
        return dict(obj) if isinstance(obj, dict) else {}
    except Exception:
        pass

    # 2) Python dict 문자열 fallback: {'summary': '...', 'key_risks': [...]}
    try:
        obj = ast.literal_eval(text)
        return dict(obj) if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _flatten_finance_payload(data: dict[str, Any]) -> dict[str, Any]:
    """LLM 응답의 중첩 구조를 Report 스키마에 맞게 평탄화한다.

    특히 Gemini가 summary 필드에 다시 summary/key_thesis/key_risks를
    넣어 반환하는 경우를 처리한다. 기존 NVIDIA/OpenAI-compatible 응답에는
    영향을 주지 않는다.
    """
    if not isinstance(data, dict):
        return {}

    out = dict(data)

    # summary/result/analysis 계열 안에 실제 payload가 들어간 경우를 모두 흡수
    nested_keys = (
        "summary",
        "result",
        "analysis",
        "finance_analysis",
        "financial_analysis",
        "재무분석",
        "분석결과",
    )

    for key in nested_keys:
        nested = _coerce_mapping(out.get(key))
        if not nested:
            continue

        # nested.summary는 top-level summary 문자열로 승격
        nested_summary = (
            nested.get("summary")
            or nested.get("analysis_summary")
            or nested.get("종합의견")
        )
        if nested_summary and not isinstance(nested_summary, (dict, list)):
            out["summary"] = nested_summary

        # key_thesis/key_risks 등은 비어 있을 때만 보강
        for nested_name, top_name in (
            ("key_thesis", "key_thesis"),
            ("strengths", "key_thesis"),
            ("핵심근거", "key_thesis"),
            ("key_risks", "key_risks"),
            ("risks", "key_risks"),
            ("리스크", "key_risks"),
            ("warning_note", "warning_note"),
        ):
            value = nested.get(nested_name)
            if value is not None and not out.get(top_name):
                out[top_name] = value

    return out


def _summary_text(value: Any, limit: int = 700) -> str:
    """summary 후보를 사람이 읽을 수 있는 한 문장/문단 문자열로 정리한다."""
    nested = _coerce_mapping(value)
    if nested:
        for key in ("summary", "analysis_summary", "종합의견"):
            text = nested.get(key)
            if text and not isinstance(text, (dict, list)):
                return _clean_short_text(text, limit)

        # 그래도 문자열 summary가 없으면 핵심 필드만 짧게 조합
        pieces: list[str] = []
        for key in ("company_name", "risk_assessment"):
            text = nested.get(key)
            if text and not isinstance(text, (dict, list)):
                pieces.append(str(text))
        if pieces:
            return _clean_short_text(" / ".join(pieces), limit)
        return ""

    if isinstance(value, list):
        parts = [_summary_text(v, limit=limit) for v in value]
        return _clean_short_text(" ".join([p for p in parts if p]), limit)

    return _clean_short_text(value, limit)


def _extract_company_name_from_prompt(prompt: str) -> str:
    # prompts.py 본문 안의 [기업명] 다음 줄에서 회사명을 가져온다.
    m = re.search(r"\[기업명\]\s*\n\s*([^\n\r]+)", prompt)
    if m:
        return m.group(1).strip()
    return "확인 제한"


def _derive_key_lists(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    key_thesis = [
        _clean_short_text(v, 260)
        for v in _as_list(data.get("key_thesis") or data.get("strengths") or data.get("positive_factors"))
        if _clean_short_text(v, 260)
    ]
    key_risks = [
        _clean_short_text(v, 260)
        for v in _as_list(data.get("key_risks") or data.get("risk_factors") or data.get("risks"))
        if _clean_short_text(v, 260)
    ]

    return key_thesis[:8], key_risks[:8]


def _normalize_report_payload(data: dict[str, Any], prompt: str) -> dict[str, Any]:
    data = _flatten_finance_payload(data)

    company_name = (
        data.get("company_name")
        or data.get("company")
        or data.get("기업명")
        or _extract_company_name_from_prompt(prompt)
    )
    industry_type = data.get("industry_type") or data.get("industry") or "deeptech_semiconductor"

    summary_candidates = [
        data.get("summary"),
        data.get("analysis_summary"),
        data.get("investment_summary"),
        data.get("report_summary"),
        data.get("종합의견"),
        data.get("요약"),
    ]
    summary = next((_summary_text(v, 700) for v in summary_candidates if _summary_text(v, 700)), "제공된 데이터 기준으로 재무·주가 지표를 분석했습니다.")

    # risk_assessment 같은 자유 필드도 summary 뒤에 자연스럽게 보존한다.
    risk_assessment = _clean_short_text(data.get("risk_assessment") or data.get("risk_summary"), 350)
    if risk_assessment and risk_assessment not in summary:
        summary = f"{summary} 리스크 평가: {risk_assessment}"

    key_thesis, key_risks = _derive_key_lists(data)
    if not key_risks:
        key_risks = ["수익성, 레버리지, 주가 변동성은 함께 확인해야 합니다."]

    warning_note = data.get("warning_note")
    if warning_note is not None:
        warning_note = _clean_short_text(warning_note, 300) or None

    return {
        "agent": "finance",
        "company_name": str(company_name),
        "industry_type": str(industry_type),
        "summary": summary,
        "key_thesis": key_thesis[:8],
        "key_risks": key_risks[:8],
        "warning_note": warning_note,
    }


_PROMPT_JSON_GUARD = """

[최종 JSON 출력 재확인]
- 위 prompts.py의 작성 규칙을 최우선으로 따른다.
- 최종 출력은 JSON 객체 1개만 출력한다.
- 설명문, 마크다운, 코드펜스, <think>, <tool_call> 블록은 출력하지 않는다.
- key_thesis와 key_risks에는 prompts.py가 지정한 필수 지표를 최대한 반영한다.
- 데이터로 산출할 수 없는 필수 지표는 확인 필요 항목으로만 보수적으로 언급한다.
"""

_SCHEMA_GUIDE = """

[최종 출력 스키마 - 반드시 준수]
반드시 아래 스키마 형태의 JSON 객체 1개만 출력하세요.
JSON 바깥의 설명문은 출력하지 마세요.
필드명은 영문 snake_case 그대로 사용하고, 누락하지 마세요.

{
  "agent": "finance",
  "company_name": "string",
  "industry_type": "string",
  "summary": "string",
  "key_thesis": ["string", "string"],
  "key_risks": ["string", "string"],
  "warning_note": "string 또는 null"
}

[summary/key_thesis 작성 고정 규칙]
- summary는 3~4문장 이내의 기관 리포트 톤으로 작성한다.
- key_thesis는 최소 4개, 최대 8개 작성한다.
- key_risks는 최소 3개, 최대 8개 작성한다.
- key_thesis와 key_risks는 반드시 제공 데이터의 연도, 수치, 방향성을 포함한다.
"""

_FEW_SHOT_REPORT_STYLE = """

[출력 스타일 예시 - 형식과 밀도만 참고, 회사명/수치/문장은 현재 입력 데이터로 새로 작성]
{
  "agent": "finance",
  "company_name": "예시회사",
  "industry_type": "deeptech_semiconductor",
  "summary": "예시회사는 최근 연도 매출이 두 자릿수 성장으로 전환되며 감소세가 멈췄으나, 영업이익률과 ROE는 여전히 음수여서 수익성 회복 확인이 필요하다. 자유현금흐름은 3년 연속 양의 값을 유지해 현금 창출 능력은 남아 있으나, 부채비율이 높은 수준이어서 재무 건전성 부담은 지속된다. 주가는 연초 대비 큰 폭으로 반등했지만 연간 MDD와 최근 급락 구간이 확인되어 변동성 리스크가 크다.",
  "key_thesis": [
    "최근 연도 매출성장률이 양수로 전환되며 이전 역성장에서 벗어나는 흐름을 보였다.",
    "자유현금흐름은 복수 연도에 걸쳐 양의 값을 유지해 현금 창출 능력이 확인된다.",
    "연수익률은 전년도 부진 이후 큰 폭으로 반등하며 주가 모멘텀이 개선됐다.",
    "유동비율은 전년 대비 개선되었으나 100% 미만이면 단기 유동성 점검이 필요하다."
  ],
  "key_risks": [
    "영업이익률이 음수로 남아 있어 본업 수익성 회복 여부가 핵심 변수다.",
    "ROE가 음수이면 자본 대비 수익성이 아직 정상화되지 않았다는 점을 확인해야 한다.",
    "부채비율이 높은 수준이면 재무 레버리지 부담이 투자 판단의 주요 리스크다.",
    "연간 MDD가 큰 폭이면 주가 변동성에 따른 손실 가능성을 함께 고려해야 한다."
  ],
  "warning_note": null
}
"""


def _build_llm_prompt(prompt: str) -> str:
    """Finance LLM에 스키마와 few-shot 스타일 가이드를 항상 함께 전달한다."""
    return f"{prompt}{_PROMPT_JSON_GUARD}{_SCHEMA_GUIDE}{_FEW_SHOT_REPORT_STYLE}"


def _normalize_content(content: Any) -> str:
    """LangChain response content를 문자열로 정규화한다."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or item))
            elif hasattr(item, "text"):
                parts.append(str(item.text))
            else:
                parts.append(str(item))
        return "".join(parts).strip()

    return str(content).strip()


def _parse_llm_result(result: Any) -> dict[str, Any]:
    content = getattr(result, "content", result)
    content_text = _normalize_content(content)

    if not content_text.strip():
        raise ValueError("LLM 응답이 비어 있습니다.")

    return _extract_json(content_text)


def _invoke_llm(llm: Any, prompt: str) -> dict[str, Any]:
    """LLM을 호출하고 응답에서 JSON을 추출합니다."""
    llm_prompt = _build_llm_prompt(prompt)
    try:
        return _parse_llm_result(llm.invoke(llm_prompt))
    except Exception as exc:
        invoke_fallback = getattr(llm, "invoke_fallback", None)
        if callable(invoke_fallback):
            return _parse_llm_result(invoke_fallback(llm_prompt, exc))
        raise


def analyze_finance(prompt: str, get_extended_data=None) -> Report:
    """재무 분석을 수행합니다.

    Args:
        prompt: 초기 프롬프트.
        get_extended_data: 추가 데이터 요청 시 호출할 콜백 함수.
            (start_date, end_date) -> extended_prompt_str
            None이면 추가 데이터 요청 기능을 비활성화합니다.
    """
    llm = build_llm()

    data = _invoke_llm(llm, prompt)

    # 에이전트가 추가 데이터를 요청했는지 확인
    if data.get("request_more_data") and get_extended_data is not None:
        start_date = data.get("start_date", "")
        end_date = data.get("end_date", "")
        reason = data.get("reason", "")
        print(f"  [추가 데이터 요청] {reason} ({start_date} ~ {end_date})")

        extended_prompt = get_extended_data(start_date, end_date)
        data = _invoke_llm(llm, extended_prompt)

    normalized = _normalize_report_payload(data, prompt)
    return Report.model_validate(normalized)
