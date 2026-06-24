import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

LOG = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_integration\codex_run.log"
size = os.path.getsize(LOG) if os.path.exists(LOG) else 0
print(f"ログサイズ: {size} bytes", flush=True)

with open(LOG, encoding="utf-8", errors="replace") as f:
    content = f.read()
lines = content.splitlines()
print(f"ログ総行数: {len(lines)}", flush=True)
print("--- 末尾40行 ---", flush=True)
for line in lines[-40:]:
    print(line, flush=True)
