import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
key = config.get("ANTHROPIC_API_KEY", "")
res = requests.post(
    "https://api.anthropic.com/v1/messages",
    headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
    json={"model": "claude-haiku-4-5-20251001", "max_tokens": 50, "messages": [{"role": "user", "content": "hello"}]},
    timeout=15,
)
out = open("model_test.txt", "w", encoding="utf-8")
out.write(f"status: {res.status_code}\n{res.text}\n")
out.close()
print("DONE")
