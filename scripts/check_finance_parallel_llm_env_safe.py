from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import find_dotenv, load_dotenv
except Exception:
    find_dotenv = None
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if load_dotenv is not None:
    env_path = find_dotenv(usecwd=True) if find_dotenv is not None else ""
    if not env_path:
        candidate = PROJECT_ROOT / ".env"
        env_path = str(candidate) if candidate.exists() else ""
    if env_path:
        load_dotenv(env_path, override=False)


def present(name: str) -> str:
    value = os.getenv(name)
    return "present" if value and str(value).strip() else "missing"


def selected_route() -> str:
    provider = (os.getenv("PARALLEL_LLM_PROVIDER") or "gemini").strip().lower()
    if provider in {"gemini", "google", "google_gemini"}:
        primary = "gemini"
    else:
        primary = provider

    if os.getenv("GEMINI_PARALLEL_API_KEY") or os.getenv("GEMINI_API_KEY"):
        gemini = "available"
    else:
        gemini = "missing"

    if os.getenv("FINANCE_NVIDIA_API_KEY") or os.getenv("NVIDIA_PARALLEL_API_KEY") or os.getenv("NVIDIA_API_KEY"):
        nvidia = "explicit_nvidia_available"
    elif os.getenv("CHAIR_LLM_API_KEY") and os.getenv("CHAIR_LLM_BASE_URL"):
        nvidia = "shared_chair_llm_available"
    elif os.getenv("DART_LLM_API_KEY") and os.getenv("DART_LLM_BASE_URL"):
        nvidia = "shared_dart_llm_available"
    else:
        nvidia = "missing"

    return f"primary={primary} gemini={gemini} fallback={nvidia}"


def main() -> int:
    print("[Finance parallel LLM env safe check]")
    print(f"project_root={PROJECT_ROOT}")
    print(f"env_file={'.env found' if (PROJECT_ROOT / '.env').exists() else '.env missing'}")
    print()

    names = [
        "PARALLEL_LLM_PROVIDER",
        "GEMINI_PARALLEL_API_KEY",
        "GEMINI_API_KEY",
        "GEMINI_PARALLEL_MODEL",
        "GEMINI_PARALLEL_MAX_TOKENS",
        "GEMINI_TEMPERATURE",
        "GEMINI_TIMEOUT",
        "FINANCE_NVIDIA_API_KEY",
        "NVIDIA_PARALLEL_API_KEY",
        "NVIDIA_API_KEY",
        "FINANCE_NVIDIA_MODEL",
        "NVIDIA_PARALLEL_MODEL",
        "FINANCE_NVIDIA_BASE_URL",
        "NVIDIA_PARALLEL_BASE_URL",
        "CHAIR_LLM_API_KEY",
        "CHAIR_LLM_MODEL",
        "CHAIR_LLM_BASE_URL",
        "DART_LLM_API_KEY",
        "DART_LLM_MODEL",
        "DART_LLM_BASE_URL",
    ]
    for name in names:
        print(f"{name}: {present(name)}")

    print()
    print(selected_route())
    print("No API key, token, raw model value, URL value, or ID was printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
