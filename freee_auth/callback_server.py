"""
freee OAuth callback_server - Basic認証対応版
"""
import http.server
import urllib.parse
import requests
import json
import os
import threading
import base64

CLIENT_ID = "730165581365342"
CLIENT_SECRET = "deK5gH1TW7wVL2Os1Fgfayqb4eK0-iiPyumvPV782uE5cJIYFN8bGl6cu_3m6mrYbt-A8-YWxH2eyI6JXNsvkg"
REDIRECT_URI = "http://localhost:8080/callback"
TOKEN_FILE = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\freee_token.json"

def try_get_token(code):
    credentials = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    
    # 方式1: Basic認証
    r = requests.post(
        "https://accounts.secure.freee.co.jp/public_api/token",
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI},
        headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"}
    )
    print(f"[Basic] status={r.status_code} body={r.text[:200]}")
    if r.status_code == 200:
        return r.json()

    # 方式2: bodyにclient_id/secret
    r2 = requests.post(
        "https://accounts.secure.freee.co.jp/public_api/token",
        data={"grant_type": "authorization_code", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "code": code, "redirect_uri": REDIRECT_URI},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    print(f"[Body] status={r2.status_code} body={r2.text[:200]}")
    if r2.status_code == 200:
        return r2.json()

    return None

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" not in params:
            return
        code = params["code"][0]
        print(f"[CODE] {code}")
        token = try_get_token(code)
        if token:
            with open(TOKEN_FILE, "w") as f:
                json.dump(token, f, indent=2, ensure_ascii=False)
            self.send_response(200)
            self.end_headers()
            self.wfile.write("認証成功！トークンを保存しました。このウィンドウを閉じてください。".encode("utf-8"))
            print("[SUCCESS]")
            threading.Thread(target=self.server.shutdown).start()
        else:
            self.send_response(500)
            self.end_headers()
            self.wfile.write("失敗。ログを確認してください。".encode("utf-8"))
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = http.server.HTTPServer(("localhost", 8080), CallbackHandler)
    print("[READY] localhost:8080 で待機中...")
    server.serve_forever()
