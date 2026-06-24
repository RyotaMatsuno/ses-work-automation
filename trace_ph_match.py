# -*- coding: utf-8 -*-
import json
import sys
import urllib.request

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# webhook_server.pyのrun_reverse_matchingをローカルでシミュレート
env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
TOKEN = env.get("NOTION_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
CASE_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"


def npost(path, payload):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


# PHさんの情報
ph = {"name": "P.H", "skills": ["PMO"], "price": 32}

# 今日の案件を取得してフィルタを追跡
print("=== PHさん(32万/PMO)の逆マッチング 除外理由トレース ===\n")
res = npost(
    f"databases/{CASE_DB}/query",
    {
        "filter": {
            "or": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
                {"property": "ステータス", "select": {"equals": "稼働中"}},
            ]
        },
        "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        "page_size": 30,
    },
)

eng_skills = set(ph["skills"])
eng_price = ph["price"]
skip_skill = skip_gross_floor = skip_gross_cap = passed = 0
skip_examples = []
pass_examples = []

for page in res.get("results", []):
    props = page["properties"]
    name_items = props.get("案件名", {}).get("title", [])
    name = name_items[0].get("plain_text", "") if name_items else ""
    req_skills = set(o["name"] for o in props.get("必要スキル", {}).get("multi_select", []))
    proj_price = props.get("単価（万円）", {}).get("number") or 0

    # フィルタ1: スキル（必須スキルが1つもマッチしない）
    if req_skills and not any(s in eng_skills for s in req_skills):
        skip_skill += 1
        if len(skip_examples) < 3:
            skip_examples.append(f"  スキルNG: {name[:30]} 必須={req_skills}")
        continue

    # フィルタ2: 粗利下限5万
    gross = (proj_price - eng_price) if (proj_price > 0 and eng_price > 0) else 0
    if eng_price > 0 and proj_price > 0 and gross < 5:
        skip_gross_floor += 1
        continue

    # フィルタ3: 粗利上限15万（今回撤廃した部分）
    if eng_price > 0 and proj_price > 0 and gross > 15:
        skip_gross_cap += 1
        if len(pass_examples) < 2:
            pass_examples.append(f"  上限超: {name[:30]} 案件{proj_price}万 粗利{gross}万")
        # 撤廃後はここをpassする
        pass

    passed += 1
    if len(pass_examples) < 5:
        pass_examples.append(f"  PASS: {name[:30]} 案件{proj_price}万 粗利{gross}万 必須={req_skills}")

print(f"スキルNG（必須不一致）: {skip_skill}件")
print(f"粗利下限NG（5万未満）: {skip_gross_floor}件")
print(f"粗利上限超（15万超→撤廃済）: {skip_gross_cap}件")
print(f"通過: {passed}件")
print()
for ex in skip_examples:
    print(ex)
print()
print("通過例:")
for ex in pass_examples[:5]:
    print(ex)
