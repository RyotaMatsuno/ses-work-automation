import json

with open("matching_v2/result.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Score distribution
from collections import Counter

scores = Counter()
for d in data:
    for c in d.get("candidates", []):
        s = c.get("score")
        scores[s] = scores.get(s, 0) + 1

print("=== Score distribution ===")
for k in sorted(scores.keys(), key=lambda x: str(x)):
    print(f"  score={k}: {scores[k]} candidates")

# Check gross_profit
gp_values = set()
for d in data:
    for c in d.get("candidates", []):
        gp_values.add(str(c.get("gross_profit", "MISSING")))
print(f"\ngross_profit values: {gp_values}")

# Check a project with 349 candidates - what skills does it have?
big = [d for d in data if len(d.get("candidates", [])) == 349]
if big:
    p = big[0]
    print("\n=== 349-candidate project ===")
    print(f"Name: {p['project_name']}")
    body = str(p.get("raw_body", ""))[:500]
    print(f"Body (first 500): {body}")

# Check a project with 0 candidates
empty = [d for d in data if len(d.get("candidates", [])) == 0]
if empty:
    p = empty[0]
    print("\n=== 0-candidate project ===")
    print(f"Name: {p['project_name']}")
    body = str(p.get("raw_body", ""))[:500]
    print(f"Body (first 500): {body}")
