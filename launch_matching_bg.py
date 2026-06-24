import datetime
import os
import subprocess

ses_work = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
log_path = os.path.join(ses_work, "matching_v2_run.log")

with open(log_path, "w", encoding="utf-8") as log_file:
    proc = subprocess.Popen(
        ["python", "matching_v2/matching_v2.py"],
        cwd=ses_work,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=0x00000008,  # CREATE_NO_WINDOW
    )

print(f"PID: {proc.pid}")
print(f"Log: {log_path}")
print(f"Started at: {datetime.datetime.now()}")
