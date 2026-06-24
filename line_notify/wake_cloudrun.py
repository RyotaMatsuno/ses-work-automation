"""
LINEのWebhook検証エンドポイントを叩いて、
直近のメッセージのuserIdをCloud Runのログから取得する代わりに、
LINE Get Profile APIでBotのフォロワー（松野）のIDを特定する。

※ フォロワーAPI（/v2/bot/followers/ids）は非対応のため、
かわりにWebhookテストを送信してCloud Runを起こし、
その後もう一度ログを確認する。
"""

import requests
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Webhook テスト送信（Cloud Runを起動させる）
resp = requests.post("https://api.line.me/v2/bot/channel/webhook/test", headers=headers, json={})
print("Webhook test:", resp.status_code, resp.text)
