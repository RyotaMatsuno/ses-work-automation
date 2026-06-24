import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

# o3が使えるか確認
r = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {cfg['OPENAI_API_KEY']}", "Content-Type": "application/json"},
    json={"model": "o3", "messages": [{"role": "user", "content": "ping"}], "max_completion_tokens": 10},
    timeout=30,
)
print(
    "o3:",
    r.status_code,
    r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    if r.status_code == 200
    else r.json().get("error", {}).get("message", "")[:150],
)

# Gemini 2.5 Pro確認
import time

time.sleep(3)
r2 = requests.post(
    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key={cfg['GEMINI_API_KEY']}",
    json={"contents": [{"parts": [{"text": "ping"}]}], "generationConfig": {"maxOutputTokens": 10}},
    timeout=30,
)
print(
    "Gemini 2.5 Pro:",
    r2.status_code,
    r2.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    if r2.status_code == 200
    else r2.json().get("error", {}).get("message", "")[:150],
)
