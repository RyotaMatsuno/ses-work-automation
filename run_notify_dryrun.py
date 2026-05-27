
import subprocess, sys

result = subprocess.run(
    [sys.executable, "matching_v2/notify_line.py", "--dry-run"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    timeout=60
)
print("STDOUT:", result.stdout[:3000])
print("STDERR:", result.stderr[:500])
print("RC:", result.returncode)
