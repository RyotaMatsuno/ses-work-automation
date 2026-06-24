import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import requests
from dotenv import dotenv_values

cfg = dotenv_values("../config/.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
eng_db = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

res = requests.post(f"https://api.notion.com/v1/databases/{eng_db}/query", headers=headers, json={"page_size": 1})
data = res.json()
if not data.get("results"):
    print("No results")
    sys.exit(1)

page = data["results"][0]
props = page.get("properties", {})
keys = list(props.keys())

# 各プロパティ名のUnicodeコードポイントを表示
print("All property keys (unicode repr):")
for k in keys:
    print(f"  {repr(k)}: type={props[k].get('type')}")

# ターゲットキーが存在するか確認
targets = [
    "\u30a4\u30cb\u30b7\u30e3\u30eb",  # イニシャル
    "\u540d\u524d",  # 名前
    "\u6700\u5bc4\u308a\u99c5",  # 最寄り駅
    "\u5099\u8003\uff08LINE\u30e1\u30e2\uff09",  # 備考（LINEメモ）
]

print("\nTarget key check:")
for t in targets:
    found = t in keys
    print(f"  {repr(t)}: {'FOUND' if found else 'NOT FOUND'}")
