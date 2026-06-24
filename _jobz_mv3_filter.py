import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
today = date.today().strftime("%Y%m%d")

# matching_v3 ログ全内容（flag_updater以外の行を抽出）
mv3_log = SES / "matching_v3" / "logs" / f"matching_v3_{today}.log"
print(f"■ matching_v3_{today}.log 全内容")
print(f"  サイズ: {mv3_log.stat().st_size}b")
with open(mv3_log, encoding="utf-8", errors="replace") as f:
    for line in f.readlines():
        # matching_v3自身のログを強調
        tag = "  [MV3] " if "flag_auto_updater" not in line and "httpx" not in line else "  [FLG] "
        print(tag + line.rstrip())
