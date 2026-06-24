import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

import requests
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = env.get("NOTION_TOKEN") or env.get("NOTION_API_KEY")
db_id = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# 3件だけ取得してプロパティ確認
resp = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=headers, json={"page_size": 3})
data = resp.json()

if data.get("results"):
    props = data["results"][0].get("properties", {})
    print("=== プロパティ一覧 ===")
    for k, v in props.items():
        vtype = v.get("type")
        # 値のサマリー
        val = ""
        if vtype == "rich_text":
            val = "".join([t["plain_text"] for t in v.get("rich_text", [])])[:80]
        elif vtype == "title":
            val = "".join([t["plain_text"] for t in v.get("title", [])])[:80]
        elif vtype == "select":
            val = v.get("select", {}).get("name", "") if v.get("select") else ""
        elif vtype == "multi_select":
            val = ", ".join([x["name"] for x in v.get("multi_select", [])])[:80]
        elif vtype == "number":
            val = str(v.get("number", ""))
        elif vtype == "checkbox":
            val = str(v.get("checkbox", ""))
        elif vtype == "date":
            val = str(v.get("date", ""))
        print(f"  [{vtype}] {k}: {val}")

    print("\n=== 2件目も確認 ===")
    if len(data["results"]) > 1:
        p2 = data["results"][1].get("properties", {})
        # スキル系フィールドのみ表示
        skill_keywords = ["スキル", "skill", "java", "python", "言語", "経験", "技術"]
        for k, v in p2.items():
            if any(kw.lower() in k.lower() for kw in skill_keywords):
                vtype = v.get("type")
                val = ""
                if vtype == "rich_text":
                    val = "".join([t["plain_text"] for t in v.get("rich_text", [])])[:200]
                elif vtype == "multi_select":
                    val = ", ".join([x["name"] for x in v.get("multi_select", [])])
                elif vtype == "title":
                    val = "".join([t["plain_text"] for t in v.get("title", [])])[:200]
                print(f"  [{vtype}] {k}: {val}")
else:
    print("Error:", data)
