import subprocess
import sys

script = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\matching_v3.py"
input_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_emails.jsonl"
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_fresh_run.log"

with open(log_path, "w", encoding="utf-8") as log_f:
    proc = subprocess.Popen(
        [sys.executable, script, "--dry-run", "--input", input_path],
        stdout=log_f,
        stderr=subprocess.STDOUT,
        cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3",
    )
print(f"Started PID={proc.pid}, log={log_path}")
