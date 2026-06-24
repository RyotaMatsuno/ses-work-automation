import os
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
python = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"
mv3_dir = os.path.join(SES, "matching_v3")

print("■ matching_v3.py 直接実行（本番モード）- 30秒待機")
print("  ※ 実際のNotionアクセスとマッチング処理を実行します")

r = subprocess.run(
    [python, "matching_v3.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=mv3_dir,
    timeout=60,
)
print(f"\n  returncode: {r.returncode}")
print(f"\n  stdout ({len(r.stdout)}文字):")
print(r.stdout[:3000])
print(f"\n  stderr ({len(r.stderr)}文字):")
print(r.stderr[:2000])
