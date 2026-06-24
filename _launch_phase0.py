import subprocess
import sys

cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3"
cmd = [
    sys.executable,
    "matching_v3.py",
    "--dry-run",
    "--input",
    r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_emails.jsonl",
]

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_run_fresh.log"

with open(log_path, "w", encoding="utf-8") as logf:
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=logf,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    )

print(f"launched PID={proc.pid}")
print(f"log: {log_path}")
