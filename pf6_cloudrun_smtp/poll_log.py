import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pf6_cloudrun_smtp\codex.log")
time.sleep(60)
size = log.stat().st_size if log.exists() else 0
lines = log.read_text(encoding="utf-8", errors="replace").splitlines() if log.exists() else []
print(f"log: {size} bytes / {len(lines)} lines")
for l in lines[-30:]:
    print(l)
