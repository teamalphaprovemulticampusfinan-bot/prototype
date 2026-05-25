from pathlib import Path

path = Path(r".\src\chair_agent\adapters.py")
text = path.read_text(encoding="utf-8")

if "import re" not in text:
    text = text.replace("import os\n", "import os\nimport re\n", 1)

path.write_text(text, encoding="utf-8")
print("[OK] import re added.")
