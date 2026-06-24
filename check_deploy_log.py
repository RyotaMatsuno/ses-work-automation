import subprocess
import time

time.sleep(5)  # 起動安定待ち

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
        "--freshness=3m",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print(result.stdout[:3000])
