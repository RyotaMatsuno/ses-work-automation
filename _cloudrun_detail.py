import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

gcloud = r"C:\Users\ma_py\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# 09:34〜09:36の詳細ログを時刻指定で取得
result = subprocess.run(
    [
        gcloud,
        "logging",
        "read",
        "resource.type=cloud_run_revision AND resource.labels.service_name=line-webhook",
        "--freshness=3h",
        "--limit=200",
        "--format=value(timestamp,textPayload)",
        "--project=ses-work-automation",
    ],
    capture_output=True,
    encoding="utf-8",
    errors="replace",
    timeout=30,
)

lines = result.stdout.split("\n")
# 09:33〜09:36付近のみ表示（matching・PH・LINE関連）
for i, line in enumerate(lines):
    if any(
        kw in line
        for kw in ["PH", "match", "マッチ", "push", "LINE", "notify", "09:3", "09:2", "fetch_all", "matsuno", "case"]
    ):
        print(line)
