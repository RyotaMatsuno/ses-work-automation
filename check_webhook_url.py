import sys, io, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import dotenv_values
config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")

TOKEN = config.get("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_ID = config.get("LINE_CHANNEL_ID", "")

# Webhook URL設定を取得
r = requests.get(
    "https://api.line.me/v2/bot/channel/webhook/endpoint",
    headers={"Authorization": f"Bearer {TOKEN}"},
    timeout=10
)
print(f"status: {r.status_code}")
print(f"body: {r.text}")
