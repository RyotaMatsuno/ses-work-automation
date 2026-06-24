import io
import subprocess
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Cloud RunのデフォルトタイムアウトはPOSTに対して60秒
# webhook postは200を返すが、処理が走り続ける（非同期）なのでタイムアウトが起きている
# → これは設計上の問題ではなく、テスト方法の問題

# Cloud Run timeout設定を確認
r = subprocess.run(
    [
        "cmd",
        "/c",
        "gcloud",
        "run",
        "services",
        "describe",
        "line-webhook",
        "--region=asia-northeast1",
        "--format=value(spec.template.spec.timeoutSeconds)",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=20,
)
print(f"Cloud Run タイムアウト設定: {r.stdout.strip()}秒")

# 直近ログ確認
time.sleep(3)
r2 = subprocess.run(
    [
        "cmd",
        "/c",
        "gcloud",
        "logging",
        "read",
        "resource.type=cloud_run_revision AND resource.labels.service_name=line-webhook",
        "--limit=20",
        "--format=value(textPayload)",
        "--freshness=10m",
    ],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    timeout=20,
)
print("=== 直近10分のログ ===")
print(r2.stdout[:3000] if r2.stdout else "(なし)")
