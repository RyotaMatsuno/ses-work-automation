import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

result = subprocess.run(
    ["python", "outreach_system/collect_targets.py", "--dry-run"],
    capture_output=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    timeout=120,
)
out = result.stdout.decode("utf-8", errors="replace")
err = result.stderr.decode("utf-8", errors="replace")
print("STDOUT:", out[:2000])
if err:
    print("STDERR:", err[:500])
print("RC:", result.returncode)
