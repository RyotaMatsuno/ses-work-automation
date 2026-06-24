import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()

# weekday_guard.py の場所を全探索
print("■ weekday_guard.py 全探索")
for root, dirs, files in os.walk(SES):
    dirs[:] = [d for d in dirs if d not in [".git", "__pycache__"]]
    for fn in files:
        if "weekday" in fn.lower() or (fn == "weekday_guard.py"):
            fp = os.path.join(root, fn)
            print(f"  発見: {os.path.relpath(fp, SES)}")
            with open(fp, encoding="utf-8", errors="replace") as f:
                print(f.read())

# matching_v3.py の場所も確認
print("\n■ matching_v3.py / run_matching.py 全探索")
for root, dirs, files in os.walk(SES):
    dirs[:] = [d for d in dirs if d not in [".git", "__pycache__"]]
    for fn in files:
        if fn in ["matching_v3.py", "run_matching.py", "__main__.py"]:
            fp = os.path.join(root, fn)
            print(f"  発見: {os.path.relpath(fp, SES)}")
            with open(fp, encoding="utf-8", errors="replace") as f:
                content = f.read()
            print(content[:500])
            print("  ...")

# matching_v3/ 内 __main__.py or __init__.py
print("\n■ matching_v3/ の全Pythonファイル")
mv3 = os.path.join(SES, "matching_v3")
for fn in sorted(os.listdir(mv3)):
    if fn.endswith(".py") or fn.endswith(".json") or fn.endswith(".md"):
        fp = os.path.join(mv3, fn)
        sz = os.path.getsize(fp)
        print(f"  {fn} ({sz}b)")

# bat が参照している matching_v3.py の実体
print("\n■ matching_v3/matching_v3.py の冒頭")
mv3py = os.path.join(SES, "matching_v3", "matching_v3.py")
if os.path.exists(mv3py):
    with open(mv3py, encoding="utf-8", errors="replace") as f:
        print(f.read()[:1000])
else:
    print("  未存在")

# logs/matching_v3_20260611.log が空の原因を推定
# → weekday_guard が今日を「非営業日」と判定したか確認
import datetime

today = datetime.date.today()
print(f"\n■ 本日の日付: {today} ({today.strftime('%A')})")
print("  木曜日（営業日）なので weekday_guard は通過するはず")
print("  → 空ログ = weekday_guard は通過したが何か別の原因でmatchingが出力なし")
print("  → または weekday_guard がログファイル自体を出力していない")
