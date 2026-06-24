import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\matching_v3_20260612.log")
with open(log, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
print(f"総行数: {len(lines)}")
print("--- 全内容（最大200行）---")
for l in lines[:200]:
    print(l.rstrip())
if len(lines) > 200:
    print(f"... 残り {len(lines) - 200} 行省略 ...")
    print("--- 末尾20行 ---")
    for l in lines[-20:]:
        print(l.rstrip())
