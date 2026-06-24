import base64
import hashlib
import hmac
import json

import requests

body = json.dumps({"events": []}).encode()
secret = "648247890a88176af56fa17a5d88d216"
sig = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()

r = requests.post(
    "https://ses-work-automation.onrender.com/webhook",
    headers={"Content-Type": "application/json", "X-Line-Signature": sig},
    data=body,
    timeout=30,
)
print(f"Status: {r.status_code}")
print(f"Body: {r.text[:500]}")
