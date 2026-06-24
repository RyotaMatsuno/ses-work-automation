import io
import subprocess
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# engineer_query の内部ループに単価上限フィルタを追加
# 月単価の上限: SES業界で200万を超える案件は異常値と判断
# エンジニア単価 70万 → 案件単価は最大でも 200万程度が現実的

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

OLD = """            budget = _number_prop(project, PROP_RATE)
            gross  = calc_gross_profit(budget, eng_rate)
            thresh = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))
            if gross < thresh:
                continue"""

NEW = """            budget = _number_prop(project, PROP_RATE)
            # 単価が200万超は時給/年額等の異常データとして除外
            if budget > 200:
                continue
            gross  = calc_gross_profit(budget, eng_rate)
            thresh = _gross_threshold(_select_prop(project, PROP_ASSIGNEE))
            if gross < thresh:
                continue"""

if OLD in src:
    src = src.replace(OLD, NEW, 1)
    print("✅ 単価200万超フィルタ追加 OK")
else:
    print("❌ パターン不一致")

with open(path, "w", encoding="utf-8") as f:
    f.write(src)

# line_query も同期
path2 = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_query\line_query.py"
with open(path2, "r", encoding="utf-8") as f:
    s2 = f.read()
if OLD in s2:
    s2 = s2.replace(OLD, NEW, 1)
    print("✅ line_query/line_query.py 同期OK")
with open(path2, "w", encoding="utf-8") as f:
    f.write(s2)

for p in [path, path2]:
    r = subprocess.run(["python", "-m", "py_compile", p], capture_output=True, text=True)
    fname = "/".join(p.split("\\")[-2:])
    print(f"{'✅' if r.returncode == 0 else '❌'} {fname}: 構文{'OK' if r.returncode == 0 else r.stderr}")
