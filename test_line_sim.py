import hmac, hashlib, base64, json, requests, time

# 実際のLINEメッセージイベントをシミュレート
body_dict = {
    "destination": "REDACTED-SECRET",
    "events": [{
        "type": "message",
        "replyToken": "nHuyWiB7yP5Zw52FIkcQobQuGDXCTA",
        "source": {"userId": "REDACTED-SECRET", "type": "user"},
        "timestamp": int(time.time() * 1000),
        "mode": "active",
        "message": {"id": "444573844083572737", "type": "text", "text": "テスト"}
    }]
}
body = json.dumps(body_dict, ensure_ascii=False).encode()
secret = "REDACTED-SECRET"
sig = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()

print(f"Sending to Render...")
t = time.time()
r = requests.post(
    "https://ses-work-automation.onrender.com/webhook",
    headers={"Content-Type": "application/json", "X-Line-Signature": sig},
    data=body,
    timeout=30
)
print(f"Status: {r.status_code}, Time: {time.time()-t:.1f}s")
print(f"Response: {r.text[:200]}")
