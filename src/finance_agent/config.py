import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

# Load the project-root .env without printing or exposing secret values.
_ENV_PATH = find_dotenv(usecwd=True)
if _ENV_PATH:
    load_dotenv(_ENV_PATH, override=False)
else:
    load_dotenv(override=False)

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
WORKSPACE_DIR = DATA_DIR / "_global_common"
COMPANIES_DIR = DATA_DIR / "반도체"

DATA_DIR.mkdir(parents=True, exist_ok=True)
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
COMPANIES_DIR.mkdir(parents=True, exist_ok=True)


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value and str(value).strip():
            return str(value).strip()
    return default


# Finance now follows the shared PARALLEL route by default.
# - default: PARALLEL_LLM_PROVIDER=gemini
# - manual switch: set FINANCE_LLM_PROVIDER=nvidia or PARALLEL_LLM_PROVIDER=nvidia
FINANCE_LLM_PROVIDER = _env_first("FINANCE_LLM_PROVIDER", "PARALLEL_LLM_PROVIDER", default="gemini").lower()

GEMINI_API_KEY = _env_first("FINANCE_GEMINI_API_KEY", "GEMINI_PARALLEL_API_KEY", "GEMINI_API_KEY")
GEMINI_MODEL_NAME = _env_first("FINANCE_GEMINI_MODEL", "GEMINI_PARALLEL_MODEL", "GEMINI_MODEL", default="gemini-2.5-flash-lite")

# These names are kept for backward compatibility with older finance code.
NVIDIA_API_KEY = _env_first(
    "FINANCE_NVIDIA_API_KEY",
    "NVIDIA_PARALLEL_API_KEY",
    "NVIDIA_API_KEY",
    "CHAIR_LLM_API_KEY",
    "DART_LLM_API_KEY",
)
MODEL_NAME = _env_first(
    "FINANCE_NVIDIA_MODEL",
    "NVIDIA_PARALLEL_MODEL",
    "NVIDIA_MODEL",
    "CHAIR_LLM_MODEL",
    "DART_LLM_MODEL",
    default="qwen/qwen3.5-122b-a10b",
)
