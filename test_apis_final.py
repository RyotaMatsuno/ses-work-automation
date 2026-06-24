import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
key = cfg["GEMINI_API_KEY"]

r = requests.post(
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
    json={"contents": [{"parts": [{"text": "「稼働中」と一言だけ答えてください"}]}]},
    timeout=15,
)
print("Gemini生成:", r.status_code)
if r.status_code == 200:
    print(r.json()["candidates"][0]["content"]["parts"][0]["text"])
else:
    print(r.json().get("error", {}).get("message", "")[:200])

# OpenAIはクレジット追加後に再確認
from dotenv import dotenv_values

r2 = requests.get(
    "https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {cfg['OPENAI_API_KEY']}"}, timeout=15
)
print("OpenAI key status:", r2.status_code)
if r2.status_code == 200:
    print("OpenAI OK - モデル取得成功")
elif r2.status_code == 401:
    print("OpenAI: APIキー無効")
elif r2.status_code == 429:
    print("OpenAI: クレジット未チャージ（キー自体は有効）")
