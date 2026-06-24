from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")

import requests

# 松野チャンネルのfollowers一覧からユーザーIDを取得
resp = requests.get("https://api.line.me/v2/bot/followers/ids", headers={"Authorization": f"Bearer {token}"})
print(resp.status_code, resp.text[:500])
