import sqlite3
from pathlib import Path

db_path = Path("data/agent_history.db")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
SELECT
    run_id,
    field,
    as_of_date,
    COUNT(*) AS saved_rows,
    MIN(created_at) AS first_saved_at,
    MAX(created_at) AS last_saved_at
FROM agent_run_results
WHERE field = ?
  AND as_of_date = ?
GROUP BY run_id, field, as_of_date
ORDER BY MAX(created_at) DESC
""", ("반도체", "2025-05-01")).fetchall()

print("=" * 80)
print("[최근 DB 저장 run_id 목록]")
print("=" * 80)

if not rows:
    print("저장된 run_id가 없습니다.")
else:
    for r in rows:
        print(
            f"run_id={r['run_id']} | "
            f"field={r['field']} | "
            f"as_of_date={r['as_of_date']} | "
            f"rows={r['saved_rows']} | "
            f"last_saved_at={r['last_saved_at']}"
        )

conn.close()
