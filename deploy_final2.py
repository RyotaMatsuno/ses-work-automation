import io
import re
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

result = subprocess.run(
    [
        "cmd",
        "/c",
        "gcloud",
        "run",
        "deploy",
        "line-webhook",
        "--source",
        r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook",
        "--region=asia-northeast1",
        "--quiet",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=240,
)
m = re.search(r"line-webhook-\d{5}-\w+", result.stderr)
rev = m.group(0) if m else "?"
print(f"returncode: {result.returncode}")
print(f"{'✅' if result.returncode == 0 else '❌'} デプロイ完了: {rev}")
if result.returncode != 0:
    print(result.stderr[-300:])
