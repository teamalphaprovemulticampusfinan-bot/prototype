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
from evaluation.signal_df_exporter import export_signal_df

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore

NATIVE_CRASH_CODES = {3221225477, -1073741819}  # Windows 0xC0000005 access violation


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


def _checkpoint_run_log(log_csv: Path, out_root: Path) -> None:
    """Keep an always-readable Excel copy of progress, including failures."""
    if pd is None or not log_csv.exists():
        return
    try:
        df = pd.read_csv(log_csv, encoding="utf-8-sig")
        checkpoint_xlsx = out_root / "monthly_cutoff_pipeline_run_log_checkpoint.xlsx"
        df.to_excel(checkpoint_xlsx, index=False)
    except Exception as exc:
        print(f"[monthly-cutoff] WARN run-log checkpoint xlsx failed: {exc}")


def _checkpoint_signal_df(out_root: Path, *, field: str, run_id: str) -> None:
    """Overwrite a stable partial signal_df file after each successful snapshot."""
    try:
        signal_export = export_signal_df(
            out_root=out_root,
            field=field,
            run_id=run_id,
            stamp="checkpoint",
            manifest_name="signal_df_checkpoint_manifest.json",
        )
        print(
            "[monthly-cutoff] checkpoint signal_df "
            f"rows={signal_export.get('rows')} xlsx={signal_export.get('combined_xlsx')}"
        )
    except Exception as exc:
        print(f"[monthly-cutoff] WARN signal_df checkpoint failed: {exc}")


def _tail(text: str, n: int = 5000) -> str:
    text = text or ""
    return text[-n:] if len(text) > n else text


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _force_local_history_env(env: dict[str, str]) -> None:
    """Backtests should not depend on Google Sheets credentials in .env."""
    env["ALPHAPROVE_HISTORY_BACKEND"] = "local"
    env["ALPHAPROVE_DISABLE_GOOGLE_SHEETS"] = "1"
    env["ALPHAPROVE_CHAIR_OUTPUT_BACKEND"] = "local"
    env["CHAIR_FORCE_LOCAL_OUTPUT"] = "1"
    env["ALPHAPROVE_SHEETS_DB_ONLY"] = "0"
    env["ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED"] = "0"
    env.setdefault("CHAIR_FORCE_TEMPLATE_REPORT", "1")


def _stabilize_native_env(env: dict[str, str], *, conservative: bool = False) -> None:
    """Reduce native-library crash risk in long Windows batch runs."""
    env.setdefault("PYTHONFAULTHANDLER", "1")
    env.setdefault("MPLBACKEND", "Agg")
    for name in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        env.setdefault(name, "1")
    if conservative:
        env["PIPELINE_INTAKE_CONCURRENCY"] = "1"
        env["PIPELINE_AGENT_CONCURRENCY"] = "1"
        env["DATA_INTAKE_PARALLEL"] = "0"
        env["DATA_INTAKE_MAX_WORKERS"] = "1"
        env["MARKET_AGENT_SKIP_LIVE_REFRESH"] = "1"
        env["MARKET_LLM_MAX_ATTEMPTS"] = "1"
        env["MARKET_GEMINI_MAX_RETRIES"] = "0"


def _pipeline_extra(
    ns: argparse.Namespace,
    *,
    intake_concurrency: str | None = None,
    agent_concurrency: str | None = None,
    market_llm_timeout: str | None = None,
    market_gemini_retries: str | None = None,
    skip_network: bool | None = None,
) -> list[str]:
    extra: list[str] = []
    if ns.mode == "pipeline":
        extra.extend(["--intake-concurrency", str(intake_concurrency or ns.intake_concurrency)])
        extra.extend(["--agent-concurrency", str(agent_concurrency or ns.agent_concurrency)])
        extra.extend(["--market-llm-timeout", str(market_llm_timeout or ns.market_llm_timeout)])
        extra.extend(["--market-gemini-retries", str(market_gemini_retries or ns.market_gemini_retries)])
        should_skip_network = ns.skip_network if skip_network is None else skip_network
        if should_skip_network:
            extra.append("--skip-network")
        if ns.force_fetch:
            extra.append("--force-fetch")
        extra.append("--fail-open")
    else:
        # chair runner usually performs intake unless disabled by user env.
        extra.append("--local-output")
    return extra


