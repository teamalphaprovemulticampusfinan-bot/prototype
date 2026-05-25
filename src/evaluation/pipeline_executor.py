from __future__ import annotations

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from evaluation.cutoff_env import build_cutoff_env, cutoff_audit_payload

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore


@dataclass(frozen=True)
class TargetRow:
    company_name: str
    company_dir: str
    stock_code: str = ""
    field: str = "반도체"
    market: str = ""
    sector: str = ""
    peer_group: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "company_name": self.company_name,
            "company": self.company_name,
            "company_dir": self.company_dir,
            "stock_code": self.stock_code,
            "ticker": self.stock_code,
            "field": self.field,
            "market": self.market,
            "sector": self.sector,
            "peer_group": self.peer_group,
        }


DEFAULT_ASOF_ENV_KEYS = [
    "ALPHAPROVE_DATA_CUTOFF_DATE",
    "FINANCE_AS_OF_DATE",
    "FINANCE_CUTOFF_YEAR",
    "FINANCE_STOCK_CUTOFF_DATE",
    "MARKET_AS_OF_DATE",
    "MARKET_END_DATE",
    "ISSUE_AS_OF_DATE",
    "ISSUE_END_DATE",
    "MACRO_AS_OF_DATE",
    "MACRO_END_DATE",
    "MACRO_CUTOFF_DATE",
    "VALUATION_AS_OF_DATE",
    "VALUATION_CUTOFF_YEAR",
    "VALUATION_PRICE_CUTOFF_DATE",
    "VALUATION_END_DATE",
]

DEFAULT_START_ENV_KEYS = [
    "FINANCE_START_DATE",
    "MARKET_START_DATE",
    "ISSUE_START_DATE",
    "MACRO_START_DATE",
    "VALUATION_START_DATE",
    "TECH_START_DATE",
]

AGENT_ALIASES: dict[str, str] = {
    "intake": "data-intake",
    "data_intake": "data-intake",
    "data-intake": "data-intake",
    "valuation_intake": "valuation-intake",
    "valuation-intake": "valuation-intake",
    "tech_intake": "tech-intake",
    "tech-intake": "tech-intake",
    "finance": "finance",
    "valuation": "valuation",
    "tech": "tech",
    "market": "market",
    "issue": "issue",
    "macro": "macro",
    "auditor": "auditor",
    "chair": "chair",
}


def _project_python(root: Path) -> str:
    candidates = [
        root / ".venv" / "Scripts" / "python.exe",
        root / ".venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if pd is not None:
        try:
            if pd.isna(value):
                return ""
        except Exception:
            pass
    return str(value).strip()


def _truthy_eval(value: Any) -> bool:
    text = _safe_text(value).lower()
    if not text:
        return True
    return text not in {"0", "false", "n", "no", "제외", "exclude", "x"}


def _normalize_stock_code(value: Any) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    text = re.sub(r"\.0$", "", text)
    digits = re.sub(r"\D", "", text)
    return digits.zfill(6) if digits and len(digits) <= 6 else text


def _first_present(row: dict[str, Any], names: Iterable[str], default: str = "") -> str:
    for name in names:
        if name in row and _safe_text(row.get(name)):
            return _safe_text(row.get(name))
    return default


def read_universe_rows(universe_csv: str | Path, limit: int | None = None, field: str | None = None) -> list[dict[str, str]]:
    """Read a universe CSV in the project format used by the v49 backtest.

    Only rows with include_in_evaluation truthy are used.  Column names are kept
    permissive so team CSV variants such as company/company_name/name and
    ticker/stock_code/code all work without touching the agent code.
    """
    path = Path(universe_csv)
    if not path.exists():
        raise FileNotFoundError(f"universe CSV를 찾지 못했습니다: {path}")

    if pd is not None:
        df = pd.read_csv(path, dtype=str, encoding="utf-8-sig").fillna("")
        records = df.to_dict("records")
    else:  # pragma: no cover
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            records = list(csv.DictReader(f))

    targets: list[dict[str, str]] = []
    for row in records:
        if "include_in_evaluation" in row and not _truthy_eval(row.get("include_in_evaluation")):
            continue
        row_field = _first_present(row, ["field", "sector_field", "industry_field"], field or "반도체")
        if field and row_field and row_field != field:
            # Keep rows with empty field, filter only explicit different fields.
            continue
        company = _first_present(row, ["company_name", "company", "name", "corp_name", "종목명"])
        company_dir = _first_present(row, ["company_dir", "slug", "ticker_slug", "folder", "폴더명"])
        stock_code = _normalize_stock_code(_first_present(row, ["stock_code", "ticker", "code", "종목코드"]))
        if not company and company_dir:
            company = company_dir
        if not company_dir and company:
            company_dir = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", company).strip("_").lower()
        if not company or not company_dir:
            continue
        target = TargetRow(
            company_name=company,
            company_dir=company_dir,
            stock_code=stock_code,
            field=row_field or field or "반도체",
            market=_first_present(row, ["market", "시장"]),
            sector=_first_present(row, ["sector", "업종"]),
            peer_group=_first_present(row, ["peer_group", "peer", "group"]),
        )
        targets.append(target.as_dict())
        if limit and len(targets) >= limit:
            break
    if not targets:
        raise RuntimeError(f"universe CSV에서 실행 대상을 찾지 못했습니다: {path}")
    return targets


def _parse_date_like(value: str, *, end_of_month: bool) -> date:
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}", text):
        y, m = map(int, text.split("-"))
        d = monthrange(y, m)[1] if end_of_month else 1
        return date(y, m, d)
    return datetime.strptime(text[:10], "%Y-%m-%d").date()


