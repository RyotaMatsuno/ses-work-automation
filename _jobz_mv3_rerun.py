import os
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = Path(os.getcwd())
python = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"
today = date.today().strftime("%Y%m%d")

# lockファイル削除
lock = SES / "matching_v3" / "matching_v3.lock"
if lock.exists():
    lock.unlink()
    print(f"lockファイル削除: {lock.name}")

# ログクリア
mv3_log = SES / "matching_v3" / "logs" / f"matching_v3_{today}.log"
mv3_log.write_text("", encoding="utf-8")

print("■ matching_v3 再実行（最大120秒）")
r = subprocess.run(
    [python, "matching_v3.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=str(SES / "matching_v3"),
    timeout=120,
)
print(f"  returncode: {r.returncode}")

print(f"\n■ matching_v3_{today}.log 全内容")
with open(mv3_log, encoding="utf-8", errors="replace") as f:
    for line in f.readlines():
        tag = "[MV3]" if "flag_auto_updater" not in line and "httpx" not in line else "[FLG]"
        print(f"  {tag} {line.rstrip()}")

if r.stderr:
    print(f"\n  stderr: {r.stderr[:300]}")
