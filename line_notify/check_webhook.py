import requests
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
headers = {"Authorization": f"Bearer {token}"}

# Webhook URL確認
resp = requests.get("https://api.line.me/v2/bot/channel/webhook/endpoint", headers=headers)
print("Webhook設定:", resp.status_code, resp.text)
