import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import subprocess
import os

SES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
script = os.path.join(SES, "research_results", "close_senkou_v2.py")
log = os.path.join(SES, "research_results", "close_senkou.log")

env = os.environ.copy()
env["PYTHONUNBUFFERED"] = "1"

proc = subprocess.Popen(
    ["python", script],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    cwd=SES,
    env=env
)
print(f"PID={proc.pid} started. Logging to close_senkou.log")
