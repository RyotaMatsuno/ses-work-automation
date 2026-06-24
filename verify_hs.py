import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_TOKEN") or config.get("NOTION_API_KEY")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# H.Sレコード確認
r = requests.get("https://api.notion.com/v1/pages/36c450ff-37c0-813b-8f31-d38228e3cf2e", headers=headers, timeout=15)
props = r.json().get("properties", {})


def gtext(p, key):
    prop = p.get(key, {})
    if prop.get("type") == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif prop.get("type") == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    elif prop.get("type") == "select":
        return (prop.get("select") or {}).get("name", "")
    elif prop.get("type") == "number":
        return str(prop.get("number", ""))
    elif prop.get("type") == "date":
        return (prop.get("date") or {}).get("start", "")
    elif prop.get("type") == "multi_select":
        return ", ".join(o.get("name", "") for o in prop.get("multi_select", []))
    return ""


print("=== H.Sのレコード（更新後確認） ===")
fields = ["名前", "イニシャル", "最寄り駅", "単価（万円）", "稼働状況", "稼働可能日", "スキル", "担当者"]
for f in fields:
    print(f"  {f}: [{gtext(props, f)}]")
print()
print("✅ イニシャル・最寄り駅が正しく設定されていれば本番テスト準備完了")
