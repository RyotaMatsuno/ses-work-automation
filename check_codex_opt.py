import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
time.sleep(120)
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\codex_pipeline_opt.log"
size = os.path.getsize(log_path)
print(f"ログサイズ: {size} bytes")
lines = open(log_path, encoding="utf-8", errors="replace").readlines()
print(f"行数: {len(lines)}")
print("--- 末尾30行 ---")
print("".join(lines[-30:]))
