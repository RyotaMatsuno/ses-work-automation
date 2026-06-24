# -*- coding: utf-8 -*-
"""LINE push残通数を確認する"""

import sys

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
TOKEN = env.get("LINE_CHANNEL_ACCESS_TOKEN", "")

# pushカウンターをNotionキューで確認（既実装）
# LINE Messaging API統計エンドポイントで今月の残通数確認
import datetime

today = datetime.date.today()
month_str = today.strftime("%Y%m")

r = requests.get(
    "https://api.line.me/v2/bot/message/quota/consumption", headers={"Authorization": f"Bearer {TOKEN}"}, timeout=10
)
print(f"quota/consumption: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"今月の使用通数: {data}")

r2 = requests.get("https://api.line.me/v2/bot/message/quota", headers={"Authorization": f"Bearer {TOKEN}"}, timeout=10)
print(f"quota: {r2.status_code}")
if r2.status_code == 200:
    print(f"プランの上限: {r2.json()}")
