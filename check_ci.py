import subprocess
import time

# 30秒待ってからリビジョンを再確認（自動デプロイが走るか確認）
time.sleep(30)

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
        "--format=value(status.latestReadyRevisionName)",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
print("Latest revision after 30s:", result.stdout.strip())

# GitHub Actions の状況を確認
result2 = subprocess.run(
    ["cmd", "/c", "gh", "run", "list", "--limit=3"], capture_output=True, text=True, encoding="utf-8", errors="replace"
)
print("GitHub Actions runs:", result2.stdout[:500])
print("GH stderr:", result2.stderr[:200])
