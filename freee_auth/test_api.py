import json

import requests

TOKEN_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\freee_token.json"

with open(TOKEN_FILE, encoding="utf-8") as f:
    token_data = json.load(f)

access_token = token_data["access_token"]

# 事業所情報取得でAPIテスト
res = requests.get("https://api.freee.co.jp/api/1/companies", headers={"Authorization": f"Bearer {access_token}"})
print(f"API test status: {res.status_code}")
if res.status_code == 200:
    data = res.json()
    companies = data.get("companies", [])
    for c in companies:
        print(f"  事業所: {c.get('display_name')} (ID: {c.get('id')})")
else:
    print(f"Error: {res.text[:200]}")
