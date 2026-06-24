import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
time.sleep(120)

LOG = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_integration\codex_run.log"
size = os.path.getsize(LOG) if os.path.exists(LOG) else 0
print(f"ログサイズ: {size} bytes", flush=True)

BASE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
files_to_check = [
    "drive_uploader.py",
    "config/send_counter.json",
    "pipeline_integration/TASKS.md",
    "mail_pipeline/mail_pipeline.py.bak_0602",
    "matching_v2/notify_line.py.bak_0602",
    "line_webhook/webhook_server.py.bak_0602",
]
for f in files_to_check:
    full = os.path.join(BASE, f)
    exists = os.path.exists(full)
    sz = os.path.getsize(full) if exists else 0
    print(f"{f}: {'OK' if exists else '未作成'} ({sz}bytes)", flush=True)

with open(LOG, encoding="utf-8", errors="replace") as f:
    content = f.read()
lines = content.splitlines()
print(f"ログ総行数: {len(lines)}", flush=True)
print("--- ログ末尾30行 ---", flush=True)
for line in lines[-30:]:
    print(line, flush=True)
