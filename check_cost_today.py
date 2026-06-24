# -*- coding: utf-8 -*-
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1. common/ledger 正本
state_path = Path(r"C:\Users\ma_py\AppData\Local\ses_work_state\cost_state.json")
print("=== common/ledger 正本 ===")
if state_path.exists():
    s = json.loads(state_path.read_text(encoding="utf-8"))
    print(f"  日次累計: ${s.get('daily_usd', 0):.4f} / $8.00")
    print(f"  月次累計: ${s.get('monthly_usd', 0):.4f} / $140.00")
    print(f"  日次コール: {s.get('daily_calls', 0)}回")
    print(f"  日付: {s.get('date')}")

# 2. 今日のcost_log詳細
cost_log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl")
print("\n=== 今日のAPI呼び出し明細（cost_log.jsonl）===")
if cost_log.exists():
    today = datetime.now().strftime("%Y-%m-%d")
    entries = []
    with cost_log.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                e = json.loads(line)
                if e.get("ts", "").startswith(today):
                    entries.append(e)
            except Exception:
                pass
    by_script = {}
    for e in entries:
        k = f"{e.get('script', '?')}({e.get('model', '?').split('-')[0]})"
        by_script[k] = by_script.get(k, 0) + e.get("cost_usd", 0)
    total = sum(by_script.values())
    for k, v in sorted(by_script.items(), key=lambda x: -x[1]):
        print(f"  {k}: ${v:.4f}")
    print(f"  合計: ${total:.4f}")
    print(f"  今日の呼び出し件数: {len(entries)}件")
else:
    print("  cost_log.jsonl が見つかりません")

# 3. gate_checker独自カウンター
gate_counter = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\gate_checker\results\daily_counter.json")
print("\n=== gate_checker 日次カウンター ===")
if gate_counter.exists():
    g = json.loads(gate_counter.read_text(encoding="utf-8"))
    print(f"  日付: {g.get('date')} / 使用: {g.get('count', 0)}/10回")
else:
    print("  ファイルなし")
