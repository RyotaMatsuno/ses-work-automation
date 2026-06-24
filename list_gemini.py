import json
import urllib.request

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
GEMINI_KEY = config.get("GEMINI_API_KEY") or config.get("GOOGLE_API_KEY")

# まずモデル一覧を確認
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
req = urllib.request.Request(url, method="GET")
with urllib.request.urlopen(req, timeout=10) as r:
    res = json.loads(r.read())
for m in res.get("models", []):
    name = m.get("name", "")
    if "flash" in name.lower():
        print(f"{name} - {m.get('displayName', '')}")
