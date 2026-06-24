import os
import sys

os.environ["SKIP_NOTION_FETCH"] = "1"

# matching_v2ディレクトリに移動してnotify_line.pyをdry-runで実行
import subprocess

result = subprocess.run(
    [sys.executable, "matching_v2/notify_line.py", "--dry-run"],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    capture_output=True,
    text=True,
    timeout=25,
    env={**os.environ, "SKIP_NOTION_FETCH": "1"},
)
print("STDOUT:", result.stdout[:2000])
print("STDERR:", result.stderr[:500])
print("RC:", result.returncode)
