import json
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1. 構文チェック
import py_compile

mp = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\mail_pipeline.py")
try:
    py_compile.compile(str(mp), doraise=True)
    print("構文チェック: OK")
except py_compile.PyCompileError as e:
    print(f"構文エラー: {e}")

# 2. get_today_cost_usd のロジックを直接シミュレーション
print("\n=== get_today_cost_usd シミュレーション ===")
cost_log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl")
today = date.today().isoformat()
total = 0.0
count = 0
with open(cost_log, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        entry_date = entry.get("date") or (entry.get("ts", "")[:10])
        if entry_date == today:
            total += entry.get("cost_usd", 0.0)
            count += 1

print(f"今日({today})のエントリ数: {count}")
print(f"今日の累計コスト: ${total:.4f}")
print("コストガード閾値: $2.0")
print(f"現在ガード発動?: {'YES → APIコールをスキップ' if total >= 2.0 else 'NO → APIコール正常'}")

# 3. 修正後のget_today_cost_usd関数を確認
print("\n=== 修正後コード確認 ===")
with open(mp, encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
for i, l in enumerate(lines, 1):
    if "def get_today_cost_usd" in l:
        for j, ll in enumerate(lines[i - 1 : i + 19], i):
            print(f"L{j}: {ll.rstrip()}")
        break
