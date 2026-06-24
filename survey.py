import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_TOKEN") or config.get("NOTION_API_KEY")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

# ① エンジニアDBの全プロパティを確認（所属関連）
r = requests.post(
    f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=headers, json={"page_size": 1}, timeout=15
)
props = r.json()["results"][0]["properties"]
print("=== エンジニアDB 所属関連プロパティ hex確認 ===")
for k in sorted(props.keys()):
    if "所属" in k or "メール" in k or "担当" in k:
        hex_str = k.encode("utf-8").hex()
        print(f"  [{k}] hex={hex_str}")

print()
# ② H.Sの所属情報を確認
r2 = requests.get("https://api.notion.com/v1/pages/36c450ff-37c0-813b-8f31-d38228e3cf2e", headers=headers, timeout=15)
hs_props = r2.json().get("properties", {})
print("=== H.S所属情報（現在値） ===")
for k in ["所属会社", "所属会社名", "所属担当者名", "所属メール", "メール", "連絡先"]:
    if k in hs_props:
        p = hs_props[k]
        ptype = p.get("type")
        if ptype == "rich_text":
            val = "".join(t.get("plain_text", "") for t in p.get("rich_text", []))
        elif ptype == "title":
            val = "".join(t.get("plain_text", "") for t in p.get("title", []))
        elif ptype == "email":
            val = p.get("email", "")
        else:
            val = str(p.get(ptype, ""))
        print(f"  {k}: [{val}]")

print()
# ③ 案件詳細の実際の内容を確認（重複案件の詳細）
r3 = requests.post(
    "https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c/query",
    headers=headers,
    json={"page_size": 5, "filter": {"property": "ステータス", "select": {"equals": "募集中"}}},
    timeout=15,
)
pages = r3.json().get("results", [])
print("=== 案件詳細の先頭（内容確認） ===")
for p in pages[:3]:
    name_t = p["properties"].get("案件名", {}).get("title", [])
    name = "".join(t.get("plain_text", "") for t in name_t)
    detail_t = p["properties"].get("案件詳細", {}).get("rich_text", [])
    detail = "".join(t.get("plain_text", "") for t in detail_t)
    print(f"案件名: {name[:40]}")
    print(f"詳細先頭: {detail[:200]}")
    print()
