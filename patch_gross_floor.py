import datetime
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8")
import os

lw = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook"
lq_path = os.path.join(lw, "line_query.py")

bak = lq_path + f".bak_{datetime.date.today().strftime('%m%d')}_gross_floor"
shutil.copy(lq_path, bak)
print(f"Backup: {bak}")

with open(lq_path, encoding="utf-8") as f:
    content = f.read()

# engineer_query: gross < thresh → gross < 0
OLD_EQ = """            if gross > 15:
                continue  # 粗利上限15万超は単価乖離大きすぎ・スキルミスマッチリスク
            thresh = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))
            if gross < thresh:
                continue"""

NEW_EQ = """            if gross > 15:
                continue  # 粗利上限15万超は単価乖離大きすぎ・スキルミスマッチリスク
            if gross < 0:
                continue  # 粗利マイナス=交渉しても利益見込めない"""

# project_query: gross < threshold → gross < 0
OLD_PQ = """        if gross > 15:
            continue  # 粗利上限15万超は単価乖離大きすぎ・スキルミスマッチリスク
        if gross < threshold:
            continue"""

NEW_PQ = """        if gross > 15:
            continue  # 粗利上限15万超は単価乖離大きすぎ・スキルミスマッチリスク
        if gross < 0:
            continue  # 粗利マイナス=交渉しても利益見込めない"""

patched = 0
if OLD_EQ in content:
    content = content.replace(OLD_EQ, NEW_EQ)
    patched += 1
    print("PATCHED: engineer_query gross floor")
else:
    print("NOT FOUND: engineer_query block")

if OLD_PQ in content:
    content = content.replace(OLD_PQ, NEW_PQ)
    patched += 1
    print("PATCHED: project_query gross floor")
else:
    print("NOT FOUND: project_query block")

if patched == 2:
    with open(lq_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n{patched}箇所パッチ完了。保存済み。")
else:
    print(f"\n{patched}箇所のみ。保存中断。")
