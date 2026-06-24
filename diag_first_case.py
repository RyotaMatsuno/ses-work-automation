import json

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_results.jsonl"
lines = open(path, encoding="utf-8").readlines()
print(f"Total lines: {len(lines)}")

# 最初の1ケースを詳細に見る
d = json.loads(lines[0])
print(f"\ncase_id: {d['case_id']}")
print(f"results count: {len(d.get('results', []))}")
for r in d.get("results", [])[:5]:
    print(f"  verdict={r['verdict']} reasons={r['reasons']}")
