import subprocess, sys

proc = subprocess.Popen(
    [sys.executable, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_v2.py"],
    stdout=open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_v2.log", "w", encoding="utf-8"),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
)
print(f"PID: {proc.pid}")
