
import subprocess, sys, os

result = subprocess.run(
    [sys.executable, "outreach_system/collect_targets.py", "--help"],
    capture_output=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    timeout=30
)
out = result.stdout.decode("utf-8", errors="replace")
err = result.stderr.decode("utf-8", errors="replace")
print(out)
print(err)
