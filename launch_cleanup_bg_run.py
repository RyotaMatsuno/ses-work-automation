import datetime
import os
import subprocess

ses_work = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
log_path = os.path.join(ses_work, "cleanup_v2_bg_run.log")

with open(log_path, "w", encoding="utf-8") as log_file:
    proc = subprocess.Popen(
        ["python", "cleanup_v2.py"],
        cwd=ses_work,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=0x00000008,
    )

print(f"PID: {proc.pid}")
print(f"Log: {log_path}")
print(f"Started at: {datetime.datetime.now()}")
