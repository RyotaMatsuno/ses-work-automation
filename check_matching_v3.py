import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

v3 = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3")
print("--- matching_v3/ ファイル一覧 ---")
for f in sorted(v3.iterdir()):
    if f.is_file():
        print(f"  {f.name}  ({f.stat().st_size:,}b)")

# TASKS.mdを読む
tasks = v3 / "TASKS.md"
if tasks.exists():
    print("\n--- TASKS.md ---")
    print(tasks.read_text(encoding="utf-8", errors="replace"))
