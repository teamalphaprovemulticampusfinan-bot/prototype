from __future__ import annotations

import argparse
import os
from pathlib import Path

from common.output_paths import agent_output_path
from common.stdio import configure_utf8_stdio

from .graph import build_chair_graph

configure_utf8_stdio()


def _chair_env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}



SHEETS_BACKEND_VALUES = {"sheets", "google_sheets", "gsheets", "google"}


def _sheets_output_requested() -> bool:
    backend = os.getenv("ALPHAPROVE_CHAIR_OUTPUT_BACKEND", "").strip().lower()
    return backend in SHEETS_BACKEND_VALUES or _chair_env_bool("CHAIR_USE_GOOGLE_SHEETS", False)


def _prepare_chair_output_env() -> None:
    """Chair 실행 기본값을 로컬 저장으로 고정한다.

    사용자가 .env에 Google Sheets history 변수를 남겨둔 상태에서 chair를 실행하면
    기존 코드가 Google Sheets only 모드로 들어가 로컬 chair JSON/MD 저장을 건너뛰었다.
    이 패치 이후에는 --sheets-output 또는 CHAIR_USE_GOOGLE_SHEETS=1을 명시하지 않는 한
    항상 로컬 저장을 우선한다.
    """
    if _sheets_output_requested():
        os.environ["CHAIR_FORCE_LOCAL_OUTPUT"] = "0"
        os.environ["ALPHAPROVE_DISABLE_GOOGLE_SHEETS"] = "0"
        os.environ.setdefault("ALPHAPROVE_SHEETS_DB_ONLY", "1")
        return

    os.environ.setdefault("ALPHAPROVE_CHAIR_OUTPUT_BACKEND", "local")
    os.environ.setdefault("CHAIR_FORCE_LOCAL_OUTPUT", "1")
    os.environ.setdefault("ALPHAPROVE_DISABLE_GOOGLE_SHEETS", "1")
    os.environ["ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED"] = "0"
    os.environ["ALPHAPROVE_SHEETS_DB_ONLY"] = "0"
    # 두 번째 기준 MD와 같은 템플릿 양식을 기본값으로 고정한다.
    # LLM 자유생성 보고서가 필요할 때만 CHAIR_FORCE_TEMPLATE_REPORT=0으로 명시한다.
    os.environ.setdefault("CHAIR_FORCE_TEMPLATE_REPORT", "1")


def _history_local_write_disabled() -> bool:
    if _chair_env_bool("CHAIR_FORCE_LOCAL_OUTPUT", True) and not _sheets_output_requested():
        return False
    backend = os.getenv("ALPHAPROVE_HISTORY_BACKEND", "").strip().lower()
    sheets_mode = backend in SHEETS_BACKEND_VALUES or bool(os.getenv("ALPHAPROVE_HISTORY_SPREADSHEET_ID"))
    db_only = _chair_env_bool("ALPHAPROVE_SHEETS_DB_ONLY", False)
    disabled = _chair_env_bool("ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED", True)
    return sheets_mode and db_only and disabled


def _save_report(company_dir: str, report: str) -> Path:
    safe_name = "".join(
        ch for ch in company_dir if ch not in '\\/:*?"<>|'
    ).strip() or "chair"

    if _history_local_write_disabled():
        # Return a virtual path for logging only.  Do not write under
        # data/<field>/<company>/chair during history replay.
        return Path(f"google_sheets_only://{safe_name}_chair_report.md")

    output_path = agent_output_path(safe_name, "chair", f"{safe_name}_chair_report.md")
    output_path.write_text(report, encoding="utf-8")
    return output_path


def _invoke_graph_with_intake_guard(graph, initial_state: dict, *, run_intake: bool):
    """Invoke Chair graph while preserving an explicit no-intake request.

    This is intentionally defensive. Even if an older graph implementation is
    still present, CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS=1 prevents Chair from
    starting a second Data Intake pass when the caller used --no-intake or when
    pipeline_runner already completed Data Intake.
    """
    if run_intake:
        return graph.invoke(initial_state)

    previous_disable = os.environ.get("CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS")
    previous_run = os.environ.get("CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS")
    os.environ["CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS"] = "1"
    os.environ["CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS"] = "0"
    try:
        return graph.invoke(initial_state)
    finally:
        if previous_disable is None:
            os.environ.pop("CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS", None)
        else:
            os.environ["CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS"] = previous_disable
        if previous_run is None:
            os.environ.pop("CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS", None)
        else:
            os.environ["CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS"] = previous_run


