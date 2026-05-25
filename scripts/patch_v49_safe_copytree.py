from pathlib import Path
import re

path = Path(r".\src_eval\evaluation\pipeline_executor.py")
text = path.read_text(encoding="utf-8")

pattern = re.compile(
    r"def _safe_copytree\(src: Path, dst: Path\) -> None:\n"
    r".*?"
    r"(?=\ndef\s+_|\nclass\s+|\Z)",
    re.DOTALL,
)

replacement = r'''def _safe_copytree(src: Path, dst: Path) -> None:
    """Best-effort copy for eval history snapshots.

    The real pipeline may leave stale reference-schema files or generated files
    that disappear while the history snapshot is being copied. Snapshot failure
    must not abort the whole backtest because agent/auditor/chair outputs have
    already been produced. Missing, unreadable, or path-problem files are skipped.
    """
    src = Path(src)
    dst = Path(dst)

    if not src.exists():
        return

    dst.mkdir(parents=True, exist_ok=True)

    for item in src.rglob("*"):
        try:
            rel = item.relative_to(src)
            target = dst / rel

            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            if not item.is_file():
                continue

            target.parent.mkdir(parents=True, exist_ok=True)

            try:
                shutil.copy2(item, target)
            except FileNotFoundError:
                print(f"[snapshot-copy-warning] skipped missing file: {item}")
                continue
            except OSError as exc:
                print(f"[snapshot-copy-warning] skipped file: {item} -> {target} ({exc})")
                continue

        except FileNotFoundError:
            print(f"[snapshot-copy-warning] skipped vanished path: {item}")
            continue
        except OSError as exc:
            print(f"[snapshot-copy-warning] skipped path: {item} ({exc})")
            continue

'''

if not pattern.search(text):
    raise SystemExit("Could not find _safe_copytree function in pipeline_executor.py")

text2 = pattern.sub(replacement, text, count=1)
path.write_text(text2, encoding="utf-8")
print("[OK] patched _safe_copytree in", path)
