import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import timedelta, timezone

JST = timezone(timedelta(hours=9))
UTC = timezone.utc

print("=" * 60)
print("【2】CostGuard実装の正確性検証")
print("=" * 60)

# .envの値
env = {}
with open("config/.env", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")

daily_limit = float(env.get("COST_GUARD_DAILY_USD", 0))
monthly_limit = float(env.get("COST_GUARD_MONTHLY_USD", 0))
llm_kill = env.get("LLM_KILL", "0")
print(f"  .env COST_GUARD_DAILY_USD  : ${daily_limit}")
print(f"  .env COST_GUARD_MONTHLY_USD: ${monthly_limit}")
print(f"  .env LLM_KILL              : {llm_kill}")

if daily_limit != 8.0 or monthly_limit != 140.0:
    print("  ⚠️ 設定値が正しくない！")
else:
    print("  ✅ 設定値正常")

# cost_guard.pyが.envを正しく読んでいるか
print()
print("  cost_guard.py の定数確認:")
with open("cost_guard.py", encoding="utf-8") as f:
    cg = f.read()
for kw in ["DAILY", "MONTHLY", "LIMIT", "KILL", "LLM_KILL"]:
    for line in cg.split("\n"):
        if kw in line and ("=" in line or "environ" in line) and not line.strip().startswith("#"):
            print(f"    {line.strip()[:100]}")
            break

# mail_pipeline の ledger_can_spend実装確認
print()
print("  mail_pipeline ledger_can_spend確認:")
with open("mail_pipeline/mail_pipeline.py", encoding="utf-8") as f:
    mp = f.read()
for kw in ["ledger_can_spend", "DAILY_COST", "cost_limit", "get_today_cost"]:
    idx = mp.find(kw)
    if idx != -1:
        print(f"    [{kw}]: {mp[idx : idx + 150].split(chr(10))[0]}")

print()
print("=" * 60)
print("【3】各システムのCostGuard被覆確認")
print("=" * 60)

systems = {
    "mail_pipeline/mail_pipeline.py": ["call_claude", "ledger_can_spend", "cost_guard"],
    "matching_v3/matching_v3.py": ["CostGuard", "can_spend", "cost_guard"],
    "line_webhook/line_bridge.py": ["cost_guard_can_call", "guarded_anthropic_call"],
    "task_auto_runner/claude_invoker.py": ["max-budget-usd", "max_budget"],
    "gate_checker/gate_check.py": ["cost", "limit"],
}

for filepath, keywords in systems.items():
    if not os.path.exists(filepath):
        print(f"  ❓ {filepath}: ファイルなし")
        continue
    with open(filepath, encoding="utf-8", errors="replace") as f:
        content = f.read()
    hits = [kw for kw in keywords if kw in content]
    status = "✅" if hits else "❌ CostGuardなし！"
    print(f"  {status} {filepath}")
    if not hits:
        print(f"       → キーワード未検出: {keywords}")
