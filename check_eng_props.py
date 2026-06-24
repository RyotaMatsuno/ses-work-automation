import json
import urllib.request

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY")
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

# 1件取得してプロパティ確認
payload = {"page_size": 1}
data = json.dumps(payload).encode()
req = urllib.request.Request(
    f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query",
    data=data,
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=15) as r:
    res = json.loads(r.read())

page = res["results"][0]
print("=== エンジニアDBプロパティ一覧 ===")
for k, v in page["properties"].items():
    vtype = v.get("type")
    val = ""
    if vtype == "date" and v.get("date"):
        val = v["date"].get("start", "")
    elif vtype == "created_time":
        val = v.get("created_time", "")
    elif vtype == "select" and v.get("select"):
        val = v["select"].get("name", "")
    elif vtype == "checkbox":
        val = v.get("checkbox", "")
    print(f"  {k} ({vtype}): {val}")
