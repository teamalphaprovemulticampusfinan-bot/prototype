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
from evaluation.cutoff_data_auditor import write_cutoff_audit
from evaluation.signal_df_exporter import export_signal_df

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore

NATIVE_CRASH_CODES = {3221225477, -1073741819}  # Windows 0xC0000005 access violation
AGENTS = ["finance", "market", "tech", "valuation", "issue", "macro"]
AGENT_OUTPUT_PATTERNS = {
    "finance": ["finance/*_finance_agent_packet.json", "finance/*_finance.json"],
    "market": ["market/*_market_agent_packet.json", "market/*_market.json"],
    "tech": ["tech/*_tech_agent_packet.json", "tech/*_tech.json", "tech/tech.json"],
    "valuation": ["valuation/*_valuation_agent_packet.json", "valuation/*_valuation_metrics.json", "valuation/*_dashboard_payload.json"],
    "issue": ["issue/*_issue_agent_packet.json", "issue/*_issue.json"],
    "macro": ["macro/*_macro_agent_packet.json", "macro/*_macro.json", "macro/macro_signal_*.json"],
}


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
    """Overwrite stable partial signal_df files after each successful company/month snapshot.

    This intentionally runs during the loop, not only at the very end, so a long
    30-company monthly backtest leaves an immediately-openable Excel checkpoint
    after every completed target.
    """
    try:
        signal_export = export_signal_df(
            out_root=out_root,
            field=field,
            run_id=run_id,
            stamp="checkpoint",
            manifest_name="signal_df_checkpoint_manifest.json",
        )
        combined_xlsx = Path(str(signal_export.get("combined_xlsx") or ""))
        combined_csv = Path(str(signal_export.get("combined_csv") or ""))
        latest_xlsx = out_root / "signal_df_latest_checkpoint.xlsx"
        latest_csv = out_root / "signal_df_latest_checkpoint.csv"
        if combined_xlsx.exists():
            shutil.copy2(combined_xlsx, latest_xlsx)
        if combined_csv.exists():
            shutil.copy2(combined_csv, latest_csv)
        print(
            "[monthly-cutoff] checkpoint signal_df "
            f"rows={signal_export.get('rows')} xlsx={combined_xlsx} latest={latest_xlsx}"
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


def _as_number(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _safe_text(value).replace(",", "")
    if not text:
        return None
    upper = text.upper()
    if upper in {"BUY", "매수"}:
        return 1.0
    if upper in {"SELL", "매도"}:
        return -1.0
    if upper in {"HOLD", "보유", "중립"}:
        return 0.0
    m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not m:
        return None
    try:
        num = float(m.group(0))
    except Exception:
        return None
    if abs(num) > 1.5 and abs(num) <= 100:
        if 0 <= num <= 100:
            return round((num - 50.0) / 50.0, 6)
        return round(num / 100.0, 6)
    return num


def _recommendation(value: Any) -> str:
    text = _safe_text(value)
    upper = text.upper()
    if text in {"매수", "보유", "매도"}:
        return text
    if upper == "BUY":
        return "매수"
    if upper == "SELL":
        return "매도"
    if upper == "HOLD":
        return "보유"
    return text


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _latest_file(root: Path, patterns: list[str]) -> Path | None:
    found: list[Path] = []
    for pattern in patterns:
        found.extend([p for p in root.glob(pattern) if p.is_file()])
    return max(found, key=lambda p: p.stat().st_mtime) if found else None


def _recursive_first(payload: Any, keys: list[str]) -> Any:
    keyset = set(keys)
    if isinstance(payload, dict):
        for key in keyset:
            value = payload.get(key)
            if value not in (None, "", [], {}):
                return value
        for value in payload.values():
            hit = _recursive_first(value, keys)
            if hit not in (None, "", [], {}):
                return hit
    elif isinstance(payload, list):
        for value in payload[:80]:
            hit = _recursive_first(value, keys)
            if hit not in (None, "", [], {}):
                return hit
    return None


def _extract_agent_decision(payload: dict[str, Any], agent: str) -> tuple[float | None, str]:
    rec = _recommendation(
        payload.get("auditor_recommendation")
        or payload.get("final_recommendation")
        or payload.get("recommendation")
        or payload.get("opinion")
        or payload.get("decision")
        or payload.get("label")
    )
    signal_keys = ["auditor_signal", "signal", "final_signal"]
    if agent == "tech":
        signal_keys.append("tech_signal")
    elif agent == "market":
        signal_keys.append("market_signal")
    signal = None
    for key in signal_keys:
        signal = _as_number(payload.get(key))
        if signal is not None:
            break
    if signal is None:
        signal = _as_number(rec)
    if not rec:
        rec = "보유"
    if signal is None:
        signal = 0.0
    return signal, rec


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
        extra.append("--no-intake")
    return extra


def _run_target_attempt(
    *,
    cmd: list[str],
    env: dict[str, str],
    root: Path,
    timeout_sec: int,
) -> tuple[int, str, str, str]:
    # Monthly backtests should finish one company/month and write checkpoints.
    # A too-small CLI timeout (e.g. 590s) killed otherwise-valid runs, so keep
    # a conservative minimum unless MONTHLY_CUTOFF_MIN_TIMEOUT_SEC is overridden.
    try:
        min_timeout = int(os.getenv("MONTHLY_CUTOFF_MIN_TIMEOUT_SEC", "1800") or "1800")
    except Exception:
        min_timeout = 1800
    timeout_sec = max(1, int(timeout_sec), min_timeout)
    proc: subprocess.Popen[str] | None = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(root),
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(timeout=timeout_sec)
        rc = int(proc.returncode)
        return rc, stdout or "", stderr or "", "OK" if rc == 0 else "FAILED"
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        if proc is not None:
            _terminate_process_tree(proc.pid)
            try:
                more_stdout, more_stderr = proc.communicate(timeout=10)
                stdout += more_stdout or ""
                stderr += more_stderr or ""
            except Exception:
                pass
        stderr = (stderr or "") + f"\n[TIMEOUT] {timeout_sec}s exceeded; process tree terminated"
        return 124, stdout, stderr, "TIMEOUT"


def _terminate_process_tree(pid: int) -> None:
    """Best-effort kill of a timed-out subprocess tree."""
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
            return
        except Exception:
            pass
    try:
        subprocess.run(
            ["kill", "-TERM", str(pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except Exception:
        pass


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


def _existing_agent_outputs(root: Path, field: str, target: dict[str, str]) -> tuple[bool, dict[str, str]]:
    company_root = _company_data_dir(root, field, target["company_dir"], target["company"])
    found: dict[str, str] = {}
    for agent in AGENTS:
        path = _latest_file(company_root, AGENT_OUTPUT_PATTERNS[agent])
        if path is None:
            return False, found
        found[agent] = str(path)
    return True, found


def _outputs_recent(output_files: dict[str, str], started: float, *, tolerance_sec: int = 60) -> bool:
    if not output_files:
        return False
    cutoff = started - max(0, tolerance_sec)
    for raw in output_files.values():
        try:
            if Path(raw).stat().st_mtime < cutoff:
                return False
        except Exception:
            return False
    return True


def _copytree(src: Path, dst: Path) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    if dst.exists():
        shutil.rmtree(dst)
    if not src.exists():
        return warnings

    ignore = shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc", "history_runs", "*.tmp")
    for cur, dirnames, filenames in os.walk(src):
        cur_path = Path(cur)
        ignored = set(ignore(str(cur_path), list(dirnames) + list(filenames)))
        dirnames[:] = [name for name in dirnames if name not in ignored]
        rel = cur_path.relative_to(src)
        dst_dir = dst / rel
        dst_dir.mkdir(parents=True, exist_ok=True)
        for name in filenames:
            if name in ignored:
                continue
            src_file = cur_path / name
            dst_file = dst_dir / name
            try:
                shutil.copy2(src_file, dst_file)
            except FileNotFoundError as exc:
                warnings.append({"source": str(src_file), "destination": str(dst_file), "error": str(exc)})
            except OSError as exc:
                warnings.append({"source": str(src_file), "destination": str(dst_file), "error": str(exc)})
    return warnings


def _snapshot(root: Path, out_root: Path, field: str, window_key: str, target: dict[str, str]) -> None:
    src = _company_data_dir(root, field, target["company_dir"], target["company"])
    dst = out_root / "real_pipeline_outputs" / window_key / target["company_dir"] / "runtime_data" / src.name
    copy_warnings: list[dict[str, str]] = []
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
        copy_warnings = _copytree(src, dst)
        if copy_warnings:
            status["status"] = "SNAPSHOT_PARTIAL"
            status["copy_warning_count"] = len(copy_warnings)
            status["copy_warnings"] = copy_warnings[:20]
    dst.parent.mkdir(parents=True, exist_ok=True)
    (dst.parent / "COPY_STATUS.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def _snapshot_runtime_path(out_root: Path, window_key: str, target: dict[str, str]) -> Path | None:
    status_path = _snapshot_status_path(out_root, window_key, target)
    if not status_path.exists():
        return None
    payload = _load_json(status_path)
    destination = Path(_safe_text(payload.get("destination")))
    return destination if destination.exists() else None


def _write_synthetic_chair_packet(
    *,
    runtime: Path,
    target: dict[str, str],
    field: str,
    as_of_date: str,
) -> Path:
    decisions: dict[str, dict[str, Any]] = {}
    weights: dict[str, float] = {}
    available: list[str] = []

    for agent in AGENTS:
        payload = _load_json(_latest_file(runtime, AGENT_OUTPUT_PATTERNS[agent]))
        signal, rec = _extract_agent_decision(payload, agent)
        if signal is None and not rec:
            continue
        available.append(agent)
        decisions[agent] = {
            "signal": signal if signal is not None else 0.0,
            "recommendation": rec or "보유",
            "source": "synthetic_chair_from_existing_agent_outputs",
        }

    if not available:
        raise RuntimeError(f"no agent outputs available for synthetic chair: {runtime}")

    uniform = 1.0 / len(available)
    weighted_signal = 0.0
    for agent in available:
        weights[agent] = uniform
        signal = _as_number(decisions[agent].get("signal")) or 0.0
        decisions[agent]["weighted_contribution"] = round(signal * uniform, 6)
        weighted_signal += signal * uniform

    if weighted_signal > 0.15:
        final_rec = "매수"
    elif weighted_signal < -0.15:
        final_rec = "매도"
    else:
        final_rec = "보유"

    packet = {
        "agent": "chair",
        "company": target["company"],
        "company_dir": target["company_dir"],
        "field": field,
        "as_of_date": as_of_date,
        "opinion": final_rec,
        "recommendation": final_rec,
        "synthetic_chair_packet": True,
        "synthetic_reason": "Created by monthly cutoff runner from existing specialist agent outputs to avoid rerunning a timed-out target.",
        "auditor_summary": {
            "quantitative_decision": {
                "weighted_signal": round(weighted_signal, 6),
                "final_recommendation": final_rec,
                "base_recommendation": final_rec,
                "weights": weights,
                "agent_decisions": decisions,
            }
        },
    }
    chair_dir = runtime / "chair"
    chair_dir.mkdir(parents=True, exist_ok=True)
    out = chair_dir / f"{target['company_dir']}_chair_agent_packet.json"
    out.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    (chair_dir / f"{target['company_dir']}_chair.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _snapshot_status_path(out_root: Path, window_key: str, target: dict[str, str]) -> Path:
    return out_root / "real_pipeline_outputs" / window_key / target["company_dir"] / "runtime_data" / "COPY_STATUS.json"


def _snapshot_complete(out_root: Path, window_key: str, target: dict[str, str]) -> bool:
    status_path = _snapshot_status_path(out_root, window_key, target)
    if not status_path.exists():
        return False
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    status = _safe_text(payload.get("status"))
    destination = Path(_safe_text(payload.get("destination")))
    return status in {"OK", "SNAPSHOT_PARTIAL"} and destination.exists()


def _load_completed_log_rows(log_csv: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not log_csv.exists():
        return {}
    with log_csv.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    completed: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if _safe_text(row.get("status")) != "OK":
            continue
        as_of = _safe_text(row.get("as_of_date"))
        company_dir = _safe_text(row.get("company_dir"))
        if as_of and company_dir:
            completed[(as_of, company_dir)] = row
    return completed


def _attempt_rows_had_timeout(attempt_rows: list[dict[str, Any]]) -> bool:
    for attempt in attempt_rows:
        status = _safe_text(attempt.get("status")).upper()
        reason = _safe_text(attempt.get("reason")).lower()
        rc = _safe_int(attempt.get("returncode"), 0)
        if status == "TIMEOUT" or reason in {"timeout", "native_access_violation"} or rc in NATIVE_CRASH_CODES:
            return True
    return False


def _logged_rows_had_timeout(rows: list[dict[str, str]]) -> bool:
    for row in rows:
        raw = _safe_text(row.get("attempts"))
        if not raw:
            continue
        try:
            attempts = json.loads(raw)
        except Exception:
            continue
        if isinstance(attempts, list) and _attempt_rows_had_timeout([a for a in attempts if isinstance(a, dict)]):
            return True
    return False


def _logged_rows_hit_slow_threshold(rows: list[dict[str, str]], timeout_sec: int, ratio: float) -> bool:
    for row in rows:
        try:
            elapsed = float(_safe_text(row.get("elapsed_sec")) or "0")
        except Exception:
            continue
        if _slow_threshold_hit(elapsed, timeout_sec, ratio):
            return True
    return False


def _slow_threshold_hit(elapsed_sec: float, timeout_sec: int, ratio: float) -> bool:
    if timeout_sec <= 0 or ratio <= 0:
        return False
    return elapsed_sec >= float(timeout_sec) * ratio


def _safe_pipeline_profile(
    ns: argparse.Namespace,
    env: dict[str, str],
) -> tuple[dict[str, str], list[str], int]:
    safe_env = dict(env)
    _force_local_history_env(safe_env)
    _stabilize_native_env(safe_env, conservative=True)
    safe_extra = _pipeline_extra(
        ns,
        intake_concurrency="1",
        agent_concurrency="1",
        market_llm_timeout=str(max(45, _safe_int(ns.market_llm_timeout, 25))),
        market_gemini_retries="0",
        skip_network=bool(ns.retry_skip_network),
    )
    safe_timeout = max(1, _safe_int(ns.retry_timeout_sec, _safe_int(ns.timeout_sec, 1200)))
    return safe_env, safe_extra, safe_timeout


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
    ap.add_argument("--market-gemini-retries", default="0")
    ap.add_argument("--max-retries", type=int, default=1, help="Failed company/window attempts are retried with a conservative profile.")
    ap.add_argument("--retry-timeout-sec", type=int, default=1800)
    ap.add_argument("--retry-skip-network", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--safe-first", action="store_true", help="Start every target with the conservative local profile.")
    ap.add_argument(
        "--skip-network-normal-first",
        action="store_true",
        help="With --skip-network, keep requested concurrency for the first attempt; timeout/crash fallback still uses the conservative profile.",
    )
    ap.add_argument("--auto-safe-after-timeout", action=argparse.BooleanOptionalAction, default=True, help="After a timeout/native crash, start later targets with the conservative local profile.")
    ap.add_argument("--auto-safe-slow-ratio", type=float, default=0.95, help="Also switch to conservative first-attempts when elapsed time reaches this share of --timeout-sec. Set 0 to disable.")
    ap.add_argument("--accept-existing-outputs", action="store_true", help="If all six specialist agent outputs already exist, snapshot them and mark the target OK without rerunning.")
    ap.add_argument("--accept-existing-after-timeout", action=argparse.BooleanOptionalAction, default=True, help="If a timed-out target produced fresh six-agent outputs, snapshot those outputs and mark the target OK.")
    ap.add_argument("--resume", action="store_true", help="Reuse the same --run-stamp/--run-id folder and skip completed OK snapshots.")
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
    completed_log_rows = _load_completed_log_rows(log_csv) if ns.resume else {}
    # Backtest reruns with --skip-network should start in the stable local profile.
    # This avoids native crashes/LLM retries and keeps one-company checkpoints moving.
    safe_first_profile = bool(ns.safe_first) or (bool(ns.skip_network) and not bool(ns.skip_network_normal_first))
    if ns.resume and ns.auto_safe_after_timeout:
        completed_rows = list(completed_log_rows.values())
        if _logged_rows_had_timeout(completed_rows):
            safe_first_profile = True
            print("[monthly-cutoff] auto-safe enabled from resume log: prior timeout/native crash detected")
        elif _logged_rows_hit_slow_threshold(completed_rows, _safe_int(ns.timeout_sec, 1200), float(ns.auto_safe_slow_ratio)):
            safe_first_profile = True
            print("[monthly-cutoff] auto-safe enabled from resume log: prior near-timeout elapsed detected")

    for w_i, as_of in enumerate(windows, 1):
        window_key = as_of[:7]
        for t_i, target in enumerate(targets, 1):
            if ns.resume and (as_of, target["company_dir"]) in completed_log_rows:
                if _snapshot_complete(out_root, window_key, target):
                    print(f"[monthly-cutoff] {as_of} {target['company_dir']} SKIP resume snapshot=OK")
                    continue
                print(f"[monthly-cutoff] {as_of} {target['company_dir']} RESUME snapshot missing -> snapshot only")
                try:
                    _snapshot(root, out_root, ns.field, window_key, target)
                    completed_attempts += 1
                    if not ns.no_checkpoint_xlsx and completed_attempts % max(1, int(ns.checkpoint_every)) == 0:
                        _checkpoint_run_log(log_csv, out_root)
                        _checkpoint_signal_df(out_root, field=ns.field, run_id=run_id)
                    continue
                except Exception as exc:
                    print(f"[monthly-cutoff] WARN resume snapshot failed; rerunning target: {exc}")

            if ns.accept_existing_outputs:
                outputs_ok, output_files = _existing_agent_outputs(root, ns.field, target)
                if outputs_ok:
                    started = time.time()
                    _snapshot(root, out_root, ns.field, window_key, target)
                    runtime = _snapshot_runtime_path(out_root, window_key, target)
                    synthetic_chair = ""
                    if runtime is not None:
                        synthetic_chair = str(_write_synthetic_chair_packet(
                            runtime=runtime,
                            target=target,
                            field=ns.field,
                            as_of_date=as_of,
                        ))
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
                        "status": "OK",
                        "returncode": 0,
                        "elapsed_sec": elapsed,
                        "attempt_count": 0,
                        "attempts": json.dumps([{
                            "attempt": 0,
                            "profile": "accepted_existing_agent_outputs",
                            "status": "OK",
                            "returncode": 0,
                            "reason": "all_six_specialist_outputs_present",
                        }], ensure_ascii=False),
                        "command": "ACCEPT_EXISTING_OUTPUTS",
                        "cutoff_env": json.dumps(cutoff_audit_payload(as_of, start_date=ns.data_start, include_tech=ns.include_tech_cutoff), ensure_ascii=False),
                        "stdout_tail": json.dumps({"output_files": output_files, "synthetic_chair": synthetic_chair}, ensure_ascii=False),
                        "stderr_tail": "",
                    }
                    _append_log(log_csv, row)
                    completed_attempts += 1
                    print(f"[monthly-cutoff] {as_of} {target['company_dir']} OK existing_outputs elapsed={elapsed}s")
                    if not ns.no_checkpoint_xlsx and completed_attempts % max(1, int(ns.checkpoint_every)) == 0:
                        _checkpoint_run_log(log_csv, out_root)
                        _checkpoint_signal_df(out_root, field=ns.field, run_id=run_id)
                    continue

            env = build_cutoff_env(as_of, start_date=ns.data_start, include_tech=ns.include_tech_cutoff, base_env=os.environ)
            env.setdefault("PYTHONUTF8", "1")
            env.setdefault("PYTHONIOENCODING", "utf-8")
            env["PYTHONPATH"] = str(root / "src") + (os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else "")
            env["ALPHAPROVE_EVAL_OUTPUT_ROOT"] = str(out_root)
            env["ALPHAPROVE_EVAL_WINDOW"] = window_key
            _force_local_history_env(env)
            _stabilize_native_env(env)

            # Explicit no-look-ahead and local-source hints consumed by intake/agent code.
            company_data_dir = _company_data_dir(root, ns.field, target["company_dir"], target["company"])
            env["ALPHAPROVE_MONTHLY_CUTOFF_MODE"] = "1"
            env["ALPHAPROVE_NO_LOOKAHEAD"] = "1"
            env["ALPHAPROVE_COMPANY_DATA_DIR"] = str(company_data_dir)
            env["MARKET_EXCEL_DIR"] = str(root / "data" / "market_excel")
            env["MARKET_PRICE_CACHE_DIR"] = str(root / "data" / "market_excel")
            env["VALUATION_INTAKE_DIR"] = str(company_data_dir / "valuation" / "intake")
            env["VALUATION_INPUT_DIR"] = str(company_data_dir / "valuation" / "intake")
            env["VALUATION_OUTPUT_DIR"] = str(company_data_dir / "valuation")
            env["FINANCE_INTAKE_DIR"] = str(company_data_dir / "finance" / "intake")
            env["ISSUE_INTAKE_DIR"] = str(company_data_dir / "issue" / "intake")
            env["MACRO_INPUT_DIR"] = str(root / "data" / "_global_common" / "macro")
            try:
                audit_path = write_cutoff_audit(
                    root=root,
                    field=ns.field,
                    company=target["company"],
                    company_dir=target["company_dir"],
                    as_of_date=as_of,
                    output_dir=out_root / "cutoff_audits" / window_key / target["company_dir"],
                )
                env["ALPHAPROVE_CUTOFF_AUDIT_PATH"] = str(audit_path)
            except Exception as exc:
                print(f"[monthly-cutoff] WARN cutoff source audit failed for {as_of} {target['company_dir']}: {exc}")

            extra = _pipeline_extra(ns)
            cmd = _command(root, py, target, ns.field, ns.mode, extra)
            started = time.time()
            status = "OK"
            rc = 0
            stdout = ""
            stderr = ""
            attempt_rows: list[dict[str, Any]] = []
            snapshot_already_written = False

            first_env = env
            first_extra = extra
            first_timeout = ns.timeout_sec
            first_profile = "normal"
            if safe_first_profile:
                first_env, first_extra, first_timeout = _safe_pipeline_profile(ns, env)
                first_profile = "safe_local_low_concurrency"
                cmd = _command(root, py, target, ns.field, ns.mode, first_extra)

            rc, stdout, stderr, status = _run_target_attempt(cmd=cmd, env=first_env, root=root, timeout_sec=first_timeout)
            attempt_rows.append({
                "attempt": 1,
                "profile": first_profile,
                "status": status,
                "returncode": rc,
                "reason": "" if status == "OK" else _retry_reason(status, rc, stderr, stdout),
            })

            max_retries = max(0, int(ns.max_retries))
            if status != "OK" and max_retries:
                for retry_i in range(1, max_retries + 1):
                    reason = _retry_reason(status, rc, stderr, stdout)
                    retry_env, retry_extra, retry_timeout = _safe_pipeline_profile(ns, env)
                    retry_cmd = _command(root, py, target, ns.field, ns.mode, retry_extra)
                    print(
                        f"[monthly-cutoff] retry {retry_i}/{max_retries} {as_of} {target['company_dir']} "
                        f"after {reason}: low-concurrency local profile"
                    )
                    rc, stdout, stderr, status = _run_target_attempt(
                        cmd=retry_cmd,
                        env=retry_env,
                        root=root,
                        timeout_sec=retry_timeout,
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
            if ns.auto_safe_after_timeout and not safe_first_profile:
                switch_reason = ""
                if _attempt_rows_had_timeout(attempt_rows):
                    switch_reason = "timeout/native crash"
                elif _slow_threshold_hit(float(elapsed), _safe_int(ns.timeout_sec, 1200), float(ns.auto_safe_slow_ratio)):
                    switch_reason = f"near-timeout elapsed={elapsed}s threshold={round(_safe_int(ns.timeout_sec, 1200) * float(ns.auto_safe_slow_ratio), 1)}s"
                if switch_reason:
                    safe_first_profile = True
                    print(f"[monthly-cutoff] auto-safe enabled for remaining targets after {as_of} {target['company_dir']}: {switch_reason}")
            if status == "TIMEOUT" and ns.accept_existing_after_timeout:
                outputs_ok, output_files = _existing_agent_outputs(root, ns.field, target)
                if outputs_ok and _outputs_recent(output_files, started):
                    try:
                        _snapshot(root, out_root, ns.field, window_key, target)
                        runtime = _snapshot_runtime_path(out_root, window_key, target)
                        synthetic_chair = ""
                        if runtime is not None:
                            synthetic_chair = str(_write_synthetic_chair_packet(
                                runtime=runtime,
                                target=target,
                                field=ns.field,
                                as_of_date=as_of,
                            ))
                        status = "OK"
                        rc = 0
                        snapshot_already_written = True
                        attempt_rows.append({
                            "attempt": len(attempt_rows) + 1,
                            "profile": "accepted_fresh_outputs_after_timeout",
                            "status": "OK",
                            "returncode": 0,
                            "reason": "timeout_process_tree_killed_but_all_six_agent_outputs_were_fresh",
                        })
                        stdout = (stdout or "") + "\n[monthly-cutoff] accepted fresh existing outputs after timeout: " + json.dumps({
                            "output_files": output_files,
                            "synthetic_chair": synthetic_chair,
                        }, ensure_ascii=False)
                        stderr = stderr.replace("[TIMEOUT]", "[TIMEOUT_RECOVERED]")
                        print(f"[monthly-cutoff] {as_of} {target['company_dir']} recovered fresh outputs after timeout")
                    except Exception as exc:
                        print(f"[monthly-cutoff] WARN timeout recovery snapshot failed: {exc}")
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
                if not snapshot_already_written:
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
