import io
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

time.sleep(5)  # ログ反映待ち

result = subprocess.run(
    [
        "cmd",
        "/c",
        "gcloud",
        "logging",
        "read",
        "resource.type=cloud_run_revision AND resource.labels.service_name=line-webhook",
        "--limit=50",
        "--format=value(textPayload)",
        "--freshness=3m",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=30,
)
print("=== Cloud Run ログ（直近3分）===")
logs = result.stdout if result.stdout else "(ログなし)"
print(logs[:4000])
