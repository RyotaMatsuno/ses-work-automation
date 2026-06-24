import json
from collections import Counter
from pathlib import Path

result_path = Path("matching_v3/logs/phase0_results.jsonl")

verdicts = Counter()
review_reasons = Counter()

with result_path.open("r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        for r in obj.get("results", []):
            v = r.get("verdict", "?")
            verdicts[v] += 1
            if v == "REVIEW":
                for reason in r.get("reasons", []):
                    category = reason.split(":")[0].strip()
                    review_reasons[category] += 1

total = sum(verdicts.values())
print(f"総ペア数: {total}")
for v, cnt in verdicts.most_common():
    print(f"  {v}: {cnt} ({cnt / total * 100:.1f}%)")

print("\nREVIEW理由 上位:")
for reason, cnt in review_reasons.most_common(15):
    print(f"  {reason}: {cnt}")
