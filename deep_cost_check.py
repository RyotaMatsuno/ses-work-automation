# -*- coding: utf-8 -*-
# 多角的コスト調査: ledger正本 + cost_log + Anthropic API残高チェック
import json
import sys
from collections import defaultdict
from datetime import timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

JST = timezone(timedelta(hours=9))

# === 1. ledger正本（AppData）===
state = Path(r"C:\Users\ma_py\AppData\Local\ses_work_state\cost_state.json")
print("=== ledger正本 (cost_state.json) ===")
if state.exists():
    s = json.loads(state.read_text(encoding="utf-8"))
    print(f"  日次: ${s.get('daily_usd', 0):.4f} / $8.00")
    print(f"  月次: ${s.get('monthly_usd', 0):.4f} / $140.00")
    print(f"  日付: {s.get('date')}")
    print(f"  月: {s.get('month')}")

# === 2. cost_log.jsonl の全期間集計 ===
cost_log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl")
print("\n=== cost_log.jsonl 全期間集計 ===")
daily_costs = defaultdict(float)
daily_calls = defaultdict(int)
script_total = defaultdict(float)
with cost_log.open(encoding="utf-8", errors="replace") as f:
    for line in f:
        try:
            e = json.loads(line)
            day = e.get("ts", "")[:10]
            cost = e.get("cost_usd", 0)
            daily_costs[day] += cost
            daily_calls[day] += 1
            script_total[e.get("script", "?")] += cost
        except:
            pass

print("日別コスト:")
for day in sorted(daily_costs.keys()):
    flag = "⚠️ $8超" if daily_costs[day] > 8 else ""
    print(f"  {day}: ${daily_costs[day]:.4f} ({daily_calls[day]}コール) {flag}")

month_sum = defaultdict(float)
for day, cost in daily_costs.items():
    month_sum[day[:7]] += cost
print("\n月別コスト:")
for month in sorted(month_sum.keys()):
    flag = "⚠️ $140超" if month_sum[month] > 140 else ""
    print(f"  {month}: ${month_sum[month]:.4f} {flag}")

print("\nスクリプト別累計:")
for k, v in sorted(script_total.items(), key=lambda x: -x[1])[:10]:
    print(f"  {k}: ${v:.4f}")

# === 3. Anthropic Spending Limit確認 ===
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
import requests as req

headers = {"x-api-key": env.get("ANTHROPIC_API_KEY", ""), "anthropic-version": "2023-06-01"}

print("\n=== Anthropic API 残高・制限確認 ===")
# Workspaceの利用状況
endpoints = [
    "https://api.anthropic.com/v1/usage",
    "https://api.anthropic.com/v1/organizations",
]
for url in endpoints:
    try:
        r = req.get(url, headers=headers, timeout=10)
        print(f"  {url}: {r.status_code} {r.text[:200]}")
    except Exception as e:
        print(f"  {url}: エラー {e}")
