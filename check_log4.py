import subprocess

result = subprocess.run(
    [
        "cmd",
        "/c",
        "gcloud",
        "logging",
        "read",
        "resource.type=cloud_run_revision AND resource.labels.service_name=line-webhook",
        "--limit=80",
        "--format=value(textPayload)",
        "--freshness=5m",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print(result.stdout[:6000])
