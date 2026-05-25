from __future__ import annotations

import base64
import csv
import gzip
import hashlib
import json
import os
import random
import ssl
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SNAPSHOT_INDEX_SHEET = "agent_snapshots"
SNAPSHOT_CHUNKS_SHEET = "agent_snapshot_chunks"
RUN_INDEX_SHEET = "agent_run_results"
RUN_CHUNKS_SHEET = "agent_run_result_chunks"

SNAPSHOT_INDEX_HEADER = [
    "logical_key",
    "record_key",
    "as_of_date",
    "field",
    "company_dir",
    "company_name",
    "agent",
    "payload_hash",
    "payload_bytes",
    "source_file",
    "source_mode",
    "chunk_count",
    "created_at",
]

SNAPSHOT_CHUNKS_HEADER = ["record_key", "chunk_index", "payload_chunk"]

RUN_INDEX_HEADER = [
    "logical_key",
    "record_key",
    "run_id",
    "as_of_date",
    "field",
    "company_dir",
    "company_name",
    "agent",
    "output_kind",
    "payload_hash",
    "payload_bytes",
    "chunk_count",
    "created_at",
]

RUN_CHUNKS_HEADER = ["record_key", "chunk_index", "payload_chunk"]

DEFAULT_CHUNK_SIZE = 30000
CACHE_TTL_SEC = 20

_INDEX_CACHE: dict[str, tuple[float, list[dict[str, str]]]] = {}
_CHUNK_CACHE: dict[str, tuple[float, list[dict[str, str]]]] = {}
_SERVICE_CACHE: Any = None
_SHEETS_LOCK = threading.RLock()
_ENSURED_SHEETS_CACHE: set[str] = set()


class GoogleSheetsHistoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class SheetConfig:
    spreadsheet_id: str
    chunk_size: int = DEFAULT_CHUNK_SIZE


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _stable_json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _payload_hash(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _encode_payload_json(payload_json: str) -> str:
    raw = payload_json.encode("utf-8")
    compressed = gzip.compress(raw, compresslevel=6)
    return base64.b64encode(compressed).decode("ascii")


def _decode_payload_json(encoded: str) -> str:
    compressed = base64.b64decode(str(encoded).encode("ascii"))
    raw = gzip.decompress(compressed)
    return raw.decode("utf-8")


def _chunks(text: str, size: int) -> list[str]:
    if size <= 0:
        size = DEFAULT_CHUNK_SIZE
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]


def _safe_part(value: Any) -> str:
    text = str(value or "").strip()
    return (
        text.replace("|", "_")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("\t", " ")
    )


def snapshot_logical_key(*, as_of_date: str, field: str, company_dir: str, agent: str) -> str:
    return "|".join(
        [
            "snapshot",
            _safe_part(as_of_date),
            _safe_part(field),
            _safe_part(company_dir),
            _safe_part(agent),
        ]
    )


def run_result_logical_key(
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
            "result",
            _safe_part(run_id),
            _safe_part(as_of_date),
            _safe_part(field),
            _safe_part(company_dir),
            _safe_part(agent),
            _safe_part(output_kind),
        ]
    )


def make_record_key(logical_key: str, payload_hash: str, created_at: str | None = None) -> str:
    ts = (created_at or _now_iso()).replace(":", "").replace("-", "")
    return f"{logical_key}|{ts}|{payload_hash[:12]}"


def get_spreadsheet_id(spreadsheet_id: str | None = None) -> str:
    value = (
        spreadsheet_id
        or os.getenv("ALPHAPROVE_HISTORY_SPREADSHEET_ID")
        or os.getenv("GOOGLE_SHEETS_HISTORY_SPREADSHEET_ID")
        or os.getenv("GSHEETS_HISTORY_SPREADSHEET_ID")
    )
    value = str(value or "").strip()
    if not value:
        raise GoogleSheetsHistoryError(
            "Google Sheets history spreadsheet id가 없습니다.\n"
            "PowerShell 예: $env:ALPHAPROVE_HISTORY_SPREADSHEET_ID='스프레드시트_ID'"
        )
    return value


def get_chunk_size() -> int:
    raw = os.getenv("ALPHAPROVE_SHEETS_CHUNK_SIZE", str(DEFAULT_CHUNK_SIZE))
    try:
        return max(5000, min(45000, int(raw)))
    except Exception:
        return DEFAULT_CHUNK_SIZE


