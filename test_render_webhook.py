import hmac, hashlib, base64, json, requests

body = json.dumps({"events": []}).encode()
secret = "REDACTED-SECRET"
sig = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()

r = requests.post(
    "https://ses-work-automation.onrender.com/webhook",
    headers={"Content-Type": "application/json", "X-Line-Signature": sig},
    data=body,
    timeout=30
)
print(f"Status: {r.status_code}")
print(f"Body: {r.text[:500]}")
