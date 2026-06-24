import json
import os
import sys
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

# gemini-1.5-flash で試す（別モデル）
for model in ["gemini-1.5-flash", "gemini-1.0-pro", "gemini-2.0-flash-lite"]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
    payload = json.dumps(
        {
            "contents": [{"parts": [{"text": "hi"}]}],
            "generationConfig": {"maxOutputTokens": 10},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            print(f"{model}: OK -> {text.strip()}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:150]
        print(f"{model}: HTTP {e.code}")
    except Exception as e:
        print(f"{model}: ERROR {e}")

# wall_hitting.py で過去に使ったモデルを確認
wh_path = os.path.join(base, "wall_hitting.py")
for line in open(wh_path, encoding="utf-8"):
    if "gemini" in line.lower() and "model" in line.lower():
        print("wall_hitting model line:", line.strip())
        break
