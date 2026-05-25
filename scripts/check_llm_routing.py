from __future__ import annotations

import os
from pathlib import Path


try:
    from dotenv import load_dotenv

    ROOT = Path(__file__).resolve().parents[1]
    load_dotenv(ROOT / ".env")
except Exception:
    ROOT = Path(__file__).resolve().parents[1]


def env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def masked(value: str | None, visible: int = 8) -> str:
    if not value:
        return "(empty)"
    value = str(value)
    if len(value) <= visible:
        return "*" * len(value)
    return value[:visible] + "..." + "*" * 6


def is_gemini(provider: str | None) -> bool:
    return str(provider or "").strip().lower() in {
        "gemini",
        "google",
        "google_gemini",
        "google-gemini",
    }


def is_nvidia(provider: str | None) -> bool:
    return str(provider or "").strip().lower() in {
        "nvidia",
        "openai_compatible",
        "openai-compatible",
        "openai",
        "",
    }


def is_anthropic(provider: str | None) -> bool:
    return str(provider or "").strip().lower() in {"anthropic", "claude"}


def file_contains(path: Path, needles: list[str]) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    return all(needle in text for needle in needles)


def print_env_block() -> None:
    lower_provider = env_first("PARALLEL_LLM_PROVIDER", default="nvidia").lower()

    nvidia_key = env_first("NVIDIA_PARALLEL_API_KEY", "NVIDIA_API_KEY", "OPENAI_API_KEY")
    nvidia_base = env_first(
        "NVIDIA_PARALLEL_BASE_URL",
        "NVIDIA_BASE_URL",
        "OPENAI_BASE_URL",
        default="https://integrate.api.nvidia.com/v1",
    )
    nvidia_model = env_first(
        "NVIDIA_PARALLEL_MODEL",
        "OPENAI_MODEL",
        default="qwen/qwen3.5-397b-a17b",
    )

    gemini_key = env_first("GEMINI_PARALLEL_API_KEY", "GEMINI_API_KEY")
    gemini_model = env_first(
        "GEMINI_PARALLEL_MODEL",
        "GEMINI_MODEL",
        default="gemini-2.5-flash-lite",
    )

    chair_provider = env_first("CHAIR_LLM_PROVIDER", default="nvidia")
    chair_key = env_first("CHAIR_LLM_API_KEY", "NVIDIA_PARALLEL_API_KEY", "NVIDIA_API_KEY")
    chair_base = env_first(
        "CHAIR_LLM_BASE_URL",
        "NVIDIA_PARALLEL_BASE_URL",
        "NVIDIA_BASE_URL",
        default="https://integrate.api.nvidia.com/v1",
    )
    chair_model = env_first(
        "CHAIR_LLM_MODEL",
        "NVIDIA_PARALLEL_MODEL",
        default=nvidia_model,
    )

    auditor_provider = env_first("AUDITOR_LLM_PROVIDER", "AUDITOR_PROVIDER", default="anthropic")
    auditor_gemini_model = env_first(
        "AUDITOR_GEMINI_MODEL",
        "GEMINI_AUDITOR_MODEL",
        "AUDITOR_MODEL",
        "GEMINI_PARALLEL_MODEL",
        "GEMINI_MODEL",
        default="gemini-2.5-flash-lite",
    )
    anthropic_model = env_first("ANTHROPIC_AUDITOR_MODEL", default="(not set)")
    nvidia_auditor_model = env_first("NVIDIA_AUDITOR_MODEL", default="(not set)")
    auditor_gemini_key = env_first(
        "AUDITOR_GEMINI_API_KEY",
        "GEMINI_AUDITOR_API_KEY",
        "GEMINI_PARALLEL_API_KEY",
        "GEMINI_API_KEY",
    )
    anthropic_key = env_first("ANTHROPIC_AUDITOR_API_KEY", "AUDITOR_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
    nvidia_auditor_key = env_first(
        "NVIDIA_WEB_VERIFY_KEY",
        "WEB_VERIFY_API_KEY",
        "NVIDIA_AUDITOR_API_KEY",
        "AUDITOR_API_KEY",
        "NVIDIA_API_KEY",
        "OPENAI_API_KEY",
    )

    print("=" * 88)
    print("AlphaProve LLM routing check")
    print("=" * 88)

    print("\n[Lower 5 agents: Finance / Market / Macro / Issue / Tech]")
    print(f"PARALLEL_LLM_PROVIDER = {lower_provider}")
    if is_gemini(lower_provider):
        print("active provider       = gemini")
        print(f"active model          = {gemini_model}")
        print(f"GEMINI_API_KEY        = {masked(gemini_key)}")
        print("NVIDIA backup kept    = yes")
        print(f"NVIDIA backup model   = {nvidia_model}")
    else:
        print("active provider       = nvidia/openai-compatible")
        print(f"active model          = {nvidia_model}")
        print(f"NVIDIA base_url       = {nvidia_base}")
        print(f"NVIDIA key            = {masked(nvidia_key)}")
        print("Gemini backup kept    = yes")
        print(f"Gemini backup model   = {gemini_model}")

    print("\n[Chair only]")
    print(f"CHAIR_LLM_PROVIDER    = {chair_provider}")
    print(f"CHAIR_LLM_MODEL       = {chair_model}")
    print(f"CHAIR_LLM_BASE_URL    = {chair_base}")
    print(f"CHAIR/NVIDIA key      = {masked(chair_key)}")

    print("\n[First Auditor]")
    print(f"AUDITOR_LLM_PROVIDER  = {auditor_provider}")
    print(f"AUDITOR_PROVIDER      = {env_first('AUDITOR_PROVIDER', default='(not set)')}")
    if is_anthropic(auditor_provider):
        print(f"ANTHROPIC_AUDITOR_MODEL = {anthropic_model}")
        print(f"ANTHROPIC key           = {masked(anthropic_key)}")
        print(f"Gemini fallback model   = {auditor_gemini_model}")
    elif is_gemini(auditor_provider):
        print(f"AUDITOR_GEMINI_MODEL    = {auditor_gemini_model}")
        print(f"Gemini key              = {masked(auditor_gemini_key)}")
        print(f"Anthropic fallback model = {anthropic_model}")
    else:
        print(f"NVIDIA_AUDITOR_MODEL    = {nvidia_auditor_model}")
        print(f"NVIDIA/Auditor key      = {masked(nvidia_auditor_key)}")
        print(f"Anthropic fallback model = {anthropic_model}")

    print("\n[Switch guide]")
    print("Use Gemini for lower 5 agents : PARALLEL_LLM_PROVIDER=gemini")
    print("Use NVIDIA for lower 5 agents : PARALLEL_LLM_PROVIDER=nvidia")
    print("Do not delete either NVIDIA_* or GEMINI_* keys; just switch PARALLEL_LLM_PROVIDER.")


def print_code_block() -> int:
    checks = [
        (
            "common Gemini REST client",
            ROOT / "src" / "common" / "llm_clients.py",
            ["GeminiChatClient", "build_gemini_chat_client"],
        ),
        (
            "finance Gemini switch",
            ROOT / "src" / "finance_agent" / "analyzer.py",
            ["PARALLEL_LLM_PROVIDER", "build_gemini_chat_client"],
        ),
        (
            "market Gemini switch",
            ROOT / "src" / "market_agent" / "analyzer.py",
            ["PARALLEL_LLM_PROVIDER", "build_gemini_chat_client"],
        ),
        (
            "macro Gemini switch",
            ROOT / "src" / "macro_agent" / "llm_analyzer.py",
            ["PARALLEL_LLM_PROVIDER", "build_gemini_chat_client"],
        ),
        (
            "issue Gemini switch",
            ROOT / "src" / "issue_agent" / "llm.py",
            ["PARALLEL_LLM_PROVIDER", "build_gemini_chat_client"],
        ),
        (
            "chair separated model",
            ROOT / "src" / "chair_agent" / "graph.py",
            ["CHAIR_LLM_MODEL"],
        ),
        (
            "auditor LLM provider switch",
            ROOT / "src" / "auditor_agent" / "web_verify.py",
            ["AUDITOR_LLM_PROVIDER", "AUDITOR_PROVIDER", "anthropic", "gemini"],
        ),
    ]

    print("\n[Code integration check]")
    failed = 0
    for label, path, needles in checks:
        exists = path.exists()
        ok = exists and file_contains(path, needles)
        status = "OK" if ok else "FAIL"
        display_path = path.relative_to(ROOT) if exists else path
        print(f"{status:4} {label:28} -> {display_path}")
        if not ok:
            failed += 1

    return failed


def main() -> int:
    print_env_block()
    failed = print_code_block()

    lower_provider = env_first("PARALLEL_LLM_PROVIDER", default="nvidia").lower()
    nvidia_model = env_first("NVIDIA_PARALLEL_MODEL", default="")
    gemini_model = env_first("GEMINI_PARALLEL_MODEL", default="")
    chair_model = env_first("CHAIR_LLM_MODEL", default=nvidia_model)
    auditor_provider = env_first("AUDITOR_LLM_PROVIDER", "AUDITOR_PROVIDER", default="anthropic")

    print("\n[Decision]")
    if failed:
        print("FAIL: Some routing files are missing required Gemini/NVIDIA switch code.")
        return 1

    if is_gemini(lower_provider):
        if not env_first("GEMINI_PARALLEL_API_KEY", "GEMINI_API_KEY"):
            print("WARN: PARALLEL_LLM_PROVIDER=gemini but GEMINI_API_KEY is empty.")
        print("OK: Lower 5 agents will use Gemini backup now.")
        print("OK: NVIDIA settings are preserved, so you can return later with PARALLEL_LLM_PROVIDER=nvidia.")
    elif is_nvidia(lower_provider):
        if not env_first("NVIDIA_PARALLEL_API_KEY", "NVIDIA_API_KEY", "OPENAI_API_KEY"):
            print("WARN: PARALLEL_LLM_PROVIDER=nvidia but NVIDIA key is empty.")
        print("OK: Lower 5 agents will use NVIDIA/OpenAI-compatible route now.")
        print("OK: Gemini backup settings are preserved.")
    else:
        print(f"WARN: Unknown PARALLEL_LLM_PROVIDER={lower_provider!r}. Code will likely fall back to NVIDIA route.")

    active_lower_model = gemini_model if is_gemini(lower_provider) else nvidia_model
    if chair_model and active_lower_model and chair_model == active_lower_model:
        print("WARN: Chair and lower 5 agents use the same model.")
    else:
        print("OK: Chair model is separated from lower 5 agents.")

    if is_gemini(auditor_provider):
        if not env_first("AUDITOR_GEMINI_API_KEY", "GEMINI_AUDITOR_API_KEY", "GEMINI_PARALLEL_API_KEY", "GEMINI_API_KEY"):
            print("WARN: Auditor provider is Gemini but no Gemini key was found; Auditor web-verify will fall back or disable LLM safely.")
        else:
            print("OK: Auditor can use Gemini via AUDITOR_LLM_PROVIDER/AUDITOR_PROVIDER.")
    elif is_anthropic(auditor_provider):
        if not env_first("ANTHROPIC_AUDITOR_API_KEY", "AUDITOR_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"):
            print("WARN: Auditor provider is Anthropic but no Anthropic key was found; Auditor web-verify will fall back or disable LLM safely.")
        else:
            print("OK: Auditor can use Anthropic.")
    elif is_nvidia(auditor_provider):
        print("OK: Auditor can use NVIDIA/OpenAI-compatible route.")
    else:
        print(f"WARN: Unknown Auditor provider={auditor_provider!r}; web-verify will try configured fallbacks safely.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
