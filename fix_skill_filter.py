import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# engineer_query の projects フィルタと内部マッチングロジックを修正
# 修正1: Notionフィルタに単価>=75を追加（BUG-9の再設計）
#   岡本案件は閾値3万だが、単価73-74万の案件は75未満なので弾かれる
#   しかし実務上は単価75万未満の案件に70万エンジニアを提案しない（粗利5万以下）
#   → PROP_RATE>=75フィルタ復活が正しい
# 修正2: スキル空案件を完全除外（`if not required: continue`）
#   スキル未設定案件はマッチング対象外とする

OLD_QUERY_LOOP = """    replies = []
    for engineer in matched_engineers:
        eng_skills = _multi_select_prop(engineer, PROP_SKILL)
        eng_rate   = _number_prop(engineer, PROP_RATE)
        matched: list[dict] = []
        for project in projects:
            # 鮮度チェック: 4営業日以内
            if business_days_since(project.get("last_edited_time")) > 4:
                continue
            required = _multi_select_prop(project, PROP_REQSK)
            if not skill_match(required, eng_skills):
                continue
            budget = _number_prop(project, PROP_RATE)
            gross  = calc_gross_profit(budget, eng_rate)
            thresh = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))
            # スキル未設定案件はノイズ削減のため粗利10万以上のみ
            if not required and gross < 10:
                continue
            if gross < thresh:
                continue
            matched.append({"page": project, "gross_profit": gross})
        matched.sort(key=lambda x: x["gross_profit"], reverse=True)
        replies.append(format_project_result(engineer, matched))
    return "\\n\\n".join(replies)"""

NEW_QUERY_LOOP = """    replies = []
    for engineer in matched_engineers:
        eng_skills = _multi_select_prop(engineer, PROP_SKILL)
        eng_rate   = _number_prop(engineer, PROP_RATE)
        matched: list[dict] = []
        for project in projects:
            # 鮮度チェック: 4営業日以内
            if business_days_since(project.get("last_edited_time")) > 4:
                continue
            required = _multi_select_prop(project, PROP_REQSK)
            # スキル未設定案件はマッチング対象外
            if not required:
                continue
            if not skill_match(required, eng_skills):
                continue
            budget = _number_prop(project, PROP_RATE)
            gross  = calc_gross_profit(budget, eng_rate)
            thresh = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))
            if gross < thresh:
                continue
            matched.append({"page": project, "gross_profit": gross})
        matched.sort(key=lambda x: x["gross_profit"], reverse=True)
        replies.append(format_project_result(engineer, matched))
    return "\\n\\n".join(replies)"""

if OLD_QUERY_LOOP in src:
    src = src.replace(OLD_QUERY_LOOP, NEW_QUERY_LOOP, 1)
    print("✅ engineer_query: スキル空案件を完全除外 OK")
else:
    print("❌ パターン不一致")
    idx = src.find("def engineer_query")
    print(src[idx : idx + 1200])

# Notionフィルタも単価>=75に戻す（900万案件でも75以上は通る → スキルフィルタで弾く）
# → 単価フィルタは不要（スキルフィルタで十分）
# → ただし単価0万の案件（無効データ）を弾くためrate>0フィルタを追加

OLD_FILTER = """    # FIX-BUG9: フィルタはステータス=募集中のみ。単価フィルタは撤廃して後段で担当者別粗利チェック
    _prj_filter = {
        "property": PROP_STATUS,
        "select": {"equals": VAL_RECRUITING},
    }"""

NEW_FILTER = """    # 案件フィルタ: ステータス=募集中 かつ 単価>0（無効データ除外）
    # スキル空案件は後段で除外するのでここではフィルタしない
    _prj_filter = {
        "and": [
            {"property": PROP_STATUS, "select": {"equals": VAL_RECRUITING}},
            {"property": PROP_RATE,   "number": {"greater_than": 0}},
        ]
    }"""

if OLD_FILTER in src:
    src = src.replace(OLD_FILTER, NEW_FILTER, 1)
    print("✅ engineer_query フィルタ: 単価>0フィルタ追加 OK")
else:
    print("❌ フィルタパターン不一致")

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

# line_query/line_query.py も同期
path2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"
with open(path2, "r", encoding="utf-8") as f:
    src2 = f.read()
if OLD_QUERY_LOOP in src2:
    src2 = src2.replace(OLD_QUERY_LOOP, NEW_QUERY_LOOP, 1)
    print("✅ line_query/line_query.py: スキル空除外 OK")
if OLD_FILTER in src2:
    src2 = src2.replace(OLD_FILTER, NEW_FILTER, 1)
    print("✅ line_query/line_query.py: フィルタ OK")
with open(path2, "w", encoding="utf-8") as f:
    f.write(src2)

# 構文チェック
for p in [path, path2]:
    r = subprocess.run(["python", "-m", "py_compile", p], capture_output=True, text=True)
    fname = "/".join(p.split("\\")[-2:])
    print(f"{'✅' if r.returncode == 0 else '❌'} {fname}: 構文{'OK' if r.returncode == 0 else r.stderr[:100]}")
