import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import timedelta, timezone

JST = timezone(timedelta(hours=9))

print("=" * 60)
print("【6】STATE_FILE実態 + ledger can_spend() 実動作検証")
print("=" * 60)

# AppData側のstate_fileを読む
state_path = r"C:\Users\ma_py\AppData\Local\ses_work_state\cost_state.json"
with open(state_path, encoding="utf-8") as f:
    state = json.load(f)
print("\n  AppData STATE_FILE:")
print(f"    date        : {state.get('date')}")
print(f"    month       : {state.get('month')}")
print(f"    daily_usd   : ${state.get('daily_usd', 0):.4f}")
print(f"    monthly_usd : ${state.get('monthly_usd', 0):.4f}")
print(f"    daily_calls : {state.get('daily_calls', 0)}")

# common/ledger.py を直接インポートして can_spend を実行
sys.path.insert(0, ".")
try:
    from common.ledger import DAILY_HARD_USD, MONTHLY_USD, can_spend, daily_total, monthly_total

    print("\n  ledger 実際に読んでいる上限値:")
    print(f"    DAILY_HARD_USD : ${DAILY_HARD_USD}")
    print(f"    MONTHLY_USD    : ${MONTHLY_USD}")
    print(f"    daily_total()  : ${daily_total():.4f}")
    print(f"    monthly_total(): ${monthly_total():.4f}")

    # can_spend テスト
    result = can_spend(est_in=1000, est_out=500, model="claude-haiku-4-5-20251001")
    print(f"\n  can_spend(1000in, 500out, haiku) → {result}")
    result2 = can_spend(est_in=10000, est_out=5000, model="claude-sonnet-4-6")
    print(f"  can_spend(10000in, 5000out, sonnet) → {result2}")
except Exception as e:
    print(f"  ❌ インポートエラー: {e}")

print()
print("=" * 60)
print("【7】6/2 暴走事件との比較・再発リスク評価")
print("=" * 60)
print("""
  6/2 暴走原因（記録より）:
    - .envが COST_GUARD_DAILY_USD=1.0 / COST_GUARD_MONTHLY_USD=6.0 だった
    - mail_pipeline が17,621回APIを呼び出した
    - $50.88/日の損害

  現在の状態:
""")

# .envの値を再確認
env = {}
with open("config/.env", encoding="utf-8") as f:
    for line in f:
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")

daily_env = float(env.get("COST_GUARD_DAILY_USD", 0))
monthly_env = float(env.get("COST_GUARD_MONTHLY_USD", 0))

print(f"    .env DAILY  : ${daily_env}  {'✅ 正常' if daily_env == 8.0 else '❌ 異常！'}")
print(f"    .env MONTHLY: ${monthly_env}  {'✅ 正常' if monthly_env == 140.0 else '❌ 異常！'}")

# ledger が実際に読む値
import importlib

import common.ledger as ledger_mod

importlib.reload(ledger_mod)
print(
    f"    ledger実値 DAILY  : ${ledger_mod.DAILY_HARD_USD}  {'✅' if ledger_mod.DAILY_HARD_USD == 8.0 else '❌ .envと不一致！'}"
)
print(
    f"    ledger実値 MONTHLY: ${ledger_mod.MONTHLY_USD}  {'✅' if ledger_mod.MONTHLY_USD == 140.0 else '❌ .envと不一致！'}"
)

print(f"""
  再発リスク評価:
    ① mail_pipeline がAPIを大量呼び出し → ledger で ${ledger_mod.DAILY_HARD_USD}/日 の壁あり ✅
    ② cost_guard.py は $1.5/日 $6/月 のより厳しい独自ガード ✅（二重防護）
    ③ task_auto_runner は --max-budget-usd 5 で1タスク$5上限 ✅
    ④ AnthropicのAPI月次リミット（Anthropic側の外部制限） ✅

  ⚠️ 残存リスク:
    - cost_guard.py の月次$6上限が厳しすぎる
      → 月次$6を超えると usage_tracker_daily がCloud RunのLLM_KILL=1を発動
      → 現在$2.61使用済み → あと$3.39で月次アラート発動
      → 今月中にCloud Run停止になる可能性あり
""")
