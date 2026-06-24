import json
from collections import Counter

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_results.jsonl"

total_pairs = 0
verdict_counter = Counter()
reason_counter = Counter()
review_reasons = []

with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        for r in d.get("results", []):
            verdict = str(r.get("verdict", "")).upper()
            verdict_counter[verdict] += 1
            total_pairs += 1

            # REVIEW/NGの理由を収集
            reason = r.get("reason", r.get("ng_reason", r.get("review_reason", "")))
            if reason and verdict in ("REVIEW", "NG"):
                reason_counter[str(reason)[:80]] += 1
                if len(review_reasons) < 5:
                    review_reasons.append(
                        {"verdict": verdict, "engineer": r.get("engineer_initial", ""), "reason": str(reason)[:150]}
                    )

case_count = 0
with open(path, encoding="utf-8") as f:
    for line in f:
        if line.strip():
            case_count += 1

print("=== Phase 0 集計結果 ===")
print(f"案件数: {case_count}")
print(f"総ペア数: {total_pairs}")
print(f"案件あたり平均: {total_pairs / case_count:.1f}件" if case_count else "")
print()
for k in ["MATCH", "REVIEW", "NG"]:
    cnt = verdict_counter.get(k, 0)
    pct = f"{cnt / total_pairs * 100:.1f}%" if total_pairs else "-"
    print(f"  {k}: {cnt} ({pct})")
other_keys = [k for k in verdict_counter if k not in ("MATCH", "REVIEW", "NG")]
for k in other_keys:
    print(f"  {k}: {verdict_counter[k]}")

print("\n=== REVIEW/NG 理由 TOP10 ===")
for reason, cnt in reason_counter.most_common(10):
    print(f"  [{cnt}] {reason}")

print("\n=== REVIEW サンプル5件 ===")
for s in review_reasons:
    print(f"  [{s['verdict']}] {s['engineer']}: {s['reason']}")
