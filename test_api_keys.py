import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

# OpenAI疎通確認
r = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {cfg['OPENAI_API_KEY']}", "Content-Type": "application/json"},
    json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5},
    timeout=15,
)
print("OpenAI:", r.status_code, r.json().get("choices", [{}])[0].get("message", {}).get("content", r.text[:100]))

# Gemini疎通確認
r2 = requests.post(
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={cfg['GEMINI_API_KEY']}",
    json={"contents": [{"parts": [{"text": "ping"}]}]},
    timeout=15,
)
print(
    "Gemini:",
    r2.status_code,
    r2.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", r2.text[:100]),
)
