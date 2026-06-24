import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

cwd = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3"
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"

# pytestで全テスト
result = subprocess.run(
    ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
    cwd=cwd,
    env=env,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=60,
)
lines = result.stdout.splitlines() + result.stderr.splitlines()
print(f"returncode: {result.returncode}")
# 末尾30行（サマリー）
for l in lines[-30:]:
    print(l)
