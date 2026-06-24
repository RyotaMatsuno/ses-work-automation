import json
import os
import sqlite3
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

# gcloudのcredentials.dbからclient情報取得
db_path = os.path.expandvars(r"%APPDATA%\gcloud\credentials.db")
conn = sqlite3.connect(db_path)
row = conn.execute("SELECT value FROM credentials WHERE account_id='mappi9118@gmail.com'").fetchone()
conn.close()
data = json.loads(row[0])

CLIENT_ID = data["client_id"]
CLIENT_SECRET = data["client_secret"]
REDIRECT_URI = "http://localhost:8766"
SCOPE = "https://www.googleapis.com/auth/drive"

print(f"CLIENT_ID: {CLIENT_ID}")
print("CLIENT_SECRET: present")

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

print(f"\n以下のURLをブラウザで開いてGoogleアカウントで承認してください:\n{auth_url}\n")
webbrowser.open(auth_url)

received = {}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            received["code"] = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write("認証完了。このウィンドウを閉じてください。".encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *a):
        pass


print("ブラウザで承認後、自動的に続きます...")
server = HTTPServer(("localhost", 8766), Handler)
server.handle_request()

code = received.get("code")
if not code:
    print("認証コードが取得できませんでした")
    exit(1)

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

if "refresh_token" in token_data:
    # token.jsonとして保存
    token_json = {
        "token": token_data.get("access_token"),
        "refresh_token": token_data["refresh_token"],
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scopes": [SCOPE],
    }
    out_path = "config/drive_token.json"
    with open(out_path, "w") as f:
        json.dump(token_json, f, indent=2)
    print(f"\n保存完了: {out_path}")
    print("Drive認証成功！以降は自動アップロードできます。")
else:
    print(f"エラー: {token_data}")
