"""
freee認証URLを直接叩いてレスポンスを確認
"""

import requests

CLIENT_ID = "730165581365342"
REDIRECT_URI = "http://localhost:8080/callback"

url = "https://accounts.secure.freee.co.jp/public_api/authorize"
params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "prompt": "select_company",
}

r = requests.get(url, params=params, allow_redirects=False)
print(f"status: {r.status_code}")
print(f"location: {r.headers.get('Location', 'なし')}")
print(f"body[:500]: {r.text[:500]}")
