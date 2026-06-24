import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
MATSUNO_TOKEN = config.get("LINE_CHANNEL_ACCESS_TOKEN", "")

# LINE Messaging API の使用量確認
r = requests.get(
    "https://api.line.me/v2/bot/insight/message/delivery",
    headers={"Authorization": f"Bearer {MATSUNO_TOKEN}"},
    timeout=10,
)
print(f"delivery API: {r.status_code}")

# 統計情報
r2 = requests.get(
    "https://api.line.me/v2/bot/message/quota", headers={"Authorization": f"Bearer {MATSUNO_TOKEN}"}, timeout=10
)
print(f"quota API: {r2.status_code} {r2.text}")

# 消費量
r3 = requests.get(
    "https://api.line.me/v2/bot/message/quota/consumption",
    headers={"Authorization": f"Bearer {MATSUNO_TOKEN}"},
    timeout=10,
)
print(f"consumption: {r3.status_code} {r3.text}")
