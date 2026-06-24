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
                    key = reason.split(":")[0].strip()
                    reason_counter[key] += 1

lines = []
lines.append(f"総ペア数: {total}")
for v, c in verdicts.most_common():
    lines.append(f"  {v}: {c} ({100 * c / total:.1f}%)")

lines.append("\nREVIEW理由トップ10:")
for reason, cnt in reason_counter.most_common(10):
    lines.append(f"  {cnt:5d}  {reason}")

with open("diag_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("done")
