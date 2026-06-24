import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
time.sleep(90)

LOG = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\codex_detail_run.log"
size = os.path.getsize(LOG) if os.path.exists(LOG) else 0
print(f"ログサイズ: {size} bytes", flush=True)

bak = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py.bak_0602"
print(f"bak_0602: {'OK' if os.path.exists(bak) else '未作成'}", flush=True)

with open(LOG, encoding="utf-8", errors="replace") as f:
    content = f.read()
lines = content.splitlines()
print(f"ログ行数: {len(lines)}", flush=True)
print("--- 末尾30行 ---", flush=True)
for line in lines[-30:]:
    print(line, flush=True)
