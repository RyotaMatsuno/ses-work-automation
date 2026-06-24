import subprocess

# 最新のCloud Runリビジョンを確認
result = subprocess.run(
    [
        "cmd",
        "/c",
        "gcloud",
        "run",
        "services",
        "describe",
        "line-webhook",
        "--region=asia-northeast1",
        "--format=value(status.latestReadyRevisionName,status.latestCreatedRevisionName)",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print("Revision:", result.stdout.strip())
print("STDERR:", result.stderr[:200])
