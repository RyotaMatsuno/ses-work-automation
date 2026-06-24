import os
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = os.getcwd()
python = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"

# matching_v3 実行
print("■ matching_v3 実行（ログ確認用）")
r = subprocess.run(
    [python, "matching_v3.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=os.path.join(SES, "matching_v3"),
    timeout=120,
)
print(f"  returncode: {r.returncode}")

# matching_v3 ログ確認
from datetime import date

today = date.today().strftime("%Y%m%d")
mv3_log = Path(SES) / "matching_v3" / "logs" / f"matching_v3_{today}.log"
fu_log = Path(SES) / "flag_auto_updater" / "logs" / f"flag_updater_{today}.log"

print(f"\n■ matching_v3_{today}.log")
if mv3_log.exists():
    sz = mv3_log.stat().st_size
    print(f"  サイズ: {sz}b")
    if sz > 0:
        with open(mv3_log, encoding="utf-8", errors="replace") as f:
            for l in f.readlines()[-30:]:
                print("  " + l.rstrip())
    else:
        print("  まだ空")
else:
    print("  未存在")

print(f"\n■ flag_updater_{today}.log")
if fu_log.exists():
    sz = fu_log.stat().st_size
    print(f"  サイズ: {sz}b")
    if sz > 0:
        with open(fu_log, encoding="utf-8", errors="replace") as f:
            for l in f.readlines()[-10:]:
                print("  " + l.rstrip())
else:
    print("  未存在")

# 単独実行テスト
print("\n■ flag_auto_updater 単独実行テスト")
r2 = subprocess.run(
    [python, "-m", "flag_auto_updater.run_flag_updater"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=SES,
    timeout=120,
)
print(f"  returncode: {r2.returncode}")
print("  stdout末尾3行:")
for l in r2.stdout.strip().split("\n")[-3:]:
    print(f"  {l}")
