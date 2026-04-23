import hmac
import hashlib
import base64
import json
import requests

secret = 'REDACTED-SECRET'

body = json.dumps({
    "destination": "Uxxxxx",
    "events": [{
        "type": "message",
        "mode": "active",
        "timestamp": 1713268800000,
        "source": {"type": "user", "userId": "Utest1234567890"},
        "replyToken": "test-reply-token-0000000000",
        "message": {
            "type": "text",
            "id": "msg001",
            "text": "名前：テスト太郎\nスキル：Java, Python\n単価：70\n稼働可能日：2026年5月1日\n経験年数：5\n連絡先：090-0000-0000\nメール：test@example.com\n備考：テスト送信"
        }
    }]
}, ensure_ascii=False)

sig = base64.b64encode(
    hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest()
).decode()

res = requests.post(
    'https://ses-work-automation-production.up.railway.app/webhook',
    headers={
        'Content-Type': 'application/json',
        'X-Line-Signature': sig
    },
    data=body.encode('utf-8')
)

print(f"ステータス: {res.status_code}")
print(f"レスポンス: {res.text}")