def _run_target_attempt(
    *,
    cmd: list[str],
    env: dict[str, str],
    root: Path,
    timeout_sec: int,
) -> tuple[int, str, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout_sec,
        )
        rc = int(proc.returncode)
        return rc, proc.stdout or "", proc.stderr or "", "OK" if rc == 0 else "FAILED"
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr if isinstance(exc.stderr, str) else "") + f"\n[TIMEOUT] {timeout_sec}s exceeded"
        return 124, stdout, stderr, "TIMEOUT"


def _retry_reason(status: str, rc: int, stderr: str, stdout: str) -> str:
    combined = f"{stderr}\n{stdout}".lower()
    if rc in NATIVE_CRASH_CODES:
        return "native_access_violation"
    if "service_account.json" in combined or "google sheets" in combined:
        return "google_sheets_env"
    if status == "TIMEOUT":
        return "timeout"
    return "nonzero_exit"


def _split_company_dirs(value: str) -> set[str]:
    return {chunk.strip().lower() for chunk in str(value or "").replace(";", ",").split(",") if chunk.strip()}


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
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc", "history_runs", "*.tmp"))


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
    base = [python_exe, main, mode, "--company-dir", target["company_dir"], "--company", target["company"]]
    if mode != "chair":
        base.extend(["--field", field])
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
    ap.add_argument("--only-company-dir", default="", help="Comma-separated company_dir filter for reruns, e.g. telechips,gst")
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
    ap.add_argument("--max-retries", type=int, default=1, help="Failed company/window attempts are retried with a conservative profile.")
    ap.add_argument("--retry-timeout-sec", type=int, default=1800)
    ap.add_argument("--retry-skip-network", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--checkpoint-every", type=int, default=1, help="Refresh partial Excel/CSV checkpoints every N completed target attempts.")
    ap.add_argument("--no-checkpoint-xlsx", action="store_true", help="Disable incremental checkpoint Excel generation.")
    ns = ap.parse_args(argv)

    root = ROOT.resolve()
    end = ns.end or datetime.now().strftime("%Y-%m-%d")
    windows = month_windows(ns.start, end)
    targets = read_universe(root / ns.universe_csv if not Path(ns.universe_csv).is_absolute() else ns.universe_csv, field=ns.field, limit=ns.limit)
    only_company_dirs = _split_company_dirs(ns.only_company_dir)
    if only_company_dirs:
        targets = [t for t in targets if str(t.get("company_dir", "")).strip().lower() in only_company_dirs]
        if not targets:
            raise RuntimeError(f"No targets matched --only-company-dir={ns.only_company_dir}")
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
    completed_attempts = 0

    for w_i, as_of in enumerate(windows, 1):
        window_key = as_of[:7]
        for t_i, target in enumerate(targets, 1):
            env = build_cutoff_env(as_of, start_date=ns.data_start, include_tech=ns.include_tech_cutoff, base_env=os.environ)
            env.setdefault("PYTHONUTF8", "1")
            env.setdefault("PYTHONIOENCODING", "utf-8")
            env["PYTHONPATH"] = str(root / "src") + (os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else "")
            env["ALPHAPROVE_EVAL_OUTPUT_ROOT"] = str(out_root)
            env["ALPHAPROVE_EVAL_WINDOW"] = window_key
            _force_local_history_env(env)
            _stabilize_native_env(env)

            extra = _pipeline_extra(ns)
            cmd = _command(root, py, target, ns.field, ns.mode, extra)
            started = time.time()
            status = "OK"
            rc = 0
            stdout = ""
            stderr = ""
            attempt_rows: list[dict[str, Any]] = []

            rc, stdout, stderr, status = _run_target_attempt(cmd=cmd, env=env, root=root, timeout_sec=ns.timeout_sec)
            attempt_rows.append({
                "attempt": 1,
                "profile": "normal",
                "status": status,
                "returncode": rc,
                "reason": "" if status == "OK" else _retry_reason(status, rc, stderr, stdout),
            })

            max_retries = max(0, int(ns.max_retries))
            if status != "OK" and max_retries:
                for retry_i in range(1, max_retries + 1):
                    reason = _retry_reason(status, rc, stderr, stdout)
                    retry_env = dict(env)
                    _force_local_history_env(retry_env)
                    _stabilize_native_env(retry_env, conservative=True)
                    retry_extra = _pipeline_extra(
                        ns,
                        intake_concurrency="1",
                        agent_concurrency="1",
                        market_llm_timeout=str(max(45, _safe_int(ns.market_llm_timeout, 25))),
                        market_gemini_retries="0",
                        skip_network=bool(ns.retry_skip_network),
                    )
                    retry_cmd = _command(root, py, target, ns.field, ns.mode, retry_extra)
                    print(
                        f"[monthly-cutoff] retry {retry_i}/{max_retries} {as_of} {target['company_dir']} "
                        f"after {reason}: low-concurrency local profile"
                    )
                    rc, stdout, stderr, status = _run_target_attempt(
                        cmd=retry_cmd,
                        env=retry_env,
                        root=root,
                        timeout_sec=max(_safe_int(ns.timeout_sec, 1200), _safe_int(ns.retry_timeout_sec, 1800)),
                    )
                    cmd = retry_cmd
                    attempt_rows.append({
                        "attempt": retry_i + 1,
                        "profile": "safe_local_low_concurrency",
                        "status": status,
                        "returncode": rc,
                        "reason": "" if status == "OK" else _retry_reason(status, rc, stderr, stdout),
                    })
                    if status == "OK":
                        break
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
                "attempt_count": len(attempt_rows),
                "attempts": json.dumps(attempt_rows, ensure_ascii=False),
                "command": " ".join(cmd),
                "cutoff_env": json.dumps(cutoff_audit_payload(as_of, start_date=ns.data_start, include_tech=ns.include_tech_cutoff), ensure_ascii=False),
                "stdout_tail": _tail(stdout),
                "stderr_tail": _tail(stderr),
            }
            _append_log(log_csv, row)
            completed_attempts += 1
            print(f"[monthly-cutoff] {as_of} {target['company_dir']} {status} rc={rc} elapsed={elapsed}s")
            checkpoint_due = not ns.no_checkpoint_xlsx and completed_attempts % max(1, int(ns.checkpoint_every)) == 0
            if checkpoint_due:
                _checkpoint_run_log(log_csv, out_root)
            if status == "OK":
                _snapshot(root, out_root, ns.field, window_key, target)
                if checkpoint_due:
                    _checkpoint_signal_df(out_root, field=ns.field, run_id=run_id)
            elif not ns.continue_on_error:
                if not ns.no_checkpoint_xlsx:
                    _checkpoint_run_log(log_csv, out_root)
                raise SystemExit(f"failed: {as_of} {target['company_dir']} rc={rc}\n{_tail(stderr, 1500)}")

    try:
        signal_export = export_signal_df(out_root=out_root, field=ns.field, run_id=run_id)
        manifest["signal_df_export"] = signal_export
        print(f"[monthly-cutoff] signal_df csv={signal_export.get('combined_csv')}")
        if signal_export.get("combined_xlsx"):
            print(f"[monthly-cutoff] signal_df xlsx={signal_export.get('combined_xlsx')}")
    except Exception as exc:
        manifest["signal_df_export"] = {"status": "FAILED", "error": str(exc)}
        print(f"[monthly-cutoff] WARN signal_df export failed: {exc}")
        if not ns.continue_on_error:
            raise

    manifest["status"] = "DONE"
    manifest["finished_at"] = datetime.now().isoformat(timespec="seconds")
    (out_root / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_root.parent / "LATEST_MONTHLY_CUTOFF_RUN.txt").write_text(str(out_root), encoding="utf-8")
    print(f"[monthly-cutoff] DONE output={out_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
