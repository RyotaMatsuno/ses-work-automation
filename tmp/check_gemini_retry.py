import json
import os
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = os.path.join(os.path.expanduser("~"), "OneDrive", "\u30c7\u30b9\u30af\u30c8\u30c3\u30d7", "ses_work")
env_path = os.path.join(base, "config", ".env")
env = {}
for line in open(env_path, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    env[k.strip()] = v.strip().strip('"').strip("'")

gemini_key = env.get("GEMINI_API_KEY", "")
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + gemini_key
payload = json.dumps(
    {
        "contents": [{"parts": [{"text": "テスト。一言で返してください。"}]}],
        "generationConfig": {"maxOutputTokens": 20},
    }
).encode("utf-8")
req = urllib.request.Request(
    url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)

print("60秒待機後にリトライします...")
time.sleep(62)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        print("Gemini疎通: OK ->", text.strip())
except urllib.error.HTTPError as e:
    body = e.read().decode("utf-8", errors="replace")[:300]
    print(f"Gemini疎通: HTTP {e.code} -> {body}")
except Exception as e:
    print("Gemini疎通: ERROR ->", type(e).__name__, str(e))
