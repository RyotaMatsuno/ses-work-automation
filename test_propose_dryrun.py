import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
env = os.environ.copy()
env["DRY_RUN"] = "1"
env["PYTHONIOENCODING"] = "utf-8"

result = subprocess.run(
    ["python", "propose_pipeline/propose.py"],
    cwd=cwd,
    env=env,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=60,
)
# 最初の50行だけ出力
lines = result.stdout.splitlines()
print(f"総行数: {len(lines)}")
print("--- 先頭30行 ---")
for l in lines[:30]:
    print(l)
print("--- 末尾10行 ---")
for l in lines[-10:]:
    print(l)
if result.stderr:
    print(f"STDERR: {result.stderr[:500]}")
print(f"returncode: {result.returncode}")
