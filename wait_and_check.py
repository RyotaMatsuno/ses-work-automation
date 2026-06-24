import json
import os
import time
from collections import Counter

time.sleep(120)

log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_fresh_run.log"
struct_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\structured.jsonl"
results_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_results.jsonl"

# structured件数
cnt = 0
if os.path.exists(struct_path):
    with open(struct_path, encoding="utf-8") as f:
        cnt = sum(1 for l in f if l.strip())

print(f"structured.jsonl: {cnt}件")

# results件数とverdict分布
if os.path.exists(results_path):
    verdicts = Counter()
    reason_counter = Counter()
    total = 0
    with open(results_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            for r in obj.get("results", []):
                v = r.get("verdict", "?")
                verdicts[v] += 1
                total += 1
                if v == "REVIEW":
                    for reason in r.get("reasons", []):
                        key = reason.split(":")[0].strip()
                        reason_counter[key] += 1
    print(f"\n総ペア数: {total}")
    for v, c in verdicts.most_common():
        print(f"  {v}: {c} ({100 * c / total:.1f}%)")
    print("\nREVIEW理由:")
    for r, c in reason_counter.most_common(10):
        print(f"  {c:5d}  {r}")
else:
    print("results.jsonl: 未作成")
