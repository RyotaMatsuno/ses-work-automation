import subprocess
import sys
import os

# バックグラウンドで cleanup_v2.py を起動し、ログをファイルに書き出す
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_v2_bg.log"
script_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\cleanup_v2.py"
cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

with open(log_path, "w", encoding="utf-8") as log_f:
    proc = subprocess.Popen(
        [sys.executable, script_path],
        cwd=cwd,
        stdout=log_f,
        stderr=log_f,
        creationflags=subprocess.CREATE_NO_WINDOW
    )

print(f"Started PID={proc.pid}")
print(f"Log: {log_path}")
