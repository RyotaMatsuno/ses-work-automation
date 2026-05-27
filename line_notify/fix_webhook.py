import requests
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# Webhook URLを正しいCloud RunのURLに更新
new_url = "https://line-webhook-74735301292.asia-northeast1.run.app/webhook"
resp = requests.put(
    "https://api.line.me/v2/bot/channel/webhook/endpoint",
    headers=headers,
    json={"webhook_url": new_url}
)
print("更新結果:", resp.status_code, resp.text)

# 確認
resp2 = requests.get("https://api.line.me/v2/bot/channel/webhook/endpoint", headers=headers)
print("更新後:", resp2.text)
