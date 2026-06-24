import json

struct_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\structured.jsonl"

# raw_important_notes が存在するレコードを確認（パース失敗の痕跡）
print("=== raw_important_notes の中身サンプル（最初の3件） ===")
count = 0
with open(struct_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        rn = d.get("raw_important_notes")
        if rn and count < 3:
            print(f"case_id: {d['case_id']}")
            print(f"  conf: {d.get('extraction_confidence')}")
            print(f"  raw_notes(最初300字): {str(rn)[:300]}")
            print()
            count += 1

# ログファイルでJSON parse failed のエラーを確認
log_path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\matching_v3_20260603.log"
print("=== ログ中のJSONエラー（最初の10件） ===")
count = 0
with open(log_path, encoding="utf-8", errors="replace") as f:
    for line in f:
        if "parse failed" in line or "JSON" in line:
            print(f"  {line.rstrip()}")
            count += 1
            if count >= 10:
                break
