import json

with open("matching_v2/result.json", "r", encoding="utf-8") as f:
    data = json.load(f)

total = len(data)
with_candidates = [d for d in data if d.get("candidates") and len(d["candidates"]) > 0]
empty = total - len(with_candidates)

print("=== matching result.json analysis ===")
print(f"Total projects: {total}")
print(f"With candidates: {len(with_candidates)}")
print(f"No candidates: {empty}")

# candidate count distribution
from collections import Counter

counts = Counter()
for d in with_candidates:
    counts[len(d["candidates"])] += 1
print("\nCandidate count distribution:")
for k in sorted(counts.keys()):
    print(f"  {k} candidates: {counts[k]} projects")

# Check skill empty projects
skill_empty = [d for d in data if not d.get("raw_body") or len(str(d.get("raw_body", "")).strip()) < 10]
print(f"\nraw_body empty/short: {len(skill_empty)}/{total}")

# Sample a project with candidates
if with_candidates:
    sample = with_candidates[0]
    print("\n=== Sample project ===")
    print(f"Name: {sample['project_name']}")
    print(f"Budget: {sample.get('budget')}")
    print(f"Candidates: {len(sample['candidates'])}")
    for c in sample["candidates"][:3]:
        print(f"  - {c.get('engineer_name', '?')}: score={c.get('score', '?')}, gross={c.get('gross_profit', '?')}")
