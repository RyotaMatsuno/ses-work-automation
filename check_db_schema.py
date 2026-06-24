import sys

import requests
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# ステータスフィールドの正確な情報をDB定義から確認
res = requests.get("https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c", headers=headers)
db = res.json()
props = db.get("properties", {})

# ステータス関連フィールドを探す
for k, v in props.items():
    if v.get("type") in ("select", "status"):
        sys.stdout.buffer.write(f"{k!r} type={v['type']} id={v.get('id')!r}\n".encode("utf-8"))
        opts = v.get("select", {}).get("options", []) or v.get("status", {}).get("options", [])
        for opt in opts[:5]:
            sys.stdout.buffer.write(f"  option: {opt.get('name')!r}\n".encode("utf-8"))
