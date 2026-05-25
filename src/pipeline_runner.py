from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Sequence

from common.stdio import configure_utf8_stdio
from data_intake.runner import run_data_intake
from chair_agent.graph import build_chair_graph

configure_utf8_stdio()


DEFAULT_PIPELINE_AGENTS = "macro,market,issue,finance,tech,valuation"
SHEETS_BACKEND_VALUES = {"sheets", "google_sheets", "gsheets", "google"}


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        value = str(os.getenv(name, "")).strip()
        return int(value) if value else default
    except Exception:
        return default


def _sheets_output_requested() -> bool:
    backend = os.getenv("ALPHAPROVE_CHAIR_OUTPUT_BACKEND", "").strip().lower()
    return backend in SHEETS_BACKEND_VALUES or _env_bool("CHAIR_USE_GOOGLE_SHEETS", False)


def _force_local_chair_history() -> None:
    """Keep full-pipeline runs independent from stale Google Sheets .env values."""
    if _sheets_output_requested():
        return
    os.environ["ALPHAPROVE_HISTORY_BACKEND"] = "local"
    os.environ["ALPHAPROVE_DISABLE_GOOGLE_SHEETS"] = "1"
    os.environ["ALPHAPROVE_CHAIR_OUTPUT_BACKEND"] = "local"
    os.environ["CHAIR_FORCE_LOCAL_OUTPUT"] = "1"
    os.environ["ALPHAPROVE_SHEETS_DB_ONLY"] = "0"
    os.environ["ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED"] = "0"
    os.environ.setdefault("CHAIR_FORCE_TEMPLATE_REPORT", "1")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the full AlphaProve flow: data_intake -> 6 specialist agents "
            "-> First Auditor -> Chair report."
        )
    )
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--agents", default=DEFAULT_PIPELINE_AGENTS)
    parser.add_argument("--skip-network", action="store_true", help="intake 단계에서 가능한 네트워크 수집을 생략")
    parser.add_argument("--force-fetch", action="store_true", help="intake 단계에서 원천 데이터 재수집 강제")
    parser.add_argument("--tech-max-patents", type=int, default=None)
    parser.add_argument("--tech-sleep-sec", type=float, default=None)
    parser.add_argument("--tech-timeout", type=int, default=None)
    parser.add_argument(
        "--intake-concurrency",
        type=int,
        default=_env_int("PIPELINE_INTAKE_CONCURRENCY", 4),
        help="data_intake agent 병렬 실행 수. 1이면 순차 실행",
    )
    parser.add_argument(
        "--agent-concurrency",
        type=int,
        default=_env_int("PIPELINE_AGENT_CONCURRENCY", 6),
        help="Chair graph specialist agent 병렬 실행 수",
    )
    parser.add_argument(
        "--market-llm-timeout",
        type=int,
        default=_env_int("PIPELINE_MARKET_LLM_TIMEOUT", 25),
        help="pipeline 실행 중 Market Agent LLM 1회 요청 timeout",
    )
    parser.add_argument(
        "--market-gemini-retries",
        type=int,
        default=_env_int("PIPELINE_MARKET_GEMINI_RETRIES", 0),
        help="pipeline 실행 중 Market Agent Gemini 재시도 횟수",
    )
    parser.add_argument(
        "--tech-intake-run-agent",
        action="store_true",
        help="호환용: data_intake의 tech_intake 안에서도 Tech Agent를 실행",
    )
    parser.add_argument("--stop-on-intake-error", action="store_true")
    parser.add_argument("--fail-open", action="store_true", help="Auditor가 실패해도 Chair 보고서 생성을 시도")
    parser.add_argument("--json", action="store_true", help="최종 state 요약 JSON 출력")
    args = parser.parse_args(argv)

    _force_local_chair_history()

    if args.fail_open:
        os.environ["AUDITOR_FIRST_FAIL_OPEN"] = "1"

    print("=" * 88)
    print(f"AlphaProve Full Pipeline 시작: {args.company} / {args.company_dir}")
    print("단계: data_intake -> 6 agents(finance/market/tech/valuation/issue/macro) -> auditor -> chair")
    print(f"병렬 설정: data_intake={max(1, args.intake_concurrency)}, chair_agents={max(1, args.agent_concurrency)}")
    print(f"Market LLM budget: timeout={max(1, args.market_llm_timeout)}s, retries={max(0, args.market_gemini_retries)}")
    print("=" * 88)

    total_started = time.perf_counter()
    intake_started = time.perf_counter()
    intake_result = run_data_intake(
        company_dir=args.company_dir,
        company=args.company,
        field=args.field,
        agents=[a.strip() for a in args.agents.replace(";", ",").split(",") if a.strip()],
        continue_on_error=not args.stop_on_intake_error,
        tech_max_patents=args.tech_max_patents,
        tech_sleep_sec=args.tech_sleep_sec,
        tech_timeout=args.tech_timeout,
        tech_force_fetch=args.force_fetch,
        skip_network=args.skip_network,
        tech_skip_network=args.skip_network,
        # The full pipeline runs Tech Agent in the Chair graph's tech node.
        # Running it inside tech_intake as well doubles that specialist stage.
        tech_skip_agent=not args.tech_intake_run_agent,
        parallel=args.intake_concurrency != 1,
        max_workers=max(1, args.intake_concurrency),
    )
    intake_seconds = time.perf_counter() - intake_started

    graph = build_chair_graph()

    # Data Intake already ran above. Chair must NOT run it again.
    # Set both state and temporary env guards so the no-rerun contract is honored
    # even if an older chair graph is still imported from cache or another path.
    previous_disable = os.environ.get("CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS")
    previous_run = os.environ.get("CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS")
    os.environ["CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS"] = "1"
    os.environ["CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS"] = "0"
    market_speed_defaults = {
        "MARKET_AGENT_SKIP_LIVE_REFRESH": "1",
        "MARKET_LLM_MAX_ATTEMPTS": "1",
        "MARKET_GEMINI_TIMEOUT": str(max(1, args.market_llm_timeout)),
        "MARKET_GEMINI_MAX_RETRIES": str(max(0, args.market_gemini_retries)),
        "MARKET_MAX_TOKENS": "2048",
    }
    previous_market_speed = {key: os.environ.get(key) for key in market_speed_defaults}
    for key, value in market_speed_defaults.items():
        os.environ.setdefault(key, value)
    chair_started = time.perf_counter()
    try:
        state = graph.invoke(
            {
                "company_dir": args.company_dir,
                "company": args.company,
                "run_data_intake": False,
                "data_intake_result": intake_result,
                "pipeline_data_intake_already_ran": True,
            },
            config={"max_concurrency": max(1, args.agent_concurrency)},
        )
    finally:
        if previous_disable is None:
            os.environ.pop("CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS", None)
        else:
            os.environ["CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS"] = previous_disable
        if previous_run is None:
            os.environ.pop("CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS", None)
        else:
            os.environ["CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS"] = previous_run
        for key, previous_value in previous_market_speed.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value
    chair_seconds = time.perf_counter() - chair_started
    total_seconds = time.perf_counter() - total_started

    report = state.get("chair_report") or ""
    print("=" * 88)
    print("[Pipeline] 완료")
    print(f"[Pipeline] data_intake_status={intake_result.get('status')}")
    print(f"[Pipeline] opinions={len(state.get('opinions') or [])}")
    print(f"[Pipeline] report_chars={len(report)}")
    print(
        "[Pipeline] timings: "
        f"data_intake={intake_seconds:.1f}s, chair_graph={chair_seconds:.1f}s, total={total_seconds:.1f}s"
    )
    print("=" * 88)

    if args.json:
        payload: dict[str, Any] = {
            "company_dir": args.company_dir,
            "company": args.company,
            "data_intake_status": intake_result.get("status"),
            "opinion_agents": [o.get("agent") for o in (state.get("opinions") or []) if isinstance(o, dict)],
            "auditor_result": state.get("auditor_result"),
            "report_chars": len(report),
            "timings_sec": {
                "data_intake": round(intake_seconds, 3),
                "chair_graph": round(chair_seconds, 3),
                "total": round(total_seconds, 3),
            },
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
