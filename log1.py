import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import subprocess
import time

# Cloud Runのログを確認 → webhook内部でどう処理されたか
time.sleep(5)
r = subprocess.run(
    [
        "cmd",
        "/c",
        "gcloud",
        "logging",
        "read",
        "resource.type=cloud_run_revision AND resource.labels.service_name=line-webhook",
        "--limit=40",
        "--format=value(textPayload)",
        "--freshness=5m",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=25,
)
print("=== Cloud Run ログ（直近5分）===")
print(r.stdout[:4000] if r.stdout else "(なし)")
