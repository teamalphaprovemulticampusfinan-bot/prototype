from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "agent_history.db"


CREATE_AGENT_SNAPSHOTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS agent_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of_date TEXT NOT NULL,
    field TEXT NOT NULL,
    company_dir TEXT NOT NULL,
    company_name TEXT NOT NULL,
    agent TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT,
    source_file TEXT,
    source_mode TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(as_of_date, field, company_dir, agent)
);
"""


CREATE_AGENT_SNAPSHOTS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_agent_snapshots_lookup
ON agent_snapshots (as_of_date, field, company_dir, agent);
"""


CREATE_RUN_RESULTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS run_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    logical_key TEXT NOT NULL,
    record_key TEXT NOT NULL UNIQUE,
    run_id TEXT NOT NULL,
    as_of_date TEXT NOT NULL,
    field TEXT NOT NULL,
    company_dir TEXT NOT NULL,
    company_name TEXT NOT NULL,
    agent TEXT NOT NULL,
    output_kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    payload_hash TEXT,
    payload_bytes INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


CREATE_RUN_RESULTS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_run_results_lookup
ON run_results (run_id, as_of_date, field, company_dir, agent, output_kind);
"""


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_agent_history_db(db_path: str | Path | None = None) -> Path:
    path = Path(db_path) if db_path else DEFAULT_DB_PATH

    with get_connection(path) as conn:
        conn.execute(CREATE_AGENT_SNAPSHOTS_TABLE_SQL)
        conn.execute(CREATE_AGENT_SNAPSHOTS_INDEX_SQL)
        conn.execute(CREATE_RUN_RESULTS_TABLE_SQL)
        conn.execute(CREATE_RUN_RESULTS_INDEX_SQL)
        conn.commit()

    return path


def _stable_json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _payload_hash(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


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
    db_path: str | Path | None = None,
    overwrite: bool = True,
) -> None:
    """
    특정 날짜 기준의 agent JSON 결과를 SQLite DB에 저장한다.

    overwrite=True이면 같은 날짜/기업/agent가 이미 있어도 최신 payload로 갱신한다.
    overwrite=False이면 이미 있는 경우 무시한다.
    """
    init_agent_history_db(db_path)

    payload_json = _stable_json_dumps(payload)
    payload_hash = _payload_hash(payload_json)

    if overwrite:
        sql = """
        INSERT INTO agent_snapshots (
            as_of_date, field, company_dir, company_name, agent,
            payload_json, payload_hash, source_file, source_mode, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(as_of_date, field, company_dir, agent)
        DO UPDATE SET
            company_name = excluded.company_name,
            payload_json = excluded.payload_json,
            payload_hash = excluded.payload_hash,
            source_file = excluded.source_file,
            source_mode = excluded.source_mode,
            created_at = excluded.created_at;
        """
    else:
        sql = """
        INSERT OR IGNORE INTO agent_snapshots (
            as_of_date, field, company_dir, company_name, agent,
            payload_json, payload_hash, source_file, source_mode, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

    with get_connection(db_path) as conn:
        conn.execute(
            sql,
            (
                as_of_date,
                field,
                company_dir,
                company_name,
                agent,
                payload_json,
                payload_hash,
                source_file,
                source_mode,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()


def load_agent_snapshot(
    *,
    as_of_date: str,
    field: str,
    company_dir: str,
    agent: str,
    db_path: str | Path | None = None,
) -> Optional[dict[str, Any]]:
    """
    특정 날짜/기업/agent의 JSON payload를 DB에서 불러온다.
    없으면 None을 반환한다.
    """
    init_agent_history_db(db_path)

    sql = """
    SELECT payload_json
    FROM agent_snapshots
    WHERE as_of_date = ?
      AND field = ?
      AND company_dir = ?
      AND agent = ?
    LIMIT 1;
    """

    with get_connection(db_path) as conn:
        row = conn.execute(sql, (as_of_date, field, company_dir, agent)).fetchone()

    if row is None:
        return None

    return json.loads(row["payload_json"])


def list_agent_snapshots(
    *,
    as_of_date: str | None = None,
    field: str | None = None,
    company_dir: str | None = None,
    agent: str | None = None,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """
    저장된 snapshot 목록을 확인한다.
    payload_json 전체는 제외하고 메타데이터만 반환한다.
    """
    init_agent_history_db(db_path)

    conditions = []
    params: list[Any] = []

    if as_of_date:
        conditions.append("as_of_date = ?")
        params.append(as_of_date)
    if field:
        conditions.append("field = ?")
        params.append(field)
    if company_dir:
        conditions.append("company_dir = ?")
        params.append(company_dir)
    if agent:
        conditions.append("agent = ?")
        params.append(agent)

    where_sql = ""
    if conditions:
        where_sql = "WHERE " + " AND ".join(conditions)

    sql = f"""
    SELECT
        id,
        as_of_date,
        field,
        company_dir,
        company_name,
        agent,
        payload_hash,
        source_file,
        source_mode,
        created_at
    FROM agent_snapshots
    {where_sql}
    ORDER BY as_of_date, field, company_dir, agent;
    """

    with get_connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]


def _run_result_logical_key(
    *,
    run_id: str,
    as_of_date: str,
    field: str,
    company_dir: str,
    agent: str,
    output_kind: str,
) -> str:
    return "|".join(
        [
            str(run_id or "").strip(),
            str(as_of_date or "").strip(),
            str(field or "").strip(),
            str(company_dir or "").strip(),
            str(agent or "").strip(),
            str(output_kind or "").strip(),
        ]
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
    db_path: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    """
    Chair/Auditor run result를 로컬 SQLite에 append 저장한다.

    Google Sheets의 run_results 저장 인터페이스와 최대한 같은 형태를 반환한다.
    payload는 dict/list/str 모두 허용하며 JSON 문자열로 보관한다.
    """
    init_agent_history_db(db_path)

    payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    payload_hash = _payload_hash(payload_json)
    payload_bytes = len(payload_json.encode("utf-8"))
    created_at = datetime.now().isoformat(timespec="seconds")
    logical_key = _run_result_logical_key(
        run_id=run_id,
        as_of_date=as_of_date,
        field=field,
        company_dir=company_dir,
        agent=agent,
        output_kind=output_kind,
    )
    record_key = hashlib.sha256(
        f"{logical_key}|{created_at}|{payload_hash}".encode("utf-8")
    ).hexdigest()

    sql = """
    INSERT INTO run_results (
        logical_key, record_key, run_id, as_of_date, field, company_dir,
        company_name, agent, output_kind, payload_json, payload_hash,
        payload_bytes, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """

    with get_connection(db_path) as conn:
        conn.execute(
            sql,
            (
                logical_key,
                record_key,
                run_id,
                as_of_date,
                field,
                company_dir,
                company_name,
                agent,
                output_kind,
                payload_json,
                payload_hash,
                payload_bytes,
                created_at,
            ),
        )
        conn.commit()

    return {
        "logical_key": logical_key,
        "record_key": record_key,
        "run_id": run_id,
        "as_of_date": as_of_date,
        "field": field,
        "company_dir": company_dir,
        "company_name": company_name,
        "agent": agent,
        "output_kind": output_kind,
        "payload_hash": payload_hash,
        "payload_bytes": payload_bytes,
        "chunk_count": 1,
        "created_at": created_at,
        "backend": "sqlite",
    }


def list_run_results(
    *,
    run_id: str | None = None,
    as_of_date: str | None = None,
    field: str | None = None,
    company_dir: str | None = None,
    agent: str | None = None,
    output_kind: str | None = None,
    db_path: str | Path | None = None,
    include_payload: bool = False,
    **_: Any,
) -> list[dict[str, Any]]:
    """저장된 Chair/Auditor run result 목록을 로컬 SQLite에서 조회한다."""
    init_agent_history_db(db_path)

    conditions = []
    params: list[Any] = []

    if run_id:
        conditions.append("run_id = ?")
        params.append(run_id)
    if as_of_date:
        conditions.append("as_of_date = ?")
        params.append(as_of_date)
    if field:
        conditions.append("field = ?")
        params.append(field)
    if company_dir:
        conditions.append("company_dir = ?")
        params.append(company_dir)
    if agent:
        conditions.append("agent = ?")
        params.append(agent)
    if output_kind:
        conditions.append("output_kind = ?")
        params.append(output_kind)

    where_sql = ""
    if conditions:
        where_sql = "WHERE " + " AND ".join(conditions)

    payload_column = ", payload_json" if include_payload else ""
    sql = f"""
    SELECT
        logical_key,
        record_key,
        run_id,
        as_of_date,
        field,
        company_dir,
        company_name,
        agent,
        output_kind,
        payload_hash,
        payload_bytes,
        1 AS chunk_count,
        created_at
        {payload_column}
    FROM run_results
    {where_sql}
    ORDER BY as_of_date, field, company_dir, agent, output_kind, created_at;
    """

    with get_connection(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()

    results: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if include_payload:
            payload_json = item.pop("payload_json", None)
            if payload_json is not None:
                try:
                    item["payload"] = json.loads(payload_json)
                except Exception:
                    item["payload"] = payload_json
        results.append(item)

    return results


def load_run_result_payload(
    *,
    record_key: str,
    db_path: str | Path | None = None,
) -> Any:
    """record_key로 저장된 run result payload를 로컬 SQLite에서 불러온다."""
    init_agent_history_db(db_path)

    sql = """
    SELECT payload_json
    FROM run_results
    WHERE record_key = ?
    LIMIT 1;
    """

    with get_connection(db_path) as conn:
        row = conn.execute(sql, (record_key,)).fetchone()

    if row is None:
        return None

    try:
        return json.loads(row["payload_json"])
    except Exception:
        return row["payload_json"]
