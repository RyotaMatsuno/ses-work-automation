import base64
import hashlib
import hmac
import json
import time

import requests

# 実際のLINEメッセージイベントをシミュレート
body_dict = {
    "destination": "Ue3508b43b84991f5a68281da5bf4cf39",
    "events": [
        {
            "type": "message",
            "replyToken": "nHuyWiB7yP5Zw52FIkcQobQuGDXCTA",
            "source": {"userId": "Ue3508b43b84991f5a68281da5bf4cf39", "type": "user"},
            "timestamp": int(time.time() * 1000),
            "mode": "active",
            "message": {"id": "444573844083572737", "type": "text", "text": "テスト"},
        }
    ],
}
body = json.dumps(body_dict, ensure_ascii=False).encode()
secret = "648247890a88176af56fa17a5d88d216"
sig = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()

print("Sending to Render...")
t = time.time()
r = requests.post(
    "https://ses-work-automation.onrender.com/webhook",
    headers={"Content-Type": "application/json", "X-Line-Signature": sig},
    data=body,
    timeout=30,
)
print(f"Status: {r.status_code}, Time: {time.time() - t:.1f}s")
print(f"Response: {r.text[:200]}")
