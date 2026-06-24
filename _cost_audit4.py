import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import timedelta, timezone

JST = timezone(timedelta(hours=9))

print("=" * 60)
print("【5】問題点の完全列挙と影響範囲")
print("=" * 60)

# ledger.pyのデフォルト値
print("""
🚨 問題①: common/ledger.py のデフォルト値が危険
  DAILY_HARD_USD  = _float_env("COST_GUARD_DAILY_USD",  1.0)  ← .envに値がなければ$1
  MONTHLY_USD     = _float_env("COST_GUARD_MONTHLY_USD", 6.0)  ← .envに値がなければ$6
  
  現状: .envには正しく COST_GUARD_DAILY_USD=8.0 が設定されているためOK
  リスク: .envが読まれない場合（Cloud Run・subprocess起動等）はデフォルト$1/$6で動作する
""")

# cost_guard.pyのハードコード
print("""🚨 問題②: cost_guard.py の上限値がハードコードで.envと完全に別管理
  SOFT_DAILY_LIMIT = 0.8   ← 独自の小さな値
  HARD_DAILY_LIMIT = 1.5   ← $1.5で発動（.envの$8と無関係）
  MONTHLY_LIMIT    = 6.0   ← $6で発動（.envの$140と無関係）
  
  つまり: cost_guard.py は "日次$1.5 / 月次$6" で発動する別システム
  影響範囲: cost_guard.py を呼ぶ usage_tracker_daily / Cloud Run停止処理
""")

# ledger.pyが.envを読む仕組みを確認
with open("common/ledger.py", encoding="utf-8") as f:
    ledger = f.read()

print("  common/ledger.py の.env読み込み実装:")
for i, line in enumerate(ledger.split("\n"), 1):
    if "_ENV" in line or "load" in line.lower() or ".env" in line:
        print(f"    L{i}: {line.strip()[:120]}")

# STATE_FILEのパスが正しいか
print()
import re

m = re.search(r"STATE_FILE\s*=.*", ledger)
if m:
    print(f"  STATE_FILE定義: {m.group()}")
    # 実際のパスを評価
    appdata = os.environ.get("APPDATA", "")
    state_path = os.path.join(os.path.dirname(appdata), "Local", "ses_work_state", "cost_state.json")
    print(f"  実パス評価: {state_path}")
    print(f"  存在確認: {'✅ あり' if os.path.exists(state_path) else '❌ なし'}")

# common/cost_state.json
print()
if os.path.exists("common/cost_state.json"):
    with open("common/cost_state.json", encoding="utf-8") as f:
        import json

        state = json.load(f)
    print(f"  common/cost_state.json: {json.dumps(state, ensure_ascii=False)}")