def month_ends(start: str, end: str) -> list[str]:
    start_d = _parse_date_like(start, end_of_month=False)
    end_d = _parse_date_like(end, end_of_month=True)
    y, m = start_d.year, start_d.month
    out: list[str] = []
    while True:
        last = date(y, m, monthrange(y, m)[1])
        if last >= start_d and last <= end_d:
            out.append(last.isoformat())
        if (y, m) >= (end_d.year, end_d.month):
            break
        m += 1
        if m == 13:
            y += 1
            m = 1
    return out


def daily_dates(start: str, end: str) -> list[str]:
    cur = _parse_date_like(start, end_of_month=False)
    end_d = _parse_date_like(end, end_of_month=True)
    out: list[str] = []
    while cur <= end_d:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def _window_folder(frequency: str, as_of_date: str) -> str:
    return as_of_date[:7] if frequency == "monthly" else as_of_date


def _normalize_agents(agents: Iterable[str]) -> list[str]:
    out: list[str] = []
    for raw in agents:
        key = str(raw).strip().lower().replace("_", "-")
        agent = AGENT_ALIASES.get(key)
        if agent and agent not in out:
            out.append(agent)
    return out


def _common_env(root: Path, field: str, frequency: str, as_of_date: str) -> dict[str, str]:
    env = build_cutoff_env(as_of_date, start_date=os.getenv("ALPHAPROVE_EVAL_DATA_START", "2021-01-01"), include_tech=False, base_env=os.environ)
    src_path = str(root / "src")
    current_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_path if not current_pp else src_path + os.pathsep + current_pp
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env["ALPHAPROVE_DATA_FIELD"] = field
    env["ALPHAPROVE_FIELD"] = field
    env["ALPHAPROVE_EVAL_HISTORY"] = "1"
    env["ALPHAPROVE_EVAL_FREQUENCY"] = frequency
    env["ALPHAPROVE_HISTORY_BACKEND"] = "local"
    env["ALPHAPROVE_DISABLE_GOOGLE_SHEETS"] = "1"
    env["ALPHAPROVE_HISTORY_LOCAL_WRITE_DISABLED"] = "0"
    env["CHAIR_FORCE_LOCAL_OUTPUT"] = "1"
    env["ALPHAPROVE_CHAIR_OUTPUT_BACKEND"] = "local"
    env.setdefault("CHAIR_FORCE_TEMPLATE_REPORT", "1")
    env.setdefault("AUDITOR_FIRST_FAIL_OPEN", "true")
    return env


