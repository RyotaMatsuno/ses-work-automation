import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
print("待機中...", flush=True)
time.sleep(60)
print("60秒経過", flush=True)

LOG = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_integration\codex_run.log"
size = os.path.getsize(LOG) if os.path.exists(LOG) else 0
print(f"ログサイズ: {size} bytes", flush=True)

if size > 0:
    with open(LOG, encoding="utf-8", errors="replace") as f:
        content = f.read()
    # 末尾20行
    lines = content.splitlines()
    print("--- ログ末尾 ---", flush=True)
    for line in lines[-20:]:
        print(line, flush=True)
