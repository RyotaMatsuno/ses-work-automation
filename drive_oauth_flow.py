"""
One-time OAuth2 flow to get Drive refresh_token.
Starts local server on port 8766, opens browser for auth.
"""

import json
import os
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

# GCPコンソールのOAuth Desktop client
CLIENT_ID = "74735301292-op9eiut55pjdkhb44p25c6hlokcf01ql.apps.googleusercontent.com"
# Desktop app client_secret取得を試みる - 既存credentials.jsonがあれば読む
CRED_PATH = "config/credentials.json"

if os.path.exists(CRED_PATH):
    with open(CRED_PATH) as f:
        creds = json.load(f)
    installed = creds.get("installed") or creds.get("web") or {}
    CLIENT_ID = installed.get("client_id", CLIENT_ID)
    CLIENT_SECRET = installed.get("client_secret", "")
    print(f"Loaded from credentials.json: {CLIENT_ID[:30]}...")
else:
    print("credentials.json not found")
    print(f"CLIENT_ID: {CLIENT_ID}")
    CLIENT_SECRET = input("GCPコンソールのclient_secretを入力: ").strip()

REDIRECT_URI = "http://localhost:8766"
SCOPE = "https://www.googleapis.com/auth/drive"

auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(
    {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
)

print(f"\n認証URL: {auth_url}\n")
print("ブラウザが開きます。Googleアカウントでログインして承認してください。")
webbrowser.open(auth_url)

# ローカルサーバーでcodeを受け取る
received = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            received["code"] = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write("認証完了。このウィンドウを閉じてください。".encode())
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *a):
        pass


server = HTTPServer(("localhost", 8766), Handler)
print("待機中... (ブラウザで認証後、自動的に続きます)")
server.handle_request()

code = received.get("code")
if not code:
    print("認証コードが取得できませんでした")
    exit(1)

# トークン取得
resp = requests.post(
    "https://oauth2.googleapis.com/token",
    data={
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    },
)
token_data = resp.json()
print("\nToken response:", json.dumps({k: v for k, v in token_data.items() if k != "access_token"}, indent=2))

if "refresh_token" in token_data:
    # .envに保存
    env_path = "config/.env"
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()

    additions = []
    if "DRIVE_REFRESH_TOKEN" not in content:
        additions.append(f"DRIVE_REFRESH_TOKEN={token_data['refresh_token']}")
    if "DRIVE_CLIENT_ID" not in content:
        additions.append(f"DRIVE_CLIENT_ID={CLIENT_ID}")
    if "DRIVE_CLIENT_SECRET" not in content:
        additions.append(f"DRIVE_CLIENT_SECRET={CLIENT_SECRET}")

    if additions:
        with open(env_path, "a", encoding="utf-8") as f:
            f.write("\n# Drive OAuth tokens\n")
            for line in additions:
                f.write(line + "\n")
        print("\n.envに保存しました:")
        for a in additions:
            key = a.split("=")[0]
            print(f"  {key}: [set]")
    print("\nDrive認証完了！以降は自動でアップロードできます。")
else:
    print("refresh_tokenが取得できませんでした:", token_data)