def _command_for_agent(root: Path, python_exe: str, agent: str, target: dict[str, str], field: str, as_of_date: str) -> list[str]:
    company_dir = target["company_dir"]
    company = target["company_name"]
    main = str(root / "main.py")

    if agent == "data-intake":
        return [python_exe, main, "data-intake", "--field", field, "--company-dir", company_dir, "--company", company]
    if agent == "valuation-intake":
        return [python_exe, main, "valuation-intake", "--field", field, "--company-dir", company_dir, "--company", company, "--start", "2021-01-01", "--end", as_of_date]
    if agent == "tech-intake":
        return [python_exe, main, "tech-intake", "--field", field, "--company-dir", company_dir, "--company", company]
    if agent == "chair":
        return [python_exe, main, "chair", "--company-dir", company_dir, "--company", company, "--no-intake", "--local-output"]
    return [python_exe, main, agent, "--company-dir", company_dir, "--company", company]


def _tail(text: str, max_chars: int = 4000) -> str:
    text = text or ""
    return text[-max_chars:] if len(text) > max_chars else text


def _append_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    fieldnames = list(row.keys())
    with path.open("a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def _copytree_clean(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    if src.exists():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))


def _resolve_company_data_dir(root: Path, field: str, company_dir: str, company_name: str) -> Path:
    # Prefer the project helper because it resolves slug -> Korean company folder.
    try:
        if str(root / "src") not in sys.path:
            sys.path.insert(0, str(root / "src"))
        from common.data_paths import company_root  # type: ignore

        path = company_root(company_dir, field=field, create=False)
        if path.exists():
            return path
    except Exception:
        pass

    direct = root / "data" / field / company_name
    if direct.exists():
        return direct
    slug_direct = root / "data" / field / company_dir
    if slug_direct.exists():
        return slug_direct
    return direct


def _safe_rm(path: Path) -> None:
    if path.exists():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def _backup_before_run(root: Path, field: str, target: dict[str, str], out_root: Path, window_key: str) -> Path | None:
    src = _resolve_company_data_dir(root, field, target["company_dir"], target["company_name"])
    if not src.exists():
        return None
    backup = out_root / "_operational_backup" / window_key / target["company_dir"] / "data" / field / src.name
    _copytree_clean(src, backup)
    return backup


def _restore_after_run(root: Path, field: str, target: dict[str, str], backup: Path | None) -> None:
    current = _resolve_company_data_dir(root, field, target["company_dir"], target["company_name"])
    if backup is None:
        # No pre-existing folder; remove generated folder in safe backtest mode.
        _safe_rm(current)
        return
    _copytree_clean(backup, current)


def _snapshot_after_run(root: Path, field: str, target: dict[str, str], out_root: Path, window_key: str) -> dict[str, Any]:
    src = _resolve_company_data_dir(root, field, target["company_dir"], target["company_name"])
    company_out = out_root / "real_pipeline_outputs" / window_key / target["company_dir"]
    status: dict[str, Any] = {
        "company": target["company_name"],
        "company_dir": target["company_dir"],
        "field": field,
        "source_company_dir": str(src),
        "runtime_data": None,
        "operational_data_snapshot": None,
        "status": "MISSING_SOURCE_COMPANY_DIR",
    }
    if not src.exists():
        company_out.mkdir(parents=True, exist_ok=True)
        (company_out / "COPY_STATUS.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
        return status

    runtime_dst = company_out / "runtime_data" / src.name
    operational_dst = company_out / "operational_data_snapshot" / src.name
    _copytree_clean(src, runtime_dst)
    _copytree_clean(src, operational_dst)
    status.update({
        "runtime_data": str(runtime_dst),
        "operational_data_snapshot": str(operational_dst),
        "status": "OK",
        "copied_at": datetime.now().isoformat(timespec="seconds"),
    })
    (company_out / "COPY_STATUS.json").write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    return status


_DATE_RE = re.compile(r"(?<!\d)(20\d{2})[-./](\d{1,2})[-./](\d{1,2})(?!\d)")


def _scan_future_dates(path: Path, as_of_date: str, max_bytes: int = 2_000_000) -> dict[str, Any] | None:
    cutoff = datetime.strptime(as_of_date[:10], "%Y-%m-%d").date()
    if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".txt", ".csv"}:
        return None
    try:
        raw = path.read_bytes()[:max_bytes]
        text = raw.decode("utf-8", errors="ignore")
    except Exception:
        return None
    examples: list[str] = []
    count = 0
    for m in _DATE_RE.finditer(text):
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            continue
        if d > cutoff:
            count += 1
            if len(examples) < 10:
                examples.append(d.isoformat())
    if count <= 0:
        return None
    return {
        "file": str(path),
        "as_of_date": as_of_date,
        "future_date_count": count,
        "future_date_examples": ",".join(examples),
        "audit_status": "POSSIBLE_CUTOFF_LEAKAGE",
    }


def _write_cutoff_audit(out_root: Path, company_snapshot_root: Path, as_of_date: str) -> None:
    audit_csv = out_root / "real_pipeline_cutoff_audit.csv"
    if not company_snapshot_root.exists():
        return
    for file in company_snapshot_root.rglob("*"):
        row = _scan_future_dates(file, as_of_date)
        if row:
            _append_csv(audit_csv, row)


def run_real_pipeline_for_window(
    *,
    root: Path,
    field: str,
    frequency: str,
    as_of_date: str,
    run_id: str,
    targets: list[dict[str, str]],
    agents: list[str],
    timeout_sec: int,
    continue_on_error: bool,
    out_root: Path,
    keep_local_outputs: bool = False,
) -> Path:
    """Run the actual AlphaProve agent pipeline for one as-of date.

    This module intentionally does not change individual agent code.  It only
    sets cutoff environment variables, calls ``main.py <agent>``, and copies the
    resulting local company folder into the v49-style backtest output tree.
    """
    root = Path(root).resolve()
    out_root = Path(out_root).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    window_key = _window_folder(frequency, as_of_date)
    log_csv = out_root / "real_pipeline_agent_run_log.csv"
    python_exe = _project_python(root)
    agent_list = _normalize_agents(agents)

    for target in targets:
        backup: Path | None = None
        if not keep_local_outputs:
            backup = _backup_before_run(root, field, target, out_root, window_key)

        try:
            for agent in agent_list:
                env = _common_env(root, field, frequency, as_of_date)
                command = _command_for_agent(root, python_exe, agent, target, field, as_of_date)
                started = time.time()
                status = "OK"
                returncode = 0
                stdout = ""
                stderr = ""
                try:
                    proc = subprocess.run(
                        command,
                        cwd=str(root),
                        env=env,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        capture_output=True,
                        timeout=timeout_sec,
                    )
                    returncode = int(proc.returncode)
                    stdout = proc.stdout or ""
                    stderr = proc.stderr or ""
                    if returncode != 0:
                        status = "FAILED"
                except subprocess.TimeoutExpired as exc:
                    status = "TIMEOUT"
                    returncode = 124
                    stdout = exc.stdout if isinstance(exc.stdout, str) else ""
                    stderr = exc.stderr if isinstance(exc.stderr, str) else ""
                    stderr += f"\n[TIMEOUT] {timeout_sec} seconds exceeded"
                elapsed = round(time.time() - started, 3)
                row = {
                    "run_id": run_id,
                    "field": field,
                    "frequency": frequency,
                    "as_of_date": as_of_date,
                    "company": target.get("company_name", ""),
                    "company_dir": target.get("company_dir", ""),
                    "ticker": target.get("stock_code", ""),
                    "agent": agent,
                    "status": status,
                    "returncode": returncode,
                    "elapsed_sec": elapsed,
                    "command": " ".join(command),
                    "cwd": str(root),
                    "eval_entrypoint": str(root / "main.py"),
                    "asof_env_applied": json.dumps(cutoff_audit_payload(as_of_date, start_date=env.get("FINANCE_START_DATE", "2021-01-01"), include_tech=False), ensure_ascii=False),
                    "stdout_tail": _tail(stdout),
                    "stderr_tail": _tail(stderr),
                }
                _append_csv(log_csv, row)
                print(f"[real-pipeline] {as_of_date} {target['company_dir']} {agent}: {status} rc={returncode} elapsed={elapsed}s")
                if status != "OK" and not continue_on_error:
                    raise RuntimeError(f"{as_of_date} {target['company_dir']} {agent} failed rc={returncode}. stderr={_tail(stderr, 1000)}")

            copy_status = _snapshot_after_run(root, field, target, out_root, window_key)
            snap_root = Path(copy_status.get("operational_data_snapshot") or "")
            if snap_root.exists():
                _write_cutoff_audit(out_root, snap_root, as_of_date)
        finally:
            if not keep_local_outputs:
                _restore_after_run(root, field, target, backup)

    return out_root
