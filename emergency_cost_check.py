# -*- coding: utf-8 -*-
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

JST = timezone(timedelta(hours=9))
cost_log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl")

# 今月の日別コスト（6月）
daily = defaultdict(float)
with cost_log.open(encoding="utf-8", errors="replace") as f:
    for line in f:
        try:
            e = json.loads(line)
            ts = e.get("ts", "")
            if ts.startswith("2026-06"):
                daily[ts[:10]] += e.get("cost_usd", 0)
        except:
            pass

june_total = sum(daily.values())
print("=== 6月の日別コスト（ledger記録） ===")
for d in sorted(daily):
    print(f"  {d}: ${daily[d]:.4f}")
print(f"\nledger累計: ${june_total:.4f}")

# Anthropic実績から逆算
# Console表示: $225.38使用済み（月次上限$250）
# ledger記録: $8.68
# → 差額: $225.38 - $8.68 = $216.70
# これはclaude.ai本体（ジョブズとの会話）のコストが含まれている！

anthropic_total = 225.38
api_only = june_total  # API経由のみ
claude_ai_cost = anthropic_total - api_only

print("\n=== Anthropic Console vs ledger の差異分析 ===")
print(f"Anthropic Console表示: ${anthropic_total:.2f}")
print(f"ledger記録（API自動処理）: ${api_only:.2f}")
print(f"差額（Claude.ai利用コスト推定）: ${claude_ai_cost:.2f}")
print()
print("月次上限: $250")
print(f"残り使用可能: ${250 - anthropic_total:.2f}")
print(f"残日数（7/1まで）: {(datetime(2026, 7, 1, tzinfo=JST) - datetime.now(JST)).days}日")

# 残り日数で使えるコスト/日
remaining_days = (datetime(2026, 7, 1, tzinfo=JST) - datetime.now(JST)).days
remaining_budget = 250 - anthropic_total
daily_budget = remaining_budget / max(remaining_days, 1)
print(f"1日あたり使えるコスト: ${daily_budget:.2f}")
print()

# API自動処理の今日のペース
today = datetime.now(JST).strftime("%Y-%m-%d")
today_api = daily.get(today, 0)
print(f"今日のAPI使用（ledger）: ${today_api:.4f}")

# Claude.ai（ジョブズとの会話）のコストも含めると
# 今日のトータルはもっと高い可能性
print()
print("=== 対策の緊急度 ===")
if daily_budget < 2.0:
    print("🚨 緊急: 1日あたり$2未満。API自動処理を大幅削減が必須")
elif daily_budget < 5.0:
    print("⚠️ 警告: 1日あたり$5未満。API処理を絞る必要あり")
else:
    print(f"余裕あり: 1日あたり${daily_budget:.2f}使える")
