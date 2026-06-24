import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
python = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"

# matching_v3 の案件取得・マッチング結果が stdout に出るか確認
print("■ matching_v3 stdout直接確認（30秒）")
r = subprocess.run(
    [python, "matching_v3.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=os.path.join(SES, "matching_v3"),
    timeout=30,
)
print(f"  returncode: {r.returncode}")
print(f"  stdout ({len(r.stdout)}文字):")
# matching_v3自身のログを抽出（flag_updater以外）
for line in r.stdout.split("\n"):
    if line and "flag_auto_updater" not in line and "httpx" not in line:
        print(f"  {line}")
print(f"  stderr: {r.stderr[:200]}")
