from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


def norm_key(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def read_csv_flexible(path: Path) -> list[dict[str, str]]:
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]

    for enc in encodings:
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            continue

    raise RuntimeError(f"CSV를 읽지 못했습니다: {path}")


def get_value(row: dict[str, str], candidates: list[str]) -> str:
    mapped = {norm_key(k): v for k, v in row.items()}

    for cand in candidates:
        value = mapped.get(norm_key(cand))
        if value is not None and str(value).strip():
            return str(value).strip()

    return ""


def resolve_universe_csv(field: str, universe_csv: str | None) -> Path:
    if universe_csv:
        p = Path(universe_csv)
        if not p.exists():
            raise FileNotFoundError(f"universe CSV가 없습니다: {p}")
        return p

    base = Path("data") / field / "_sector_common" / "universe"

    preferred = base / "universe_30_semiconductor_20260514.csv"
    if preferred.exists():
        return preferred

    candidates = sorted(base.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"universe CSV를 찾지 못했습니다: {base}")

    return candidates[0]


def parse_companies(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    companies: list[dict[str, str]] = []

    for row in rows:
        company_dir = get_value(
            row,
            [
                "company_dir",
                "slug",
                "company_slug",
                "dir",
                "폴더명",
                "기업폴더",
            ],
        )

        company = get_value(
            row,
            [
                "company",
                "company_name",
                "name",
                "corp_name",
                "기업명",
                "종목명",
                "회사명",
            ],
        )

        ticker = get_value(
            row,
            [
                "ticker",
                "stock_code",
                "code",
                "종목코드",
                "단축코드",
            ],
        )

        if not company_dir or not company:
            print(f"[SKIP] company_dir/company를 찾지 못했습니다: {row}")
            continue

        companies.append(
            {
                "company_dir": company_dir,
                "company": company,
                "ticker": ticker,
            }
        )

    return companies


def company_base_dir(field: str, company: str, company_dir: str) -> Path:
    candidates = [
        Path("data") / field / company,
        Path("data") / field / company_dir,
    ]

    for p in candidates:
        if p.exists():
            return p

    return candidates[0]


def run_command(
    cmd: list[str],
    *,
    env: dict[str, str],
    cwd: Path,
    log_path: Path,
) -> tuple[int, float]:
    started = time.time()

    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    elapsed = time.time() - started

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(proc.stdout or "", encoding="utf-8")

    return proc.returncode, elapsed


def copy_existing_outputs(
    *,
    src_dir: Path,
    dst_dir: Path,
    label: str,
) -> None:
    if not src_dir.exists():
        return

    dst = dst_dir / label
    dst.mkdir(parents=True, exist_ok=True)

    patterns = [
        "*.json",
        "*.md",
        "*.txt",
    ]

    for pattern in patterns:
        for p in src_dir.glob(pattern):
            if p.is_file():
                shutil.copy2(p, dst / p.name)


def copy_after_outputs(
    *,
    field: str,
    company: str,
    company_dir: str,
    output_root: Path,
) -> dict[str, str]:
    base = company_base_dir(field, company, company_dir)

    chair_dir = base / "chair"
    auditor_dir = base / "auditor" / "first_auditor"
    tech_dir = base / "tech"

    out_dir = output_root / company_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []

    for src_dir, sub in [
        (chair_dir, "chair"),
        (auditor_dir, "auditor_first"),
        (tech_dir, "tech"),
    ]:
        if not src_dir.exists():
            continue

        dst_dir = out_dir / sub
        dst_dir.mkdir(parents=True, exist_ok=True)

        for pattern in ["*.json", "*.md"]:
            for p in src_dir.glob(pattern):
                if p.is_file():
                    target = dst_dir / p.name
                    shutil.copy2(p, target)
                    copied.append(str(target))

    return {
        "saved_dir": str(out_dir),
        "copied_count": str(len(copied)),
    }


def newest_file(path: Path, patterns: list[str]) -> Path | None:
    files: list[Path] = []

    if not path.exists():
        return None

    for pattern in patterns:
        files.extend(path.glob(pattern))

    files = [p for p in files if p.is_file()]
    if not files:
        return None

    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def read_json_safe(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}

    for enc in ["utf-8", "utf-8-sig", "cp949"]:
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue

    return {}


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
        for item in obj[:80]:
            found = deep_find(item, target_keys, max_depth - 1)
            if found not in (None, "", [], {}):
                return found

    return None


def extract_result(
    *,
    field: str,
    company: str,
    company_dir: str,
    returncode: int,
    elapsed: float,
    log_path: Path,
    saved_dir: str,
    copied_count: str,
) -> dict[str, Any]:
    base = company_base_dir(field, company, company_dir)

    chair_dir = base / "chair"
    auditor_dir = base / "auditor" / "first_auditor"

    chair_json_path = newest_file(
        chair_dir,
        [
            f"{company_dir}_chair*.json",
            "*chair*.json",
        ],
    )

    chair_report_path = newest_file(
        chair_dir,
        [
            f"{company_dir}_chair*report*.md",
            "*chair*report*.md",
            "*.md",
        ],
    )

    receipt_path = auditor_dir / "first_auditor_receipt.json"

    chair_json = read_json_safe(chair_json_path)
    receipt = read_json_safe(receipt_path)

    final_recommendation = deep_find(
        chair_json,
        {
            "final_recommendation",
            "recommendation",
            "final_opinion",
            "최종추천",
            "최종_추천",
        },
    )

    weighted_signal = deep_find(
        chair_json,
        {
            "weighted_signal",
            "chair_weighted_signal",
            "final_weighted_signal",
        },
    )

    auditor_passed = receipt.get("passed")
    failed_agents = receipt.get("failed_agents")
    min_actual_match = receipt.get("min_actual_match")
    avg_actual_match = receipt.get("avg_actual_match")
    threshold = receipt.get("threshold")

    return {
        "company": company,
        "company_dir": company_dir,
        "returncode": returncode,
        "status": "OK" if returncode == 0 else "FAILED",
        "elapsed_sec": round(elapsed, 2),
        "auditor_passed": auditor_passed,
        "failed_agents": json.dumps(failed_agents, ensure_ascii=False) if failed_agents is not None else "",
        "min_actual_match": min_actual_match,
        "avg_actual_match": avg_actual_match,
        "threshold": threshold,
        "final_recommendation": final_recommendation or "",
        "weighted_signal": weighted_signal or "",
        "chair_json_path": str(chair_json_path) if chair_json_path else "",
        "chair_report_path": str(chair_report_path) if chair_report_path else "",
        "receipt_path": str(receipt_path) if receipt_path.exists() else "",
        "saved_dir": saved_dir,
        "copied_count": copied_count,
        "log_path": str(log_path),
    }


def write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "company",
        "company_dir",
        "returncode",
        "status",
        "elapsed_sec",
        "auditor_passed",
        "failed_agents",
        "min_actual_match",
        "avg_actual_match",
        "threshold",
        "final_recommendation",
        "weighted_signal",
        "chair_json_path",
        "chair_report_path",
        "receipt_path",
        "saved_dir",
        "copied_count",
        "log_path",
    ]

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--field", default="반도체")
    parser.add_argument("--universe-csv", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--run-value-evidence", action="store_true")
    parser.add_argument("--with-intake", action="store_true")
    parser.add_argument("--fail-open", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    root = Path.cwd()
    universe_csv = resolve_universe_csv(args.field, args.universe_csv or None)
    rows = read_csv_flexible(universe_csv)
    companies = parse_companies(rows)

    if args.start_index > 1:
        companies = companies[args.start_index - 1 :]

    if args.limit > 0:
        companies = companies[: args.limit]

    if not companies:
        raise RuntimeError("실행 대상 기업이 없습니다.")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_root = (
        Path("data")
        / args.field
        / "_sector_common"
        / "chair_rerun_outputs"
        / run_id
    )

    backup_root = (
        Path("data")
        / args.field
        / "_sector_common"
        / "chair_rerun_backups"
        / run_id
    )

    log_dir = (
        Path("data")
        / args.field
        / "_sector_common"
        / "chair_rerun_logs"
        / run_id
    )

    summary_csv = (
        Path("data")
        / args.field
        / "_sector_common"
        / "chair_rerun_results"
        / f"chair_rerun_summary_{run_id}.csv"
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    # 핵심: agent_history replay를 강제로 끕니다.
    env["ALPHAPROVE_USE_AGENT_HISTORY"] = "0"
    env.pop("ALPHAPROVE_AS_OF_DATE", None)

    if args.fail_open:
        env["AUDITOR_FIRST_FAIL_OPEN"] = "1"
    else:
        env.pop("AUDITOR_FIRST_FAIL_OPEN", None)

    print("=" * 80)
    print("[Chair Re-run All Companies]")
    print(f"field              : {args.field}")
    print(f"universe_csv       : {universe_csv}")
    print(f"companies          : {len(companies)}")
    print(f"run_value_evidence : {args.run_value_evidence}")
    print(f"with_intake        : {args.with_intake}")
    print(f"fail_open          : {args.fail_open}")
    print(f"output_root        : {output_root}")
    print(f"backup_root        : {backup_root}")
    print(f"log_dir            : {log_dir}")
    print(f"summary_csv        : {summary_csv}")
    print("=" * 80)

    results: list[dict[str, Any]] = []

    for idx, item in enumerate(companies, start=1):
        company_dir = item["company_dir"]
        company = item["company"]

        print()
        print("=" * 80)
        print(f"[{idx}/{len(companies)}] {company} / {company_dir}")
        print("=" * 80)

        base = company_base_dir(args.field, company, company_dir)
        chair_dir = base / "chair"

        if args.skip_existing:
            existing = newest_file(chair_dir, [f"{company_dir}_chair*.json", "*chair*.json"])
            if existing:
                print(f"[SKIP] existing chair json: {existing}")
                copied = copy_after_outputs(
                    field=args.field,
                    company=company,
                    company_dir=company_dir,
                    output_root=output_root,
                )
                result = extract_result(
                    field=args.field,
                    company=company,
                    company_dir=company_dir,
                    returncode=0,
                    elapsed=0.0,
                    log_path=Path(""),
                    saved_dir=copied["saved_dir"],
                    copied_count=copied["copied_count"],
                )
                results.append(result)
                write_summary_csv(summary_csv, results)
                continue

        # 기존 Chair 산출물 백업
        copy_existing_outputs(
            src_dir=chair_dir,
            dst_dir=backup_root / company_dir,
            label="before_chair_rerun",
        )

        if args.run_value_evidence:
            ve_log = log_dir / f"{idx:02d}_{company_dir}_01_value_evidence.log"
            ve_cmd = [
                sys.executable,
                "scripts/run_tech_intake_value_evidence.py",
                "--field",
                args.field,
                "--company-dir",
                company_dir,
                "--company",
                company,
            ]

            code, elapsed = run_command(
                ve_cmd,
                env=env,
                cwd=root,
                log_path=ve_log,
            )

            print(f"[Value Evidence] returncode={code}, elapsed={elapsed:.1f}s, log={ve_log}")

            if code != 0:
                copied = copy_after_outputs(
                    field=args.field,
                    company=company,
                    company_dir=company_dir,
                    output_root=output_root,
                )
                result = extract_result(
                    field=args.field,
                    company=company,
                    company_dir=company_dir,
                    returncode=code,
                    elapsed=elapsed,
                    log_path=ve_log,
                    saved_dir=copied["saved_dir"],
                    copied_count=copied["copied_count"],
                )
                results.append(result)
                write_summary_csv(summary_csv, results)
                continue

        chair_log = log_dir / f"{idx:02d}_{company_dir}_02_chair.log"
        chair_cmd = [
            sys.executable,
            "main.py",
            "chair",
            "--company-dir",
            company_dir,
            "--company",
            company,
        ]

        if not args.with_intake:
            chair_cmd.append("--no-intake")

        code, elapsed = run_command(
            chair_cmd,
            env=env,
            cwd=root,
            log_path=chair_log,
        )

        print(f"[Chair] returncode={code}, elapsed={elapsed:.1f}s, log={chair_log}")

        copied = copy_after_outputs(
            field=args.field,
            company=company,
            company_dir=company_dir,
            output_root=output_root,
        )

        result = extract_result(
            field=args.field,
            company=company,
            company_dir=company_dir,
            returncode=code,
            elapsed=elapsed,
            log_path=chair_log,
            saved_dir=copied["saved_dir"],
            copied_count=copied["copied_count"],
        )

        results.append(result)
        write_summary_csv(summary_csv, results)

        print(
            f"[Result] status={result['status']} "
            f"auditor_passed={result['auditor_passed']} "
            f"recommendation={result['final_recommendation']} "
            f"saved={result['saved_dir']}"
        )

    ok = sum(1 for r in results if r["status"] == "OK")
    fail = len(results) - ok

    print()
    print("=" * 80)
    print("[DONE]")
    print(f"OK={ok}, FAILED={fail}, TOTAL={len(results)}")
    print(f"summary_csv : {summary_csv}")
    print(f"output_root : {output_root}")
    print(f"backup_root : {backup_root}")
    print(f"log_dir     : {log_dir}")
    print("=" * 80)

    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
