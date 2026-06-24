import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")

os.chdir(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")

from line_query import (
    ENGINEER_DB_ID,
    PROJECT_DB_ID,
    PROP_NAME,
    PROP_RATE,
    PROP_REQSK,
    PROP_SKILL,
    PROP_STATUS,
    VAL_ADJUSTING,
    VAL_RECRUITING,
    _gross_threshold,
    _match_initial,
    _match_station,
    _multi_select_prop,
    _number_prop,
    _select_prop,
    business_days_since,
    calc_gross_profit,
    fetch_all_pages,
)

print("=== H.S を直接検索 ===")
engineers = fetch_all_pages(ENGINEER_DB_ID)
hs_list = [e for e in engineers if _match_initial(e, "HS") and _match_station(e, "北小金")]
print(f"HS+北小金にマッチするエンジニア: {len(hs_list)}人")
for e in hs_list:
    name = _multi_select_prop(e, PROP_NAME) or e.get("properties", {}).get("名前", {})
    skills = _multi_select_prop(e, PROP_SKILL)
    rate = _number_prop(e, PROP_RATE)
    print(
        f"  name={e['properties'].get('名前', {}).get('title', [{}])[0].get('plain_text', '?')} skills={skills} rate={rate}"
    )

# 案件DBの状況
print("\n=== 案件DB: 単価あり募集中・調整中 ===")
from line_query import PROP_PJNAME, _text_prop

projects = fetch_all_pages(PROJECT_DB_ID, filter_body={"property": PROP_RATE, "number": {"greater_than": 0}})
recruiting = [p for p in projects if _select_prop(p, PROP_STATUS) in (VAL_RECRUITING, VAL_ADJUSTING)]
print(f"単価あり案件: {len(projects)}件 / うち募集中+調整中: {len(recruiting)}件")

# HSのスキルとマッチする案件を数える
if hs_list:
    hs = hs_list[0]
    hs_skills = _multi_select_prop(hs, PROP_SKILL)
    hs_rate = _number_prop(hs, PROP_RATE)
    print(f"\nHS スキル: {hs_skills} / 単価: {hs_rate}万")

    matched = []
    for p in recruiting:
        # 鮮度チェック
        age = business_days_since(p.get("last_edited_time"))
        if age > 4:
            continue
        req = _multi_select_prop(p, PROP_REQSK)
        if not req:
            continue
        budget = _number_prop(p, PROP_RATE)
        if budget > 150:
            continue
        gross = calc_gross_profit(budget, hs_rate)
        thresh = _gross_threshold(_select_prop(p, PROP_STATUS))
        if gross < thresh:
            continue
        # スキルマッチ
        from line_query import skill_match

        if not skill_match(req, hs_skills):
            continue
        matched.append({"name": _text_prop(p, PROP_PJNAME), "budget": budget, "gross": gross, "req": req, "age": age})

    print(f"\nHS にマッチする案件: {len(matched)}件")
    for m in matched[:25]:
        print(f"  [{m['age']}日前] {m['name'][:35]} 単価:{m['budget']}万 粗利:{m['gross']}万 必須:{m['req']}")
