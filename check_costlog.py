import json
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

cost_log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl")
print(f"存在: {cost_log.exists()}")
if cost_log.exists():
    today = date.today().isoformat()
    entries = []
    with open(cost_log, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except:
                pass
    print(f"総エントリ数: {len(entries)}")
    today_entries = [e for e in entries if e.get("date") == today]
    print(f"今日({today})のエントリ数: {len(today_entries)}")
    if entries:
        print("\n直近3件:")
        for e in entries[-3:]:
            print(f"  {e}")
    if today_entries:
        total = sum(e.get("cost_usd", 0) for e in today_entries)
        print(f"\n今日の累計: ${total:.4f}")
    else:
        print("\n今日の記録なし → cost_guardが0.0を返す（正常動作するがガード値が低め）")
        print("→ 問題なし: $0.0 < $2.0 なのでAPIコールは通る。課金が進んだらガードが効く。")
