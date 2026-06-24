import os
import subprocess
import sys

env = {**os.environ, "SKIP_NOTION_FETCH": "1"}
r = subprocess.run(
    ["python", "matching_v2/notify_line.py", "--dry-run"],
    env=env,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    capture_output=True,
)
sys.stdout.buffer.write(r.stdout)
sys.stdout.buffer.write(r.stderr)
