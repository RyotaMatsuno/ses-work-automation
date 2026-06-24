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
with open("dry_run_result.txt", "w", encoding="utf-8") as f:
    f.write(f"RC: {result.returncode}\n")
    f.write(f"STDOUT:\n{result.stdout}\n")
    f.write(f"STDERR:\n{result.stderr}\n")
print(f"RC={result.returncode}, written to dry_run_result.txt")
