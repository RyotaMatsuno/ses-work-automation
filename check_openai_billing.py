import json
import sys
from pathlib import Path

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
config = dotenv_values(base / "config" / ".env")
openai_key = config.get("OPENAI_API_KEY", "")

# OpenAI API疎通確認 + モデル確認
import urllib.error
import urllib.request

headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
body = json.dumps({"model": "gpt-4o-mini", "max_tokens": 10, "messages": [{"role": "user", "content": "hi"}]}).encode()

req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body, headers=headers, method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
        print("API疎通: OK")
        print(f"モデル: {data.get('model')}")
        usage = data.get("usage", {})
        print(f"usage: {usage}")
        cost_est = usage.get("prompt_tokens", 0) * 0.15 / 1e6 + usage.get("completion_tokens", 0) * 0.6 / 1e6
        print(f"今回のコスト: ${cost_est:.6f}")
except urllib.error.HTTPError as e:
    body_txt = e.read().decode()
    print(f"HTTPError {e.code}: {body_txt[:300]}")
except Exception as e:
    print(f"Error: {e}")
