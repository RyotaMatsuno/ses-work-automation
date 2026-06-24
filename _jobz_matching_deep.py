import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()

# bat の実際のコマンドを分析
print("■ wd_matching_v3.bat のコマンド解析")
print("""
bat内容:
  python.exe weekday_guard.py python.exe matching_v3.py
  
  ↑ weekday_guard.py は sys.argv[1:] をそのまま subprocess.run() に渡す
  → ['python.exe', 'matching_v3.py'] を実行する
  → cwd が matching_v3/ に cd してあるので matching_v3/matching_v3.py を実行
  → ★ matching_v3.py は matching_v3/ 内にある → OK
  
  問題: bat が実行する weekday_guard.py は ses_work/weekday_guard.py
  → cwd は matching_v3/ に変更後
  → weekday_guard.py はパスが %~dp0weekday_guard.py = ses_work/weekday_guard.py → フルパス指定なので問題なし
""")

# matching_v3.py の logging 設定確認
print("\n■ matching_v3.py のlogging/ログファイル設定")
mv3py = os.path.join(SES, "matching_v3", "matching_v3.py")
with open(mv3py, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
for i, line in enumerate(lines, 1):
    if any(kw in line.lower() for kw in ["logging", "log_file", "filehandler", "basicconfig", "log_dir"]):
        print(f"  L{i}: {line.rstrip()}")

# matching_v3.py main() 関数部分
print("\n■ matching_v3.py 末尾100行（main処理確認）")
for l in lines[-100:]:
    print("  " + l.rstrip())

# タスクスケジューラの前回結果:1 の意味を確認
# 前回実行: 2026/06/11 18:07:50 → 結果:1
# ★ 18:07 は本日！スケジューラは動いていた
# 結果:1 = エラー終了
# weekday_guard.py の問題か、matching_v3.py 内のエラーか

# ログが空 → ログ設定前にクラッシュしている可能性
# 直接 matching_v3.py を --dry-run や引数なしで実行してエラー確認
print("\n■ matching_v3.py 直接実行（--help）")
python = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"
r = subprocess.run(
    [python, "matching_v3.py", "--help"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=os.path.join(SES, "matching_v3"),
    timeout=10,
)
print(f"  returncode: {r.returncode}")
print(f"  stdout: {r.stdout[:500]}")
print(f"  stderr: {r.stderr[:500]}")
