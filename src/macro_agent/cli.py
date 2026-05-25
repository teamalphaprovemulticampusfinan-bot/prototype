from __future__ import annotations

import argparse

from .runner import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Macro Agent CLI")
    parser.add_argument("--company-dir", default=None, help="회사 slug 예: nepes")
    parser.add_argument("--company", default=None, help="표시 회사명 예: 네패스")
    parser.add_argument("--date", default="latest", help="latest 또는 YYYYMMDD")
    parser.add_argument("--no-llm", action="store_true", help="LLM 보조 분석 없이 rule-based macro만 실행")
    args = parser.parse_args(argv)

    run(
        date=args.date,
        company_dir=args.company_dir,
        company=args.company,
        use_llm=not args.no_llm,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
