from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from src.common.agent_history import load_agent_snapshot  # noqa: E402


DEFAULT_AGENTS = [
    "finance",
    "market",
    "issue",
    "macro",
    "tech",
    "valuation",
    "chair",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="agent_history.db에서 특정 날짜/기업의 agent snapshot을 불러옵니다."
    )
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--agents", nargs="*", default=DEFAULT_AGENTS)
    parser.add_argument(
        "--export-dir",
        default=None,
        help="지정하면 DB에서 읽은 snapshot을 JSON 파일로 다시 내보냅니다.",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("[Load Agent History Snapshot]")
    print(f"field       : {args.field}")
    print(f"company_dir : {args.company_dir}")
    print(f"company     : {args.company}")
    print(f"as_of_date  : {args.as_of_date}")
    print(f"agents      : {args.agents}")
    print("=" * 80)

    loaded = {}
    missing = []

    for agent in args.agents:
        payload = load_agent_snapshot(
            as_of_date=args.as_of_date,
            field=args.field,
            company_dir=args.company_dir,
            agent=agent,
        )

        if payload is None:
            missing.append(agent)
            print(f"[MISSING] {agent}")
            continue

        loaded[agent] = payload
        keys = list(payload.keys())[:12] if isinstance(payload, dict) else []
        print(f"[LOADED] {agent}: type={type(payload).__name__}, keys={keys}")

    print()
    print("=" * 80)
    print("[Summary]")
    print(f"loaded  : {len(loaded)}")
    print(f"missing : {len(missing)}")
    print("=" * 80)

    if args.export_dir:
        export_root = Path(args.export_dir)
        export_root.mkdir(parents=True, exist_ok=True)

        for agent, payload in loaded.items():
            out_path = export_root / f"{args.company_dir}_{args.as_of_date}_{agent}.json"
            out_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"[EXPORTED] {agent}: {out_path}")

    if missing:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())