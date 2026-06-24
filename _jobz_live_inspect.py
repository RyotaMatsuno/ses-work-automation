import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
mv3_dir = os.path.join(SES, "matching_v3")

# _run_live() 全体を確認
print("■ _run_live() 全内容")
with open(os.path.join(mv3_dir, "matching_v3.py"), encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

in_run_live = False
for i, line in enumerate(lines, 1):
    if "def _run_live(" in line:
        in_run_live = True
    if in_run_live:
        print(f"  L{i}: {line.rstrip()}")
    if in_run_live and i > 91 and line.strip().startswith("def ") and "_run_live" not in line:
        break

# LockFile 残留チェック
lock_path = os.path.join(mv3_dir, "matching_v3.lock")
print(f"\n■ ロックファイル確認: {lock_path}")
if os.path.exists(lock_path):
    import time

    age = (time.time() - os.path.getmtime(lock_path)) / 60
    print(f"  ⚠️ ロックファイル存在！ 経過: {age:.1f}分")
    print("  → 前回の実行が異常終了してロックが残っている可能性")
    print("  → 30分以上経過していれば次回実行時に自動奪取")
else:
    print("  ✅ ロックファイルなし（正常）")

# 今日のマッチングログを再確認
print("\n■ 今日のマッチングログ（最新）")
log_today = os.path.join(mv3_dir, "logs", "matching_v3_20260611.log")
if os.path.exists(log_today):
    sz = os.path.getsize(log_today)
    print(f"  サイズ: {sz} bytes")
    if sz > 0:
        with open(log_today, encoding="utf-8", errors="replace") as f:
            print(f.read())
    else:
        print("  まだ空（先ほどの手動実行は flag_auto_updaterのみでログ未出力）")
        print("  → _setup_logging()後にflag_auto_updaterが呼ばれるはずだが...")
        print("  → flag_auto_updaterのloggerが別ファイルに書いているか確認")

# flag_auto_updater の logging 設定確認
print("\n■ flag_auto_updater/run_flag_updater.py のlogging設定")
rfu = os.path.join(SES, "flag_auto_updater", "run_flag_updater.py")
with open(rfu, encoding="utf-8", errors="replace") as f:
    content = f.read()
print(content[:3000])
