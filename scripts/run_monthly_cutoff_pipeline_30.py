from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evaluation.cutoff_env import build_cutoff_env, cutoff_audit_payload, month_windows


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_name(value: str) -> str:
    text = _safe_text(value)
    text = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "run"


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    for enc in ("utf-8-sig", "utf-8", "cp949"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                return [{k: _safe_text(v) for k, v in row.items()} for row in csv.DictReader(f)]
        except UnicodeDecodeError:
            continue
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: _safe_text(v) for k, v in row.items()} for row in csv.DictReader(f)]


def _truthy(value: str) -> bool:
    text = _safe_text(value).lower()
    return text not in {"0", "false", "n", "no", "x", "exclude", "제외"}


def _first(row: dict[str, str], names: list[str], default: str = "") -> str:
    for name in names:
        if _safe_text(row.get(name)):
            return _safe_text(row.get(name))
    return default


def _normalize_code(value: str) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    text = re.sub(r"\.0$", "", text)
    digits = re.sub(r"\D", "", text)
    return digits.zfill(6) if digits and len(digits) <= 6 else text


def read_universe(path: str | Path, *, field: str, limit: int | None = None) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"universe CSV not found: {p}")
    rows = _read_csv_rows(p)
    out: list[dict[str, str]] = []
    for row in rows:
        if "include_in_evaluation" in row and not _truthy(row.get("include_in_evaluation", "")):
            continue
        row_field = _first(row, ["field", "sector_field", "industry_field"], field)
        if row_field and row_field != field:
            continue
        company = _first(row, ["company_name", "company", "name", "corp_name", "종목명"])
        company_dir = _first(row, ["company_dir", "slug", "folder", "ticker_slug", "폴더명"])
        stock_code = _normalize_code(_first(row, ["stock_code", "ticker", "code", "종목코드"]))
        if not company and company_dir:
            company = company_dir
        if not company_dir and company:
            company_dir = _safe_name(company).lower()
        if not company or not company_dir:
            continue
        out.append({
            "company": company,
            "company_dir": company_dir,
            "stock_code": stock_code,
            "field": row_field or field,
        })
        if limit and len(out) >= limit:
            break
    if not out:
        raise RuntimeError(f"No targets found in universe CSV: {p}")
    return out


def _project_python(root: Path) -> str:
    for candidate in [root / ".venv" / "Scripts" / "python.exe", root / ".venv" / "bin" / "python"]:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _append_log(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    fields = list(row.keys())
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerow(row)


def _tail(text: str, n: int = 5000) -> str:
    text = text or ""
    return text[-n:] if len(text) > n else text


def _company_data_dir(root: Path, field: str, company_dir: str, company: str) -> Path:
    try:
        from common.data_paths import company_root  # type: ignore
        p = company_root(company_dir, field=field, create=False)
        if p.exists():
            return p
    except Exception:
        pass
    for p in [root / "data" / field / company, root / "data" / field / company_dir]:
        if p.exists():
            return p
    return root / "data" / field / company


def _copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    if src.exists():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))


