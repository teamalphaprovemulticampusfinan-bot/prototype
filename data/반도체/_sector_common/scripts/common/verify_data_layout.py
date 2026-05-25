from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIELD = "반도체"
COMPANIES = {
    "nepes": "네패스",
    "hanmi": "한미반도체",
    "hansol": "한솔케미칼",
    "duksan": "덕산테코피아",
    "ltc": "엘티씨",
}
AGENTS = ["finance", "market", "issue", "macro", "tech", "chair", "auditor"]


def check(path: Path, *, allow_empty_file: bool = False) -> tuple[bool, str]:
    if not path.exists():
        return False, "MISSING"
    if path.is_file() and not allow_empty_file and path.stat().st_size == 0:
        return False, "EMPTY"
    return True, "OK"


def main() -> int:
    checks: list[tuple[str, Path, bool]] = [
        ("global warning csv", DATA / "common" / "투자경고종목.csv", False),
        ("issue workbook", DATA / FIELD / "common" / "data" / "Issue_Integration.xlsx", False),
        ("market workbook", DATA / FIELD / "common" / "data" / "Market_통합.xlsx", False),
        ("tech template", DATA / FIELD / "common" / "templates" / "tech_template.xlsx", False),
        ("tech template base", DATA / FIELD / "common" / "templates" / "tech_template_base.xlsx", False),
        ("ml universe", DATA / FIELD / "common" / "ml_universe" / "deeptech_reference_universe.csv", False),
    ]
    for slug, name in COMPANIES.items():
        base = DATA / FIELD / name
        checks += [
            (f"{name} company.yaml", base / "common" / "company.yaml", False),
            (f"{name} finance csv", base / "finance" / f"{name}_재무.csv", False),
            (f"{name} stock csv", base / "market" / f"{name}_주식.csv", False),
            (f"{name} tech source dir", base / "tech" / "source", True),
        ]
        for agent in AGENTS:
            checks.append((f"{name} {agent} dir", base / agent, True))
    failed = []
    for label, path, allow_empty in checks:
        passed, status = check(path, allow_empty_file=allow_empty)
        print(f"[{status:7}] {label}: {path.relative_to(ROOT)}")
        if not passed:
            failed.append((label, path, status))
    if failed:
        print(f"\n[FAIL] missing/empty required items: {len(failed)}")
        return 1
    print("\n[PASS] data layout is ready.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
