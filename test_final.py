import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

# OpenAI
r = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {cfg['OPENAI_API_KEY']}", "Content-Type": "application/json"},
    json={
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "「稼働中」と一言だけ答えてください"}],
        "max_tokens": 10,
    },
    timeout=20,
)
print(
    "OpenAI:",
    r.status_code,
    r.json()["choices"][0]["message"]["content"]
    if r.status_code == 200
    else r.json().get("error", {}).get("message", "")[:100],
)

# Gemini
import time

time.sleep(3)
r2 = requests.post(
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={cfg['GEMINI_API_KEY']}",
    json={"contents": [{"parts": [{"text": "「稼働中」と一言だけ答えてください"}]}]},
    timeout=15,
)
print(
    "Gemini:",
    r2.status_code,
    r2.json()["candidates"][0]["content"]["parts"][0]["text"]
    if r2.status_code == 200
    else r2.json().get("error", {}).get("message", "")[:100],
)
