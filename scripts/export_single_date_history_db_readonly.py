from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]


def norm_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def safe_json_loads(value: Any) -> Any:
    if value in (None, ""):
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return {}


def to_json_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return ""
    return json.dumps(value, ensure_ascii=False)


def deep_find(obj: Any, target_keys: set[str], max_depth: int = 8) -> Any:
    if max_depth < 0:
        return None

    if isinstance(obj, dict):
        for k, v in obj.items():
            if norm_key(k) in target_keys and v not in (None, "", [], {}):
                return v

        for v in obj.values():
            found = deep_find(v, target_keys, max_depth - 1)
            if found not in (None, "", [], {}):
                return found

    elif isinstance(obj, list):
        for item in obj[:120]:
            found = deep_find(item, target_keys, max_depth - 1)
            if found not in (None, "", [], {}):
                return found

    return None


def open_db_readonly(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"DB 파일이 없습니다: {db_path}")

    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    if not table_exists(conn, table_name):
        return set()
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(r["name"]) for r in rows}


def row_get(row: sqlite3.Row | dict[str, Any], key: str, default: Any = "") -> Any:
    try:
        return row[key]
    except Exception:
        return default


def payload_from_row(row: sqlite3.Row, cols: set[str]) -> Any:
    for col in ["payload_json", "payload", "result_json", "output_json"]:
        if col in cols:
            payload = safe_json_loads(row_get(row, col, ""))
            if payload not in (None, "", [], {}):
                return payload
    return {}


def identity_from_row(row: sqlite3.Row, cols: set[str], payload: Any) -> tuple[str, str]:
    company = ""
    company_dir = ""

    if "company" in cols:
        company = str(row_get(row, "company", "") or "").strip()

    if "company_dir" in cols:
        company_dir = str(row_get(row, "company_dir", "") or "").strip()

    if not company:
        company = str(
            deep_find(payload, {"company", "company_name", "corp_name", "기업명"}) or ""
        ).strip()

    if not company_dir:
        company_dir = str(
            deep_find(payload, {"company_dir", "slug", "company_slug"}) or ""
        ).strip()

    return company, company_dir


def select_exact_date_rows(
    conn: sqlite3.Connection,
    table_name: str,
    *,
    field: str,
    as_of_date: str,
) -> tuple[list[sqlite3.Row], set[str]]:
    cols = table_columns(conn, table_name)
    if not cols:
        return [], cols

    where = []
    params: list[Any] = []

    if "field" in cols:
        where.append("field = ?")
        params.append(field)

    if "as_of_date" in cols:
        where.append("as_of_date = ?")
        params.append(as_of_date)

    where_sql = ""
    if where:
        where_sql = "WHERE " + " AND ".join(where)

    order_cols = []
    for c in ["company_dir", "agent", "output_kind", "created_at"]:
        if c in cols:
            order_cols.append(c)

    order_sql = ""
    if order_cols:
        order_sql = " ORDER BY " + ", ".join(order_cols)

    rows = conn.execute(
        f"SELECT * FROM {table_name} {where_sql}{order_sql}",
        params,
    ).fetchall()

    # as_of_date 컬럼이 없을 경우 payload 내부에서 필터링
    if "as_of_date" not in cols:
        filtered = []
        for r in rows:
            payload = payload_from_row(r, cols)
            payload_date = deep_find(payload, {"as_of_date", "date", "base_date", "기준일"})
            if str(payload_date or "").strip() == as_of_date:
                filtered.append(r)
        rows = filtered

    return rows, cols


