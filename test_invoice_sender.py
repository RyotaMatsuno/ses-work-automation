import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
r = subprocess.run(
    ["python", r"freee\invoice_sender.py", "--dry-run"],
    capture_output=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    timeout=30,
)
print(r.stdout.decode("utf-8", errors="replace"))
print("STDERR:", r.stderr.decode("utf-8", errors="replace")[:300])
print("RC:", r.returncode)
