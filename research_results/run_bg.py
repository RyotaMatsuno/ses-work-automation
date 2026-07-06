import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import subprocess
import os

SES = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
script = os.path.join(SES, "research_results", "close_senkou.py")
log = os.path.join(SES, "research_results", "close_senkou.log")

proc = subprocess.Popen(
    ["python", script],
    stdout=open(log, 'w', encoding='utf-8'),
    stderr=subprocess.STDOUT,
    cwd=SES
)
print(f"Started PID={proc.pid}")
print(f"Log: {log}")
