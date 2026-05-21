"""
freee OAuth - Basic認証方式でトークン取得を試みる
"""
import requests
import json
import base64

CLIENT_ID = "730165581365342"
CLIENT_SECRET = "deK5gH1TW7wVL2Os1Fgfayqb4eK0-iiPyumvPV782uE5cJIYFN8bGl6cu_3m6mrYbt-A8-YWxH2eyI6JXNsvkg"
REDIRECT_URI = "http://localhost:8080/callback"
TOKEN_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\freee_token.json"

# 直前のログから取得したcode（使い捨てなので新しいcodeが必要）
# このスクリプトはcallback_server.pyから呼ばれる想定
import sys
code = sys.argv[1] if len(sys.argv) > 1 else ""

if not code:
    print("codeが必要です")
    sys.exit(1)

# 方式1: Basic認証ヘッダー
credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
r1 = requests.post(
    "https://accounts.secure.freee.co.jp/public_api/token",
    data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    },
    headers={
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
)
print(f"[Basic認証] status={r1.status_code} body={r1.text[:200]}")

if r1.status_code == 200:
    with open(TOKEN_FILE, "w") as f:
        json.dump(r1.json(), f, indent=2, ensure_ascii=False)
    print(f"SUCCESS: {TOKEN_FILE}")
    sys.exit(0)

# 方式2: JSONボディ
r2 = requests.post(
    "https://accounts.secure.freee.co.jp/public_api/token",
    json={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }
)
print(f"[JSON] status={r2.status_code} body={r2.text[:200]}")

if r2.status_code == 200:
    with open(TOKEN_FILE, "w") as f:
        json.dump(r2.json(), f, indent=2, ensure_ascii=False)
    print(f"SUCCESS: {TOKEN_FILE}")