def run_chair(company_dir: str, company: str, *, run_intake: bool | None = None) -> int:
    _prepare_chair_output_env()

    # Chair standalone default remains backward-compatible: run Data Intake first.
    # Explicit --no-intake must override this default completely.
    if run_intake is None:
        run_intake = _chair_env_bool("CHAIR_RUN_DATA_INTAKE_BEFORE_AGENTS", True)
    if _chair_env_bool("CHAIR_DISABLE_DATA_INTAKE_BEFORE_AGENTS", False):
        run_intake = False

    # Enable fail-open mode for First Auditor to allow validation failures to be logged
    # instead of blocking Chair execution. This ensures consistent validation across all companies.
    os.environ.setdefault("AUDITOR_FIRST_FAIL_OPEN", "true")

    """Chair 그래프를 실행합니다."""
    print(f"{'='*60}")
    print(f" Chair Agent 실행: {company} ({company_dir})")
    print(f" Data Intake 선행 실행: {'ON' if run_intake else 'OFF'}")
    print(f" 저장 방식: {'Google Sheets' if _sheets_output_requested() else 'LOCAL(data/<field>/<company>/chair)'}")
    print(f"{'='*60}")

    graph = build_chair_graph()

    initial_state = {
        "company_dir": company_dir,
        "company": company,
        "run_data_intake": run_intake,
        "opinions": [],
    }

    result = _invoke_graph_with_intake_guard(graph, initial_state, run_intake=bool(run_intake))

    report = result.get("chair_report", "")
    if not report:
        print("[오류] 최종 보고서가 생성되지 않았습니다.")
        return 1

    output_path = _save_report(company_dir, report)
    print(f"\n{'='*60}")
    print(f" 최종 보고서 저장 완료: {output_path}")
    print(f"{'='*60}")
    print(f"\n{report}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Chair Agent - 종합 투자 보고서 생성")
    parser.add_argument(
        "--company-dir",
        type=str,
        required=True,
        help="회사 폴더명 (예: hanmi, nepes, duksan)",
    )
    parser.add_argument(
        "--company",
        type=str,
        required=True,
        help="회사명 (예: 한미반도체)",
    )
    parser.add_argument(
        "--run-intake",
        action="store_true",
        help="Chair 전에 Data Intake를 먼저 실행합니다. 시간이 오래 걸릴 수 있습니다.",
    )
    parser.add_argument(
        "--no-intake",
        action="store_true",
        help="이번 Chair 실행에서만 Data Intake 선행 실행을 끕니다.",
    )
    parser.add_argument(
        "--local-output",
        action="store_true",
        help="Google Sheets를 사용하지 않고 로컬 chair 폴더에 저장합니다. 기본값입니다.",
    )
    parser.add_argument(
        "--sheets-output",
        action="store_true",
        help="기존 Google Sheets history 저장 방식을 명시적으로 사용합니다.",
    )
    args = parser.parse_args(argv)

    if getattr(args, "sheets_output", False):
        os.environ["ALPHAPROVE_CHAIR_OUTPUT_BACKEND"] = "sheets"
        os.environ["CHAIR_USE_GOOGLE_SHEETS"] = "1"
        os.environ["CHAIR_FORCE_LOCAL_OUTPUT"] = "0"
        os.environ["ALPHAPROVE_DISABLE_GOOGLE_SHEETS"] = "0"
    elif getattr(args, "local_output", False):
        os.environ["ALPHAPROVE_CHAIR_OUTPUT_BACKEND"] = "local"
        os.environ["CHAIR_FORCE_LOCAL_OUTPUT"] = "1"
        os.environ["ALPHAPROVE_DISABLE_GOOGLE_SHEETS"] = "1"

    run_intake = False if getattr(args, "no_intake", False) else (True if args.run_intake else None)
    return run_chair(args.company_dir, args.company, run_intake=run_intake)
