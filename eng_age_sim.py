import datetime
import json
import urllib.request

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY")
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

# 全エンジニアの「稼働予定日」分布を取得
payload = {"page_size": 100}
all_pages = []
cursor = None
while True:
    if cursor:
        payload["start_cursor"] = cursor
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query",
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
    all_pages.extend(res.get("results", []))
    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")

today = datetime.date.today()
no_date = 0
future = 0
past_7 = 0
past_14 = 0
past_21 = 0
past_older = 0

for p in all_pages:
    props = p["properties"]
    created = p.get("created_time", "")[:10]
    created_date = datetime.date.fromisoformat(created) if created else None

    if created_date:
        diff = (today - created_date).days
        if diff <= 7:
            future += 1
        elif diff <= 14:
            past_7 += 1
        elif diff <= 21:
            past_14 += 1
        else:
            past_older += 1
    else:
        no_date += 1

print(f"総エンジニア数: {len(all_pages)}人")
print("\n=== 登録からの経過日数 ===")
print(f"  7日以内:  {future}人")
print(f"  8〜14日:  {past_7}人")
print(f"  15〜21日: {past_14}人")
print(f"  22日以上: {past_older}人")

# コストシミュレーション（USD→JPY 155円換算）
rate = 155
cost_per_call = 0.0094
active_projects = 3767

print("\n=== 絞り込み案シミュレーション ===")
print(f"案件: 2日以内 {active_projects}件（キーワード絞り込み後10件想定）")
filtered = 10

for eng_count, label in [
    (future, "7日以内のみ"),
    (future + past_7, "14日以内"),
    (future + past_7 + past_14, "21日以内（現状）"),
]:
    new_eng = 20  # 新着人材/日
    # 新着トリガー
    new_daily = new_eng * filtered * cost_per_call
    # 既存バッチ1日1回
    batch_daily = eng_count * filtered * cost_per_call
    total_daily = new_daily + batch_daily
    monthly_usd = total_daily * 30
    monthly_jpy = monthly_usd * rate
    print(f"\n  【{label} {eng_count}人】")
    print(f"    新着20人/日: ${new_daily:.2f}/日")
    print(f"    既存バッチ1回: ${batch_daily:.2f}/日")
    print(f"    月次: ${monthly_usd:.0f} / 約{monthly_jpy:,.0f}円")
