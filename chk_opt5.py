import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
time.sleep(90)
log_path = r"C:\Users\ma_py\OneDrive\Desktop\ses_work\codex_pipeline_opt.log"
size = os.path.getsize(log_path)
print(f"サイズ: {size} bytes")
lines = open(log_path, encoding="utf-8", errors="replace").readlines()
print(f"行数: {len(lines)}")
print("".join(lines[-25:]))
