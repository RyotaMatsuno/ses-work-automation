"""
freee認証デバッグ: redirect_uriとclient_secretを検証
"""
import requests
import json

CLIENT_ID = "730165581365342"
CLIENT_SECRET = "deK5gH1TW7wVL2Os1Fgfayqb4eK0-iiPyumvPV782uE5cJIYFN8bGl6cu_3m6mrYbt-A8-YWxH2eyI6JXNsvkg"

# テスト1: redirect_uriのバリエーションをすべてリストアップ
uris = [
    "http://localhost:8080/callback",
    "http://127.0.0.1:8080/callback",
    "http://localhost:8080/",
    "urn:ietf:wg:oauth:2.0:oob",
]

print("=== redirect_URI候補 ===")
for uri in uris:
    print(f"  {uri}")

# テスト2: 既存トークンファイルの確認
import os
token_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\freee_token.json"
if os.path.exists(token_path):
    with open(token_path) as f:
        data = json.load(f)
    print(f"\n=== 既存トークンあり ===")
    print(f"  access_token: {data.get('access_token','')[:20]}...")
    print(f"  refresh_token: {data.get('refresh_token','')[:20]}...")
    print(f"  expires_in: {data.get('expires_in')}")
    print(f"  created_at: {data.get('created_at')}")
    
    # refresh_tokenで再取得を試みる
    print("\n=== refresh_tokenでアクセストークン更新を試みます ===")
    r = requests.post("https://accounts.secure.freee.co.jp/public_api/token", data={
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": data.get("refresh_token"),
    })
    print(f"  ステータス: {r.status_code}")
    print(f"  レスポンス: {r.text[:300]}")
else:
    print("\n既存トークンなし")
