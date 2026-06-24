import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_v2.log")
if not log.exists():
    print("ログファイル未生成")
else:
    content = log.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    print(f"行数: {len(lines)}")
    for l in lines[-15:]:
        print(l)
