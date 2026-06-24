import glob
import os
import time

time.sleep(120)

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\logs\skill_autofill_codex.log"
print(f"=== log ({os.path.getsize(log_path)} bytes) ===")
with open(log_path, "r", encoding="utf-8", errors="replace") as f:
    print(f.read()[-1000:])

print("\n=== pipeline_v1/ .py files ===")
for f in glob.glob(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\pipeline_v1\*.py"):
    print(os.path.basename(f))
