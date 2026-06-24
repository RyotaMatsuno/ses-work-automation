from datetime import datetime, timedelta

import requests
from dotenv import dotenv_values

# jpholidayがあれば営業日計算に使う
try:
    import jpholiday

    HAS_JPHOLIDAY = True
except ImportError:
    HAS_JPHOLIDAY = False

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
API_KEY = env.get("NOTION_API_KEY", "")
PROJECT_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def is_business_day(d):
    if d.weekday() >= 5:
        return False
    if HAS_JPHOLIDAY and jpholiday.is_holiday(d):
        return False
    return True


def subtract_business_days(from_date, n_days):
    current = from_date
    count = 0
    while count < n_days:
        current -= timedelta(days=1)
        if is_business_day(current):
            count += 1
    return current


# 4営業日前の日付を算出
today = datetime.now().date()
cutoff = subtract_business_days(today, 4)
print(f"today: {today}, cutoff(4biz days ago): {cutoff}")

# 募集中案件のうち、作成日がcutoff以降のものを数える
results = []
payload = {"page_size": 100, "filter": {"property": "ステータス", "select": {"equals": "募集中"}}}
while True:
    r = requests.post(
        f"https://api.notion.com/v1/databases/{PROJECT_DB_ID}/query", headers=HEADERS, json=payload, timeout=30
    )
    data = r.json()
    results.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    payload["start_cursor"] = data["next_cursor"]

total = len(results)
fresh = 0
old = 0
no_date = 0
for page in results:
    created = page.get("created_time", "")[:10]
    if not created:
        no_date += 1
        continue
    created_date = datetime.strptime(created, "%Y-%m-%d").date()
    if created_date >= cutoff:
        fresh += 1
    else:
        old += 1

print(f"total: {total}, fresh(4biz内): {fresh}, old: {old}, no_date: {no_date}")

# スキル要件ありの案件数
has_skills = 0
for page in results:
    props = page["properties"]
    req = [item["name"] for item in props.get("必要スキル", {}).get("multi_select", [])]
    opt = [item["name"] for item in props.get("尚可スキル", {}).get("multi_select", [])]
    if req or opt:
        has_skills += 1
print(f"skills populated: {has_skills}/{total}")
