import json
from collections import Counter

path = r"matching_v3\logs\phase0_results.jsonl"
verdicts = Counter()
reason_counter = Counter()
total = 0

with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        for r in obj.get("results", []):
            v = r.get("verdict", "?")
            verdicts[v] += 1
            total += 1
            if v == "REVIEW":
                for reason in r.get("reasons", []):
                    # 理由の先頭部分だけ取る
                    key = reason.split(":")[0].strip()
                    reason_counter[key] += 1

print(f"総ペア数: {total}")
for v, c in verdicts.most_common():
    print(f"  {v}: {c} ({100 * c / total:.1f}%)")

print("\nREVIEW理由トップ10:")
for reason, cnt in reason_counter.most_common(10):
    print(f"  {cnt:5d}  {reason}")
