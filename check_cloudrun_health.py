import io
import sys

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Cloud Runの/healthを直接叩いてレスポンス確認
r = requests.get("https://line-webhook-74735301292.asia-northeast1.run.app/health", timeout=15)
print(f"status: {r.status_code}")
print(f"body: {r.text[:200]}")
