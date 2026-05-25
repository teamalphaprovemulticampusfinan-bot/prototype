from pathlib import Path

p = Path(r".\src\data_intake\tech_intake\value_evidence_bridge.py")
text = p.read_text(encoding="utf-8")

new_line = r'HANGUL_SENTENCE_SPLIT_RE = re.compile(r"\n+|(?<=[.!?。])\s+|(?<=다\.)\s+|(?<=요\.)\s+|(?<=음\.)\s+|(?<=임\.)\s+")'

lines = text.splitlines()
changed = False

for i, line in enumerate(lines):
    if line.strip().startswith("HANGUL_SENTENCE_SPLIT_RE = re.compile("):
        lines[i] = new_line
        changed = True
        break

if not changed:
    raise RuntimeError("HANGUL_SENTENCE_SPLIT_RE 라인을 찾지 못했습니다.")

p.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("[OK] regex fixed:", p)
