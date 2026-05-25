from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


def main() -> int:
    graph = _read("src/chair_agent/graph.py")
    pipe = _read("src/pipeline_runner.py")
    runner = _read("src/chair_agent/runner.py")

    checks = [
        (
            "graph honors explicit run_data_intake=False",
            'explicit_run_intake = state.get("run_data_intake", None)' in graph
            and 'run_flag = bool(explicit_run_intake)' in graph
            and 'REUSED_PREVIOUS_PIPELINE_STAGE' in graph,
        ),
        (
            "pipeline sets chair no-intake env guard",
            'CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS' in pipe
            and 'pipeline_data_intake_already_ran' in pipe
            and '"run_data_intake": False' in pipe,
        ),
        (
            "chair --no-intake has env guard",
            '_invoke_graph_with_intake_guard' in runner
            and 'CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS' in runner,
        ),
        (
            "old buggy OR expression removed from graph",
            'bool(state.get("run_data_intake")) or env_default' not in graph,
        ),
    ]

    ok = True
    print("=" * 72)
    print("Chair duplicate Data Intake guard check")
    print("=" * 72)
    for name, passed in checks:
        print(f"[{'OK' if passed else 'FAIL'}] {name}")
        ok = ok and passed

    if not ok:
        print("\n[RESULT] FAIL: 중복 intake 방지 패치가 완전히 반영되지 않았습니다.")
        return 1

    print("\n[RESULT] OK: pipeline -> chair 단계에서 Chair가 data_intake를 재실행하지 않도록 고정되었습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
