import sys
sys.stdout.reconfigure(encoding='utf-8')

# run_matching_and_notify.bat の内容確認
bat_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\run_matching_and_notify.bat"
import os
if os.path.exists(bat_path):
    with open(bat_path, encoding="utf-8", errors="replace") as f:
        print(f.read())
else:
    print("bat not found")

# 現在のタスク設定確認
import subprocess
r = subprocess.run(["schtasks", "/query", "/tn", "jobz_matching_daily", "/fo", "LIST", "/v"],
    capture_output=True, text=True, encoding="utf-8", errors="replace")
# スケジュール部分だけ抽出
for line in r.stdout.splitlines():
    if any(k in line for k in ["スケジュール", "Schedule", "繰り返し", "Repeat", "タスク名", "Task Name", "次回", "状態"]):
        print(line)
