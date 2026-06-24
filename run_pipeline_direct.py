# -*- coding: utf-8 -*-
import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# mail_pipelineを直接実行してstdoutをキャプチャ
result = subprocess.run(
    [sys.executable, "-m", "mail_pipeline.mail_pipeline"],
    cwd=r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work",
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=110,
)
print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[:1000])
print("return code:", result.returncode)
