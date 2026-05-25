from __future__ import annotations

"""
AlphaProve historical storage facade.

2026-05 local-output patch
--------------------------
Chair 실행은 기본적으로 Google Sheets에 의존하지 않고 로컬에 저장한다.
기존 Google Sheets history 흐름은 완전히 제거하지 않고, 명시적으로 opt-in 한 경우에만 사용한다.

기본값:
    - agent snapshot: data/agent_history.db(SQLite) 또는 각 agent의 로컬 JSON
    - Chair/Auditor run result: data/agent_history.db(SQLite) + chair 폴더 JSON/MD

Google Sheets를 꼭 써야 하는 경우:
    - ALPHAPROVE_HISTORY_BACKEND=sheets
    - ALPHAPROVE_CHAIR_OUTPUT_BACKEND=sheets 또는 CHAIR_USE_GOOGLE_SHEETS=1
    - ALPHAPROVE_HISTORY_SPREADSHEET_ID=<spreadsheet id>
    - ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE=<service_account.json path>

강제 로컬 모드:
    - CHAIR_FORCE_LOCAL_OUTPUT=1
    - ALPHAPROVE_DISABLE_GOOGLE_SHEETS=1
"""

import os
from pathlib import Path
from typing import Any, Optional


SHEETS_BACKEND_VALUES = {"sheets", "google_sheets", "gsheets", "google"}
SQLITE_BACKEND_VALUES = {"sqlite", "db", "local_db", "local", "file", "json"}


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _explicit_chair_sheets_requested() -> bool:
    backend = os.getenv("ALPHAPROVE_CHAIR_OUTPUT_BACKEND", "").strip().lower()
    return backend in SHEETS_BACKEND_VALUES or _env_bool("CHAIR_USE_GOOGLE_SHEETS", False)


def google_sheets_disabled() -> bool:
    """
    Chair local patch용 안전장치.

    .env에 ALPHAPROVE_HISTORY_SPREADSHEET_ID가 남아 있어도
    CHAIR_FORCE_LOCAL_OUTPUT=1 또는 ALPHAPROVE_DISABLE_GOOGLE_SHEETS=1이면
    common.agent_history는 Google Sheets backend를 타지 않는다.

    단, 사용자가 ALPHAPROVE_CHAIR_OUTPUT_BACKEND=sheets 또는
    CHAIR_USE_GOOGLE_SHEETS=1로 명시 opt-in 하면 Google Sheets를 허용한다.
    """
    if _explicit_chair_sheets_requested():
        return False
    return _env_bool("ALPHAPROVE_DISABLE_GOOGLE_SHEETS", False) or _env_bool("CHAIR_FORCE_LOCAL_OUTPUT", False)


def _backend() -> str:
    raw = os.getenv("ALPHAPROVE_HISTORY_BACKEND", "").strip().lower()

    if google_sheets_disabled():
        return "sqlite"

    if raw:
        return raw

    # 스프레드시트 ID가 있으면 기존 호환을 위해 Sheets로 간주한다.
    # 단, Chair runner는 기본적으로 CHAIR_FORCE_LOCAL_OUTPUT=1을 설정하므로
    # 일반 Chair 실행에서는 이 분기로 들어오지 않는다.
    if os.getenv("ALPHAPROVE_HISTORY_SPREADSHEET_ID") or os.getenv("GOOGLE_SHEETS_HISTORY_SPREADSHEET_ID"):
        return "sheets"

    return "sqlite"


def using_google_sheets_history() -> bool:
    return _backend() in SHEETS_BACKEND_VALUES


def history_source_label() -> str:
    if using_google_sheets_history():
        return "Google Sheets"
    return "local SQLite history: data/agent_history.db"


def init_agent_history_db(*args: Any, **kwargs: Any) -> Any:
    """호환용 이름입니다. Sheets backend에서는 워크시트와 헤더를 준비하고, 로컬 모드에서는 SQLite DB를 준비합니다."""
    if using_google_sheets_history():
        from common.google_sheets_history import ensure_history_sheets, get_spreadsheet_id

        ensure_history_sheets(kwargs.get("spreadsheet_id"))
        return get_spreadsheet_id(kwargs.get("spreadsheet_id"))

    from common.agent_history_sqlite import init_agent_history_db as _sqlite_init

    return _sqlite_init(*args, **kwargs)


def save_agent_snapshot(
    *,
    as_of_date: str,
    field: str,
    company_dir: str,
    company_name: str,
    agent: str,
    payload: dict[str, Any],
    source_file: str | None = None,
    source_mode: str = "archived_from_json",
    overwrite: bool = True,
    db_path: str | Path | None = None,
    spreadsheet_id: str | None = None,
) -> Any:
    if using_google_sheets_history():
        from common.google_sheets_history import save_agent_snapshot as _save_sheets

        return _save_sheets(
            as_of_date=as_of_date,
            field=field,
            company_dir=company_dir,
            company_name=company_name,
            agent=agent,
            payload=payload,
            source_file=source_file,
            source_mode=source_mode,
            overwrite=overwrite,
            spreadsheet_id=spreadsheet_id,
        )

    from common.agent_history_sqlite import save_agent_snapshot as _save_sqlite

    return _save_sqlite(
        as_of_date=as_of_date,
        field=field,
        company_dir=company_dir,
        company_name=company_name,
        agent=agent,
        payload=payload,
        source_file=source_file,
        source_mode=source_mode,
        overwrite=overwrite,
        db_path=db_path,
    )