def _snapshot(root: Path, out_root: Path, field: str, window_key: str, target: dict[str, str]) -> None:
    src = _company_data_dir(root, field, target["company_dir"], target["company"])
    dst = out_root / "real_pipeline_outputs" / window_key / target["company_dir"] / "runtime_data" / src.name
    status = {
        "company": target["company"],
        "company_dir": target["company_dir"],
        "field": field,
        "source": str(src),
        "destination": str(dst),
        "status": "MISSING_SOURCE" if not src.exists() else "OK",
        "copied_at": datetime.now().isoformat(timespec="seconds"),
    }
    if src.exists():
        _copytree(src, dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    (dst.parent / "COPY_STATUS.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def _command(root: Path, python_exe: str, target: dict[str, str], field: str, mode: str, extra_args: list[str]) -> list[str]:
    main = str(root / "main.py")
    base = [python_exe, main, mode, "--company-dir", target["company_dir"], "--company", target["company"], "--field", field]
    return base + extra_args


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run 30-company monthly pipeline with automatic no-look-ahead cutoff envs.")
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--start", default="2025-01", help="YYYY-MM or YYYY-MM-DD")
    ap.add_argument("--end", default=None, help="YYYY-MM or YYYY-MM-DD. Default: today")
    ap.add_argument("--data-start", default="2021-01-01", help="Input history start date exposed to agents")
    ap.add_argument("--universe-csv", default="data/반도체/_sector_common/universe/universe_30_semiconductor_20260514.csv")
    ap.add_argument("--run-id", default="monthly_cutoff_30")
    ap.add_argument("--run-stamp", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--timeout-sec", type=int, default=1200)
    ap.add_argument("--continue-on-error", action="store_true")
    ap.add_argument("--include-tech-cutoff", action="store_true", help="Default off. Tech/IP cutoff was intentionally disabled by project policy.")
    ap.add_argument("--mode", choices=["pipeline", "chair"], default="pipeline")
    ap.add_argument("--skip-network", action="store_true")
    ap.add_argument("--force-fetch", action="store_true")
    ap.add_argument("--intake-concurrency", default="4")
    ap.add_argument("--agent-concurrency", default="6")
    ap.add_argument("--market-llm-timeout", default="25")
    ap.add_argument("--market-gemini-retries", default="3")
    ns = ap.parse_args(argv)

    root = ROOT.resolve()
    end = ns.end or datetime.now().strftime("%Y-%m-%d")
    windows = month_windows(ns.start, end)
    targets = read_universe(root / ns.universe_csv if not Path(ns.universe_csv).is_absolute() else ns.universe_csv, field=ns.field, limit=ns.limit)
    stamp = _safe_name(ns.run_stamp or datetime.now().strftime("%Y%m%d_%H%M%S"))
    run_id = _safe_name(ns.run_id)
    out_root = root / "data" / ns.field / "_sector_common" / "history_sheets_exports" / "monthly" / "backtest" / stamp / run_id
    out_root.mkdir(parents=True, exist_ok=True)

    manifest = {
        "status": "STARTED",
        "field": ns.field,
        "start": ns.start,
        "end": end,
        "data_start": ns.data_start,
        "windows": windows,
        "targets": len(targets),
        "mode": ns.mode,
        "include_tech_cutoff": bool(ns.include_tech_cutoff),
        "output_root": str(out_root),
        "cutoff_policy": "For 2025-01 window, all non-tech dated data uses <= 2025-01-31. For 2025-02, <= 2025-02-28, etc.",
        "first_cutoff_env": cutoff_audit_payload(windows[0], start_date=ns.data_start, include_tech=ns.include_tech_cutoff) if windows else {},
        "last_cutoff_env": cutoff_audit_payload(windows[-1], start_date=ns.data_start, include_tech=ns.include_tech_cutoff) if windows else {},
    }
    (out_root / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[monthly-cutoff] output={out_root}")
    print(f"[monthly-cutoff] windows={len(windows)} targets={len(targets)} mode={ns.mode}")
    py = _project_python(root)
    log_csv = out_root / "monthly_cutoff_pipeline_run_log.csv"

    extra: list[str] = []
    if ns.mode == "pipeline":
        extra.extend(["--intake-concurrency", str(ns.intake_concurrency), "--agent-concurrency", str(ns.agent_concurrency)])
        extra.extend(["--market-llm-timeout", str(ns.market_llm_timeout), "--market-gemini-retries", str(ns.market_gemini_retries)])
        if ns.skip_network:
            extra.append("--skip-network")
        if ns.force_fetch:
            extra.append("--force-fetch")
        extra.append("--fail-open")
    else:
        # chair runner usually performs intake unless disabled by user env.
        extra.append("--local-output")

    for w_i, as_of in enumerate(windows, 1):
        window_key = as_of[:7]
        for t_i, target in enumerate(targets, 1):
            env = build_cutoff_env(as_of, start_date=ns.data_start, include_tech=ns.include_tech_cutoff, base_env=os.environ)
            env.setdefault("PYTHONUTF8", "1")
            env.setdefault("PYTHONIOENCODING", "utf-8")
            env["PYTHONPATH"] = str(root / "src") + (os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else "")
            env["ALPHAPROVE_EVAL_OUTPUT_ROOT"] = str(out_root)
            env["ALPHAPROVE_EVAL_WINDOW"] = window_key
            cmd = _command(root, py, target, ns.field, ns.mode, extra)
            started = time.time()
            status = "OK"
            rc = 0
            stdout = ""
            stderr = ""
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=str(root),
                    env=env,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    timeout=ns.timeout_sec,
                )
                rc = int(proc.returncode)
                stdout = proc.stdout or ""
                stderr = proc.stderr or ""
                if rc != 0:
                    status = "FAILED"
            except subprocess.TimeoutExpired as exc:
                status = "TIMEOUT"
                rc = 124
                stdout = exc.stdout if isinstance(exc.stdout, str) else ""
                stderr = (exc.stderr if isinstance(exc.stderr, str) else "") + f"\n[TIMEOUT] {ns.timeout_sec}s exceeded"
            elapsed = round(time.time() - started, 3)
            row = {
                "run_id": run_id,
                "as_of_date": as_of,
                "window": window_key,
                "window_index": w_i,
                "window_count": len(windows),
                "target_index": t_i,
                "target_count": len(targets),
                "company": target["company"],
                "company_dir": target["company_dir"],
                "stock_code": target.get("stock_code", ""),
                "mode": ns.mode,
                "status": status,
                "returncode": rc,
                "elapsed_sec": elapsed,
                "command": " ".join(cmd),
                "cutoff_env": json.dumps(cutoff_audit_payload(as_of, start_date=ns.data_start, include_tech=ns.include_tech_cutoff), ensure_ascii=False),
                "stdout_tail": _tail(stdout),
                "stderr_tail": _tail(stderr),
            }
            _append_log(log_csv, row)
            print(f"[monthly-cutoff] {as_of} {target['company_dir']} {status} rc={rc} elapsed={elapsed}s")
            if status == "OK":
                _snapshot(root, out_root, ns.field, window_key, target)
            elif not ns.continue_on_error:
                raise SystemExit(f"failed: {as_of} {target['company_dir']} rc={rc}\n{_tail(stderr, 1500)}")

    manifest["status"] = "DONE"
    manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
    (out_root / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_root.parent / "LATEST_MONTHLY_CUTOFF_RUN.txt").write_text(str(out_root), encoding="utf-8")
    print(f"[monthly-cutoff] DONE output={out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
