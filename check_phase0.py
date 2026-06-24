import json
import os

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\matching_v3"
log_dir = os.path.join(base, "logs")

print("=== logs/ 内ファイル一覧 ===")
if os.path.exists(log_dir):
    for f in sorted(os.listdir(log_dir)):
        size = os.path.getsize(os.path.join(log_dir, f))
        print(f"  {f}  ({size:,} bytes)")
else:
    print("  logs/ ディレクトリが存在しない")

# phase0_results.jsonl を探す
candidates = [
    os.path.join(log_dir, "phase0_results.jsonl"),
    os.path.join(base, "phase0_results.jsonl"),
]
for path in candidates:
    if os.path.exists(path):
        print(f"\n=== {path} ===")
        counts = {"MATCH": 0, "REVIEW": 0, "NG": 0, "OTHER": 0}
        total = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    v = str(d.get("verdict", d.get("result", ""))).upper()
                    if v in counts:
                        counts[v] += 1
                    else:
                        counts["OTHER"] += 1
                    total += 1
                except:
                    pass
        print(f"  Total: {total}")
        for k, v in counts.items():
            pct = f"{v / total * 100:.1f}%" if total else "-"
            print(f"  {k}: {v} ({pct})")
        break
else:
    print("\nphase0_results.jsonl が見つかりません")
