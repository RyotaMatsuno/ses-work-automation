import os
import py_compile
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"

# 構文チェック
try:
    py_compile.compile(cwd + r"\propose_pipeline\propose.py", doraise=True)
    print("構文チェック: OK")
except Exception as e:
    print(f"構文エラー: {e}")
    sys.exit(1)

# DRY_RUN 先頭5行確認
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
lines = result.stdout.splitlines()
print(f"DRY_RUN 総行数: {len(lines)}, returncode: {result.returncode}")
for l in lines[:5]:
    print(l)
if result.stderr:
    print("STDERR:", result.stderr[:200])
