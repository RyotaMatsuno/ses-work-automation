import base64
import hashlib
import hmac
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
MATSUNO_SECRET = config.get("LINE_CHANNEL_SECRET", "")
MATSUNO_USER_ID = config.get("MATSUNO_LINE_USER_ID") or "Ue3508b43b84991f5a68281da5bf4cf39"
WEBHOOK_URL = "https://line-webhook-74735301292.asia-northeast1.run.app/webhook"


def post(text):
    body = json.dumps(
        {
            "events": [
                {
                    "type": "message",
                    "webhookEventId": f"f{abs(hash(text)) % 9999}",
                    "replyToken": "noreply_" + "0" * 32,
                    "source": {"type": "user", "userId": MATSUNO_USER_ID},
                    "message": {"type": "text", "text": text, "id": "1"},
                }
            ]
        }
    ).encode()
    sig = base64.b64encode(hmac.new(MATSUNO_SECRET.encode(), body, hashlib.sha256).digest()).decode()
    r = requests.post(
        WEBHOOK_URL, headers={"Content-Type": "application/json", "X-Line-Signature": sig}, data=body, timeout=10
    )
    return r.status_code


print("webhook POST テスト:")
print(f"  HS 北小金: {post('HS 北小金')}")
print(f"  H.S 北小金: {post('H.S 北小金')}")
