import base64
import hashlib
import hmac
import io
import json
import sys
import time

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

SECRET = config.get("LINE_CHANNEL_SECRET", "")
MATSUNO_USER_ID = config.get("MATSUNO_LINE_USER_ID", "")

# 疑似LINEイベント（/healthコマンド）
body_dict = {
    "events": [
        {
            "type": "message",
            "replyToken": "test_reply_token_000",
            "message": {"type": "text", "text": "/health"},
            "source": {"userId": MATSUNO_USER_ID, "type": "user"},
            "timestamp": int(time.time() * 1000),
        }
    ]
}
body_str = json.dumps(body_dict)
body_bytes = body_str.encode("utf-8")

# 署名生成
sig = base64.b64encode(hmac.new(SECRET.encode("utf-8"), body_bytes, hashlib.sha256).digest()).decode("utf-8")

r = requests.post(
    "https://line-webhook-74735301292.asia-northeast1.run.app/webhook",
    headers={"Content-Type": "application/json", "X-Line-Signature": sig},
    data=body_bytes,
    timeout=15,
)
print(f"status: {r.status_code}")
print(f"body: {r.text[:300]}")
