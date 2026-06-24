# phase0_results.jsonl の最初と最後の数行のcase_idとtimestampを確認
import json

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_results.jsonl"

lines = []
with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            lines.append(line)

print(f"Total lines: {len(lines)}")
print()

# 最初の3件
print("=== 最初の3件 ===")
for line in lines[:3]:
    d = json.loads(line)
    first_result = d.get("results", [{}])[0]
    print(f"case_id: {d['case_id'][:16]}...")
    print(f"  verdict: {first_result.get('verdict')}")
    print(f"  reasons: {first_result.get('reasons')}")

print()
print("=== 最後の3件 ===")
for line in lines[-3:]:
    d = json.loads(line)
    first_result = d.get("results", [{}])[0]
    print(f"case_id: {d['case_id'][:16]}...")
    print(f"  verdict: {first_result.get('verdict')}")
    print(f"  reasons: {first_result.get('reasons')}")

# NGが存在するか確認
ng_count = 0
review_missing = 0
for line in lines:
    d = json.loads(line)
    for r in d.get("results", []):
        if r.get("verdict") == "NG":
            ng_count += 1
        if r.get("verdict") == "REVIEW":
            for reason in r.get("reasons", []):
                if "必須スキル不足" in reason:
                    review_missing += 1

print(f"\nNG件数: {ng_count}")
print(f"REVIEW+必須スキル不足: {review_missing}")