def get_config(spreadsheet_id: str | None = None) -> SheetConfig:
    return SheetConfig(spreadsheet_id=get_spreadsheet_id(spreadsheet_id), chunk_size=get_chunk_size())


def _load_service_account_info_from_env() -> dict[str, Any] | None:
    raw = os.getenv("ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_JSON") or os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        return None
    return json.loads(raw)


def _service_account_file_from_env() -> str | None:
    candidates = [
        os.getenv("ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE"),
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        os.getenv("GOOGLE_SHEETS_SERVICE_ACCOUNT_FILE"),
    ]
    for value in candidates:
        value = str(value or "").strip().strip('"')
        if value:
            return value
    return None


def get_sheets_service() -> Any:
    global _SERVICE_CACHE
    if _SERVICE_CACHE is not None:
        return _SERVICE_CACHE

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except Exception as exc:  # pragma: no cover - depends on user env
        raise GoogleSheetsHistoryError(
            "Google Sheets API 패키지가 설치되어 있지 않습니다.\n"
            "설치: pip install google-api-python-client google-auth google-auth-httplib2"
        ) from exc

    info = _load_service_account_info_from_env()
    if info:
        credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    else:
        file_path = _service_account_file_from_env()
        if not file_path:
            raise GoogleSheetsHistoryError(
                "Google service account 인증 정보가 없습니다.\n"
                "권장: $env:ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE='C:\\...\\service_account.json'\n"
                "또는 GOOGLE_APPLICATION_CREDENTIALS를 설정하세요."
            )
        credentials = service_account.Credentials.from_service_account_file(file_path, scopes=SCOPES)

    _SERVICE_CACHE = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    return _SERVICE_CACHE


def _is_retryable_google_error(exc: Exception) -> bool:
    text = repr(exc).lower()

    retry_terms = [
        "wrong_version_number",
        "ssl",
        "timeout",
        "timed out",
        "connection reset",
        "connection aborted",
        "temporarily unavailable",
        "rate limit",
        "429",
        "500",
        "502",
        "503",
        "504",
    ]

    if isinstance(exc, ssl.SSLError):
        return True

    return any(term in text for term in retry_terms)


def _reset_service_cache() -> None:
    global _SERVICE_CACHE
    _SERVICE_CACHE = None


def _execute_google_request(request_or_factory: Any, *, label: str = "") -> Any:
    """Execute a Google API request with retry and serialized access.

    The Chair graph can load six agent snapshots in parallel. In some Windows
    environments, concurrent httplib2/google-api-client calls intermittently
    fail with SSL WRONG_VERSION_NUMBER. This wrapper serializes Sheets calls,
    retries transient SSL/network/server errors, and rebuilds the service cache
    before the next attempt.
    """
    max_attempts = int(os.getenv("ALPHAPROVE_SHEETS_MAX_RETRIES", "5"))
    base_sleep = float(os.getenv("ALPHAPROVE_SHEETS_RETRY_BASE_SLEEP", "1.0"))

    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            with _SHEETS_LOCK:
                request = request_or_factory() if callable(request_or_factory) else request_or_factory
                return request.execute(num_retries=2)

        except Exception as exc:
            last_exc = exc

            if not _is_retryable_google_error(exc) or attempt >= max_attempts:
                raise

            _reset_service_cache()

            sleep_sec = base_sleep * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
            print(
                f"[GoogleSheets][retry] {label or 'request'} 실패 "
                f"attempt={attempt}/{max_attempts}: {exc} -> {sleep_sec:.1f}s 대기"
            )
            time.sleep(sleep_sec)

    raise last_exc or RuntimeError("Google Sheets request failed")


def _values_get(sheet_name: str, *, spreadsheet_id: str | None = None, value_range: str | None = None) -> list[list[str]]:
    cfg = get_config(spreadsheet_id)
    range_name = value_range or f"'{sheet_name}'!A:Z"

    def _make_request() -> Any:
        service = get_sheets_service()
        return (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=cfg.spreadsheet_id, range=range_name)
        )

    result = _execute_google_request(_make_request, label=f"values_get:{sheet_name}")
    return result.get("values", [])


def _values_append(sheet_name: str, values: list[list[Any]], *, spreadsheet_id: str | None = None) -> None:
    if not values:
        return

    cfg = get_config(spreadsheet_id)
    body = {"values": values}

    def _make_request() -> Any:
        service = get_sheets_service()
        return (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=cfg.spreadsheet_id,
                range=f"'{sheet_name}'!A1",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
        )

    _execute_google_request(_make_request, label=f"values_append:{sheet_name}")


