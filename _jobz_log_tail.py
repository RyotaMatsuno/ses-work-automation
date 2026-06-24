import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\pipeline.log")
with open(log, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
print(f"総行数: {len(lines)}")
print("--- 末尾30行 ---")
for l in lines[-30:]:
    print(l.rstrip())
