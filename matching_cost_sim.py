import json
import urllib.request

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"


def count_db(db_id):
    payload = {"page_size": 100}
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


total_projects = count_db(PROJECT_DB)
total_engineers = count_db(ENGINEER_DB)
print(f"案件DB: {total_projects}件")
print(f"エンジニアDB: {total_engineers}人")

# 1回のAPI呼び出しコスト（今朝の実績から）
cost_per_call = 0.0094
# 改善後の構造シミュレーション
new_engineers_per_day = 30
existing_engineers = total_engineers
batch_times_per_day = 2  # 既存人員は1日2回

# 新着人員トリガー：30人×有効案件
# 有効案件は全案件の一部（4営業日以内）。仮に全体の20%と仮定
active_projects = int(total_projects * 0.2)

calls_new_eng = new_engineers_per_day * active_projects
calls_existing = existing_engineers * active_projects * batch_times_per_day

total_calls = calls_new_eng + calls_existing
daily_cost = total_calls * cost_per_call
monthly_cost = daily_cost * 30

print("\n=== 改善後シミュレーション ===")
print(f"有効案件（推定20%）: {active_projects}件")
print(f"新着人員トリガー: {new_engineers_per_day}人 × {active_projects}案件 = {calls_new_eng}回/日")
print(f"既存人員バッチ: {existing_engineers}人 × {active_projects}案件 × 2回 = {calls_existing}回/日")
print(f"合計: {total_calls}回/日")
print(f"日次コスト: ${daily_cost:.2f}")
print(f"月次コスト: ${monthly_cost:.2f}")
