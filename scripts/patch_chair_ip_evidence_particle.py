from pathlib import Path

path = Path("src/tech_agent/chair_section.py")
text = path.read_text(encoding="utf-8")

backup = path.with_suffix(".py.bak_particle_fix")
backup.write_text(text, encoding="utf-8")

text = text.replace(
    'Base Bridge Score "',
    'Base Bridge Score "'
)

text = text.replace(
    'f"{_ipev_chair_fmt_score(base_score)}와 별도로, "',
    'f"{_ipev_chair_fmt_score(base_score)}과 별도로, "'
)

text = text.replace(
    'f"{_ipev_chair_fmt_score(final_score)}를 기술 종합 판단에 우선 반영해야 합니다."',
    'f"{_ipev_chair_fmt_score(final_score)}을 기술 종합 판단에 우선 반영해야 합니다."'
)

path.write_text(text, encoding="utf-8")

print("[DONE] Korean particle fixed in chair_section.py")
print(f"[BACKUP] {backup}")
