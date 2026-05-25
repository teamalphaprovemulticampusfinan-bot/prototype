from pathlib import Path
import shutil

target = Path("src/common/company_metadata.py")

if not target.exists():
    target.parent.mkdir(parents=True, exist_ok=True)
else:
    backup = target.with_suffix(".py.bak_bad_v8")
    if not backup.exists():
        shutil.copy2(target, backup)

source = Path(__file__).resolve().parents[1] / "src" / "common" / "company_metadata.py"

if source.resolve() == target.resolve():
    print("[OK] source and target are the same file; no copy needed.")
else:
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"[OK] repaired: {target}")

print("Next:")
print(r"  $env:PYTHONPATH=(Resolve-Path .\src).Path")
print(r"  python -m py_compile .\src\common\company_metadata.py")
print(r"""  python -c "from common.company_metadata import get_company_metadata; print(get_company_metadata('dbhitek', 'DB하이텍'))" """)
