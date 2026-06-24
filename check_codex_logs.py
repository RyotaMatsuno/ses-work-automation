import os
import time

time.sleep(30)

for logfile in [
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\pipeline_v1_run.log",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\outreach_system_run.log",
]:
    print(f"\n=== {os.path.basename(logfile)} ===")
    try:
        with open(logfile, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        print(content[-2000:] if len(content) > 2000 else content or "(empty)")
    except Exception as e:
        print(f"ERROR: {e}")
