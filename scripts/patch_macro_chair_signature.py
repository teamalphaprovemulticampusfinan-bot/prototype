from pathlib import Path
import re

targets = []

for path in Path("src").rglob("*.py"):
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8-sig")
    except Exception:
        continue

    if "def run_macro_for_chair" in text:
        targets.append(path)

if not targets:
    raise SystemExit("[ERROR] def run_macro_for_chair 를 찾지 못했습니다.")

changed = []

pattern = re.compile(
    r"def\s+run_macro_for_chair\s*\(\s*(?P<params>[^,\)]*?)\s*\)(?P<ret>\s*->\s*[^:]+)?\s*:",
    flags=re.MULTILINE,
)

for path in targets:
    text = path.read_text(encoding="utf-8")
    backup = path.with_suffix(path.suffix + ".bak_macro_chair_signature")
    backup.write_text(text, encoding="utf-8")

    def repl(m):
        params = m.group("params").strip()
        ret = m.group("ret") or ""

        # 이미 2개 이상 인자를 받는 경우는 건드리지 않음
        if "," in params:
            return m.group(0)

        return f"def run_macro_for_chair({params}, _chair_company_name: str | None = None){ret}:"

    new_text, n = pattern.subn(repl, text, count=1)

    if n > 0 and new_text != text:
        path.write_text(new_text, encoding="utf-8")
        changed.append(str(path))

print("[DONE] patched files:")
for p in changed:
    print("-", p)

if not changed:
    print("[SKIP] run_macro_for_chair already accepts multiple args or pattern did not need change.")
