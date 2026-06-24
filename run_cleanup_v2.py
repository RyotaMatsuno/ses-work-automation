import subprocess
import sys

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_v2.log"
script = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_v2.py"

with open(log_path, "w", encoding="utf-8") as f:
    proc = subprocess.Popen(
        [sys.executable, "-u", script],  # -u = unbuffered
        stdout=f,
        stderr=subprocess.STDOUT,
        cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    )
print(f"起動 PID={proc.pid}", flush=True)
