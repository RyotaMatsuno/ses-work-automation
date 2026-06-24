import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ses_work = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
mp = ses_work / "mail_pipeline" / "mail_pipeline.py"

with open(mp, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

# L1290〜1370 周辺を確認（新規処理対象カウント周辺）
print("=== L1280〜1400 ===")
for i, l in enumerate(lines[1279:1399], start=1280):
    print(f"L{i}: {l.rstrip()}")
