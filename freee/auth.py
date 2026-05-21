# -*- coding: utf-8 -*-
"""
freee OAuth2 auth.py
"""
import os, json, secrets, threading, webbrowser, time, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
import requests

CLIENT_ID     = "731109064351970"
CLIENT_SECRET = "6rbUbEgQ1i58C7O6Ndg8TQDDQcoO6w9EGkCt_HkWADe9klxnGoN1iNd-vlF0vqkqdVOJYi8nfkYNY9M9evkBJQ"
REDIRECT_URI  = "http://localhost:8080/callback"
TOKEN_PATH    = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\freee_freee_token.json"
AUTH_URL      = "https://accounts.secure.freee.co.jp/public_api/authorize"
TOKEN_URL     = "https://accounts.secure.freee.co.jp/public_api/token"

auth_code_holder = {"code": None}

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            params = parse_qs(parsed.query)
            auth_code_holder["code"] = params.get("code", [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Auth OK! Close this tab.")
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *a): pass

t = threading.Thread(target=lambda: HTTPServer(("localhost", 8080), CallbackHandler).handle_request())
t.daemon = True
t.start()

url = f"{AUTH_URL}?{urlencode({'client_id':CLIENT_ID,'redirect_uri':REDIRECT_URI,'response_type':'code','state':'jobz2026'})}"
print("[INFO] Opening browser:", url)
webbrowser.open(url)

for _ in range(60):
    if auth_code_holder["code"]: break
    time.sleep(1)

code = auth_code_holder["code"]
if not code:
    print("[ERROR] Timeout - no auth code received")
    sys.exit(1)

print("[OK] Code received:", code[:10], "...")

res = requests.post(TOKEN_URL, data={
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": code,
    "redirect_uri": REDIRECT_URI,
})

if res.status_code not in (200, 201):
    print(f"[ERROR] Token exchange failed: {res.status_code} {res.text}")
    sys.exit(1)

data = res.json()
with open(TOKEN_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("[OK] freee_token.json saved:", TOKEN_PATH)
print("  access_token :", data.get("access_token","")[:20], "...")
print("  refresh_token:", data.get("refresh_token","")[:20], "...")
print("  expires_in   :", data.get("expires_in"), "sec")
