import json

# extraction_confidence = 0.0 の案件を抽出して、
# その案件本文をphase0_emails.jsonlから拾う

struct_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\structured.jsonl"
email_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_emails.jsonl"

# structured.jsonlの confidence 分布
conf_dist = {}
low_conf_cases = []
total = 0
with open(struct_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        c = d.get("extraction_confidence", -1)
        # 0.7未満をカウント
        bucket = round(c, 1)
        conf_dist[bucket] = conf_dist.get(bucket, 0) + 1
        total += 1
        if c < 0.7 and len(low_conf_cases) < 3:
            low_conf_cases.append(d["case_id"])

print("=== extraction_confidence 分布 ===")
for k in sorted(conf_dist.keys()):
    cnt = conf_dist[k]
    pct = f"{cnt / total * 100:.1f}%"
    print(f"  conf={k}: {cnt}件 ({pct})")
print(f"  合計: {total}件")
print(f"\n低信頼度（<0.7）案件数: {sum(v for k, v in conf_dist.items() if k < 0.7)}")

# 低信頼度案件の本文を確認
print("\n=== 低信頼度案件の本文サンプル（最初の1件）===")
if low_conf_cases:
    target_id = low_conf_cases[0]
    with open(email_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            if d.get("case_id") == target_id or d.get("id") == target_id:
                body = d.get("body", d.get("案件詳細", ""))
                print(f"  case_id: {target_id}")
                print(f"  本文（最初の300字）: {body[:300]}")
                break
