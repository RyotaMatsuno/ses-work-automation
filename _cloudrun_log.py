import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

gcloud = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# Cloud Run の最新ログ（直近50件）
result = subprocess.run(
    [
        gcloud,
        "logging",
        "read",
        "resource.type=cloud_run_revision AND resource.labels.service_name=line-webhook",
        "--limit=50",
        "--format=value(timestamp,textPayload)",
        "--project=ses-work-automation",
    ],
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    timeout=30,
)
print(result.stdout[-4000:] if result.stdout else "(empty)")
print(result.stderr[-1000:] if result.stderr else "")
