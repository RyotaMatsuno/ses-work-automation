"""
Cloud RunのLINE webhookに/healthコマンドを松野user_idから送信してエンドツーエンドをテスト
"""
import requests, json

# .envから読み込み
from dotenv import dotenv_values
config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

TOKEN = config.get("LINE_CHANNEL_ACCESS_TOKEN", "")
MATSUNO_USER_ID = config.get("MATSUNO_LINE_USER_ID", "")

print(f"送信先user_id: {MATSUNO_USER_ID}")

# pushメッセージで/healthを松野に送信してCloud Runの動作確認
# → 実際には「LINEから/healthを松野が送信」で確認するため
#    ここではCloud Run→jobz-command疎通をremote_command_handlerで直接確認

import sys
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
from remote_command_handler import get_health

result = get_health()
print(f"health結果: {result}")

# テスト用にLINEにpush通知
r = requests.post(
    "https://api.line.me/v2/bot/message/push",
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    json={"to": MATSUNO_USER_ID, "messages": [{"type": "text", "text": f"🔧 Jobz Tunnel テスト\n{result}\nURL: https://sessions-bone-immune-mtv.trycloudflare.com"}]},
    timeout=10
)
print(f"LINE push: {r.status_code}")
