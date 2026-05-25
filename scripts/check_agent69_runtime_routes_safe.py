from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import find_dotenv, load_dotenv

    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path, override=False)
except Exception:
    env_path = ""


def present(name: str) -> str:
    value = os.getenv(name)
    return "present" if value and value.strip() else "missing"


def first_present(*names: str) -> str:
    for name in names:
        if os.getenv(name) and os.getenv(name, "").strip():
            return name
    return "<missing>"


def main() -> int:
    project_root = Path.cwd()
    print("[Agent 6.9 runtime route safe check]")
    print(f"project_root={project_root}")
    print(f"env_file={Path(env_path).name if env_path else '<not found>'}")
    print()

    names = [
        "PARALLEL_LLM_PROVIDER",
        "FINANCE_LLM_PROVIDER",
        "GEMINI_PARALLEL_API_KEY",
        "GEMINI_API_KEY",
        "FINANCE_GEMINI_API_KEY",
        "GEMINI_PARALLEL_MODEL",
        "FINANCE_GEMINI_MODEL",
        "GEMINI_TIMEOUT",
        "GEMINI_MAX_RETRIES",
        "FINANCE_NVIDIA_API_KEY",
        "NVIDIA_PARALLEL_API_KEY",
        "NVIDIA_API_KEY",
        "CHAIR_LLM_API_KEY",
        "CHAIR_DATA_INTAKE_AGENTS",
        "CHAIR_DATA_INTAKE_SKIP_NETWORK",
        "CHAIR_TECH_INTAKE_SKIP_NETWORK",
    ]
    for name in names:
        print(f"{name}: {present(name)}")

    provider = (os.getenv("FINANCE_LLM_PROVIDER") or os.getenv("PARALLEL_LLM_PROVIDER") or "gemini").strip().lower()
    gemini_key_source = first_present("GEMINI_PARALLEL_API_KEY", "FINANCE_GEMINI_API_KEY", "GEMINI_API_KEY")
    nvidia_key_source = first_present("FINANCE_NVIDIA_API_KEY", "NVIDIA_PARALLEL_API_KEY", "NVIDIA_API_KEY", "CHAIR_LLM_API_KEY")

    print()
    print(f"finance_selected_provider={provider}")
    print(f"finance_gemini_key_source={gemini_key_source}")
    print(f"nvidia_key_source_if_manually_selected={nvidia_key_source}")
    print("finance_auto_nvidia_fallback=disabled")
    print("chair_default_data_intake_agents=macro,market,issue,finance,tech,valuation")
    print()
    print("No API key, raw token, URL value, model value, or spreadsheet ID was printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
