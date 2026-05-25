from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in [str(ROOT / "src_eval"), str(ROOT / "src")]:
    if p not in sys.path:
        sys.path.insert(0, p)

print("[check] root:", ROOT)
print("[check] src_eval exists:", (ROOT / "src_eval").exists())
print("[check] production src exists:", (ROOT / "src").exists())
print("[check] history backend:", os.getenv("ALPHAPROVE_HISTORY_BACKEND", ""))
print("[check] spreadsheet id set:", bool(os.getenv("ALPHAPROVE_HISTORY_SPREADSHEET_ID")))
print("[check] service account file:", os.getenv("ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE", ""))
if os.getenv("ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE"):
    print("[check] service account exists:", Path(os.getenv("ALPHAPROVE_GOOGLE_SERVICE_ACCOUNT_FILE", "")).exists())

from evaluation.objective_basis import OBJECTIVE_BASIS
print("[check] objective basis keys:", ", ".join(OBJECTIVE_BASIS.keys()))

try:
    from common.agent_history import using_google_sheets_history
    print("[check] common.agent_history import: OK")
    print("[check] using google sheets history:", using_google_sheets_history())
except Exception as exc:
    print("[check] common.agent_history import failed:", repr(exc))
    raise SystemExit(1)

print("[check] OK")