def _values_update(sheet_name: str, values: list[list[Any]], *, spreadsheet_id: str | None = None) -> None:
    cfg = get_config(spreadsheet_id)
    body = {"values": values}

    def _make_request() -> Any:
        service = get_sheets_service()
        return (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=cfg.spreadsheet_id,
                range=f"'{sheet_name}'!A1",
                valueInputOption="RAW",
                body=body,
            )
        )

    _execute_google_request(_make_request, label=f"values_update:{sheet_name}")


def _sheet_metadata(spreadsheet_id: str | None = None) -> dict[str, Any]:
    cfg = get_config(spreadsheet_id)

    def _make_request() -> Any:
        service = get_sheets_service()
        return service.spreadsheets().get(spreadsheetId=cfg.spreadsheet_id)

    return _execute_google_request(_make_request, label="sheet_metadata")


def _existing_sheet_titles(spreadsheet_id: str | None = None) -> set[str]:
    meta = _sheet_metadata(spreadsheet_id)
    titles = set()
    for item in meta.get("sheets", []):
        props = item.get("properties", {})
        title = props.get("title")
        if title:
            titles.add(title)
    return titles


def ensure_history_sheets(spreadsheet_id: str | None = None) -> None:
    cfg = get_config(spreadsheet_id)
    cache_key = cfg.spreadsheet_id

    with _SHEETS_LOCK:
        if cache_key in _ENSURED_SHEETS_CACHE:
            return

        titles = _existing_sheet_titles(cfg.spreadsheet_id)

        required = {
            SNAPSHOT_INDEX_SHEET: SNAPSHOT_INDEX_HEADER,
            SNAPSHOT_CHUNKS_SHEET: SNAPSHOT_CHUNKS_HEADER,
            RUN_INDEX_SHEET: RUN_INDEX_HEADER,
            RUN_CHUNKS_SHEET: RUN_CHUNKS_HEADER,
        }

        requests = []
        for title in required:
            if title not in titles:
                requests.append({"addSheet": {"properties": {"title": title}}})

        if requests:
            def _make_request() -> Any:
                service = get_sheets_service()
                return service.spreadsheets().batchUpdate(
                    spreadsheetId=cfg.spreadsheet_id,
                    body={"requests": requests},
                )

            _execute_google_request(_make_request, label="batch_update_add_sheets")

        for title, header in required.items():
            values = _values_get(
                title,
                spreadsheet_id=cfg.spreadsheet_id,
                value_range=f"'{title}'!1:1",
            )
            if not values or values[0] != header:
                _values_update(title, [header], spreadsheet_id=cfg.spreadsheet_id)

        _ENSURED_SHEETS_CACHE.add(cache_key)


def _rows_to_dicts(values: list[list[str]], expected_header: list[str]) -> list[dict[str, str]]:
    if not values:
        return []
    header = values[0]
    if not header:
        header = expected_header
    rows = []
    for raw in values[1:]:
        row = {}
        for i, col in enumerate(header):
            row[str(col)] = str(raw[i]) if i < len(raw) else ""
        rows.append(row)
    return rows


def _get_rows_cached(sheet_name: str, header: list[str], *, spreadsheet_id: str | None = None, force: bool = False) -> list[dict[str, str]]:
    cfg = get_config(spreadsheet_id)
    cache_key = f"{cfg.spreadsheet_id}:{sheet_name}"
    cache = _INDEX_CACHE if "chunks" not in sheet_name else _CHUNK_CACHE

    with _SHEETS_LOCK:
        now = time.time()
        if not force and cache_key in cache:
            ts, rows = cache[cache_key]
            if now - ts <= CACHE_TTL_SEC:
                return rows

        values = _values_get(sheet_name, spreadsheet_id=cfg.spreadsheet_id)
        rows = _rows_to_dicts(values, header)
        cache[cache_key] = (now, rows)
        return rows


def clear_caches() -> None:
    with _SHEETS_LOCK:
        _INDEX_CACHE.clear()
        _CHUNK_CACHE.clear()


