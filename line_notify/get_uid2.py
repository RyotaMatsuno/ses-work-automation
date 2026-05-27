"""
Cloud Runに届いたWebhookのリクエストボディをデバッグ取得するため
webhook_server.pyにデバッグルートを追加してデプロイする代わりに、
直接LINE Messaging APIのinsight/message/deliveryで
最近のメッセージ送信者のuserIdを取得する
"""
import requests
from dotenv import dotenv_values
from datetime import datetime, timezone, timedelta

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
headers = {"Authorization": f"Bearer {token}"}

# webhook_server.pyのデバッグエンドポイントを直接叩く
resp = requests.get(
    "https://line-webhook-74735301292.asia-northeast1.run.app/debug",
    timeout=10
)
print("debug endpoint:", resp.status_code, resp.text[:500])
