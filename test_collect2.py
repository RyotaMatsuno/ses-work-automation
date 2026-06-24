import subprocess
import sys

result = subprocess.run(
    [sys.executable, "outreach_system/collect_targets.py", "--help"],
    capture_output=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    timeout=30,
)
out = result.stdout.decode("utf-8", errors="replace")
err = result.stderr.decode("utf-8", errors="replace")

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\collect_help.txt", "w", encoding="utf-8") as f:
    f.write(out + "\n" + err)
print("rc:", result.returncode)
print("size:", len(out), len(err))
