import datetime
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
lq_path = os.path.join(lw, "line_query.py")

# バックアップ
bak = lq_path + f".bak_{datetime.date.today().strftime('%m%d')}_gross_cap"
shutil.copy(lq_path, bak)
print(f"Backup: {bak}")

with open(lq_path, encoding="utf-8") as f:
    content = f.read()

# engineer_query (L347-352): budget > 150 除外の直後に gross > 15 除外を追加
OLD_EQ = """            budget = _number_prop(project, PROP_RATE)
            if budget > 150:
                continue  # 異常単価除外
            gross  = calc_gross_profit(budget, eng_rate)
            thresh = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))
            if gross < thresh:
                continue"""

NEW_EQ = """            budget = _number_prop(project, PROP_RATE)
            if budget > 150:
                continue  # 異常単価除外
            gross  = calc_gross_profit(budget, eng_rate)
            if gross > 15:
                continue  # 粗利上限15万超は単価乖離大きすぎ・スキルミスマッチリスク
            thresh = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))
            if gross < thresh:
                continue"""

# project_query (L367-380): gross < threshold の直前に gross > 15 を追加
OLD_PQ = """        gross = calc_gross_profit(budget, _number_prop(eng, PROP_RATE))
        if gross < threshold:
            continue"""

NEW_PQ = """        gross = calc_gross_profit(budget, _number_prop(eng, PROP_RATE))
        if gross > 15:
            continue  # 粗利上限15万超は単価乖離大きすぎ・スキルミスマッチリスク
        if gross < threshold:
            continue"""

patched = 0
if OLD_EQ in content:
    content = content.replace(OLD_EQ, NEW_EQ)
    patched += 1
    print("PATCHED: engineer_query gross cap")
else:
    print("NOT FOUND: engineer_query block")

if OLD_PQ in content:
    content = content.replace(OLD_PQ, NEW_PQ)
    patched += 1
    print("PATCHED: project_query gross cap")
else:
    print("NOT FOUND: project_query block")

if patched == 2:
    with open(lq_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n{patched}箇所パッチ適用済み。ファイル保存完了。")
else:
    print(f"\n{patched}箇所しかパッチできなかった。保存中断。")
