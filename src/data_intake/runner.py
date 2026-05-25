from __future__ import annotations

import argparse
import importlib
import json
import os
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Sequence

from common.data_paths import company_agent_dir, normalize_field_name
from data_intake.tech_intake.runner import run_tech_intake

# -----------------------------------------------------------------------------
# AlphaProve unified Data Intake policy
# -----------------------------------------------------------------------------
# Market and Issue now have explicit intake wrappers under data_intake/.
# Chair must run those wrappers before specialist agents so that market/issue
# inputs are refreshed consistently with macro/finance/tech/valuation.
# -----------------------------------------------------------------------------
DEFAULT_AGENTS = ["macro", "market", "issue", "finance", "tech", "valuation"]
DIRECT_AGENT_ONLY_AGENTS: set[str] = set()
LEGACY_KNOWN_AGENTS = ["macro", "market", "issue", "finance", "tech", "valuation"]
AGENT_ALIASES = {
    "macro-intake": "macro",
    "macro_intake": "macro",
    "market-intake": "market",
    "market_intake": "market",
    "issue-intake": "issue",
    "issue_intake": "issue",
    "finance-intake": "finance",
    "finance_intake": "finance",
    "tech-intake": "tech",
    "tech_intake": "tech",
    "valuation-intake": "valuation",
    "valuation_intake": "valuation",
}


def _normalize_agent_name(value: str) -> str:
    item = str(value or "").strip().lower().replace("_agent", "").replace("-agent", "")
    return AGENT_ALIASES.get(item, item)


def _split_agents(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_AGENTS[:]
    items: list[str] = []
    for chunk in value.replace(";", ",").split(","):
        item = _normalize_agent_name(chunk)
        if item:
            items.append(item)
    return items or DEFAULT_AGENTS[:]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        value = str(os.getenv(name, "")).strip()
        return int(value) if value else default
    except Exception:
        return default


def _direct_agent_only_record(agent: str) -> dict[str, Any]:
    message = (
        f"{agent}_agent는 별도 data_intake 단계 없이 직접 실행하는 구조입니다. "
        f"Chair 실행 시 {agent} 노드에서 python main.py {agent} 형태로 직접 실행됩니다."
    )
    return {
        "agent": agent,
        "status": "SKIPPED_DIRECT_AGENT_ONLY",
        "started_at": _now(),
        "ended_at": _now(),
        "reason": message,
        "direct_run_command_example": f'python main.py {agent} --company-dir <slug> --company "<회사명>"',
    }



def _network_skipped_record(agent: str, *, company_dir: str, company: str, field: str) -> dict[str, Any]:
    started = _now()
    return {
        "agent": agent,
        "status": "SKIPPED_NETWORK_DISABLED",
        "started_at": started,
        "ended_at": _now(),
        "company_dir": company_dir,
        "company": company,
        "field": field,
        "reason": f"data_intake가 --skip-network로 실행되어 {agent}_intake 네트워크 수집을 생략했습니다.",
    }



_COMPANY_STOCK_CODE = {
    "nepes": "033640",
    "hanmi": "042700",
    "hansol": "014680",
    "duksan": "317330",
    "ltc": "170920",
}


def _resolve_stock_code(company_dir: str, company: str | None = None) -> str | None:
    """Resolve stock code for finance_intake from slug/name/company.yaml."""
    raw_values = [str(company_dir or "").strip(), str(company or "").strip()]
    for raw in raw_values:
        key = raw.lower()
        if key in _COMPANY_STOCK_CODE:
            return _COMPANY_STOCK_CODE[key]
        if raw.isdigit() and len(raw) == 6:
            return raw

    try:
        from common.data_paths import company_config_path, company_slug
        try:
            slug = company_slug(company_dir or company or "")
        except Exception:
            slug = str(company_dir or "").strip().lower()
        if slug in _COMPANY_STOCK_CODE:
            return _COMPANY_STOCK_CODE[slug]
        cfg_path = company_config_path(slug, create_parent=False)
        if cfg_path.exists():
            try:
                import yaml  # type: ignore
                cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            except UnicodeDecodeError:
                import yaml  # type: ignore
                cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8-sig")) or {}
            except Exception:
                cfg = {}
            stock_code = str(cfg.get("stock_code") or "").strip()
            if stock_code:
                return stock_code.zfill(6) if stock_code.isdigit() else stock_code
    except Exception:
        pass

    return None


def _run_finance_intake(
    *,
    company_dir: str,
    company: str,
    field: str,
    skip_network: bool,
    force_fetch: bool,
    continue_on_error: bool,
    mode: str = "all",
    years: list[int] | None = None,
) -> dict[str, Any]:
    """Run finance_intake with the CLI-required --mode/--stock arguments filled.

    finance_intake is network-heavy because it can collect DART financials,
    stock prices, KIND warnings and VKOSPI. When unified data_intake is called
    with --skip-network, this wrapper records a clear skipped manifest instead
    of invoking finance_intake without --mode and aborting argparse.
    """
    started = datetime.now()
    stock_code = _resolve_stock_code(company_dir, company)
    out_dir = company_agent_dir(company_dir, "finance", create=True) / "intake"
    out_dir.mkdir(parents=True, exist_ok=True)

    if skip_network:
        record = {
            "agent": "finance",
            "status": "SKIPPED_NETWORK_DISABLED",
            "started_at": started.isoformat(timespec="seconds"),
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "company_dir": company_dir,
            "company": company,
            "field": field,
            "stock_code": stock_code,
            "reason": "data_intake가 --skip-network로 실행되어 DART/주가/KIND 기반 finance_intake를 호출하지 않았습니다. 기존 finance 산출물이 있으면 finance_agent가 직접 읽습니다.",
            "direct_command_example": f'python -m data_intake.finance_intake.runner --mode all --stock {stock_code or "종목코드"} --sector {field}',
        }
        path = out_dir / "finance_intake_manifest.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[Finance Intake] skip-network로 생략: {path}")
        return record

    if not stock_code:
        record = {
            "agent": "finance",
            "status": "FAILED_NO_STOCK_CODE",
            "started_at": started.isoformat(timespec="seconds"),
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "company_dir": company_dir,
            "company": company,
            "field": field,
            "error": "company.yaml 또는 기본 매핑에서 stock_code를 찾지 못했습니다.",
        }
        path = out_dir / "finance_intake_manifest.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        if not continue_on_error:
            raise ValueError(record["error"])
        return record

    try:
        from data_intake.finance_intake.runner import run_finance_intake

        return run_finance_intake(
            company_dir=company_dir,
            company=company,
            field=field,
            stock_code=stock_code,
            mode=mode,
            years=years or [2023, 2024, 2025],
            force_fetch=force_fetch,
            skip_network=False,
            continue_on_error=continue_on_error,
        )
    except Exception as exc:
        tb = traceback.format_exc()
        print(f"[Data Intake] finance intake error: {exc}")
        print(tb)
        if not continue_on_error:
            raise
        record = {
            "agent": "finance",
            "status": "FAILED_EXCEPTION",
            "started_at": started.isoformat(timespec="seconds"),
            "ended_at": datetime.now().isoformat(timespec="seconds"),
            "company_dir": company_dir,
            "company": company,
            "field": field,
            "stock_code": stock_code,
            "error": str(exc),
            "traceback": tb,
        }
        path = out_dir / "finance_intake_manifest.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return record


