from pathlib import Path

path = Path("src/tech_agent/chair_section.py")
text = path.read_text(encoding="utf-8")

backup = path.with_suffix(".py.bak_dynamic_ip_evidence_sentence")
backup.write_text(text, encoding="utf-8")

old = '''    lines.append("- 다만 Chair 보고서에서는 기존 Base Bridge Score 72.00이 아니라, Peer ML 및 IP Evidence 반영 후 최종 점수 80.53을 기술 종합 판단에 우선 반영해야 합니다.")'''

new = '''    base_score = tv.get("base_bridge_score") or tv.get("score")
    lines.append(
        "- Chair 보고서에서는 기존 Base Bridge Score "
        f"{_ipev_chair_fmt_score(base_score)}와 별도로, "
        "Peer ML 및 IP Evidence 반영 후 최종 점수 "
        f"{_ipev_chair_fmt_score(final_score)}를 기술 종합 판단에 우선 반영해야 합니다."
    )'''

if old not in text:
    raise SystemExit("[ERROR] hard-coded sentence not found. 이미 수정됐거나 문장이 다릅니다.")

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("[DONE] chair_section.py hard-coded IP Evidence sentence fixed")
print(f"[BACKUP] {backup}")
