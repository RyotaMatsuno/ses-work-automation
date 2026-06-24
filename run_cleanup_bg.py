import subprocess
import sys

proc = subprocess.Popen(
    [sys.executable, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_engineer_db.py"],
    stdout=open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup.log", "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
)
print(f"起動 PID={proc.pid}")
