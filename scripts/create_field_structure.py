from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AGENTS = ["finance", "market", "issue", "macro", "tech", "chair", "auditor"]

def create_field(field):
    base = DATA / field / "_sector_common"
    for p in [DATA / "_global_common", DATA / "_global_common" / "macro", base / "data", base / "templates", base / "ml_universe"]:
        p.mkdir(parents=True, exist_ok=True)

def create_company(field, raw):
    parts = [x.strip() for x in raw.split(":")]
    slug = parts[0]
    name = parts[1] if len(parts) > 1 else slug
    ticker = parts[2] if len(parts) > 2 else ""
    market = parts[3] if len(parts) > 3 else ""

    root = DATA / field / name
    common = root / "_company_common"
    common.mkdir(parents=True, exist_ok=True)

    for a in AGENTS:
        (root / a).mkdir(parents=True, exist_ok=True)
    (root / "tech" / "source").mkdir(parents=True, exist_ok=True)

    yml = common / "company.yaml"
    if not yml.exists():
        yml.write_text(
            f'slug: "{slug}"\n'
            f'corp_name: "{name}"\n'
            f'display_name: "{name}"\n'
            f'field: "{field}"\n'
            f'stock_code: "{ticker}"\n'
            f'market: "{market}"\n',
            encoding="utf-8",
        )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--field", required=True)
    ap.add_argument("--company", action="append", default=[])
    args = ap.parse_args()

    create_field(args.field)
    for c in args.company:
        create_company(args.field, c)

    print("[OK] created")
    print("global : data/_global_common")
    print("sector : data/<field>/_sector_common")
    print("company: data/<field>/<company>/_company_common")

if __name__ == "__main__":
    main()