def _append_payload_record(
    *,
    index_sheet: str,
    index_header: list[str],
    chunks_sheet: str,
    logical_key: str,
    index_row: dict[str, Any],
    payload: Any,
    spreadsheet_id: str | None = None,
) -> dict[str, Any]:
    ensure_history_sheets(spreadsheet_id)
    cfg = get_config(spreadsheet_id)

    payload_json = _stable_json_dumps(payload)
    payload_hash = _payload_hash(payload_json)
    encoded = _encode_payload_json(payload_json)
    payload_chunks = _chunks(encoded, cfg.chunk_size)
    created_at = str(index_row.get("created_at") or _now_iso())
    record_key = make_record_key(logical_key, payload_hash, created_at)

    index_row = dict(index_row)
    index_row.update(
        {
            "logical_key": logical_key,
            "record_key": record_key,
            "payload_hash": payload_hash,
            "payload_bytes": str(len(payload_json.encode("utf-8"))),
            "chunk_count": str(len(payload_chunks)),
            "created_at": created_at,
        }
    )

    _values_append(index_sheet, [[index_row.get(col, "") for col in index_header]], spreadsheet_id=cfg.spreadsheet_id)
    _values_append(
        chunks_sheet,
        [[record_key, str(i), chunk] for i, chunk in enumerate(payload_chunks)],
        spreadsheet_id=cfg.spreadsheet_id,
    )
    clear_caches()

    return {
        "logical_key": logical_key,
        "record_key": record_key,
        "payload_hash": payload_hash,
        "payload_bytes": len(payload_json.encode("utf-8")),
        "chunk_count": len(payload_chunks),
        "created_at": created_at,
    }


def _latest_index_row(rows: Iterable[dict[str, str]], logical_key: str) -> dict[str, str] | None:
    matched = [r for r in rows if r.get("logical_key") == logical_key]
    if not matched:
        return None
    matched.sort(key=lambda r: (r.get("created_at") or "", r.get("record_key") or ""), reverse=True)
    return matched[0]


def _load_payload_by_record_key(
    *,
    record_key: str,
    chunks_sheet: str,
    chunks_header: list[str],
    spreadsheet_id: str | None = None,
) -> Any:
    chunk_rows = _get_rows_cached(chunks_sheet, chunks_header, spreadsheet_id=spreadsheet_id)
    selected = [r for r in chunk_rows if r.get("record_key") == record_key]
    if not selected:
        return None
    selected.sort(key=lambda r: int(r.get("chunk_index") or 0))
    encoded = "".join(r.get("payload_chunk", "") for r in selected)
    payload_json = _decode_payload_json(encoded)
    return json.loads(payload_json)


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
    spreadsheet_id: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    # overwrite는 Google Sheets append-only 저장에서 삭제를 수행하지 않는다.
    # 같은 logical_key의 최신 created_at row를 읽는 방식으로 동작한다.
    logical_key = snapshot_logical_key(as_of_date=as_of_date, field=field, company_dir=company_dir, agent=agent)
    return _append_payload_record(
        index_sheet=SNAPSHOT_INDEX_SHEET,
        index_header=SNAPSHOT_INDEX_HEADER,
        chunks_sheet=SNAPSHOT_CHUNKS_SHEET,
        logical_key=logical_key,
        index_row={
            "as_of_date": as_of_date,
            "field": field,
            "company_dir": company_dir,
            "company_name": company_name,
            "agent": agent,
            "source_file": source_file or "",
            "source_mode": source_mode,
        },
        payload=payload,
        spreadsheet_id=spreadsheet_id,
    )


def load_agent_snapshot(
    *,
    as_of_date: str,
    field: str,
    company_dir: str,
    agent: str,
    spreadsheet_id: str | None = None,
    **_: Any,
) -> Optional[dict[str, Any]]:
    ensure_history_sheets(spreadsheet_id)
    logical_key = snapshot_logical_key(as_of_date=as_of_date, field=field, company_dir=company_dir, agent=agent)
    rows = _get_rows_cached(SNAPSHOT_INDEX_SHEET, SNAPSHOT_INDEX_HEADER, spreadsheet_id=spreadsheet_id)
    latest = _latest_index_row(rows, logical_key)
    if latest is None:
        return None
    payload = _load_payload_by_record_key(
        record_key=latest.get("record_key", ""),
        chunks_sheet=SNAPSHOT_CHUNKS_SHEET,
        chunks_header=SNAPSHOT_CHUNKS_HEADER,
        spreadsheet_id=spreadsheet_id,
    )
    if isinstance(payload, dict):
        payload.setdefault("_history_store", "google_sheets")
        payload.setdefault("_history_record_key", latest.get("record_key", ""))
    return payload


