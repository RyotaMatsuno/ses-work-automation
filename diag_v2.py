import json
import os
from collections import Counter

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs"
struct_path = os.path.join(base, "structured.jsonl")
result_path = os.path.join(base, "phase0_results.jsonl")

# === 1. extraction_confidence 分布 ===
conf_dist = Counter()
low_conf = []
total = 0
with open(struct_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        c = round(float(d.get("extraction_confidence", -1)), 1)
        conf_dist[c] += 1
        total += 1
        if c < 0.7 and len(low_conf) < 2:
            low_conf.append(d)

print(f"=== structured.jsonl: extraction_confidence 分布 ({total}件) ===")
for k in sorted(conf_dist.keys()):
    cnt = conf_dist[k]
    pct = f"{cnt / total * 100:.1f}%"
    print(f"  conf={k}: {cnt}件 ({pct})")
print(f"低信頼度(<0.7)案件: {sum(v for k, v in conf_dist.items() if k < 0.7)}")

# === 2. REVIEW の理由分布 ===
print("\n=== REVIEW 理由分布 TOP10 ===")
reason_counter = Counter()
with open(result_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        for r in d.get("results", []):
            for reason in r.get("reasons", []):
                # reasonを短く正規化してカウント
                key = str(reason)[:60]
                reason_counter[key] += 1

for reason, cnt in reason_counter.most_common(10):
    print(f"  [{cnt:5d}] {reason}")

# === 3. 信頼度0.0の案件サンプル ===
if low_conf:
    print("\n=== 低信頼度案件サンプル ===")
    d = low_conf[0]
    print(f"  case_id: {d.get('case_id', '')}")
    print(f"  conf: {d.get('extraction_confidence')}")
    rn = d.get("raw_important_notes", "")
    print(f"  raw_notes: {str(rn)[:200]}")
