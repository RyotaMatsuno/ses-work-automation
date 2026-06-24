import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
time.sleep(90)
print("90秒経過", flush=True)

LOG = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_integration\codex_run.log"
size = os.path.getsize(LOG) if os.path.exists(LOG) else 0
print(f"ログサイズ: {size} bytes", flush=True)

# 作成ファイル確認
files_to_check = [
    r"ses_work\drive_uploader.py",
    r"ses_work\config\send_counter.json",
]
BASE = r"C:\Users\ma_py\OneDrive\デスクトップ"
for f in files_to_check:
    full = os.path.join(BASE, f)
    exists = os.path.exists(full)
    size_f = os.path.getsize(full) if exists else 0
    print(f"{f}: {'OK' if exists else '未作成'} ({size_f}bytes)", flush=True)

# ログ末尾
with open(LOG, encoding="utf-8", errors="replace") as f:
    content = f.read()
lines = content.splitlines()
print("--- ログ末尾 ---", flush=True)
for line in lines[-25:]:
    print(line, flush=True)
