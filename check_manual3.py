import sys

sys.stdout.reconfigure(encoding="utf-8")
import requests
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# 手動登録3件のpage_id
targets = [
    "360450ff-37c0-811d-9a67-eef211dc351f",  # U.H
    "360450ff-37c0-8137-9dc1-e11b8e6a022c",  # R.H
    "360450ff-37c0-81cc-bf28-cc3c8969fd0a",  # OA
]

for pid in targets:
    r = requests.get(f"https://api.notion.com/v1/pages/{pid}", headers=headers)
    p = r.json()
    props = p["properties"]

    def gp(name):
        prop = props.get(name, {})
        t = prop.get("type", "")
        if t == "title":
            return "".join(i.get("plain_text", "") for i in prop.get("title", []))
        if t == "rich_text":
            return "".join(i.get("plain_text", "") for i in prop.get("rich_text", []))
        if t == "email":
            return prop.get("email") or ""
        if t == "select":
            s = prop.get("select")
            return s["name"] if s else ""
        return ""

    name = gp("\u540d\u524d")
    biko = gp("\u5099\u8003\uff08LINE\u30e1\u30e2\uff09")
    affil = gp("\u6240\u5c5e\u4f1a\u793e") or gp("\u6240\u5c5e\u4f1a\u793e\u540d")
    print(f"\n=== {name} ({pid}) ===")
    print(f"所属会社: {affil!r}")
    print(f"備考全文:\n{biko}")
    print()
