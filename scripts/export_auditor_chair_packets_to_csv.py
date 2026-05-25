from __future__ import annotations

import argparse
import csv
import json
import sqlite3
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


def safe_filename(value: str) -> str:
    return (
        str(value)
        .replace("\\", "_")
        .replace("/", "_")
        .replace(":", "_")
        .replace(" ", "_")
    )


def get_table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {str(r["name"]) for r in rows}


def row_get(row: sqlite3.Row, key: str, default: Any = "") -> Any:
    try:
        return row[key]
    except Exception:
        return default


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


def resolve_run_id(
    conn: sqlite3.Connection,
    *,
    table_cols: set[str],
    field: str,
    as_of_date: str,
    run_id: str,
) -> str:
    where = ["run_id = ?"]
    params: list[Any] = [run_id]

    if "field" in table_cols:
        where.insert(0, "field = ?")
        params.insert(0, field)

    if "as_of_date" in table_cols:
        insert_at = 1 if "field" in table_cols else 0
        where.insert(insert_at, "as_of_date = ?")
        params.insert(insert_at, as_of_date)

    exact = conn.execute(
        f"""
        SELECT run_id, COUNT(*) AS cnt, MAX(created_at) AS last_created_at
        FROM agent_run_results
        WHERE {' AND '.join(where)}
        GROUP BY run_id
        """,
        params,
    ).fetchone()

    if exact:
        return exact["run_id"]

    where = ["run_id LIKE ?"]
    params = [f"%{run_id}%"]

    if "field" in table_cols:
        where.insert(0, "field = ?")
        params.insert(0, field)

    if "as_of_date" in table_cols:
        insert_at = 1 if "field" in table_cols else 0
        where.insert(insert_at, "as_of_date = ?")
        params.insert(insert_at, as_of_date)

    like_rows = conn.execute(
        f"""
        SELECT run_id, COUNT(*) AS cnt, MAX(created_at) AS last_created_at
        FROM agent_run_results
        WHERE {' AND '.join(where)}
        GROUP BY run_id
        ORDER BY MAX(created_at) DESC
        """,
        params,
    ).fetchall()

    if not like_rows:
        raise RuntimeError(
            f"run_id를 찾지 못했습니다. field={field}, as_of_date={as_of_date}, run_id={run_id}"
        )

    chosen = like_rows[0]["run_id"]

    if len(like_rows) > 1:
        print("[WARN] 입력한 run_id와 부분 일치하는 실행이 여러 개입니다. 가장 최근 run_id를 사용합니다.")
        for r in like_rows[:10]:
            print(f"  - {r['run_id']} | rows={r['cnt']} | last={r['last_created_at']}")

    print(f"[INFO] resolved run_id: {chosen}")
    return chosen


def inspect_output_kinds(
    conn: sqlite3.Connection,
    *,
    table_cols: set[str],
    field: str,
    as_of_date: str,
    run_id: str,
) -> None:
    select_cols = ["run_id"]

    for c in ["field", "as_of_date", "agent", "output_kind"]:
        if c in table_cols:
            select_cols.append(c)

    select_sql = ", ".join(select_cols)

    where = ["run_id = ?"]
    params: list[Any] = [run_id]

    if "field" in table_cols:
        where.append("field = ?")
        params.append(field)

    if "as_of_date" in table_cols:
        where.append("as_of_date = ?")
        params.append(as_of_date)

    group_cols = ", ".join(select_cols)

    rows = conn.execute(
        f"""
        SELECT
            {select_sql},
            COUNT(*) AS cnt,
            MAX(created_at) AS last_created_at
        FROM agent_run_results
        WHERE {' AND '.join(where)}
        GROUP BY {group_cols}
        ORDER BY {group_cols}
        """,
        params,
    ).fetchall()

    print("=" * 100)
    print("[해당 run_id의 저장 항목]")
    print(f"run_id={run_id}")
    print("=" * 100)

    if not rows:
        print("저장 항목이 없습니다.")
        return

    for r in rows:
        agent = row_get(r, "agent", "")
        output_kind = row_get(r, "output_kind", "")
        print(
            f"agent={agent} | "
            f"output_kind={output_kind} | "
            f"rows={r['cnt']} | "
            f"last={r['last_created_at']}"
        )


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


def get_packet_agent(packet: dict[str, Any], fallback: str = "") -> str:
    value = (
        packet.get("agent")
        or packet.get("agent_name")
        or packet.get("name")
        or fallback
    )
    return str(value or "").strip()


