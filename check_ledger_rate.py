# -*- coding: utf-8 -*-
# ledger.pyのコスト計算ロジックと実際のトークン使用量を確認
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ledger.pyのレート設定を確認
ledger = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\common\ledger.py")
if ledger.exists():
    content = ledger.read_text(encoding="utf-8", errors="replace")
    # レート定義部分を抽出
    for i, line in enumerate(content.splitlines(), 1):
        if any(
            k in line
            for k in [
                "rate",
                "RATE",
                "price",
                "PRICE",
                "cost",
                "COST",
                "1_000_000",
                "1000000",
                "input",
                "output",
                "haiku",
                "sonnet",
            ]
        ):
            if any(k in line for k in ["=", "*", "/", "rate", "price", "3.0", "15.0", "1.0", "5.0", "0.25", "0.8"]):
                print(f"L{i}: {line.strip()[:100]}")

# 実際のトークン使用量を集計（今日）
print("\n=== 今日の実トークン使用量 ===")
cost_log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl")
JST = timezone(timedelta(hours=9))
today = datetime.now(JST).strftime("%Y-%m-%d")

total_in = total_out = total_cached = 0
by_model = defaultdict(lambda: {"in": 0, "out": 0, "cached": 0, "cost": 0, "calls": 0})

with cost_log.open(encoding="utf-8", errors="replace") as f:
    for line in f:
        try:
            e = json.loads(line)
            if e.get("ts", "").startswith(today):
                model = e.get("model", "?")
                in_tok = e.get("input_tokens", 0)
                out_tok = e.get("output_tokens", 0)
                cached = e.get("cached_tokens", 0)
                cost = e.get("cost_usd", 0)
                total_in += in_tok
                total_out += out_tok
                total_cached += cached
                by_model[model]["in"] += in_tok
                by_model[model]["out"] += out_tok
                by_model[model]["cached"] += cached
                by_model[model]["cost"] += cost
                by_model[model]["calls"] += 1
        except:
            pass

print(f"総入力トークン: {total_in:,}")
print(f"総出力トークン: {total_out:,}")
print(f"総キャッシュトークン: {total_cached:,}")

print("\nモデル別:")
for model, d in sorted(by_model.items(), key=lambda x: -x[1]["cost"]):
    print(f"  {model}:")
    print(f"    入力{d['in']:,} / 出力{d['out']:,} / キャッシュ{d['cached']:,}")
    print(f"    コスト${d['cost']:.4f} / {d['calls']}コール")

# 実際のhaikuレートで再計算
# claude-haiku-4-5: input $1/M, output $5/M
print("\n=== haiku 4.5 公式レートで再計算 ===")
haiku_in_rate = 1.0  # per million
haiku_out_rate = 5.0
recalc = (total_in * haiku_in_rate + total_out * haiku_out_rate) / 1_000_000
print(f"  再計算コスト: ${recalc:.4f}")
print(f"  ledger記録: ${sum(d['cost'] for d in by_model.values()):.4f}")
