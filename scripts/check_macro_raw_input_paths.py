from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Macro Agent raw CSV input path resolution.")
    parser.add_argument("--input-dir", default="data/_global_common/macro")
    parser.add_argument("--date", default="latest")
    args = parser.parse_args()

    root = Path.cwd()
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

    from macro_agent.loader import load_macro_data, resolve_macro_input_dir

    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        input_dir = root / input_dir

    print("=" * 80)
    print("Macro raw CSV path check")
    print("=" * 80)
    print(f"requested: {input_dir}")

    actual = resolve_macro_input_dir(input_dir)
    print(f"resolved : {actual}")

    data = load_macro_data(actual, date=args.date)
    print("\n[loaded keys]")
    for key, df in data.items():
        print(f"- {key}: rows={len(df)}, cols={len(df.columns)}")

    required_any = {"ecos_일별", "ext_일별", "ecos_월별", "ext_월별"}
    missing = [k for k in required_any if k not in data]
    if missing:
        print(f"\n[WARN] 일부 표준 key가 없습니다: {missing}")
    else:
        print("\n[OK] standard macro keys loaded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
