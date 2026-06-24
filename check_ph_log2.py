# -*- coding: utf-8 -*-
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

log_dir = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs")
today_str = datetime.now().strftime("%Y%m%d")

# 今日のログを探す（matching_v3_YYYYMMDD.log形式）
today_logs = list(log_dir.glob(f"matching_v3_{today_str}*.log"))
all_logs = sorted(log_dir.glob("matching_v3_*.log"), reverse=True)

print(f"今日のログ: {[f.name for f in today_logs]}")
print(f"最新ログ: {[f.name for f in all_logs[:3]]}")

# 最新ログ全文からPH関連・除外関連を抽出
if all_logs:
    content = all_logs[0].read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    print(f"\n=== {all_logs[0].name} ({len(lines)}行) ===")

    # PH / stale / 除外 / filter 関連
    keywords = ["PH", "P.H", "stale", "鮮度", "fresh", "除外", "filter", "単価REVIEW", "マッチ案件なし"]
    relevant = [l for l in lines if any(k in l for k in keywords)]
    if relevant:
        print("【関連行】")
        for l in relevant[:30]:
            print(f"  {l}")
    else:
        print("PH関連の行なし")
        print("【直近30行】")
        for l in lines[-30:]:
            print(f"  {l}")
