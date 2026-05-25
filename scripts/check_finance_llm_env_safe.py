from __future__ import annotations

"""Safely inspect Finance LLM environment routing without printing secrets.

This script intentionally does not print API key values, spreadsheet IDs, tokens,
or other secret-like values. It only reports whether the variables are present and
which credential bundle Finance Agent will use.

Usage:
  python scripts/check_finance_llm_env_safe.py
"""

import os
from pathlib import Path


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def _env_first(values: dict[str, str], *names: str) -> str:
    for name in names:
        value = os.getenv(name) or values.get(name, "")
        if str(value).strip():
            return str(value).strip()
    return ""


def _present(values: dict[str, str], name: str) -> str:
    value = os.getenv(name) or values.get(name, "")
    return "present" if str(value).strip() else "missing"


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    values = _load_env_file(env_path)

    print("[Finance LLM env safe check]")
    print(f"project_root={root}")
    print(f"env_file={'.env found' if env_path.exists() else '.env missing'}")
    print()

    check_names = [
        "FINANCE_LLM_PROVIDER",
        "FINANCE_GEMINI_API_KEY",
        "GEMINI_API_KEY",
        "GEMINI_PARALLEL_API_KEY",
        "FINANCE_GEMINI_MODEL",
        "GEMINI_PARALLEL_MODEL",
        "GEMINI_BASE_URL",
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
    for name in check_names:
        print(f"{name}: {_present(values, name)}")

    route = None
    route_specs = [
        ("FINANCE_NVIDIA_*", ["FINANCE_NVIDIA_API_KEY", "FINANCE_LLM_API_KEY", "FINANCE_API_KEY"]),
        ("NVIDIA_PARALLEL_* / NVIDIA_*", ["NVIDIA_PARALLEL_API_KEY", "NVIDIA_API_KEY"]),
        ("CHAIR_LLM_*", ["CHAIR_LLM_API_KEY"]),
        ("DART_LLM_*", ["DART_LLM_API_KEY"]),
    ]
    for label, names in route_specs:
        if _env_first(values, *names):
            route = label
            break

    print()
    print(f"selected_nvidia_compatible_route={route or 'none'}")
    if route:
        print("default_finance_provider=auto -> nvidia-compatible first")
    else:
        print("default_finance_provider=auto -> gemini first, CSV fallback if Gemini fails")

    print()
    print("No API key, token, raw model value, URL value, or ID was printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
