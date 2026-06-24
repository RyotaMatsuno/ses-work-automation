import os
import time

time.sleep(60)
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\codex_sales_pipeline.log"
if os.path.exists(log_path):
    with open(log_path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print(f"LOG_LINES:{len(lines)}", flush=True)
    for l in lines[-20:]:
        print(l, end="", flush=True)
else:
    print("NO_LOG", flush=True)
