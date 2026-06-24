import json

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_results.jsonl"
counts = {"MATCH": 0, "REVIEW": 0, "NG": 0}
review_reasons = {}
total_pairs = 0
total_cases = 0

with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        total_cases += 1
        for r in d.get("results", []):
            v = r.get("verdict", "").upper()
            counts[v] = counts.get(v, 0) + 1
            total_pairs += 1
            if v == "REVIEW":
                for reason in r.get("reasons", []):
                    # reasonsのキーを正規化
                    key = reason.split(":")[0].strip()
                    review_reasons[key] = review_reasons.get(key, 0) + 1

print("=== Phase 0 診断 ===")
print(f"案件数: {total_cases}")
print(f"総ペア数: {total_pairs}")
print(f"MATCH: {counts.get('MATCH', 0)} ({counts.get('MATCH', 0) / total_pairs * 100:.1f}%)")
print(f"REVIEW: {counts.get('REVIEW', 0)} ({counts.get('REVIEW', 0) / total_pairs * 100:.1f}%)")
print(f"NG: {counts.get('NG', 0)} ({counts.get('NG', 0) / total_pairs * 100:.1f}%)")
print()
print("=== REVIEW理由TOP10 ===")
for k, v in sorted(review_reasons.items(), key=lambda x: -x[1])[:10]:
    print(f"  {v}件: {k}")
