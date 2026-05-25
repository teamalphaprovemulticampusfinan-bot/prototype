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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from common.data_paths import company_agent_dir
except Exception:  # pragma: no cover
    company_agent_dir = None  # type: ignore


@dataclass(frozen=True)
class Company:
    slug: str
    name: str


TARGET_COMPANIES: list[Company] = [
    Company("hanmi", "한미반도체"),
    Company("hansol", "한솔케미칼"),
    Company("duksan", "덕산테코피아"),
    Company("ltc", "엘티씨"),
]

ERROR_MARKERS = [
    "SERVICE_KEY_IS_NOT_REGISTERED_ERROR",
    "INVALID_REQUEST_PARAMETER_ERROR",
    "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR",
    "SERVICE_ACCESS_DENIED_ERROR",
    "APPLICATION_ERROR",
    "NO_OPENAPI_SERVICE_ERROR",
]


class PipelineError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _load_env() -> None:
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env")
        load_dotenv()


def _clean(value: Any) -> str:
    text = str(value or "").strip()
    if text.endswith(".0") and re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text


def _read_json(path: Path) -> dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}
    except Exception:
        return {}
    return {}


def _read_csv_count(path: Path) -> int:
    if not path.exists():
        return 0
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            with path.open("r", encoding=enc, newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
            if not rows:
                return 0
            return max(0, len(rows) - 1)
        except Exception:
            continue
    return 0


def _tech_dir(field: str, company: Company) -> Path:
    if company_agent_dir is not None:
        try:
            return company_agent_dir(company.slug, "tech")
        except Exception:
            pass
    return ROOT / "data" / field / company.name / "tech"


def _chair_dir(field: str, company: Company) -> Path:
    if company_agent_dir is not None:
        try:
            return company_agent_dir(company.slug, "chair")
        except Exception:
            pass
    return ROOT / "data" / field / company.name / "chair"


def _normalized_csv(tech_dir: Path, slug: str) -> Path | None:
    candidates = [
        tech_dir / f"{slug}_kipris_bibliographic_normalized.csv",
        tech_dir / f"{slug}_kipris_patents_normalized.csv",
        tech_dir / f"{slug}_tech_patent_normalized.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _target_count(tech_dir: Path, slug: str, max_patents: int) -> int:
    source = _normalized_csv(tech_dir, slug)
    if source is None:
        return 0
    total = _read_csv_count(source)
    if max_patents and max_patents > 0:
        return min(total, max_patents)
    return total


def _raw_file(tech_dir: Path, slug: str, kind: str) -> Path:
    return tech_dir / "source" / f"{slug}_kipris_plus_{kind}_raw.jsonl"


def _raw_count(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def _raw_contains_error(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace").upper()
    return any(marker in text for marker in ERROR_MARKERS)


def _backup_and_delete(path: Path, *, reason: str, dry_run: bool = False) -> str:
    if not path.exists():
        return ""
    backup = path.with_suffix(path.suffix + f".bak_{_now()}")
    msg = f"[RESET RAW] {path} -> {backup.name} / reason={reason}"
    print(msg)
    if not dry_run:
        shutil.copy2(path, backup)
        path.unlink()
    return str(backup)


def _maybe_reset_bad_raw(
    *,
    tech_dir: Path,
    slug: str,
    kind: str,
    expected_count: int,
    reset_bad_raw: bool,
    force_fetch: bool,
    dry_run: bool,
) -> None:
    path = _raw_file(tech_dir, slug, kind)
    if not path.exists():
        return

    count = _raw_count(path)
    has_error = _raw_contains_error(path)
    partial = expected_count > 0 and count < expected_count

    if force_fetch:
        _backup_and_delete(path, reason="force_fetch", dry_run=dry_run)
        return

    if reset_bad_raw and (has_error or partial):
        reason = []
        if has_error:
            reason.append("contains_kipris_error")
        if partial:
            reason.append(f"partial_raw_count_{count}_of_{expected_count}")
        _backup_and_delete(path, reason="+".join(reason), dry_run=dry_run)


def _run(
    cmd: list[str],
    *,
    env: dict[str, str],
    dry_run: bool = False,
    continue_on_error: bool = False,
) -> int:
    printable = " ".join(cmd)
    print("\n" + "-" * 90)
    print(f"[RUN] {printable}")
    print("-" * 90)

    if dry_run:
        return 0

    proc = subprocess.run(cmd, cwd=ROOT, env=env)
    if proc.returncode != 0 and not continue_on_error:
        raise PipelineError(f"Command failed with exit code {proc.returncode}: {printable}")
    return proc.returncode


def _py_cmd(script: str, *args: str) -> list[str]:
    return [sys.executable, script, *args]


def _verify_company(field: str, company: Company) -> dict[str, Any]:
    tech = _tech_dir(field, company)
    summary = _read_json(tech / "tech_chair_summary.json")
    composite = _read_json(tech / "tech_ip_evidence_composite.json")
    adjusted = _read_json(tech / "tech_to_value_bridge_ip_evidence_adjusted.json")
    legal = _read_json(tech / "tech_ip_legal_features.json")
    claim = _read_json(tech / "tech_ip_claim_features.json")
    citation = _read_json(tech / "tech_ip_citation_features.json")
    family = _read_json(tech / "tech_ip_family_features.json")

    tv = summary.get("tech_to_value", {}) or {}
    selected = summary.get("selected_ml", {}) or {}

    return {
        "company_slug": company.slug,
        "company_name": company.name,
        "tech_dir": str(tech),
        "bibliographic_rows": _target_count(tech, company.slug, 0),
        "legal_status": legal.get("status"),
        "legal_total_patents": legal.get("total_patents"),
        "claim_status": claim.get("status"),
        "claim_target_patent_count": claim.get("target_patent_count"),
        "patents_with_claims": claim.get("patents_with_claims"),
        "claim_count": claim.get("claim_count"),
        "citation_status": citation.get("status"),
        "citation_target_patent_count": citation.get("target_patent_count"),
        "family_status": family.get("status"),
        "family_target_patent_count": family.get("target_patent_count"),
        "patents_with_family": family.get("patents_with_family"),
        "family_record_count": family.get("family_record_count"),
        "ip_evidence_composite_status": composite.get("status"),
        "ip_evidence_composite_score": composite.get("ip_evidence_composite_score"),
        "ip_evidence_bridge_signal": composite.get("bridge_signal"),
        "ip_evidence_adjustment_points": composite.get("bridge_adjustment_points"),
        "summary_exists": (tech / "tech_chair_summary.json").exists(),
        "summary_ip_merge_status": summary.get("ip_evidence_composite_merge_status"),
        "summary_bridge_adjustment_status": summary.get("ip_evidence_bridge_adjustment_status"),
        "summary_selected_ml_has_composite": isinstance(selected.get("ip_evidence_composite"), dict),
        "summary_final_bridge_score_after_ip_evidence": tv.get("final_bridge_score_after_ip_evidence") or selected.get("final_bridge_score_after_ip_evidence"),
        "adjusted_bridge_packet_exists": bool(adjusted),
        "adjusted_bridge_status": adjusted.get("status"),
    }


def _write_summary(field: str, rows: list[dict[str, Any]]) -> Path:
    out_dir = ROOT / "data" / field / "_sector_common" / "tech"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "kipris_ip_full_4companies_run_summary.json"
    out_md = out_dir / "kipris_ip_full_4companies_run_summary.md"
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "companies": rows,
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# KIPRIS IP Evidence Full Pipeline - 4 Companies Summary",
        "",
        f"- created_at: {payload['created_at']}",
        "",
        "| Company | Legal | Claims | Claim Count | Citation | Family | Composite | Signal | Summary Merge | Bridge Apply |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + str(row.get("company_name"))
            + " | "
            + str(row.get("legal_status"))
            + " | "
            + str(row.get("claim_status"))
            + " | "
            + str(row.get("claim_count"))
            + " | "
            + str(row.get("citation_status"))
            + " | "
            + str(row.get("family_status"))
            + " | "
            + str(row.get("ip_evidence_composite_score"))
            + " | "
            + str(row.get("ip_evidence_bridge_signal"))
            + " | "
            + str(row.get("summary_ip_merge_status"))
            + " | "
            + str(row.get("summary_bridge_adjustment_status"))
            + " |"
        )
    lines.append("")
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[SUMMARY] {out_json}")
    print(f"[SUMMARY] {out_md}")
    return out_json


def _select_companies(only: list[str]) -> list[Company]:
    if not only:
        return TARGET_COMPANIES
    wanted = {x.strip().lower() for x in only if x.strip()}
    selected = [c for c in TARGET_COMPANIES if c.slug.lower() in wanted or c.name.lower() in wanted]
    missing = wanted - {c.slug.lower() for c in selected} - {c.name.lower() for c in selected}
    if missing:
        raise PipelineError(f"알 수 없는 회사 선택값: {', '.join(sorted(missing))}")
    return selected


def _check_env(skip_network: bool) -> None:
    if skip_network:
        return

    required_any = ["KIPRIS_PLUS_API_KEY", "KIPRIS_API_KEY", "KIPRIS_ACCESS_KEY"]
    if not any(os.getenv(k) for k in required_any):
        raise PipelineError("KIPRIS Plus API 키가 없습니다. .env에 KIPRIS_PLUS_API_KEY를 설정하세요.")

    missing = []
    if not os.getenv("KIPRIS_PLUS_CLAIMS_ENDPOINT"):
        missing.append("KIPRIS_PLUS_CLAIMS_ENDPOINT")
    if not (os.getenv("KIPRIS_PLUS_CITATION_ENDPOINT") or os.getenv("KIPRIS_CITATION_ENDPOINT")):
        missing.append("KIPRIS_PLUS_CITATION_ENDPOINT")
    if not (os.getenv("KIPRIS_PLUS_FAMILY_URL") or os.getenv("KIPRIS_FAMILY_URL")):
        missing.append("KIPRIS_PLUS_FAMILY_URL")

    if missing:
        raise PipelineError(".env에 다음 endpoint가 없습니다: " + ", ".join(missing))


def main(argv: list[str] | None = None) -> int:
    _load_env()

    parser = argparse.ArgumentParser(
        description="Run 네패스와 같은 KIPRIS IP Evidence full pipeline for 4 companies."
    )
    parser.add_argument("--field", default="반도체")
    parser.add_argument(
        "--max-patents",
        type=int,
        default=0,
        help="0이면 각 회사 normalized KIPRIS CSV의 전체 특허를 사용합니다.",
    )
    parser.add_argument("--sleep-sec", type=float, default=0.6)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--only", action="append", default=[], help="특정 회사만 실행: hanmi/hansol/duksan/ltc")
    parser.add_argument("--force-fetch", action="store_true", help="기존 KIPRIS raw를 백업 후 전체 재수집합니다.")
    parser.add_argument(
        "--reset-bad-raw",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="오류/부분 raw가 있으면 백업 후 삭제하고 재수집합니다. 기본값 true.",
    )
    parser.add_argument("--skip-network", action="store_true", help="KIPRIS Plus 네트워크 호출을 생략하고 기존 raw/features로 후속 단계만 재생성합니다.")
    parser.add_argument("--skip-tech", action="store_true", help="Tech Agent 재실행을 생략합니다.")
    parser.add_argument("--run-chair", action="store_true", help="각 회사 Chair까지 실행합니다. 기본은 Tech chair_summary까지만.")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("KIPRIS_PLUS_KEY_PARAM", "ServiceKey")
    env.setdefault("KIPRIS_PLUS_API_KEY_PARAM", "ServiceKey")
    env.setdefault("KIPRIS_PLUS_CLAIMS_KEY_PARAM", "ServiceKey")
    env.setdefault("KIPRIS_PLUS_FAMILY_KEY_PARAM", "ServiceKey")

    _check_env(args.skip_network)
    selected = _select_companies(args.only)

    print("=" * 100)
    print("[KIPRIS IP Evidence Full Pipeline - 4 Companies]")
    print("=" * 100)
    print(f"field={args.field}")
    print(f"companies={[c.slug for c in selected]}")
    print(f"max_patents={args.max_patents} (0=전체)")
    print(f"force_fetch={args.force_fetch}, reset_bad_raw={args.reset_bad_raw}, skip_network={args.skip_network}")
    print(f"run_chair={args.run_chair}")

    company_results: list[dict[str, Any]] = []

    for company in selected:
        print("\n" + "=" * 100)
        print(f"[COMPANY] {company.name} / {company.slug}")
        print("=" * 100)

        tech = _tech_dir(args.field, company)
        tech.mkdir(parents=True, exist_ok=True)
        (tech / "source").mkdir(parents=True, exist_ok=True)

        source_csv = _normalized_csv(tech, company.slug)
        if source_csv is None:
            raise PipelineError(
                f"{company.name} normalized KIPRIS CSV가 없습니다. 먼저 bibliographic normalization을 수행하세요: {tech}"
            )

        expected = _target_count(tech, company.slug, args.max_patents)
        print(f"[INPUT] source_csv={source_csv}")
        print(f"[INPUT] target_patent_count={expected}")

        for kind in ["claims", "citations", "family"]:
            _maybe_reset_bad_raw(
                tech_dir=tech,
                slug=company.slug,
                kind=kind,
                expected_count=expected,
                reset_bad_raw=args.reset_bad_raw,
                force_fetch=args.force_fetch,
                dry_run=args.dry_run,
            )

        try:
            _run(
                _py_cmd(
                    "scripts/build_kipris_tech_ml_features.py",
                    "--field",
                    args.field,
                    "--company-name",
                    company.name,
                    "--company-slug",
                    company.slug,
                ),
                env=env,
                dry_run=args.dry_run,
                continue_on_error=args.continue_on_error,
            )

            _run(
                _py_cmd(
                    "scripts/build_tech_ip_legal_features.py",
                    "--field",
                    args.field,
                    "--company-name",
                    company.name,
                    "--company-slug",
                    company.slug,
                    "--force",
                ),
                env=env,
                dry_run=args.dry_run,
                continue_on_error=args.continue_on_error,
            )

            if not args.skip_network:
                common_net_args = [
                    "--field",
                    args.field,
                    "--company-name",
                    company.name,
                    "--company-slug",
                    company.slug,
                    "--max-patents",
                    str(args.max_patents),
                    "--sleep-sec",
                    str(args.sleep_sec),
                    "--timeout",
                    str(args.timeout),
                ]

                _run(
                    _py_cmd(
                        "scripts/fetch_kipris_plus_claims.py",
                        *common_net_args,
                        "--key-param",
                        "ServiceKey",
                        "--app-param",
                        "applicationNumber",
                        *( ["--force"] if args.force_fetch else [] ),
                    ),
                    env=env,
                    dry_run=args.dry_run,
                    continue_on_error=args.continue_on_error,
                )

                _run(
                    _py_cmd(
                        "scripts/fetch_kipris_plus_citations.py",
                        *common_net_args,
                        *( ["--force"] if args.force_fetch else [] ),
                    ),
                    env=env,
                    dry_run=args.dry_run,
                    continue_on_error=args.continue_on_error,
                )

                _run(
                    _py_cmd(
                        "scripts/fetch_kipris_plus_family.py",
                        *common_net_args,
                        "--key-param",
                        "ServiceKey",
                        "--app-param",
                        "applicationNumber",
                        *( ["--force"] if args.force_fetch else [] ),
                    ),
                    env=env,
                    dry_run=args.dry_run,
                    continue_on_error=args.continue_on_error,
                )

            _run(
                _py_cmd(
                    "scripts/build_tech_ip_evidence_composite.py",
                    "--field",
                    args.field,
                    "--company-name",
                    company.name,
                    "--company-slug",
                    company.slug,
                ),
                env=env,
                dry_run=args.dry_run,
                continue_on_error=args.continue_on_error,
            )

            if not args.skip_tech:
                _run(
                    _py_cmd(
                        "main.py",
                        "tech",
                        "--company-dir",
                        company.slug,
                        "--company",
                        company.name,
                    ),
                    env=env,
                    dry_run=args.dry_run,
                    continue_on_error=args.continue_on_error,
                )

            _run(
                _py_cmd(
                    "scripts/check_ip_evidence_bridge_one.py",
                    "--tech",
                    str(tech),
                    "--slug",
                    company.slug,
                    "--company-name",
                    company.name,
                ),
                env=env,
                dry_run=args.dry_run,
                continue_on_error=True,
            )

            if args.run_chair:
                chair = _chair_dir(args.field, company)
                chair.mkdir(parents=True, exist_ok=True)
                _run(
                    _py_cmd(
                        "main.py",
                        "chair",
                        "--company-dir",
                        company.slug,
                        "--company",
                        company.name,
                    ),
                    env=env,
                    dry_run=args.dry_run,
                    continue_on_error=args.continue_on_error,
                )

            company_results.append(_verify_company(args.field, company))

        except Exception as exc:
            print(f"[COMPANY ERROR] {company.name} / {company.slug}: {exc}")
            company_results.append(
                {
                    "company_slug": company.slug,
                    "company_name": company.name,
                    "error": repr(exc),
                    **_verify_company(args.field, company),
                }
            )
            if not args.continue_on_error:
                _write_summary(args.field, company_results)
                raise

        time.sleep(0.2)

    print("\n" + "=" * 100)
    print("[OPTIONAL] Tech/IP Strength + Tech ML Signal 전체 재계산")
    print("=" * 100)
    _run(
        _py_cmd("scripts/run_tech_ip_ml.py", "--all"),
        env=env,
        dry_run=args.dry_run,
        continue_on_error=True,
    )
    _run(
        _py_cmd("scripts/run_tech_ml_signal.py", "--all"),
        env=env,
        dry_run=args.dry_run,
        continue_on_error=True,
    )

    summary_path = _write_summary(args.field, company_results)

    print("\n" + "=" * 100)
    print("[ALL DONE]")
    print("=" * 100)
    print(f"summary={summary_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PipelineError as exc:
        print(f"[PIPELINE ERROR] {exc}")
        raise SystemExit(1)
