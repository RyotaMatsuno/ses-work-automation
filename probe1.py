import base64
import hashlib
import hmac
import io
import json
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
MATSUNO_TOKEN = config.get("LINE_CHANNEL_ACCESS_TOKEN", "")
MATSUNO_SECRET = config.get("LINE_CHANNEL_SECRET", "")
MATSUNO_USER_ID = config.get("MATSUNO_LINE_USER_ID") or "Ue3508b43b84991f5a68281da5bf4cf39"
WEBHOOK_URL = "https://line-webhook-74735301292.asia-northeast1.run.app/webhook"

# ── 1. Cloud Run health ─────────────────────────────
r = requests.get("https://line-webhook-74735301292.asia-northeast1.run.app/health", timeout=10)
print(f"Cloud Run health: {r.status_code} {r.text}")

# ── 2. Webhook に「HS 北小金」を POST（本番フロー） ─────────
body = json.dumps(
    {
        "events": [
            {
                "type": "message",
                "webhookEventId": "probe_hs_001",
                "replyToken": "test_" + "0" * 35,
                "source": {"type": "user", "userId": MATSUNO_USER_ID},
                "message": {"type": "text", "text": "HS 北小金", "id": "1"},
            }
        ]
    }
).encode()
sig = base64.b64encode(hmac.new(MATSUNO_SECRET.encode(), body, hashlib.sha256).digest()).decode()
r2 = requests.post(
    WEBHOOK_URL, headers={"Content-Type": "application/json", "X-Line-Signature": sig}, data=body, timeout=30
)
print(f'Webhook POST "HS 北小金": {r2.status_code}')

time.sleep(3)

# ── 3. LINEに push で「テスト中」通知 ─────────────────────
r3 = requests.post(
    "https://api.line.me/v2/bot/message/push",
    headers={"Authorization": f"Bearer {MATSUNO_TOKEN}", "Content-Type": "application/json"},
    json={
        "to": MATSUNO_USER_ID,
        "messages": [
            {
                "type": "text",
                "text": "🔧 自走テスト中...\n「HS 北小金」をwebhook経由で送りました\n返信が来るか確認してください",
            }
        ],
    },
    timeout=10,
)
print(f"Push LINE: {r3.status_code}")