def load_agent_snapshot(
    *,
    as_of_date: str,
    field: str,
    company_dir: str,
    agent: str,
    db_path: str | Path | None = None,
    spreadsheet_id: str | None = None,
) -> Optional[dict[str, Any]]:
    if using_google_sheets_history():
        from common.google_sheets_history import load_agent_snapshot as _load_sheets

        return _load_sheets(
            as_of_date=as_of_date,
            field=field,
            company_dir=company_dir,
            agent=agent,
            spreadsheet_id=spreadsheet_id,
        )

    from common.agent_history_sqlite import load_agent_snapshot as _load_sqlite

    return _load_sqlite(
        as_of_date=as_of_date,
        field=field,
        company_dir=company_dir,
        agent=agent,
        db_path=db_path,
    )


def list_agent_snapshots(
    *,
    as_of_date: str | None = None,
    field: str | None = None,
    company_dir: str | None = None,
    agent: str | None = None,
    db_path: str | Path | None = None,
    spreadsheet_id: str | None = None,
) -> list[dict[str, Any]]:
    if using_google_sheets_history():
        from common.google_sheets_history import list_agent_snapshots as _list_sheets

        return _list_sheets(
            as_of_date=as_of_date,
            field=field,
            company_dir=company_dir,
            agent=agent,
            spreadsheet_id=spreadsheet_id,
        )

    from common.agent_history_sqlite import list_agent_snapshots as _list_sqlite

    return _list_sqlite(
        as_of_date=as_of_date,
        field=field,
        company_dir=company_dir,
        agent=agent,
        db_path=db_path,
    )


def save_run_result(
    *,
    run_id: str,
    as_of_date: str,
    field: str,
    company_dir: str,
    company_name: str,
    agent: str,
    output_kind: str,
    payload: Any,
    spreadsheet_id: str | None = None,
    db_path: str | Path | None = None,
    **kwargs: Any,
) -> Any:
    """Chair/Auditor 결과 JSON·MD를 저장한다.

    - Sheets backend: 기존처럼 Google Sheets에 append
    - Local backend: data/agent_history.db의 run_results 테이블에 append
    """
    if using_google_sheets_history():
        from common.google_sheets_history import save_run_result as _save_sheets_result

        return _save_sheets_result(
            run_id=run_id,
            as_of_date=as_of_date,
            field=field,
            company_dir=company_dir,
            company_name=company_name,
            agent=agent,
            output_kind=output_kind,
            payload=payload,
            spreadsheet_id=spreadsheet_id,
            **kwargs,
        )

    from common.agent_history_sqlite import save_run_result as _save_sqlite_result

    return _save_sqlite_result(
        run_id=run_id,
        as_of_date=as_of_date,
        field=field,
        company_dir=company_dir,
        company_name=company_name,
        agent=agent,
        output_kind=output_kind,
        payload=payload,
        db_path=db_path,
        **kwargs,
    )


def list_run_results(
    *,
    run_id: str | None = None,
    as_of_date: str | None = None,
    field: str | None = None,
    company_dir: str | None = None,
    agent: str | None = None,
    output_kind: str | None = None,
    spreadsheet_id: str | None = None,
    db_path: str | Path | None = None,
    include_payload: bool = False,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    if using_google_sheets_history():
        from common.google_sheets_history import list_run_results as _list_sheets_results

        return _list_sheets_results(
            run_id=run_id,
            as_of_date=as_of_date,
            field=field,
            company_dir=company_dir,
            agent=agent,
            output_kind=output_kind,
            spreadsheet_id=spreadsheet_id,
            include_payload=include_payload,
            **kwargs,
        )

    from common.agent_history_sqlite import list_run_results as _list_sqlite_results

    return _list_sqlite_results(
        run_id=run_id,
        as_of_date=as_of_date,
        field=field,
        company_dir=company_dir,
        agent=agent,
        output_kind=output_kind,
        db_path=db_path,
        include_payload=include_payload,
        **kwargs,
    )


def load_run_result_payload(
    *,
    record_key: str,
    spreadsheet_id: str | None = None,
    db_path: str | Path | None = None,
) -> Any:
    if using_google_sheets_history():
        from common.google_sheets_history import load_run_result_payload as _load_sheets_result_payload

        return _load_sheets_result_payload(record_key=record_key, spreadsheet_id=spreadsheet_id)

    from common.agent_history_sqlite import load_run_result_payload as _load_sqlite_result_payload

    return _load_sqlite_result_payload(record_key=record_key, db_path=db_path)
