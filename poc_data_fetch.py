import datetime
import json
import urllib.request

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"


def query_all(db_id, filter_obj=None):
    payload = {"page_size": 100}
    if filter_obj:
        payload["filter"] = filter_obj
    pages = []
    cursor = None
    while True:
        if cursor:
            payload["start_cursor"] = cursor
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            res = json.loads(r.read())
        pages.extend(res.get("results", []))
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    return pages


def get_text(prop, key):
    p = prop.get(key, {})
    ptype = p.get("type", "")
    if ptype == "title":
        return "".join(t.get("plain_text", "") for t in p.get("title", []))
    elif ptype == "rich_text":
        return "".join(t.get("plain_text", "") for t in p.get("rich_text", []))
    elif ptype == "multi_select":
        return ", ".join(s["name"] for s in p.get("multi_select", []))
    elif ptype == "select" and p.get("select"):
        return p["select"].get("name", "")
    elif ptype == "number":
        return str(p.get("number", ""))
    return ""


# エンジニア全取得
engineers = query_all(ENGINEER_DB)
eng_data = []
for e in engineers:
    p = e["properties"]
    eng_data.append(
        {
            "id": e["id"],
            "name": get_text(p, "氏名"),
            "skills": get_text(p, "スキル"),
            "detail": get_text(p, "人材情報原本"),
            "price": get_text(p, "単価（万円）"),
        }
    )

# 案件最新100件取得
two_days_ago = (
    datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))) - datetime.timedelta(days=2)
).strftime("%Y-%m-%dT%H:%M:%S+09:00")
projects = query_all(PROJECT_DB, {"timestamp": "created_time", "created_time": {"after": two_days_ago}})
proj_data = []
for p in projects[:100]:  # 最新100件
    pr = p["properties"]
    proj_data.append(
        {
            "id": p["id"],
            "name": get_text(pr, "案件名"),
            "skills": get_text(pr, "必要スキル"),
            "detail": get_text(pr, "案件詳細"),
            "price": get_text(pr, "単価（万円）"),
        }
    )

# 保存
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\poc_engineers.json", "w", encoding="utf-8") as f:
    json.dump(eng_data, f, ensure_ascii=False, indent=2)
with open(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\poc_projects.json", "w", encoding="utf-8") as f:
    json.dump(proj_data, f, ensure_ascii=False, indent=2)

print(f"エンジニア: {len(eng_data)}人")
print(f"案件: {len(proj_data)}件")

# データの中身サンプル
print("\n=== エンジニアサンプル ===")
for e in eng_data[:2]:
    print(f"  {e['name']} | skills: {e['skills'][:80]} | price: {e['price']}")

print("\n=== 案件サンプル ===")
for p in proj_data[:3]:
    print(f"  {p['name'][:50]} | skills: {p['skills'][:60]} | detail: {p['detail'][:50]}")
