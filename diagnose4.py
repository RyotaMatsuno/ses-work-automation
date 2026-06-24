import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# VAL_RECRUITINGの値を確認
val = bytes.fromhex("e58b9fe99b86e4b8ad").decode("utf-8")
print(f'VAL_RECRUITING = "{val}"')

# Notionの実際のステータス値と一致するか確認
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_TOKEN") or config.get("NOTION_API_KEY")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# 募集中でフィルタして件数確認
r = requests.post(
    f"https://api.notion.com/v1/databases/{PROJECT_DB}/query",
    headers=headers,
    json={"page_size": 1, "filter": {"property": "ステータス", "select": {"equals": val}}},
)
d = r.json()
print(f"「{val}」でフィルタしたAPI結果: status={r.status_code}")

# 単価75以上 + 募集中 のフィルタテスト
r2 = requests.post(
    f"https://api.notion.com/v1/databases/{PROJECT_DB}/query",
    headers=headers,
    json={
        "page_size": 1,
        "filter": {
            "and": [
                {"property": "単価（万円）", "number": {"greater_than_or_equal_to": 75}},
                {"property": "ステータス", "select": {"equals": val}},
            ]
        },
    },
)
d2 = r2.json()
print(f"単価75以上+募集中: status={r2.status_code}")
if r2.status_code == 200:
    print(f"  ヒット件数(1ページ目): {len(d2.get('results', []))}件, has_more={d2.get('has_more')}")
else:
    print(f"  エラー: {r2.text[:200]}")

print()
print("=== line_webhook/line_query.pyのエンジニアクエリで実際に何件取れるか ===")
# _prj_filterが機能しているか直接テスト
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
import os

for k, v in config.items():
    os.environ.setdefault(k, v)

# importリセット
if "line_query" in sys.modules:
    del sys.modules["line_query"]
from line_query import PROJECT_DB_ID, PROP_RATE, PROP_STATUS, VAL_RECRUITING, fetch_all_pages

prj_filter = {
    "and": [
        {"property": PROP_RATE, "number": {"greater_than_or_equal_to": 75}},
        {"property": PROP_STATUS, "select": {"equals": VAL_RECRUITING}},
    ]
}
print(f'PROP_RATE = "{PROP_RATE}"')
print(f'PROP_STATUS = "{PROP_STATUS}"')
print(f'VAL_RECRUITING = "{VAL_RECRUITING}"')

projects = fetch_all_pages(PROJECT_DB_ID, filter_body=prj_filter)
print(f"フィルタ後の案件数: {len(projects)}件")
print()

# 鮮度フィルタ後
from line_query import business_days_since

fresh_projects = [p for p in projects if business_days_since(p.get("last_edited_time", "2020-01-01")) <= 4]
print(f"4営業日以内: {fresh_projects.__len__()}件")

# スキルありに絞ると
from line_query import PROP_REQSK, _multi_select_prop

skill_projects = [p for p in fresh_projects if _multi_select_prop(p, PROP_REQSK)]
print(f"さらにスキルあり: {len(skill_projects)}件")
