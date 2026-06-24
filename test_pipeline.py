"""テスト用: 1件だけ処理して動作確認"""

import os
import subprocess
import sys

env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
env["PROCESS_LIMIT_OVERRIDE"] = "1"

result = subprocess.run(
    [sys.executable, "mail_pipeline/mail_pipeline.py", "--test"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    env=env,
    timeout=90,
)
print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[-1000:])
