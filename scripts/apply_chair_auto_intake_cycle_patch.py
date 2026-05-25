from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAPH_PATH = ROOT / "src" / "chair_agent" / "graph.py"
RUNNER_PATH = ROOT / "src" / "chair_agent" / "runner.py"


def _backup(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".bak_auto_intake_{stamp}")
    backup.write_text(path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    return backup


def _ensure_import_os(text: str) -> str:
    if re.search(r"^import os\b", text, flags=re.M):
        return text
    if "import argparse" in text:
        return text.replace("import argparse\n", "import argparse\nimport os\n", 1)
    if "import json" in text:
        return text.replace("import json\n", "import json\nimport os\n", 1)
    return "import os\n" + text


def patch_graph() -> None:
    if not GRAPH_PATH.exists():
        raise FileNotFoundError(f"graph.py not found: {GRAPH_PATH}")

    text = GRAPH_PATH.read_text(encoding="utf-8", errors="replace")
    _backup(GRAPH_PATH)

    text = _ensure_import_os(text)

    text = re.sub(
        r"\n\ndef _chair_csv_env\(.*?\n(?=def data_intake_node\(state: ChairState\))",
        "\n\n",
        text,
        flags=re.S,
    )

    replacement = """
def _chair_csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    items: list[str] = []
    for chunk in str(raw).replace(";", ",").split(","):
        item = chunk.strip()
        if item:
            items.append(item)
    return items


def data_intake_node(state: ChairState) -> dict[str, Any]:
    # Chair full-cycle gate:
    # Data Intake -> finance/issue/macro/market/tech -> Auditor -> Chair report
    #
    # Default is ON because intake is the automation layer that refreshes or
    # reuses latest data before each specialist agent runs.
    #
    # Controls:
    #   CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS=0 : default OFF unless --run-intake is passed
    #   CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS=1 : force skip
    #   CHAIR_DATA_INTAKE_AGENTS=macro,market,issue,finance,tech
    #   CHAIR_TECH_INTAKE_SKIP_AGENT=1 : collect/update Tech data only, then Chair tech node runs Tech Agent

    env_default = _env_bool("CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS", True)
    run_flag = bool(state.get("run_data_intake")) or env_default

    if _env_bool("CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS", False):
        run_flag = False

    if not run_flag:
        return {
            "data_intake_result": {
                "status": "SKIPPED",
                "reason": "chair data intake disabled",
            }
        }

    agents = _chair_csv_env("CHAIR_DATA_INTAKE_AGENTS", "macro,market,issue,finance,tech")
    field = os.getenv("CHAIR_DATA_INTAKE_FIELD", "반도체")

    # Tech Intake can itself run main.py tech. During Chair cycle we do NOT
    # want to run Tech Agent twice. Intake should prepare templates/KIPRIS/IP
    # artifacts, and the Chair graph's tech node should run the actual Tech Agent.
    tech_skip_agent = _env_bool("CHAIR_TECH_INTAKE_SKIP_AGENT", True)
    tech_skip_network = _env_bool(
        "CHAIR_TECH_INTAKE_SKIP_NETWORK",
        _env_bool("TECH_INTAKE_SKIP_NETWORK", False),
    )
    tech_force_fetch = _env_bool(
        "CHAIR_TECH_INTAKE_FORCE_FETCH",
        _env_bool("TECH_INTAKE_FORCE_FETCH", False),
    )

    print("[Chair] Data Intake 선행 실행 중...")
    print(f"[Chair] Data Intake agents={agents}")
    print(
        "[Chair] Tech Intake options: "
        f"skip_agent={tech_skip_agent}, "
        f"skip_network={tech_skip_network}, "
        f"force_fetch={tech_force_fetch}"
    )

    try:
        from data_intake.runner import run_data_intake

        try:
            result = run_data_intake(
                company_dir=state["company_dir"],
                company=state["company"],
                field=field,
                agents=agents,
                continue_on_error=True,
                tech_skip_agent=tech_skip_agent,
                tech_skip_network=tech_skip_network,
                tech_force_fetch=tech_force_fetch,
            )
        except TypeError as exc:
            # Compatibility fallback for older data_intake.runner signatures.
            print(f"[Chair] Data Intake 신형 인자 미지원 → 구형 호출로 재시도: {exc}")
            result = run_data_intake(
                company_dir=state["company_dir"],
                company=state["company"],
                agents=agents,
                continue_on_error=True,
            )

        status = result.get("status") if isinstance(result, dict) else type(result).__name__
        print(f"[Chair] Data Intake 완료 → status={status}")
        return {"data_intake_result": result}

    except Exception as exc:
        # Chair should not die only because intake partially failed.
        # Individual agents can still use existing data/fallbacks.
        print(f"[Chair] Data Intake 실패 → 에이전트 실행은 계속 진행: {exc}")
        return {"data_intake_result": {"status": "FAILED", "error": str(exc)}}


"""

    pattern = r"def data_intake_node\(state: ChairState\) -> dict\[str, Any\]:.*?\n(?=def finance_node\(state: ChairState\))"
    new_text, count = re.subn(pattern, replacement, text, flags=re.S)

    if count != 1:
        raise RuntimeError(
            "Could not patch data_intake_node exactly once. "
            f"Replacement count={count}. Please inspect src/chair_agent/graph.py."
        )

    GRAPH_PATH.write_text(new_text, encoding="utf-8")
    print(f"[OK] patched {GRAPH_PATH}")


def patch_runner() -> None:
    if not RUNNER_PATH.exists():
        raise FileNotFoundError(f"runner.py not found: {RUNNER_PATH}")

    text = RUNNER_PATH.read_text(encoding="utf-8", errors="replace")
    _backup(RUNNER_PATH)

    text = _ensure_import_os(text)

    if "def _chair_env_bool(" not in text:
        marker = "from .graph import build_chair_graph\n"
        helper = """from .graph import build_chair_graph


def _chair_env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

"""
        if marker in text:
            text = text.replace(marker, helper, 1)
        else:
            text = helper + "\n" + text

    text = re.sub(
        r"def run_chair\(([^)]*?), \*, run_intake: bool = False\) -> int:",
        r"def run_chair(\1, *, run_intake: bool | None = None) -> int:",
        text,
    )

    if "Chair cycle default: Data Intake -> Agents -> Auditor -> Report" not in text:
        text = re.sub(
            r"(def run_chair\(.*?\) -> int:\n)",
            r"""\1    # Chair cycle default: Data Intake -> Agents -> Auditor -> Report
    if run_intake is None:
        run_intake = _chair_env_bool("CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS", True)
    if _chair_env_bool("CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS", False):
        run_intake = False

""",
            text,
            count=1,
            flags=re.S,
        )

    if '"--no-intake"' not in text:
        text = re.sub(
            r"(parser\.add_argument\(\s*\"--run-intake\".*?\)\n)",
            r"""\1    parser.add_argument(
        "--no-intake",
        action="store_true",
        help="이번 Chair 실행에서만 Data Intake 선행 실행을 끕니다.",
    )
""",
            text,
            count=1,
            flags=re.S,
        )

    text = re.sub(
        r"return run_chair\(args\.company_dir, args\.company, run_intake=args\.run_intake\)",
        'run_intake = False if getattr(args, "no_intake", False) else (True if args.run_intake else None)\n'
        '    return run_chair(args.company_dir, args.company, run_intake=run_intake)',
        text,
    )

    RUNNER_PATH.write_text(text, encoding="utf-8")
    print(f"[OK] patched {RUNNER_PATH}")


def main() -> int:
    patch_graph()
    patch_runner()
    print("\n[DONE] Chair auto-intake cycle patch applied.")
    print("Default chair cycle is now: Data Intake -> 5 agents -> Auditor -> Chair report.")
    print("Use --no-intake or CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS=1 to skip.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
