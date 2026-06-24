import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
OPENAI_KEY = config.get("OPENAI_API_KEY", "")
GEMINI_KEY = config.get("GEMINI_API_KEY", "")

# Gemini: 利用可能モデル確認
print("=== Gemini モデル確認 ===")
try:
    resp = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}", timeout=10)
    if resp.ok:
        for m in resp.json().get("models", []):
            name = m.get("name", "")
            if any(x in name.lower() for x in ["flash", "pro"]):
                methods = [mm for mm in m.get("supportedGenerationMethods", [])]
                if "generateContent" in methods:
                    print(f"  {name}")
    else:
        print(f"  Error: {resp.status_code}")
except Exception as e:
    print(f"  Error: {e}")

# OpenAI: 残高確認
print("\n=== OpenAI 残高確認 ===")
try:
    resp = requests.get(
        "https://api.openai.com/v1/organization/costs?start_time=1717200000&limit=1",
        headers={"Authorization": f"Bearer {OPENAI_KEY}"},
        timeout=10,
    )
    print(f"  Status: {resp.status_code}")
    if resp.status_code == 429:
        # レート制限のretry-after確認
        print(f"  Retry-After: {resp.headers.get('retry-after', 'not set')}")
        print(f"  Headers: {dict(resp.headers)}")
except Exception as e:
    print(f"  Error: {e}")
