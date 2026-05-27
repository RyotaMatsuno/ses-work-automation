"""
Google Drive OAuth認証フロー
- ブラウザで認証してrefresh_tokenを取得
- 取得したトークンをconfig/.envに追記する
"""
import sys, json, os, webbrowser
sys.stdout.reconfigure(encoding='utf-8')
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from dotenv import dotenv_values

config = dotenv_values('config/.env')

# Google Cloud ConsoleでDrive API有効化済みのOAuthクライアントが必要
# 既存のGmail MCPや他のGoogle連携で使っているクライアントIDを確認
print("=== Drive OAuth認証フロー ===", flush=True)
print("", flush=True)
print("以下のURLをブラウザで開いてGoogle認証してください:", flush=True)
print("", flush=True)

# ポーリング用コールバックサーバー
received_code = []

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if 'code' in params:
            received_code.append(params['code'][0])
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'<html><body><h2>認証完了! このウィンドウを閉じてください。</h2></body></html>')
        else:
            self.send_response(400)
            self.end_headers()
    def log_message(self, format, *args):
        pass

# クライアントIDの確認 - GmailMCPの設定ファイルから探す
mcp_paths = [
    r'C:\Users\ma_py\AppData\Roaming\Claude\claude_desktop_config.json',
    r'C:\Users\ma_py\.config\claude\claude_desktop_config.json',
]

print("MCPコンフィグからGoogle OAuthクライアント情報を探しています...", flush=True)
client_id = None
client_secret = None

for path in mcp_paths:
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        print(f"設定ファイル発見: {path}", flush=True)
        # Google関連のMCP設定を探す
        for key, val in data.get('mcpServers', {}).items():
            if 'google' in key.lower() or 'gmail' in key.lower() or 'drive' in key.lower():
                print(f"  Google MCP: {key}", flush=True)
                env = val.get('env', {})
                if 'GOOGLE_CLIENT_ID' in env:
                    client_id = env['GOOGLE_CLIENT_ID']
                    client_secret = env.get('GOOGLE_CLIENT_SECRET','')
                    print(f"  クライアントID発見: {client_id[:20]}...", flush=True)
        break
    
if not client_id:
    print("", flush=True)
    print("MCPコンフィグからクライアントIDが見つかりませんでした。", flush=True)
    print("Google Cloud Consoleで新規OAuthクライアントIDの作成が必要です。", flush=True)
    print("手順は別途案内します。", flush=True)
