import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth")
import json

token_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\freee_auth\token.json"
with open(token_path, encoding="utf-8") as f:
    data = json.load(f)

print(f"scope: {data.get('scope', '')}")
print(f"token_type: {data.get('token_type', '')}")
# アクセストークンの先頭部分（確認用）
at = data.get("access_token", "")
print(f"access_token: {at[:20]}...{at[-10:]}")
