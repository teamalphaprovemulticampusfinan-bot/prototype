from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
COMPANIES = ["네패스", "한미반도체", "한솔케미칼", "덕산테코피아", "엘티씨"]
AGENTS = ["finance", "market", "issue", "macro", "tech", "chair", "auditor"]

def check(label, path):
    ok = path.exists() and (path.is_dir() or path.stat().st_size > 0)
    print(f"[{'OK' if ok else 'MISSING':<7}] {label}: {path.relative_to(ROOT)}")
    return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", default="반도체")
    ap.add_argument("--create", action="store_true")
    args = ap.parse_args()

    g = DATA / "_global_common"
    s = DATA / args.field / "_sector_common"

    if args.create:
        for p in [g, g / "macro", s / "data", s / "templates", s / "ml_universe"]:
            p.mkdir(parents=True, exist_ok=True)

    results = [
        check("global common dir", g),
        check("global macro dir", g / "macro"),
        check("global warning csv", g / "투자경고종목.csv"),
        check("sector common dir", s),
        check("issue workbook", s / "data" / "Issue_Integration.xlsx"),
        check("market workbook", s / "data" / "Market_통합.xlsx"),
        check("tech template", s / "templates" / "tech_template.xlsx"),
        check("tech template base", s / "templates" / "tech_template_base.xlsx"),
        check("ml universe", s / "ml_universe" / "deeptech_reference_universe.csv"),
    ]

    for c in COMPANIES:
        root = DATA / args.field / c
        results.append(check(f"{c} company.yaml", root / "_company_common" / "company.yaml"))
        for a in AGENTS:
            results.append(check(f"{c} {a} dir", root / a))
        results.append(check(f"{c} tech source dir", root / "tech" / "source"))

    print("")
    if all(results):
        print("[PASS] data layout is ready.")
        print("[layout] data/_global_common, data/<field>/_sector_common, data/<field>/<company>/_company_common")
    else:
        print(f"[FAIL] missing/empty required items: {sum(1 for x in results if not x)}")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