def extract_packets(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    candidate_keys = [
        "compact_agent_packets",
        "agent_packets",
        "packets",
        "auditor_chair_packet",
        "chair_input_packets",
        "inputs",
    ]

    for key in candidate_keys:
        value = payload.get(key)

        if isinstance(value, list):
            packets = [x for x in value if isinstance(x, dict)]
            if packets:
                return packets

        if isinstance(value, dict):
            packets = []
            for agent, packet in value.items():
                if isinstance(packet, dict):
                    p = dict(packet)
                    p.setdefault("agent", agent)
                    packets.append(p)
            if packets:
                return packets

    packets = []
    for agent in AGENTS:
        value = payload.get(agent)
        if isinstance(value, dict):
            p = dict(value)
            p.setdefault("agent", agent)
            packets.append(p)

    return packets


def packet_agent(packet: dict[str, Any], fallback: str) -> str:
    return str(
        packet.get("agent")
        or packet.get("agent_name")
        or packet.get("name")
        or fallback
    ).strip()


def packet_signal_summary(packets: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    agents = []
    signals = {}
    recommendations = {}

    for i, p in enumerate(packets):
        agent = packet_agent(p, f"packet_{i + 1}")
        agents.append(agent)

        signal = deep_find(
            p,
            {"auditor_signal", "weighted_signal", "signal", "directional_signal"},
        )
        rec = deep_find(
            p,
            {"auditor_recommendation", "recommendation", "opinion", "final_recommendation"},
        )

        if signal not in (None, "", [], {}):
            signals[agent] = signal

        if rec not in (None, "", [], {}):
            recommendations[agent] = rec

    return agents, signals, recommendations


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def export_run_ids(
    rows: list[sqlite3.Row],
    cols: set[str],
    *,
    out_dir: Path,
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}

    for r in rows:
        run_id = str(row_get(r, "run_id", "") or "").strip()
        if not run_id:
            continue

        if run_id not in grouped:
            grouped[run_id] = {
                "run_id": run_id,
                "row_count": 0,
                "agents": set(),
                "output_kinds": set(),
                "first_created_at": "",
                "last_created_at": "",
            }

        g = grouped[run_id]
        g["row_count"] += 1

        if "agent" in cols:
            g["agents"].add(str(row_get(r, "agent", "") or ""))

        if "output_kind" in cols:
            g["output_kinds"].add(str(row_get(r, "output_kind", "") or ""))

        created_at = str(row_get(r, "created_at", "") or "")
        if created_at:
            if not g["first_created_at"] or created_at < g["first_created_at"]:
                g["first_created_at"] = created_at
            if not g["last_created_at"] or created_at > g["last_created_at"]:
                g["last_created_at"] = created_at

    output_rows = []
    for run_id, g in sorted(grouped.items(), key=lambda x: x[1]["last_created_at"], reverse=True):
        output_rows.append(
            {
                "run_id": run_id,
                "row_count": g["row_count"],
                "agents": ",".join(sorted(x for x in g["agents"] if x)),
                "output_kinds": ",".join(sorted(x for x in g["output_kinds"] if x)),
                "first_created_at": g["first_created_at"],
                "last_created_at": g["last_created_at"],
            }
        )

    write_csv(
        out_dir / "00_run_ids_available.csv",
        output_rows,
        [
            "run_id",
            "row_count",
            "agents",
            "output_kinds",
            "first_created_at",
            "last_created_at",
        ],
    )

    return output_rows


def export_agent_snapshots(
    rows: list[sqlite3.Row],
    cols: set[str],
    *,
    field: str,
    as_of_date: str,
    out_dir: Path,
    include_payload: bool,
) -> list[dict[str, Any]]:
    output_rows = []

    for r in rows:
        payload = payload_from_row(r, cols)
        company, company_dir = identity_from_row(r, cols, payload)

        row = {
            "as_of_date": row_get(r, "as_of_date", as_of_date) or as_of_date,
            "field": row_get(r, "field", field) or field,
            "company": company,
            "company_dir": company_dir,
            "agent": row_get(r, "agent", ""),
            "source_file": row_get(r, "source_file", ""),
            "payload_hash": row_get(r, "payload_hash", ""),
            "payload_bytes": row_get(r, "payload_bytes", ""),
            "created_at": row_get(r, "created_at", ""),
        }

        if include_payload:
            row["payload_json"] = row_get(r, "payload_json", "")

        output_rows.append(row)

    fieldnames = [
        "as_of_date",
        "field",
        "company",
        "company_dir",
        "agent",
        "source_file",
        "payload_hash",
        "payload_bytes",
        "created_at",
    ]

    if include_payload:
        fieldnames.append("payload_json")

    write_csv(out_dir / "01_agent_snapshots_summary.csv", output_rows, fieldnames)
    return output_rows


def is_auditor_packet_row(row: sqlite3.Row, cols: set[str], payload: Any) -> bool:
    agent = str(row_get(row, "agent", "") or "").strip()
    output_kind = str(row_get(row, "output_kind", "") or "").strip()

    if agent == "auditor":
        return True

    if "auditor_chair_packet" in output_kind:
        return True

    if "auditor" in output_kind and "packet" in output_kind:
        return True

    packets = extract_packets(payload)
    return len(packets) >= 3


def is_chair_result_row(row: sqlite3.Row, cols: set[str]) -> bool:
    agent = str(row_get(row, "agent", "") or "").strip()
    output_kind = str(row_get(row, "output_kind", "") or "").strip()

    if agent == "chair":
        return True

    if output_kind.startswith("chair"):
        return True

    return False


def export_auditor_packets(
    rows: list[sqlite3.Row],
    cols: set[str],
    *,
    field: str,
    as_of_date: str,
    out_dir: Path,
    include_payload: bool,
) -> list[dict[str, Any]]:
    output_rows = []

    for r in rows:
        payload = payload_from_row(r, cols)

        if not is_auditor_packet_row(r, cols, payload):
            continue

        company, company_dir = identity_from_row(r, cols, payload)
        packets = extract_packets(payload)
        agents, signals, recommendations = packet_signal_summary(packets)

        row = {
            "run_id": row_get(r, "run_id", ""),
            "as_of_date": row_get(r, "as_of_date", as_of_date) or as_of_date,
            "field": row_get(r, "field", field) or field,
            "company": company,
            "company_dir": company_dir,
            "agent": row_get(r, "agent", ""),
            "output_kind": row_get(r, "output_kind", ""),
            "packet_agent_count": len(agents),
            "packet_agents": ",".join(agents),
            "packet_signals": to_json_text(signals),
            "packet_recommendations": to_json_text(recommendations),
            "auditor_final_recommendation": deep_find(
                payload,
                {"auditor_final_recommendation", "final_recommendation", "recommendation"},
            ) or "",
            "auditor_weighted_signal": deep_find(
                payload,
                {"auditor_weighted_signal", "weighted_signal", "final_weighted_signal"},
            ) or "",
            "auditor_passed": deep_find(
                payload,
                {"auditor_passed", "passed", "raw_passed"},
            ) if deep_find(payload, {"auditor_passed", "passed", "raw_passed"}) is not None else "",
            "failed_agents": to_json_text(
                deep_find(payload, {"failed_agents", "failed_agent_names"})
            ),
            "payload_hash": row_get(r, "payload_hash", ""),
            "payload_bytes": row_get(r, "payload_bytes", ""),
            "created_at": row_get(r, "created_at", ""),
        }

        if include_payload:
            row["payload_json"] = row_get(r, "payload_json", "")

        output_rows.append(row)

    fieldnames = [
        "run_id",
        "as_of_date",
        "field",
        "company",
        "company_dir",
        "agent",
        "output_kind",
        "packet_agent_count",
        "packet_agents",
        "packet_signals",
        "packet_recommendations",
        "auditor_final_recommendation",
        "auditor_weighted_signal",
        "auditor_passed",
        "failed_agents",
        "payload_hash",
        "payload_bytes",
        "created_at",
    ]

    if include_payload:
        fieldnames.append("payload_json")

    write_csv(out_dir / "02_auditor_chair_packets_summary.csv", output_rows, fieldnames)
    return output_rows


def export_chair_results(
    rows: list[sqlite3.Row],
    cols: set[str],
    *,
    field: str,
    as_of_date: str,
    out_dir: Path,
    include_payload: bool,
) -> list[dict[str, Any]]:
    output_rows = []

    for r in rows:
        if not is_chair_result_row(r, cols):
            continue

        payload = payload_from_row(r, cols)
        company, company_dir = identity_from_row(r, cols, payload)

        row = {
            "run_id": row_get(r, "run_id", ""),
            "as_of_date": row_get(r, "as_of_date", as_of_date) or as_of_date,
            "field": row_get(r, "field", field) or field,
            "company": company,
            "company_dir": company_dir,
            "agent": row_get(r, "agent", ""),
            "output_kind": row_get(r, "output_kind", ""),
            "final_recommendation": deep_find(
                payload,
                {"final_recommendation", "recommendation", "final_opinion"},
            ) or "",
            "weighted_signal": deep_find(
                payload,
                {"weighted_signal", "chair_weighted_signal", "final_weighted_signal"},
            ) or "",
            "payload_hash": row_get(r, "payload_hash", ""),
            "payload_bytes": row_get(r, "payload_bytes", ""),
            "created_at": row_get(r, "created_at", ""),
        }

        if include_payload:
            row["payload_json"] = row_get(r, "payload_json", "")

        output_rows.append(row)

    fieldnames = [
        "run_id",
        "as_of_date",
        "field",
        "company",
        "company_dir",
        "agent",
        "output_kind",
        "final_recommendation",
        "weighted_signal",
        "payload_hash",
        "payload_bytes",
        "created_at",
    ]

    if include_payload:
        fieldnames.append("payload_json")

    write_csv(out_dir / "03_chair_results_summary.csv", output_rows, fieldnames)
    return output_rows


def latest_by_company(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest = {}

    for row in rows:
        key = row.get("company_dir") or row.get("company")
        if not key:
            continue

        created_at = str(row.get("created_at") or "")

        if key not in latest:
            latest[key] = row
            continue

        if created_at >= str(latest[key].get("created_at") or ""):
            latest[key] = row

    return latest


def build_company_dataset(
    snapshot_rows: list[dict[str, Any]],
    auditor_rows: list[dict[str, Any]],
    chair_rows: list[dict[str, Any]],
    *,
    field: str,
    as_of_date: str,
    out_dir: Path,
) -> list[dict[str, Any]]:
    snapshot_group = defaultdict(list)

    for row in snapshot_rows:
        key = row.get("company_dir") or row.get("company")
        if key:
            snapshot_group[key].append(row)

    latest_auditor = latest_by_company(auditor_rows)
    latest_chair = latest_by_company(chair_rows)

    keys = sorted(set(snapshot_group.keys()) | set(latest_auditor.keys()) | set(latest_chair.keys()))

    output_rows = []

    for key in keys:
        snapshots = snapshot_group.get(key, [])
        auditor = latest_auditor.get(key, {})
        chair = latest_chair.get(key, {})

        company = ""
        company_dir = key

        for source in [chair, auditor] + snapshots:
            if source.get("company"):
                company = source.get("company")
            if source.get("company_dir"):
                company_dir = source.get("company_dir")
            if company and company_dir:
                break

        snapshot_agents = sorted(set(str(x.get("agent") or "") for x in snapshots if x.get("agent")))

        output_rows.append(
            {
                "as_of_date": as_of_date,
                "field": field,
                "company": company,
                "company_dir": company_dir,
                "snapshot_agent_count": len(snapshot_agents),
                "snapshot_agents": ",".join(snapshot_agents),
                "latest_run_id": chair.get("run_id") or auditor.get("run_id") or "",
                "chair_final_recommendation": chair.get("final_recommendation", ""),
                "chair_weighted_signal": chair.get("weighted_signal", ""),
                "auditor_packet_agent_count": auditor.get("packet_agent_count", ""),
                "auditor_packet_agents": auditor.get("packet_agents", ""),
                "auditor_packet_signals": auditor.get("packet_signals", ""),
                "auditor_packet_recommendations": auditor.get("packet_recommendations", ""),
                "auditor_final_recommendation": auditor.get("auditor_final_recommendation", ""),
                "auditor_weighted_signal": auditor.get("auditor_weighted_signal", ""),
                "auditor_passed": auditor.get("auditor_passed", ""),
                "failed_agents": auditor.get("failed_agents", ""),
                "chair_created_at": chair.get("created_at", ""),
                "auditor_packet_created_at": auditor.get("created_at", ""),
            }
        )

    write_csv(
        out_dir / "04_single_date_company_dataset.csv",
        output_rows,
        [
            "as_of_date",
            "field",
            "company",
            "company_dir",
            "snapshot_agent_count",
            "snapshot_agents",
            "latest_run_id",
            "chair_final_recommendation",
            "chair_weighted_signal",
            "auditor_packet_agent_count",
            "auditor_packet_agents",
            "auditor_packet_signals",
            "auditor_packet_recommendations",
            "auditor_final_recommendation",
            "auditor_weighted_signal",
            "auditor_passed",
            "failed_agents",
            "chair_created_at",
            "auditor_packet_created_at",
        ],
    )

    return output_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--as-of-date", default="2025-05-01")
    parser.add_argument("--db-path", default="data/agent_history.db")
    parser.add_argument("--include-payload-json", action="store_true")
    args = parser.parse_args()

    db_path = Path(args.db_path)

    conn = open_db_readonly(db_path)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    out_dir = (
        Path("data")
        / args.field
        / "_sector_common"
        / "history_db_exports"
        / f"single_date_{args.as_of_date}_{timestamp}"
    )

    print("=" * 100)
    print("[Single Date History DB Export - READ ONLY]")
    print(f"db_path     : {db_path.resolve()}")
    print(f"field       : {args.field}")
    print(f"as_of_date  : {args.as_of_date}")
    print(f"output_dir  : {out_dir.resolve()}")
    print(f"include_payload_json: {args.include_payload_json}")
    print("=" * 100)

    snapshot_table_rows, snapshot_cols = select_exact_date_rows(
        conn,
        "agent_snapshots",
        field=args.field,
        as_of_date=args.as_of_date,
    )

    result_table_rows, result_cols = select_exact_date_rows(
        conn,
        "agent_run_results",
        field=args.field,
        as_of_date=args.as_of_date,
    )

    print(f"[DB] agent_snapshots rows   : {len(snapshot_table_rows)}")
    print(f"[DB] agent_run_results rows : {len(result_table_rows)}")

    run_id_rows = export_run_ids(result_table_rows, result_cols, out_dir=out_dir)

    snapshot_rows = export_agent_snapshots(
        snapshot_table_rows,
        snapshot_cols,
        field=args.field,
        as_of_date=args.as_of_date,
        out_dir=out_dir,
        include_payload=args.include_payload_json,
    )

    auditor_rows = export_auditor_packets(
        result_table_rows,
        result_cols,
        field=args.field,
        as_of_date=args.as_of_date,
        out_dir=out_dir,
        include_payload=args.include_payload_json,
    )

    chair_rows = export_chair_results(
        result_table_rows,
        result_cols,
        field=args.field,
        as_of_date=args.as_of_date,
        out_dir=out_dir,
        include_payload=args.include_payload_json,
    )

    company_rows = build_company_dataset(
        snapshot_rows,
        auditor_rows,
        chair_rows,
        field=args.field,
        as_of_date=args.as_of_date,
        out_dir=out_dir,
    )

    print("=" * 100)
    print("[DONE]")
    print(f"run_ids                  : {len(run_id_rows)}")
    print(f"agent_snapshots_exported : {len(snapshot_rows)}")
    print(f"auditor_packets_exported : {len(auditor_rows)}")
    print(f"chair_results_exported   : {len(chair_rows)}")
    print(f"company_dataset_rows     : {len(company_rows)}")
    print(f"output_dir               : {out_dir.resolve()}")
    print("=" * 100)

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
