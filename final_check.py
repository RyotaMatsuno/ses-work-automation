
# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# バージョン表記をv12に更新
content = content.replace('LINE Webhook Server v10', 'LINE Webhook Server v12')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("バージョン表記更新完了")

# 現在の稼働可能エンジニアリスト確認
import requests, os, json
from dotenv import load_dotenv
load_dotenv(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')

NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
ENGINEER_DB = '343450ff-37c0-819d-8769-fb0a8a4ceeb1'
headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

res = requests.post(f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query",
    headers=headers, json={"filter": {"property": "稼働状況", "select": {"equals": "稼働可能"}}, "page_size": 50})
pages = res.json().get("results", [])
print(f"\n=== 稼働可能エンジニア（修正後）{len(pages)}件 ===")
for p in pages:
    props = p["properties"]
    name = props.get("名前", {}).get("title", [{}])[0].get("plain_text", "?")
    price = props.get("単価（万円）", {}).get("number", 0) or 0
    skills = [o["name"] for o in props.get("スキル", {}).get("multi_select", [])]
    print(f"  {name} / {price}万 / {','.join(skills[:4])}")
