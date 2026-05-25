from __future__ import annotations

import argparse
import importlib
import sys
from collections.abc import Sequence
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common.stdio import configure_utf8_stdio

configure_utf8_stdio()

AGENT_MAP = {
    "intake": ("data_intake.runner", "main"),
    "data-intake": ("data_intake.runner", "main"),
    "data_intake": ("data_intake.runner", "main"),
    "pipeline": ("pipeline_runner", "main"),
    "full-pipeline": ("pipeline_runner", "main"),
    "full_pipeline": ("pipeline_runner", "main"),
    "tech-intake": ("data_intake.tech_intake.runner", "main"),
    "tech_intake": ("data_intake.tech_intake.runner", "main"),
    "valuation-intake": ("data_intake.valuation_intake.runner", "main"),
    "valuation_intake": ("data_intake.valuation_intake.runner", "main"),
    "valuation": ("valuation_agent.runner", "main"),
    "tech": ("tech_agent.runner", "main"),
    "issue": ("issue_agent.runner", "main"),
    "market": ("market_agent.runner", "main"),
    "macro": ("macro_agent.cli", "main"),
    "finance": ("finance_agent.runner", "main"),
    "auditor": ("auditor_agent.runner", "main"),
    "chair": ("chair_agent.runner", "main"),
}

def _remove_option_with_value(argv: list[str], option: str) -> list[str]:
    cleaned: list[str] = []
    skip_next = False
    for item in argv:
        if skip_next:
            skip_next = False
            continue
        if item == option:
            skip_next = True
            continue
        if item.startswith(option + "="):
            continue
        cleaned.append(item)
    return cleaned

def normalize_agent_argv(agent_name: str, argv: Sequence[str]) -> list[str]:
    args = list(argv)
    # finance_agent.runner가 아직 --company-dir을 직접 받지 않는 경우를 위한 호환 처리.
    # Data Intake/Chair/다른 agent는 --company-dir을 그대로 받는다.
    if agent_name == "finance":
        args = _remove_option_with_value(args, "--company-dir")
    return args

def run_agent(agent_name: str, agent_argv: Sequence[str]) -> int:
    if agent_name not in AGENT_MAP:
        print(f"Unknown agent: {agent_name}")
        print(f"Available agents: {', '.join(sorted(AGENT_MAP))}")
        return 2
    module_name, func_name = AGENT_MAP[agent_name]
    normalized_argv = normalize_agent_argv(agent_name, agent_argv)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        print(f"[ERROR] {agent_name} 모듈을 불러오지 못했습니다: {module_name}")
        print(f"        detail: {exc}")
        return 1
    func = getattr(module, func_name, None)
    if func is None:
        print(f"[ERROR] {module_name}.{func_name} 함수를 찾지 못했습니다.")
        print("        해당 agent runner에 main(argv) 함수가 있는지 확인하세요.")
        return 1
    try:
        result = func(normalized_argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        return code
    except Exception as exc:
        print(f"[ERROR] {agent_name} 실행 중 오류가 발생했습니다: {exc}")
        raise
    if isinstance(result, int):
        return result
    return 0

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AlphaProve Agent CLI",
        usage="python main.py <agent> [agent options]",
    )
    parser.add_argument("agent", choices=sorted(AGENT_MAP.keys()))
    args, agent_argv = parser.parse_known_args(argv)
    return run_agent(args.agent, agent_argv)

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
