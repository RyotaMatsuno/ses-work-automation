"""
freee OAuth - oobモードで認証コードを取得してトークン保存
redirect_uriをurn:ietf:wg:oauth:2.0:oobに変更
"""

import json

import requests

CLIENT_ID = "730165581365342"
CLIENT_SECRET = "deK5gH1TW7wVL2Os1Fgfayqb4eK0-iiPyumvPV782uE5cJIYFN8bGl6cu_3m6mrYbt-A8-YWxH2eyI6JXNsvkg"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"
TOKEN_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\freee_token.json"

# 認証URL生成
import urllib.parse

params = urllib.parse.urlencode(
    {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "prompt": "select_company",
    }
)
auth_url = f"https://accounts.secure.freee.co.jp/public_api/authorize?{params}"
print("=== 以下のURLをブラウザで開いてください ===")
print(auth_url)
print()

code = input("freeeで許可後に表示される認証コードを貼り付けてください: ").strip()

res = requests.post(
    "https://accounts.secure.freee.co.jp/public_api/token",
    data={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    },
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)

print(f"status: {res.status_code}")
print(f"response: {res.text[:200]}")

if res.status_code == 200:
    with open(TOKEN_FILE, "w") as f:
        json.dump(res.json(), f, indent=2, ensure_ascii=False)
    print(f"SUCCESS: {TOKEN_FILE} に保存しました")
else:
    print("FAILED")
