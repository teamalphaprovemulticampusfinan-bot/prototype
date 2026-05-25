# src/market_agent/github_uploader.py
from __future__ import annotations
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


GITHUB_REPO_PATH = str(Path(__file__).resolve().parents[2])  # team-a 루트
DATA_FOLDER      = "data/market_excel"


def upload_to_github(file_path: str, commit_message: str | None = None) -> bool:
    if not (Path(GITHUB_REPO_PATH) / ".git").exists():
        print("  [GitHub] git repository 아님 → 업로드 건너뜀")
        return True

    src      = Path(file_path)
    dest_dir = Path(GITHUB_REPO_PATH) / DATA_FOLDER
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest = dest_dir / src.name
    shutil.copy(src, dest)
    print(f"  [GitHub] 파일 복사: {dest}")

    msg = commit_message or (
        f"Auto update: {src.name} ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
    )

    cmds = [
        ["git", "-C", GITHUB_REPO_PATH, "add", str(dest)],
        ["git", "-C", GITHUB_REPO_PATH, "commit", "-m", msg],
        ["git", "-C", GITHUB_REPO_PATH, "push"],
    ]

    for cmd in cmds:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # 변경사항 없으면 commit이 실패하는 건 정상
            if "nothing to commit" in result.stdout + result.stderr:
                print(f"  [GitHub] 변경사항 없음 → push 건너뜀")
                return True
            print(f"  [GitHub] ❌ 오류: {result.stderr.strip()}")
            return False
        print(f"  [GitHub] ✅ {' '.join(cmd[3:5])}")

    print(f"  [GitHub] 🎉 업로드 완료: {DATA_FOLDER}/{src.name}")
    return True
