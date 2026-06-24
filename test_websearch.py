import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

# gpt-4o with web search tool
r = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {cfg['OPENAI_API_KEY']}", "Content-Type": "application/json"},
    json={
        "model": "gpt-4o-search-preview",
        "messages": [{"role": "user", "content": "今日の日付を教えてください"}],
        "max_tokens": 100,
    },
    timeout=30,
)
print("gpt-4o-search-preview:", r.status_code)
if r.status_code == 200:
    print("応答:", r.json()["choices"][0]["message"]["content"][:200])
else:
    print("Error:", r.json().get("error", {}).get("message", "")[:200])
