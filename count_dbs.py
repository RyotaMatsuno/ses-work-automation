import json
import urllib.request

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"


def count_db(db_id, filter_body=None):
    payload = {"page_size": 100}
    if filter_body:
        payload["filter"] = filter_body
    count = 0
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
        count += len(res.get("results", []))
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    return count


# 全案件数
total_projects = count_db(PROJECT_DB)

# 有効案件（4営業日以内）※簡易的に全件取得して確認
import datetime

today = datetime.date.today()

# 提案対象エンジニア数
eng_total = count_db(ENGINEER_DB)
eng_active = count_db(ENGINEER_DB, {"property": "提案対象", "checkbox": {"equals": True}})

print(f"案件DB 総数: {total_projects}")
print(f"エンジニアDB 総数: {eng_total}")
print(f"エンジニアDB 提案対象: {eng_active}")
