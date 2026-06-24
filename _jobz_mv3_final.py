import os
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = Path(os.getcwd())
python = r"C:\Users\ma_py\AppData\Local\Programs\Python\Python312\python.exe"
today = date.today().strftime("%Y%m%d")

# ログファイルを一旦退避（クリーンな状態で確認）
mv3_log = SES / "matching_v3" / "logs" / f"matching_v3_{today}.log"
bak = SES / "matching_v3" / "logs" / f"matching_v3_{today}.log.bak"
if mv3_log.exists():
    mv3_log.rename(bak)
    print(f"バックアップ: {bak.name}")

# matching_v3 実行（バックグラウンド、120秒待機）
print("■ matching_v3 実行中（最大120秒）")
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

# ログ確認
print(f"\n■ matching_v3_{today}.log")
if mv3_log.exists():
    sz = mv3_log.stat().st_size
    print(f"  サイズ: {sz}b")
    with open(mv3_log, encoding="utf-8", errors="replace") as f:
        for line in f.readlines():
            tag = "[MV3]" if "flag_auto_updater" not in line and "httpx" not in line else "[FLG]"
            print(f"  {tag} {line.rstrip()}")
else:
    print("  ログファイル未生成")
    print(f"  stdout: {r.stdout[:500]}")
    print(f"  stderr: {r.stderr[:300]}")
