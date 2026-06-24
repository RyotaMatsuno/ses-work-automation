import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pf5_cloudrun\deploy.log")
print("120秒待機中...", flush=True)
time.sleep(120)
size = log.stat().st_size if log.exists() else 0
print(f"log size: {size} bytes")
lines = log.read_text(encoding="utf-8", errors="replace").splitlines() if log.exists() else []
print(f"lines: {len(lines)}")
for l in lines[-40:]:
    print(l)
