import os
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "matching_v2/notify_line.py", "--dry-run"],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    timeout=25,
    env={**os.environ, "SKIP_NOTION_FETCH": "1", "PYTHONIOENCODING": "utf-8"},
)
print("STDOUT:", result.stdout[:3000])
if result.stderr:
    print("STDERR:", result.stderr[:500])
print("RC:", result.returncode)
