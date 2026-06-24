import json

with open("matching_v2/result.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total records: {len(data)}")
first = data[0]
print(f"Keys: {list(first.keys())}")
print(f"raw_body length: {len(first.get('raw_body', ''))}")
print(f"raw_body preview: {first.get('raw_body', '')[:200]}")

# candidatesも確認
cands = first.get("candidates", [])
if cands:
    print(f"Candidate keys: {list(cands[0].keys())}")
    print(f"Candidate raw_body: {cands[0].get('raw_body', '')[:100]}")
