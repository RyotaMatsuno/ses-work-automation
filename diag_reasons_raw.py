import json

path = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3\logs\phase0_results.jsonl"

# REVIEW理由のサンプルを10件出力（文字列そのまま）
samples = []
with open(path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        for r in d.get("results", []):
            if r.get("verdict") == "REVIEW":
                for reason in r.get("reasons", []):
                    samples.append(reason)
                    if len(samples) >= 20:
                        break
        if len(samples) >= 20:
            break

print("=== REVIEW reasons サンプル (raw) ===")
for s in samples:
    print(repr(s))
