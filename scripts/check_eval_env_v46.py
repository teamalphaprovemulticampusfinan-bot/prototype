from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_EVAL = ROOT / "src_eval"
SRC = ROOT / "src"
for p in (SRC_EVAL, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from evaluation.env_loader import DEFAULT_EVAL_ENV_KEYS, env_status, load_eval_env, project_root_from


def main() -> int:
    root = project_root_from(ROOT)
    loaded = load_eval_env(root, verbose=False)
    payload = {
        "root": str(root),
        "loaded_env_files": loaded,
        "status": env_status(DEFAULT_EVAL_ENV_KEYS),
        "safe_to_write_krx_in_env": True,
        "important_note": ".env/secrets must not be committed to GitHub; process env vars override .env values.",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