def _call_optional_intake(agent: str, *, company_dir: str, company: str, field: str, continue_on_error: bool) -> dict[str, Any]:
    started = datetime.now()
    module_names = [
        f"data_intake.{agent}_intake.runner",
        f"data_intake.{agent}.runner",
    ]
    errors: list[str] = []

    for module_name in module_names:
        try:
            mod = importlib.import_module(module_name)
        except Exception as exc:
            errors.append(f"{module_name}: import failed: {exc}")
            continue

        for fn_name in (f"run_{agent}_intake", "run_intake", "run", "main"):
            fn = getattr(mod, fn_name, None)
            if not callable(fn):
                continue
            try:
                if fn_name == "main":
                    try:
                        fn(["--company-dir", company_dir, "--company", company])
                    except TypeError:
                        fn()
                else:
                    try:
                        fn(company_dir=company_dir, company=company, field=field)
                    except TypeError:
                        try:
                            fn(company, company_dir=company_dir)
                        except TypeError:
                            fn()
                return {
                    "agent": agent,
                    "status": "DONE",
                    "module": module_name,
                    "function": fn_name,
                    "started_at": started.isoformat(timespec="seconds"),
                    "ended_at": datetime.now().isoformat(timespec="seconds"),
                }
            except Exception as exc:
                tb = traceback.format_exc()
                errors.append(f"{module_name}.{fn_name}: {exc}\n{tb}")
                print(f"[Data Intake] {agent} intake error in {module_name}.{fn_name}: {exc}")
                print(tb)
                if not continue_on_error:
                    raise

    return {
        "agent": agent,
        "status": "SKIPPED_NO_INTAKE_RUNNER",
        "started_at": started.isoformat(timespec="seconds"),
        "ended_at": datetime.now().isoformat(timespec="seconds"),
        "errors": errors[-5:],
    }