def list_agent_snapshots(
    *,
    as_of_date: str | None = None,
    field: str | None = None,
    company_dir: str | None = None,
    agent: str | None = None,
    spreadsheet_id: str | None = None,
    **_: Any,
) -> list[dict[str, Any]]:
    ensure_history_sheets(spreadsheet_id)
    rows = _get_rows_cached(SNAPSHOT_INDEX_SHEET, SNAPSHOT_INDEX_HEADER, spreadsheet_id=spreadsheet_id, force=True)
    output = []
    for row in rows:
        if as_of_date and row.get("as_of_date") != as_of_date:
            continue
        if field and row.get("field") != field:
            continue
        if company_dir and row.get("company_dir") != company_dir:
            continue
        if agent and row.get("agent") != agent:
            continue
        output.append(dict(row))
    output.sort(key=lambda r: (r.get("as_of_date", ""), r.get("field", ""), r.get("company_dir", ""), r.get("agent", ""), r.get("created_at", "")))
    return output


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
    **_: Any,
) -> dict[str, Any]:
    logical_key = run_result_logical_key(
        run_id=run_id,
        as_of_date=as_of_date,
        field=field,
        company_dir=company_dir,
        agent=agent,
        output_kind=output_kind,
    )
    return _append_payload_record(
        index_sheet=RUN_INDEX_SHEET,
        index_header=RUN_INDEX_HEADER,
        chunks_sheet=RUN_CHUNKS_SHEET,
        logical_key=logical_key,
        index_row={
            "run_id": run_id,
            "as_of_date": as_of_date,
            "field": field,
            "company_dir": company_dir,
            "company_name": company_name,
            "agent": agent,
            "output_kind": output_kind,
        },
        payload=payload,
        spreadsheet_id=spreadsheet_id,
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
    include_payload: bool = False,
    **_: Any,
) -> list[dict[str, Any]]:
    ensure_history_sheets(spreadsheet_id)
    rows = _get_rows_cached(RUN_INDEX_SHEET, RUN_INDEX_HEADER, spreadsheet_id=spreadsheet_id, force=True)
    output: list[dict[str, Any]] = []
    for row in rows:
        if run_id and row.get("run_id") != run_id:
            continue
        if as_of_date and row.get("as_of_date") != as_of_date:
            continue
        if field and row.get("field") != field:
            continue
        if company_dir and row.get("company_dir") != company_dir:
            continue
        if agent and row.get("agent") != agent:
            continue
        if output_kind and row.get("output_kind") != output_kind:
            continue
        item: dict[str, Any] = dict(row)
        if include_payload:
            item["payload"] = _load_payload_by_record_key(
                record_key=row.get("record_key", ""),
                chunks_sheet=RUN_CHUNKS_SHEET,
                chunks_header=RUN_CHUNKS_HEADER,
                spreadsheet_id=spreadsheet_id,
            )
        output.append(item)
    output.sort(key=lambda r: (r.get("as_of_date", ""), r.get("company_dir", ""), r.get("agent", ""), r.get("output_kind", ""), r.get("created_at", "")))
    return output


def load_run_result_payload(
    *,
    record_key: str,
    spreadsheet_id: str | None = None,
) -> Any:
    return _load_payload_by_record_key(
        record_key=record_key,
        chunks_sheet=RUN_CHUNKS_SHEET,
        chunks_header=RUN_CHUNKS_HEADER,
        spreadsheet_id=spreadsheet_id,
    )


def export_run_results_to_csv(
    *,
    output_csv: str | Path,
    run_id: str | None = None,
    as_of_date: str | None = None,
    field: str | None = None,
    agent: str | None = None,
    output_kind: str | None = None,
    spreadsheet_id: str | None = None,
) -> Path:
    rows = list_run_results(
        run_id=run_id,
        as_of_date=as_of_date,
        field=field,
        agent=agent,
        output_kind=output_kind,
        spreadsheet_id=spreadsheet_id,
        include_payload=False,
    )
    path = Path(output_csv)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = RUN_INDEX_HEADER
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    return path


def history_source_label() -> str:
    return "Google Sheets"


def ping() -> dict[str, Any]:
    ensure_history_sheets()
    cfg = get_config()
    meta = _sheet_metadata(cfg.spreadsheet_id)
    return {
        "status": "OK",
        "backend": "google_sheets",
        "spreadsheet_id": cfg.spreadsheet_id,
        "spreadsheet_title": meta.get("properties", {}).get("title", ""),
        "sheets": sorted(_existing_sheet_titles(cfg.spreadsheet_id)),
    }