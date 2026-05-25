import sqlite3
from pathlib import Path

db_path = Path("data/agent_history.db")
run_id_like = "20260518_085442"

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
SELECT
    run_id,
    agent,
    output_kind,
    COUNT(*) AS cnt,
    MIN(created_at) AS first_created_at,
    MAX(created_at) AS last_created_at
FROM agent_run_results
WHERE run_id LIKE ?
GROUP BY run_id, agent, output_kind
ORDER BY run_id, agent, output_kind
""", (f"%{run_id_like}%",)).fetchall()

print("=" * 100)
print("[run_id별 저장 output_kind 확인]")
print("=" * 100)

if not rows:
    print("해당 run_id 패턴으로 저장된 행이 없습니다.")
else:
    for r in rows:
        print(
            f"run_id={r['run_id']} | "
            f"agent={r['agent']} | "
            f"output_kind={r['output_kind']} | "
            f"rows={r['cnt']} | "
            f"last={r['last_created_at']}"
        )

conn.close()
