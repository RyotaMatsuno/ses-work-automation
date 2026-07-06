import sys, json, os, requests
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from pathlib import Path

# Load API key
env_path = Path("config/.env")
API_KEY = None
if env_path.exists():
    for line in env_path.read_text(encoding='utf-8').splitlines():
        if line.startswith("OPENAI_API_KEY="):
            API_KEY = line.split("=", 1)[1].strip().strip('"')
            break

if not API_KEY:
    API_KEY = os.environ.get("OPENAI_API_KEY")

if not API_KEY:
    print("ERROR: No API key found")
    sys.exit(1)

print(f"API Key found: {API_KEY[:10]}...")

URL = "https://api.openai.com/v1/responses"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

payload = {
    "model": "gpt-5.4",
    "input": [{"role": "user", "content": "Hello, respond with 'OK' only."}],
    "reasoning": {"effort": "low"},
    "max_output_tokens": 100,
}

try:
    resp = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
    print(f"Status: {resp.status_code}")
    data = resp.json()
    for block in data.get("output", []):
        if block.get("type") == "message":
            for content in block.get("content", []):
                if content.get("type") == "output_text":
                    print(f"Response: {content['text']}")
except Exception as e:
    print(f"Error: {e}")
