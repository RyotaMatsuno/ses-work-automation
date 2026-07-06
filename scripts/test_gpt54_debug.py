import sys, json, os, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path

env_path = Path("config/.env")
API_KEY = None
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        if line.startswith("OPENAI_API_KEY="):
            API_KEY = line.split("=", 1)[1].strip().strip('"')
            break

URL = "https://api.openai.com/v1/responses"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

payload = {
    "model": "gpt-5.4",
    "input": [{"role": "user", "content": "Say OK"}],
    "reasoning": {"effort": "low"},
    "max_output_tokens": 50,
}

resp = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
print(f"Status: {resp.status_code}")
print(f"Headers: {dict(resp.headers)}")
print(f"Body: {resp.text[:2000]}")
