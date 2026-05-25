from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


# ASCII-safe source file: Korean names are represented with Unicode escapes.
# This avoids mojibake when a zip file or text editor rewrites scripts with the wrong encoding.
DEFAULT_COMPANIES = [
    {"company_dir": "nepes", "company": "\ub124\ud328\uc2a4"},
    {"company_dir": "hanmi", "company": "\ud55c\ubbf8\ubc18\ub3c4\uccb4"},
    {"company_dir": "hansol", "company": "\ud55c\uc194\ucf00\ubbf8\uce7c"},
    {"company_dir": "duksan", "company": "\ub355\uc0b0\ud14c\ucf54\ud53c\uc544"},
    {"company_dir": "ltc", "company": "\uc5d8\ud2f0\uc528"},
]

SLUG_TO_COMPANY = {row["company_dir"]: row["company"] for row in DEFAULT_COMPANIES}

DIR_KEYS = (
    "company_dir",
    "slug",
    "ticker_slug",
    "dir",
    "folder",
    "company_folder",
    "기업폴더",
    "슬러그",
)
NAME_KEYS = (
    "company",
    "company_name",
    "name",
    "corp_name",
    "kor_name",
    "기업명",
    "회사명",
    "종목명",
)


@dataclass(frozen=True)
class CompanyTarget:
    company_dir: str
    company: str


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip().strip('"').strip("'")


def _first_nonempty(row: dict[str, object], keys: Sequence[str]) -> str:
    lower_map = {str(k).strip().lower(): k for k in row.keys()}
    for key in keys:
        if key in row and _clean(row[key]):
            return _clean(row[key])
        lk = key.lower()
        if lk in lower_map and _clean(row[lower_map[lk]]):
            return _clean(row[lower_map[lk]])
    return ""


def _open_csv(path: Path):
    encodings = ("utf-8-sig", "utf-8", "cp949", "euc-kr")
    last_error: Exception | None = None
    for enc in encodings:
        try:
            f = path.open("r", encoding=enc, newline="")
            f.read(4096)
            f.seek(0)
            return f
        except UnicodeDecodeError as exc:
            last_error = exc
    raise RuntimeError(f"Could not decode CSV file: {path}") from last_error


def load_companies_from_csv(csv_path: str | Path) -> list[CompanyTarget]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    targets: list[CompanyTarget] = []
    with _open_csv(path) as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")

        for idx, row in enumerate(reader, start=2):
            company_dir = _first_nonempty(row, DIR_KEYS)
            company = _first_nonempty(row, NAME_KEYS)

            if not company_dir and company:
                company_dir = company
            if company_dir and not company:
                company = SLUG_TO_COMPANY.get(company_dir, company_dir)

            company_dir = _clean(company_dir)
            company = _clean(company)

            if not company_dir and not company:
                continue
            if not company_dir or not company:
                raise ValueError(
                    f"CSV row {idx} is missing company_dir/company. row={row}"
                )
            targets.append(CompanyTarget(company_dir=company_dir, company=company))

    return _dedupe(targets)


def _dedupe(targets: Iterable[CompanyTarget]) -> list[CompanyTarget]:
    seen: set[tuple[str, str]] = set()
    out: list[CompanyTarget] = []
    for target in targets:
        key = (target.company_dir, target.company)
        if key in seen:
            continue
        seen.add(key)
        out.append(target)
    return out


def default_targets() -> list[CompanyTarget]:
    return [CompanyTarget(**row) for row in DEFAULT_COMPANIES]


def build_command(
    python_exe: str,
    repo_root: Path,
    agent: str,
    target: CompanyTarget,
    extra_args: Sequence[str],
) -> list[str]:
    return [
        python_exe,
        str(repo_root / "main.py"),
        agent,
        "--company-dir",
        target.company_dir,
        "--company",
        target.company,
        *extra_args,
    ]


def run_targets(
    targets: Sequence[CompanyTarget],
    agent: str,
    continue_on_error: bool,
    dry_run: bool,
    extra_args: Sequence[str],
    python_exe: str,
) -> int:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[1]

    if not targets:
        raise ValueError("No companies to run. Use --csv or --default-five.")

    failures: list[tuple[CompanyTarget, int]] = []
    print(f"[BATCH] repo={repo_root}")
    print(f"[BATCH] agent={agent}")
    print(f"[BATCH] companies={len(targets)}")

    for i, target in enumerate(targets, start=1):
        print("=" * 78)
        print(f"[{i}/{len(targets)}] {target.company} / {target.company_dir}")
        cmd = build_command(
            python_exe=python_exe,
            repo_root=repo_root,
            agent=agent,
            target=target,
            extra_args=extra_args,
        )
        printable = " ".join(f'"{x}"' if " " in x else x for x in cmd)
        print(f"[CMD] {printable}")

        if dry_run:
            continue

        completed = subprocess.run(cmd, cwd=str(repo_root))
        if completed.returncode != 0:
            print(f"[FAIL] {target.company_dir}: exit={completed.returncode}")
            failures.append((target, completed.returncode))
            if not continue_on_error:
                return completed.returncode
        else:
            print(f"[OK] {target.company_dir}")

    print("=" * 78)
    if failures:
        print(f"[DONE WITH FAILURES] {len(failures)} failed")
        for target, code in failures:
            print(f"- {target.company_dir} / {target.company}: exit={code}")
        return 1

    print("[ALL DONE] batch completed")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run AlphaProve main.py for multiple companies safely."
    )
    parser.add_argument("--agent", default="chair", help="main.py agent name, e.g. chair, pipeline, macro, tech")
    parser.add_argument("--csv", default="", help="CSV containing company_dir/company columns")
    parser.add_argument("--default-five", action="store_true", help="Run the default five semiconductor companies")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue even if one company fails")
    parser.add_argument("--dry-run", action="store_true", help="Print commands only")
    parser.add_argument("--python-exe", default=sys.executable or "python", help="Python executable to use")
    parser.add_argument("--extra-arg", action="append", default=[], help="Extra argument forwarded to main.py after company options")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    targets: list[CompanyTarget] = []
    if args.default_five:
        targets.extend(default_targets())
    if args.csv:
        targets.extend(load_companies_from_csv(args.csv))
    targets = _dedupe(targets)

    return run_targets(
        targets=targets,
        agent=args.agent,
        continue_on_error=args.continue_on_error,
        dry_run=args.dry_run,
        extra_args=args.extra_arg,
        python_exe=args.python_exe,
    )


if __name__ == "__main__":
    raise SystemExit(main())