def _run_selected_intake_agent(
    agent: str,
    *,
    company_dir: str,
    company: str,
    field: str,
    continue_on_error: bool,
    tech_max_patents: int | None,
    tech_sleep_sec: float | None,
    tech_timeout: int | None,
    tech_force_fetch: bool,
    skip_network: bool,
    tech_skip_network: bool,
    tech_skip_agent: bool,
    tech_kipris_plus_components: str | None,
    finance_mode: str,
    finance_years: list[int] | None,
) -> dict[str, Any]:
    if agent in DIRECT_AGENT_ONLY_AGENTS:
        print(f"\n[Data Intake] {agent} intake 생략 → {agent}_agent 직접 실행 대상")
        record = _direct_agent_only_record(agent)
        print(f"[Data Intake] {agent} intake 생략 완료")
        return record

    if agent == "macro" and skip_network:
        print("\n[Data Intake] macro intake 생략 → --skip-network")
        record = _network_skipped_record("macro", company_dir=company_dir, company=company, field=field)
        print("[Data Intake] macro intake 생략 완료")
        return record

    if agent == "finance":
        print("\n[Data Intake] finance intake 시작")
        record = _run_finance_intake(
            company_dir=company_dir,
            company=company,
            field=field,
            skip_network=skip_network,
            force_fetch=tech_force_fetch,
            continue_on_error=continue_on_error,
            mode=finance_mode,
            years=finance_years,
        )
        print("[Data Intake] finance intake 완료")
        return record

    if agent == "valuation":
        print("\n[Data Intake] valuation intake 시작")
        try:
            from data_intake.valuation_intake.runner import run_valuation_intake

            record = run_valuation_intake(
                company_dir=company_dir,
                company=company,
                field=field,
                skip_network=skip_network,
                force_fetch=tech_force_fetch,
                continue_on_error=continue_on_error,
            )
        except Exception as exc:
            tb = traceback.format_exc()
            print(f"[Data Intake] valuation intake error: {exc}")
            print(tb)
            if not continue_on_error:
                raise
            record = {"agent": "valuation", "status": "FAILED_EXCEPTION", "error": str(exc), "traceback": tb}
        print("[Data Intake] valuation intake 완료")
        return record

    if agent == "tech":
        print("\n[Data Intake] tech intake 시작")
        try:
            record = run_tech_intake(
                company_dir=company_dir,
                company=company,
                field=field,
                max_patents=tech_max_patents,
                sleep_sec=tech_sleep_sec,
                timeout=tech_timeout,
                force_fetch=tech_force_fetch,
                skip_network=tech_skip_network,
                skip_agent=tech_skip_agent,
                kipris_plus_components=tech_kipris_plus_components,
                continue_on_error=continue_on_error,
            )
        except Exception as exc:
            tb = traceback.format_exc()
            print(f"[Data Intake] tech intake error: {exc}")
            print(tb)
            if not continue_on_error:
                raise
            record = {
                "agent": "tech",
                "status": "FAILED_EXCEPTION",
                "error": str(exc),
                "traceback": tb,
            }
        print("[Data Intake] tech intake 완료")
        return record

    print(f"\n[Data Intake] {agent} intake 시작")
    record = _call_optional_intake(
        agent,
        company_dir=company_dir,
        company=company,
        field=field,
        continue_on_error=continue_on_error,
    )
    print(f"[Data Intake] {agent} intake 완료")
    return record


