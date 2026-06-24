import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Cloud Runのログを確認
result = subprocess.run(
    [
        "cmd",
        "/c",
        "gcloud",
        "logging",
        "read",
        "resource.type=cloud_run_revision AND resource.labels.service_name=line-webhook",
        "--limit=30",
        "--format=value(textPayload)",
        "--freshness=5m",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=30,
)
print("=== Cloud Run ログ（直近5分） ===")
print(result.stdout[:3000] if result.stdout else "(ログなし)")
if result.stderr:
    print("STDERR:", result.stderr[:500])
