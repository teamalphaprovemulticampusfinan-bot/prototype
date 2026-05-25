from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from common.data_paths import DATA_DIR, field_agent_dir, templates_dir

load_dotenv()


def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return default


# =========================================================
# Path
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR.parent
ROOT_DIR = SRC_DIR.parent

ASSETS_DIR = BASE_DIR / "assets"
WORKSPACE_DIR = DATA_DIR
COMPANIES_DIR = DATA_DIR
OUTPUT_DIR = field_agent_dir("tech")
TEMPLATES_DIR = templates_dir()
CACHE_DIR = ROOT_DIR / ".cache"

DEFAULT_TEMPLATE_PATH = TEMPLATES_DIR / "tech_template.xlsx"
DEFAULT_TEMPLATE_BASE_PATH = TEMPLATES_DIR / "tech_template_base.xlsx"
TECH_ROW_SCHEMA_PATH = ASSETS_DIR / "tech_row_schema.json"

# =========================================================
# API / ENV
# =========================================================
PARALLEL_LLM_PROVIDER = _env_first("TECH_LLM_PROVIDER", "PARALLEL_LLM_PROVIDER", default="openai_compatible").lower()

if PARALLEL_LLM_PROVIDER in {"gemini", "google", "google_gemini", "google-gemini"}:
    NVIDIA_PARALLEL_API_KEY = _env_first(
        "TECH_GEMINI_API_KEY",
        "GEMINI_PARALLEL_API_KEY",
        "GEMINI_API_KEY",
    )
    NVIDIA_PARALLEL_BASE_URL = _env_first(
        "TECH_GEMINI_BASE_URL",
        "GEMINI_BASE_URL",
        default="https://generativelanguage.googleapis.com/v1beta",
    )
    NVIDIA_PARALLEL_MODEL = _env_first(
        "TECH_GEMINI_MODEL",
        "GEMINI_PARALLEL_MODEL",
        "GEMINI_MODEL",
        default="gemini-2.5-flash-lite",
    )
else:
    NVIDIA_PARALLEL_API_KEY = _env_first(
        "TECH_NVIDIA_API_KEY",
        "NVIDIA_PARALLEL_API_KEY",
        "OPENAI_API_KEY",
    )
    NVIDIA_PARALLEL_BASE_URL = _env_first(
        "TECH_NVIDIA_BASE_URL",
        "NVIDIA_PARALLEL_BASE_URL",
        "OPENAI_BASE_URL",
        default="https://integrate.api.nvidia.com/v1",
    )
    NVIDIA_PARALLEL_MODEL = _env_first(
        "TECH_NVIDIA_MODEL",
        "NVIDIA_PARALLEL_MODEL",
        "OPENAI_MODEL",
        default="qwen/qwen3.5-122b-a10b",
    )

OPENAI_API_KEY = NVIDIA_PARALLEL_API_KEY
OPENAI_BASE_URL = NVIDIA_PARALLEL_BASE_URL
OPENAI_MODEL = NVIDIA_PARALLEL_MODEL

DART_API_KEY = os.getenv("DART_API_KEY", "").strip()

REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "25"))
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))

USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
).strip()

# =========================================================
# LLM runtime defaults
# =========================================================
DEFAULT_MODEL = OPENAI_MODEL
DEFAULT_BASE_URL = OPENAI_BASE_URL
MODEL_NAME = OPENAI_MODEL
BASE_URL = OPENAI_BASE_URL
TIMEOUT = REQUEST_TIMEOUT

TEMPERATURE = float(os.getenv("TEMPERATURE", "0.1"))
TOP_P = float(os.getenv("TOP_P", "0.9"))
MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "4000"))

# =========================================================
# Optional flags
# =========================================================
DEBUG = os.getenv("DEBUG", "false").lower() in {"1", "true", "yes", "y"}
USE_DART = os.getenv("USE_DART", "true").lower() in {"1", "true", "yes", "y"}
USE_HOMEPAGE = os.getenv("USE_HOMEPAGE", "true").lower() in {"1", "true", "yes", "y"}
USE_EXTRA_URLS = os.getenv("USE_EXTRA_URLS", "true").lower() in {"1", "true", "yes", "y"}

# =========================================================
# Ensure directories
# =========================================================
for path in [
    ASSETS_DIR,
    WORKSPACE_DIR,
    COMPANIES_DIR,
    OUTPUT_DIR,
    TEMPLATES_DIR,
    CACHE_DIR,
]:
    path.mkdir(parents=True, exist_ok=True)

# =========================================================
# Backward-compatible aliases
# =========================================================
DEFAULT_TIMEOUT = REQUEST_TIMEOUT
DEFAULT_MAX_CONTEXT_CHARS = MAX_CONTEXT_CHARS
LLM_MODEL_NAME = DEFAULT_MODEL
HEADERS = {"User-Agent": USER_AGENT}
ENABLE_LLM_EXTRACTION = bool(OPENAI_API_KEY)