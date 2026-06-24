import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Cloud Run timeout を 120秒に延長（Notion全件取得が遅いため）
r = subprocess.run(
    [
        "cmd",
        "/c",
        "gcloud",
        "run",
        "services",
        "update",
        "line-webhook",
        "--region=asia-northeast1",
        "--timeout=120",
        "--quiet",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=30,
)
print("STDOUT:", r.stdout.strip())
print("STDERR:", r.stderr[-200:].strip())
print("returncode:", r.returncode)
if r.returncode == 0:
    print("✅ タイムアウト 60→120秒 に延長完了")
