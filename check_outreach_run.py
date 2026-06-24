import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

result = subprocess.run(
    ["python", "outreach_system/outreach.py", "--dry-run"],
    cwd=cwd,
    env=env,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=30,
)
print(f"returncode: {result.returncode}")
print("STDOUT:", result.stdout[:1000])
if result.stderr:
    print("STDERR:", result.stderr[:500])
