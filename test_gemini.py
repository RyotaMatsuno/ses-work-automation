import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

key = cfg["GEMINI_API_KEY"]

# モデル一覧取得（APIキーが有効かの確認）
r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", timeout=15)
print("Gemini models status:", r.status_code)
if r.status_code == 200:
    models = r.json().get("models", [])
    print("利用可能モデル数:", len(models))
    for m in models[:5]:
        print(" -", m.get("name"))
else:
    print("Error:", r.json().get("error", {}).get("message", "")[:200])
