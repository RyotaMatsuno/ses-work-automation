import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
for m in list(sys.modules):
    if "line_query" in m:
        del sys.modules[m]

# ── ①から⑤の実際の案件詳細テキストをNotionから直接取得 ──

import line_query as lq

headers = {
    "Authorization": f"Bearer {lq.NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}
PROJECT_DB = lq.PROJECT_DB_ID

# HS北小金で実際にヒットする案件のうち上位5件の詳細を確認
prj_filter = {
    "and": [
        {"property": lq.PROP_STATUS, "select": {"equals": lq.VAL_RECRUITING}},
        {"property": lq.PROP_RATE, "number": {"greater_than": 0}},
    ]
}
pages = lq.fetch_all_pages(PROJECT_DB, filter_body=prj_filter)

# H.Sのスキルでマッチする案件を特定
hs_skills = ["Java", "JavaScript", "SQL Server", "Oracle", "Spring", "C#"]
hs_rate = 70.0

# dedup + フィルタ（engineer_queryと同じロジック）
seen = set()
deduped = []
for p in pages:
    k = lq._text_prop(p, lq.PROP_PJNAME)
    k20 = k[:20] if k else ""
    if k20 and k20 not in seen:
        seen.add(k20)
        deduped.append(p)

matched = []
for p in deduped:
    if lq.business_days_since(p.get("last_edited_time")) > 4:
        continue
    req = lq._multi_select_prop(p, lq.PROP_REQSK)
    if not req:
        continue
    if not lq.skill_match(req, hs_skills):
        continue
    budget = lq._number_prop(p, lq.PROP_RATE)
    if budget > 150:
        continue
    gross = lq.calc_gross_profit(budget, hs_rate)
    thresh = lq._gross_threshold(lq._select_prop(p, lq.PROP_ASSIGNEE))
    if gross < thresh:
        continue
    matched.append({"page": p, "gross": gross, "budget": budget})

matched.sort(key=lambda x: x["gross"], reverse=True)

print("=" * 70)
print(f"マッチ案件数: {len(matched)}件")
print("=" * 70)

for i, item in enumerate(matched[:5], 1):
    p = item["page"]
    name = lq._text_prop(p, lq.PROP_PJNAME)
    loc = lq._text_prop(p, lq.PROP_LOCATION)
    remote = lq._select_prop(p, lq.PROP_REMOTE)
    assignee = lq._select_prop(p, lq.PROP_ASSIGNEE)
    detail_raw = lq._text_prop(p, lq.PROP_PJDETAIL)

    print(f"\n【案件{i}】{name}")
    print(f"  budget={item['budget']}万 gross={item['gross']}万 loc=[{loc}] remote=[{remote}] assignee=[{assignee}]")
    print("  --- 案件詳細 先頭300文字 (RAW) ---")
    print(f"  {repr(detail_raw[:300])}")
    print("  --- _clean_detail 結果 ---")
    cleaned = lq._clean_detail(detail_raw)
    print(f"  {repr(cleaned[:200])}")
    print()
    print("  --- バグ分析 ---")

    # Bug1: remote が空で "()" が表示される
    if not remote:
        print(f'  [BUG-A] remote空欄: loc=[{loc}] remote=[] → 表示: "{loc}()"')

    # Bug2: assignee が空
    if not assignee:
        print('  [BUG-B] assignee空欄 → 表示: "粗利XX万 / 担当" or "粗利XX万"')

    # Bug3: _clean_detail が挨拶で始まっている
    greet_words = [
        "よろしくお願い",
        "でございます",
        "お世話になっております",
        "当社案件",
        "見合う要員",
        "技術者を探",
        "お願い申し上げます",
    ]
    for gw in greet_words:
        if cleaned.startswith(gw) or (len(cleaned) > 5 and cleaned[:10].find(gw) >= 0):
            print(f"  [BUG-C] _clean_detail が挨拶で始まる: 先頭=[{cleaned[:30]}]")
            break

    # Bug4: 単価が高すぎる（SES月額として100万超）
    if item["budget"] > 100:
        print(f"  [BUG-D] 単価{item['budget']}万 → SES月額として妥当性疑問（H.S単価70万, 粗利{item['gross']}万）")