def packet_signals_and_recommendations(
    packets: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    signals: dict[str, Any] = {}
    recommendations: dict[str, Any] = {}

    for i, packet in enumerate(packets):
        agent = get_packet_agent(packet, fallback=f"packet_{i + 1}")

        signal = deep_find(
            packet,
            {
                "auditor_signal",
                "weighted_signal",
                "signal",
                "directional_signal",
            },
        )

        recommendation = deep_find(
            packet,
            {
                "auditor_recommendation",
                "recommendation",
                "opinion",
                "final_recommendation",
            },
        )

        if signal not in (None, "", [], {}):
            signals[agent] = signal

        if recommendation not in (None, "", [], {}):
            recommendations[agent] = recommendation

    return signals, recommendations


def get_payload_from_row(row: sqlite3.Row, table_cols: set[str]) -> Any:
    for col in ["payload_json", "payload", "result_json", "output_json"]:
        if col in table_cols:
            value = row_get(row, col, "")
            payload = safe_json_loads(value)
            if payload not in (None, "", [], {}):
                return payload
    return {}


def build_where_for_export(table_cols: set[str], field: str, as_of_date: str, run_id: str) -> tuple[str, list[Any]]:
    where = ["run_id = ?"]
    params: list[Any] = [run_id]

    if "field" in table_cols:
        where.append("field = ?")
        params.append(field)

    if "as_of_date" in table_cols:
        where.append("as_of_date = ?")
        params.append(as_of_date)

    if "agent" in table_cols and "output_kind" in table_cols:
        where.append(
            """
            (
                agent = 'auditor'
                OR output_kind = 'auditor_chair_packet_json'
                OR output_kind LIKE '%auditor%chair%packet%'
            )
            """
        )
    elif "output_kind" in table_cols:
        where.append(
            """
            (
                output_kind = 'auditor_chair_packet_json'
                OR output_kind LIKE '%auditor%chair%packet%'
            )
            """
        )
    elif "agent" in table_cols:
        where.append("agent = 'auditor'")

    return " AND ".join(where), params


def export_rows(
    conn: sqlite3.Connection,
    *,
    table_cols: set[str],
    field: str,
    as_of_date: str,
    run_id: str,
) -> list[dict[str, Any]]:
    where_sql, params = build_where_for_export(table_cols, field, as_of_date, run_id)

    rows = conn.execute(
        f"""
        SELECT *
        FROM agent_run_results
        WHERE {where_sql}
        ORDER BY created_at
        """,
        params,
    ).fetchall()

    output_rows: list[dict[str, Any]] = []

    for r in rows:
        payload = get_payload_from_row(r, table_cols)
        packets = extract_packets(payload)

        company = (
            row_get(r, "company", "")
            or deep_find(payload, {"company", "company_name", "corp_name", "기업명"})
            or ""
        )

        company_dir = (
            row_get(r, "company_dir", "")
            or deep_find(payload, {"company_dir", "slug", "company_slug"})
            or ""
        )

        row_field = row_get(r, "field", field) or field
        row_as_of_date = row_get(r, "as_of_date", as_of_date) or as_of_date

        packet_agents = [
            get_packet_agent(p, fallback=f"packet_{i + 1}")
            for i, p in enumerate(packets)
        ]

        signals, recommendations = packet_signals_and_recommendations(packets)

        auditor_final_recommendation = deep_find(
            payload,
            {
                "auditor_final_recommendation",
                "final_recommendation",
                "final_opinion",
                "auditor_recommendation",
                "recommendation",
            },
        )

        auditor_weighted_signal = deep_find(
            payload,
            {
                "auditor_weighted_signal",
                "weighted_signal",
                "final_weighted_signal",
            },
        )

        auditor_passed = deep_find(
            payload,
            {
                "auditor_passed",
                "passed",
                "raw_passed",
            },
        )

        failed_agents = deep_find(
            payload,
            {
                "failed_agents",
                "failed_agent_names",
            },
        )

        payload_hash = row_get(r, "payload_hash", "")
        payload_bytes = row_get(r, "payload_bytes", "")

        if not payload_bytes:
            raw_payload_text = row_get(r, "payload_json", "")
            payload_bytes = len(str(raw_payload_text).encode("utf-8")) if raw_payload_text else ""

        output_rows.append(
            {
                "run_id": row_get(r, "run_id", run_id) or run_id,
                "as_of_date": row_as_of_date,
                "field": row_field,
                "company": company,
                "company_dir": company_dir,
                "packet_agent_count": len(packet_agents),
                "packet_agents": ",".join(packet_agents),
                "packet_signals": to_json_text(signals),
                "packet_recommendations": to_json_text(recommendations),
                "auditor_final_recommendation": auditor_final_recommendation or "",
                "auditor_weighted_signal": auditor_weighted_signal or "",
                "auditor_passed": auditor_passed if auditor_passed is not None else "",
                "failed_agents": to_json_text(failed_agents),
                "payload_hash": payload_hash or "",
                "payload_bytes": payload_bytes or "",
                "created_at": row_get(r, "created_at", "") or "",
            }
        )

    return output_rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "run_id",
        "as_of_date",
        "field",
        "company",
        "company_dir",
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

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--db-path", default="data/agent_history.db")
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"DB 파일이 없습니다: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    table_cols = get_table_columns(conn, "agent_run_results")

    print("=" * 100)
    print("[agent_run_results schema columns]")
    print(", ".join(sorted(table_cols)))
    print("=" * 100)

    resolved_run_id = resolve_run_id(
        conn,
        table_cols=table_cols,
        field=args.field,
        as_of_date=args.as_of_date,
        run_id=args.run_id,
    )

    output_rows = export_rows(
        conn,
        table_cols=table_cols,
        field=args.field,
        as_of_date=args.as_of_date,
        run_id=resolved_run_id,
    )

    if not output_rows:
        inspect_output_kinds(
            conn,
            table_cols=table_cols,
            field=args.field,
            as_of_date=args.as_of_date,
            run_id=resolved_run_id,
        )

    output_path = (
        Path("data")
        / args.field
        / "_sector_common"
        / "history_db_exports"
        / f"auditor_chair_packets_{args.as_of_date}_{safe_filename(resolved_run_id)}.csv"
    )

    write_csv(output_path, output_rows)

    print("=" * 100)
    print("[Export auditor_chair_packet_json CSV]")
    print(f"resolved_run_id : {resolved_run_id}")
    print(f"rows            : {len(output_rows)}")
    print(f"output          : {output_path.resolve()}")
    print("=" * 100)

    if not output_rows:
        print("[WARN] CSV가 헤더만 생성되었습니다.")
        print("위의 [해당 run_id의 저장 항목]에서 agent=auditor 또는 output_kind=auditor_chair_packet_json 행이 있는지 확인해 주세요.")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
