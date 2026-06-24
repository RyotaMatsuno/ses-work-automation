import json

# 6/3の1件あたりのコスト内訳を確認
current_log = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\usage_tracker\cost_log.jsonl"

records = []
with open(current_log, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            if "2026-06-03" in r.get("ts", ""):
                records.append(r)
        except:
            pass

print(f"総レコード数: {len(records)}")

# スクリプト別の平均コスト・トークン
from collections import defaultdict

script_cost = defaultdict(float)
script_count = defaultdict(int)
script_input = defaultdict(int)
script_output = defaultdict(int)

for r in records:
    s = r.get("script", "unknown")
    script_cost[s] += float(r.get("cost_usd", 0) or 0)
    script_count[s] += 1
    script_input[s] += int(r.get("input_tokens", 0) or 0)
    script_output[s] += int(r.get("output_tokens", 0) or 0)

for s in sorted(script_cost, key=lambda x: -script_cost[x]):
    cnt = script_count[s]
    avg = script_cost[s] / cnt if cnt else 0
    avg_in = script_input[s] // cnt if cnt else 0
    avg_out = script_output[s] // cnt if cnt else 0
    print(f"\n{s}:")
    print(f"  呼び出し回数: {cnt}")
    print(f"  合計コスト: ${script_cost[s]:.4f}")
    print(f"  1回あたり: ${avg:.5f} (in:{avg_in}tok / out:{avg_out}tok)")
