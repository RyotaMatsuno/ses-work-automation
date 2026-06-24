import subprocess
import sys

result = subprocess.run(
    [sys.executable, "outreach_system/collect_targets.py", "--dry-run"],
    capture_output=True,
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    timeout=120,
)
out = result.stdout.decode("utf-8", errors="replace")
err = result.stderr.decode("utf-8", errors="replace")

with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\collect_dryrun.txt", "w", encoding="utf-8") as f:
    f.write(f"RC: {result.returncode}\n\n=== STDOUT ===\n{out}\n=== STDERR ===\n{err}")
print("RC:", result.returncode, "stdout_len:", len(out))
