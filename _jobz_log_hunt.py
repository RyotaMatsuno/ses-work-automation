import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

# 今日更新されたすべてのlogファイル
import datetime
import time

now = time.time()
print("■ 直近5分以内に更新されたlogファイル")
for root, dirs, files in os.walk(SES):
    dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", "node_modules"]]
    for fn in files:
        if fn.endswith(".log"):
            fp = os.path.join(root, fn)
            mtime = os.path.getmtime(fp)
            if now - mtime < 300:  # 5分以内
                sz = os.path.getsize(fp)
                rel = os.path.relpath(fp, SES)
                print(f"  {rel} ({sz}b) mtime={datetime.datetime.fromtimestamp(mtime)}")

# flag_updater の今日ログ
print("\n■ flag_updater_20260612.log 末尾20行")
fu_log = SES / "flag_auto_updater" / "logs" / "flag_updater_20260612.log"
if fu_log.exists():
    with open(fu_log, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    print(f"  総行数: {len(lines)}")
    for l in lines[-20:]:
        print("  " + l.rstrip())
else:
    print("  未存在")

# matching_v3本体ログの中身（force=True上書き後にどこに書かれているか）
print("\n■ matching_v3_20260612.log の状態")
mv3_log = SES / "matching_v3" / "logs" / "matching_v3_20260612.log"
print(f"  存在: {mv3_log.exists()}, サイズ: {mv3_log.stat().st_size if mv3_log.exists() else 'N/A'}")