def run_data_intake(
    *,
    company_dir: str,
    company: str,
    agents: list[str] | None = None,
    continue_on_error: bool = True,
    field: str = "반도체",
    tech_max_patents: int | None = None,
    tech_sleep_sec: float | None = None,
    tech_timeout: int | None = None,
    tech_force_fetch: bool = False,
    skip_network: bool = False,
    tech_skip_network: bool = False,
    tech_skip_agent: bool = False,
    tech_kipris_plus_components: str | None = None,
    finance_mode: str = "all",
    finance_years: list[int] | None = None,
    parallel: bool | None = None,
    max_workers: int | None = None,
) -> dict[str, Any]:
    field = normalize_field_name(field)
    selected = agents or DEFAULT_AGENTS[:]
    selected = [_normalize_agent_name(str(a)) for a in selected if str(a).strip()]

    print("=" * 88)
    print(f"Data Intake 실행: {company} / {company_dir}")
    print(f"대상 intake: {selected}")
    print(f"direct-agent-only: {sorted(DIRECT_AGENT_ONLY_AGENTS) if DIRECT_AGENT_ONLY_AGENTS else []}")
    print("=" * 88)

    records: list[dict[str, Any]] = []
    use_parallel = _env_bool("DATA_INTAKE_PARALLEL", False) if parallel is None else bool(parallel)
    worker_count = max_workers if max_workers is not None else _env_int("DATA_INTAKE_MAX_WORKERS", min(4, len(selected) or 1))
    worker_count = max(1, min(int(worker_count), len(selected) or 1))

    common_kwargs = {
        "company_dir": company_dir,
        "company": company,
        "field": field,
        "continue_on_error": continue_on_error,
        "tech_max_patents": tech_max_patents,
        "tech_sleep_sec": tech_sleep_sec,
        "tech_timeout": tech_timeout,
        "tech_force_fetch": tech_force_fetch,
        "skip_network": skip_network,
        "tech_skip_network": tech_skip_network,
        "tech_skip_agent": tech_skip_agent,
        "tech_kipris_plus_components": tech_kipris_plus_components,
        "finance_mode": finance_mode,
        "finance_years": finance_years,
    }

    if use_parallel and len(selected) > 1 and worker_count > 1:
        print(f"[Data Intake] 병렬 실행 활성화: max_workers={worker_count}")
        ordered: list[dict[str, Any] | None] = [None] * len(selected)
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {
                executor.submit(_run_selected_intake_agent, agent, **common_kwargs): (idx, agent)
                for idx, agent in enumerate(selected)
            }
            for future in as_completed(future_map):
                idx, agent = future_map[future]
                try:
                    ordered[idx] = future.result()
                except Exception as exc:
                    if not continue_on_error:
                        raise
                    tb = traceback.format_exc()
                    print(f"[Data Intake] {agent} intake unhandled error: {exc}")
                    print(tb)
                    ordered[idx] = {
                        "agent": agent,
                        "status": "FAILED_EXCEPTION",
                        "started_at": _now(),
                        "ended_at": _now(),
                        "error": str(exc),
                        "traceback": tb,
                    }
        records = [r for r in ordered if isinstance(r, dict)]
    else:
        for agent in selected:
            records.append(_run_selected_intake_agent(agent, **common_kwargs))

    status = "OK"
    if any(str(r.get("status", "")).startswith("FAILED") or str(r.get("status", "")).startswith("WARN") for r in records):
        status = "PARTIAL"

    manifest = {
        "pipeline": "data_intake",
        "status": status,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "company_dir": company_dir,
        "company": company,
        "field": field,
        "default_agents": DEFAULT_AGENTS,
        "direct_agent_only_agents": sorted(DIRECT_AGENT_ONLY_AGENTS),
        "agents": records,
    }
    intake_dir = company_agent_dir(company_dir, "intake", create=True)
    path = intake_dir / "data_intake_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[Data Intake] manifest 저장: {path}")
    print(f"[Data Intake] status: {status}")
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run AlphaProve Data Intake before specialist agents.")
    parser.add_argument("--company-dir", required=True)
    parser.add_argument("--company", required=True)
    parser.add_argument("--field", default="반도체")
    parser.add_argument(
        "--agents",
        default=",".join(DEFAULT_AGENTS),
        help=(
            "Comma-separated intake agents. Default runs macro, market, issue, finance, tech, valuation intake when available. "
            f"Known legacy agents: {','.join(LEGACY_KNOWN_AGENTS)}"
        ),
    )
    parser.add_argument("--stop-on-error", action="store_true")
    parser.add_argument("--finance-mode", choices=["warning", "financial", "stock", "vkospi", "all"], default="all")
    parser.add_argument("--finance-years", type=int, nargs="+", default=[2023, 2024, 2025])

    parser.add_argument("--tech-max-patents", type=int, default=None)
    parser.add_argument("--tech-sleep-sec", type=float, default=None)
    parser.add_argument("--tech-timeout", type=int, default=None)
    parser.add_argument("--tech-force-fetch", action="store_true")
    parser.add_argument("--tech-skip-network", action="store_true")
    parser.add_argument("--tech-skip-agent", action="store_true")
    parser.add_argument(
        "--tech-kipris-plus-components",
        default=None,
        help="Tech KIPRIS Plus collectors: bibliographic,claims,citation,family or all",
    )
    parser.add_argument("--parallel", action="store_true", help="선택된 intake agent들을 병렬 실행")
    parser.add_argument("--max-workers", type=int, default=None, help="--parallel 사용 시 최대 병렬 worker 수")

    # Compatibility aliases from earlier patches.
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("--skip-agent", action="store_true")
    parser.add_argument("--force-fetch", action="store_true")

    args = parser.parse_args(argv)
    run_data_intake(
        company_dir=args.company_dir,
        company=args.company,
        field=args.field,
        agents=_split_agents(args.agents),
        continue_on_error=not args.stop_on_error,
        tech_max_patents=args.tech_max_patents,
        tech_sleep_sec=args.tech_sleep_sec,
        tech_timeout=args.tech_timeout,
        tech_force_fetch=args.tech_force_fetch or args.force_fetch,
        skip_network=args.skip_network,
        tech_skip_network=args.tech_skip_network or args.skip_network,
        tech_skip_agent=args.tech_skip_agent or args.skip_agent,
        tech_kipris_plus_components=args.tech_kipris_plus_components,
        finance_mode=args.finance_mode,
        finance_years=args.finance_years,
        parallel=args.parallel,
        max_workers=args.max_workers,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
