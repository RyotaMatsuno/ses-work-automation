import datetime
import json
import urllib.request
from collections import defaultdict

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


# 2日以内の案件のスキル分布
two_days_ago = (
    datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))) - datetime.timedelta(days=2)
).strftime("%Y-%m-%dT%H:%M:%S+09:00")
projects = query_all(PROJECT_DB, {"timestamp": "created_time", "created_time": {"after": two_days_ago}})

# 案件のスキルタグ集計
project_skills = defaultdict(int)
no_skill_projects = 0
for p in projects:
    skills = [s["name"] for s in p["properties"].get("必要スキル", {}).get("multi_select", [])]
    if not skills:
        no_skill_projects += 1
    for s in skills:
        project_skills[s] += 1

print(f"2日以内の案件: {len(projects)}件")
print(f"スキルタグなし案件: {no_skill_projects}件")
print(f"上位スキル: {sorted(project_skills.items(), key=lambda x: -x[1])[:15]}")

# エンジニアのスキル分布
engineers = query_all(ENGINEER_DB)
eng_skills_all = set()
for e in engineers:
    skills = [s["name"] for s in e["properties"].get("スキル", {}).get("multi_select", [])]
    eng_skills_all.update(skills)

print(f"\nエンジニア数: {len(engineers)}人")
print(f"エンジニアスキル種類: {len(eng_skills_all)}種")

# スキル一致でフィルタした場合の想定マッチ数
matched = 0
total_pairs = 0
for p in projects:
    p_skills = set(s["name"] for s in p["properties"].get("必要スキル", {}).get("multi_select", []))
    if not p_skills:
        continue
    for e in engineers:
        e_skills = set(s["name"] for s in e["properties"].get("スキル", {}).get("multi_select", []))
        total_pairs += 1
        if p_skills & e_skills:  # 1つでも一致
            matched += 1

print("\nスキルタグ一致フィルタ結果:")
print(f"  全ペア: {total_pairs}組")
print(f"  スキル一致: {matched}組")
print(f"  絞り込み率: {(1 - matched / total_pairs) * 100:.1f}%削減" if total_pairs else "N/A")

# コスト試算
cost_per_call = 0.0094
# diff方式: 1日に新着案件は何件か？（2日分÷2で概算）
new_projects_per_day = len(projects) // 2
# 新着案件×スキル一致エンジニア（平均）
avg_match_per_project = (
    matched / len([p for p in projects if p["properties"].get("必要スキル", {}).get("multi_select", [])])
    if projects
    else 0
)

daily_calls_new = new_projects_per_day * avg_match_per_project
# 既存バッチ1日1回: 全エンジニア×新着案件
daily_calls_batch = len(engineers) * new_projects_per_day * (matched / total_pairs if total_pairs else 0.1)

print("\n=== diff+スキルフィルタ設計のコスト試算 ===")
print(f"新着案件/日（推定）: {new_projects_per_day}件")
print(f"平均スキル一致エンジニア/案件: {avg_match_per_project:.1f}人")
print(f"新着案件トリガー: {daily_calls_new:.0f}回/日 → ${daily_calls_new * cost_per_call:.2f}/日")
print(f"既存バッチ1回: {daily_calls_batch:.0f}回/日 → ${daily_calls_batch * cost_per_call:.2f}/日")
total_daily = (daily_calls_new + daily_calls_batch) * cost_per_call
print(f"合計: ${total_daily:.2f}/日 → 月${total_daily * 30:.0f} / 約{total_daily * 30 * 155:,.0f}円")
